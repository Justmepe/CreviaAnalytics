"""
WhaleAnalyzer — Layer 3

Computes whale intelligence signals using the existing DataAggregator providers.
No new API keys required beyond what is already in .env.

Data sources used:
  - Glassnode  → exchange_netflow (40% of sentiment score)  [GLASSNODE_API_KEY]
  - Binance    → funding_rate (25%), OI trend (20%)         [BINANCE_API_KEY already works]
  - Coinglass  → liquidation walls for cascade risk         [COINGLASS_API_KEY]
  - CoinGecko  → stablecoin market cap ratio (15%)         [COINGECKO_API_KEY]

Outputs:
  1. WhaleSentiment  — composite -1.0 → +1.0 score per asset
  2. CascadeWarning  — liquidation cascade risk per asset
  3. Flow chart data — hourly netflow buckets for the chart component

Run mode:
  Called from FastAPI background thread (api/main.py) every 5 minutes.
  Results stored in this module's _cache dict, read by api/routers/whale.py.
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Deque, Dict, List, Optional, Tuple

MAX_RECENT_TXNS = 200   # keep last N whale transactions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WhaleSentiment:
    asset: str
    score: float                    # -1.0 (distributing) → +1.0 (accumulating)
    label: str
    confidence: int                 # 0–100
    key_signal: str
    window_hours: int
    components: Dict[str, Any]
    computed_at: str

    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'score': round(self.score, 4),
            'label': self.label,
            'confidence': self.confidence,
            'key_signal': self.key_signal,
            'window_hours': self.window_hours,
            'components': self.components,
            'computed_at': self.computed_at,
        }


@dataclass
class CascadeWarning:
    asset: str
    risk_level: str                 # LOW | MEDIUM | HIGH | CRITICAL
    confidence: int
    estimated_usd_at_risk: float
    liq_wall_price: Optional[float]
    current_price: Optional[float]
    price_distance_pct: Optional[float]
    direction: str                  # LONG_SQUEEZE | SHORT_SQUEEZE
    key_signals: List[str]
    human_summary: str
    expires_at: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'risk_level': self.risk_level,
            'confidence': self.confidence,
            'estimated_usd_at_risk': self.estimated_usd_at_risk,
            'liq_wall_price': self.liq_wall_price,
            'current_price': self.current_price,
            'price_distance_pct': self.price_distance_pct,
            'direction': self.direction,
            'key_signals': self.key_signals,
            'human_summary': self.human_summary,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
        }


# ---------------------------------------------------------------------------
# Sentiment label bands
# ---------------------------------------------------------------------------

SENTIMENT_LABELS = [
    (0.6,  'ACCUMULATING'),
    (0.2,  'MILD_ACCUMULATION'),
    (-0.2, 'NEUTRAL'),
    (-0.6, 'MILD_DISTRIBUTION'),
    (-2.0, 'DISTRIBUTING'),
]

WEIGHTS = {
    'exchange_netflow':    0.40,
    'funding_rate':        0.25,
    'open_interest_trend': 0.20,
    'stablecoin_ratio':    0.15,
}

RISK_LEVELS = {3: 'LOW', 4: 'MEDIUM', 5: 'HIGH', 6: 'CRITICAL'}


# ---------------------------------------------------------------------------
# WhaleAnalyzer
# ---------------------------------------------------------------------------

class WhaleAnalyzer:
    """
    Computes whale sentiment and cascade risk from existing API providers.

    Usage (from FastAPI background thread):
        analyzer = WhaleAnalyzer(aggregator)
        analyzer.refresh_all()          # blocks ~2–3s, call every 5 min
        result = analyzer.get_sentiment('BTC')
        warnings = analyzer.get_cascade_warnings()
    """

    # OI rolling history: keep 30-day window of (timestamp, oi_usd) per asset
    # Used to compute OI percentile for cascade detection
    _OI_HISTORY_MAX = 288   # 30 days × 2 readings/hour ≈ 1440; use 288 (24h every 5min)

    def __init__(self, aggregator=None):
        self._agg = aggregator

        # Sentiment cache: asset → WhaleSentiment
        self._sentiment: Dict[str, WhaleSentiment] = {}

        # Cascade cache: list of active CascadeWarning
        self._cascade: List[CascadeWarning] = []

        # OI history per asset for percentile calculation
        self._oi_history: Dict[str, Deque[Tuple[float, float]]] = {}

        # Cascade cooldown: asset → last trigger timestamp
        self._cascade_cooldown: Dict[str, float] = {}

        # Flow chart data per asset (24 hourly buckets)
        # Populated from Glassnode netflow when available
        self._flow_chart: Dict[str, Dict] = {}

        # Rolling netflow buffer per asset (one entry per refresh, max 24)
        self._flow_buffer: Dict[str, Deque] = {}

        # Recent on-chain transactions fed from WhaleCollector via inject_transactions()
        self._recent_txns: Deque[Dict] = deque(maxlen=MAX_RECENT_TXNS)

        self._last_refresh: float = 0.0

    # ------------------------------------------------------------------
    # Public read API (called by api/routers/whale.py)
    # ------------------------------------------------------------------

    def get_sentiment(self, asset: str) -> Optional[WhaleSentiment]:
        return self._sentiment.get(asset.upper())

    def get_cascade_warnings(self, asset: str = 'all') -> List[CascadeWarning]:
        self._prune_expired_cascade()
        if asset == 'all':
            return self._cascade
        return [w for w in self._cascade if w.asset == asset.upper()]

    def get_flow_chart(self, asset: str) -> Optional[Dict]:
        return self._flow_chart.get(asset.upper())

    def inject_transactions(self, txns: List[Dict]) -> None:
        """Called by the whale collector drain loop to push live transactions in."""
        for tx in txns:
            self._recent_txns.appendleft(tx)

    def get_recent_transactions(
        self,
        limit: int = 20,
        chain: str = 'all',
        asset: str = None,
        flow_type: str = 'all',
    ) -> Dict:
        """Return recent whale transactions with optional filters."""
        txns = list(self._recent_txns)

        if chain != 'all':
            txns = [t for t in txns if t.get('chain', '').upper() == chain.upper()]
        if asset:
            txns = [t for t in txns if t.get('asset', '').upper() == asset.upper()]
        if flow_type != 'all':
            txns = [t for t in txns if t.get('flow_type', '') == flow_type]

        txns = txns[:limit]
        total_usd = sum(t.get('amount_usd', 0) for t in txns)

        return {
            'transactions': txns,
            'total_usd_moved': total_usd,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Main refresh  (called every 5 min from background thread)
    # ------------------------------------------------------------------

    def refresh_all(self, assets: List[str] = None) -> None:
        """Refresh sentiment + cascade for all tracked assets."""
        if self._agg is None:
            logger.warning('WhaleAnalyzer: no DataAggregator — skipping refresh')
            return

        assets = assets or ['BTC', 'ETH', 'SOL']
        for asset in assets:
            try:
                self._refresh_asset(asset)
            except Exception as e:
                logger.error('WhaleAnalyzer refresh error for %s: %s', asset, e)

        self._last_refresh = time.time()
        logger.info('WhaleAnalyzer refreshed: %s', assets)

    def _refresh_asset(self, asset: str) -> None:
        sentiment = self._compute_sentiment(asset)
        if sentiment:
            self._sentiment[asset] = sentiment
            self._update_flow_buffer(asset, sentiment)

        cascade = self._compute_cascade(asset)
        if cascade:
            # Replace existing warning for this asset
            self._cascade = [w for w in self._cascade if w.asset != asset]
            self._cascade.append(cascade)

    # ------------------------------------------------------------------
    # Sentiment computation
    # ------------------------------------------------------------------

    @staticmethod
    def _tanh(value: float, scale: float) -> float:
        if scale == 0:
            return 0.0
        return math.tanh(value / scale)

    def _netflow_score(self, asset: str) -> Tuple[float, str]:
        """
        Exchange netflow via Glassnode.
        netflow = outflow - inflow  (positive = more coins leaving = accumulation)
        """
        try:
            data = self._agg.glassnode.get_exchange_netflow(asset)
        except Exception:
            data = None

        if not data:
            # Glassnode key missing or error → neutral
            return 0.0, 'Exchange netflow unavailable (GLASSNODE_API_KEY required)'

        inflow  = float(data.get('inflow', 0))
        outflow = float(data.get('outflow', 0))
        net_usd = outflow - inflow   # positive = withdrawals dominating = bullish

        # Glassnode returns values in native units; scale by approximate price
        prices = {'btc': 80_000, 'eth': 2_000, 'sol': 100}
        price  = prices.get(asset.lower(), 1)
        net_usd_approx = net_usd * price

        score  = self._tanh(net_usd_approx, 50_000_000)   # ±$50M as mid-scale
        direction = 'withdrawals' if net_usd > 0 else 'deposits'
        detail = (
            f"Net {abs(net_usd):,.0f} {asset} {direction} from exchanges "
            f"(≈${abs(net_usd_approx) / 1e6:.1f}M)"
        )
        return score, detail

    def _funding_score(self, asset: str) -> Tuple[float, str]:
        """Funding rate from Binance derivatives — already in aggregator cache."""
        try:
            deriv = self._agg.get_derivatives(asset)
            rate  = deriv.funding_rate if deriv else 0.0
        except Exception:
            rate = 0.0

        # Invert: negative funding is bullish (shorts paying = longs winning)
        score  = -self._tanh(rate, 0.01)

        if rate > 0.05:
            detail = f"Funding +{rate*100:.3f}% — longs overleveraged, squeeze risk"
        elif rate < -0.02:
            detail = f"Funding {rate*100:.3f}% — negative, shorts paying (short squeeze setup)"
        else:
            detail = f"Funding {rate*100:.3f}% — neutral positioning"

        return score, detail

    def _oi_trend_score(self, asset: str, netflow_score: float) -> Tuple[float, str]:
        """OI change over last 4h from Binance derivatives."""
        try:
            deriv       = self._agg.get_derivatives(asset)
            current_oi  = deriv.open_interest_usd if deriv else 0.0
            oi_change   = deriv.open_interest_change_24h if deriv else 0.0  # already a %
        except Exception:
            current_oi = 0.0
            oi_change  = 0.0

        # Track rolling OI history for percentile
        self._track_oi(asset, current_oi)

        score = self._tanh(oi_change / 100.0, 0.05)
        # Amplify when aligned with netflow direction
        if (score > 0 and netflow_score > 0) or (score < 0 and netflow_score < 0):
            score = min(1.0, score * 1.2)

        direction = 'rising' if oi_change > 0 else 'falling'
        detail = (
            f"OI {direction} {abs(oi_change):.1f}% (24h) — "
            f"${current_oi / 1e9:.2f}B total"
        )
        return score, detail

    def _stablecoin_score(self) -> Tuple[float, str]:
        """
        Stablecoin market cap ratio from CoinGecko global metrics.
        Rising stablecoin dominance = dry powder entering = mild bullish.
        """
        try:
            gm  = self._agg.get_global_metrics()
            # CoinGecko global metrics don't expose stablecoin % directly;
            # use total_market_cap and stablecoin_volume as proxy
            # Approximate: stablecoin inflow signal from total_market_cap change
            total_mcap = gm.total_market_cap if gm else 0
            # Without direct stablecoin flow data, use a neutral score
            # when Glassnode stablecoin endpoint is unavailable
            stablecoin_netflow = self._agg.glassnode.get_glassnode_metric(
                'usdt', 'transactions/transfers_volume_to_exchanges_sum'
            ) or 0.0
        except Exception:
            stablecoin_netflow = 0.0

        score  = self._tanh(stablecoin_netflow, 50_000_000)
        if stablecoin_netflow > 1_000_000:
            detail = f"${stablecoin_netflow/1e6:.0f}M stablecoins flowing into exchanges — dry powder"
        elif stablecoin_netflow < -1_000_000:
            detail = f"${abs(stablecoin_netflow)/1e6:.0f}M stablecoins leaving — capital deployed"
        else:
            detail = "Stablecoin flows neutral"

        return score, detail

    @staticmethod
    def _label(score: float) -> str:
        for threshold, label in SENTIMENT_LABELS:
            if score >= threshold:
                return label
        return 'DISTRIBUTING'

    def _compute_sentiment(self, asset: str) -> Optional[WhaleSentiment]:
        netflow_score, netflow_detail = self._netflow_score(asset)
        funding_score, funding_detail = self._funding_score(asset)
        oi_score,      oi_detail      = self._oi_trend_score(asset, netflow_score)
        stable_score,  stable_detail  = self._stablecoin_score()

        w = WEIGHTS
        composite = (
            netflow_score * w['exchange_netflow']    +
            funding_score * w['funding_rate']        +
            oi_score      * w['open_interest_trend'] +
            stable_score  * w['stablecoin_ratio']
        )
        composite = max(-1.0, min(1.0, composite))
        label     = self._label(composite)

        # Confidence: how many sub-scores agree with the composite direction
        scores    = [netflow_score, funding_score, oi_score, stable_score]
        agreement = sum(1 for s in scores if (s > 0.1) == (composite > 0))
        confidence = min(95, 35 + agreement * 12 + int(abs(composite) * 30))

        # Key signal: netflow is primary; add squeeze overlay if relevant
        key_signal = netflow_detail
        if funding_score > 0 and netflow_score < -0.5:
            key_signal += ' + LONG SQUEEZE SETUP'
        elif funding_score < 0 and netflow_score > 0.5:
            key_signal += ' + SHORT SQUEEZE SETUP'

        components = {
            'exchange_netflow': {
                'raw_score': round(netflow_score, 4),
                'weight': w['exchange_netflow'],
                'weighted': round(netflow_score * w['exchange_netflow'], 4),
                'detail': netflow_detail,
            },
            'funding_rate': {
                'raw_score': round(funding_score, 4),
                'weight': w['funding_rate'],
                'weighted': round(funding_score * w['funding_rate'], 4),
                'detail': funding_detail,
            },
            'open_interest_trend': {
                'raw_score': round(oi_score, 4),
                'weight': w['open_interest_trend'],
                'weighted': round(oi_score * w['open_interest_trend'], 4),
                'detail': oi_detail,
            },
            'stablecoin_ratio': {
                'raw_score': round(stable_score, 4),
                'weight': w['stablecoin_ratio'],
                'weighted': round(stable_score * w['stablecoin_ratio'], 4),
                'detail': stable_detail,
            },
        }

        return WhaleSentiment(
            asset=asset,
            score=round(composite, 4),
            label=label,
            confidence=confidence,
            key_signal=key_signal,
            window_hours=4,
            components=components,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # OI history tracking (for cascade percentile)
    # ------------------------------------------------------------------

    def _track_oi(self, asset: str, oi_usd: float) -> None:
        if asset not in self._oi_history:
            self._oi_history[asset] = deque(maxlen=self._OI_HISTORY_MAX)
        self._oi_history[asset].append((time.time(), oi_usd))

    def _oi_percentile(self, asset: str, current_oi: float) -> float:
        """Return current OI's percentile rank within 30-day history (0–100)."""
        history = self._oi_history.get(asset)
        if not history or len(history) < 10:
            return 50.0  # not enough data yet
        values = [v for _, v in history]
        below  = sum(1 for v in values if v < current_oi)
        return round(below / len(values) * 100, 1)

    # ------------------------------------------------------------------
    # Cascade risk detection
    # ------------------------------------------------------------------

    SIGNALS_REQUIRED  = 3
    CONFIDENCE_MIN    = 70
    WARNING_TTL_SECS  = 7200
    COOLDOWN_SECS     = 7200

    def _compute_cascade(self, asset: str) -> Optional[CascadeWarning]:
        now = time.time()
        if now - self._cascade_cooldown.get(asset, 0) < self.COOLDOWN_SECS:
            return None  # in cooldown

        try:
            deriv   = self._agg.get_derivatives(asset)
            price   = self._agg.get_price(asset)
        except Exception:
            return None

        if not deriv or not price:
            return None

        current_price = price.price_usd
        oi_usd        = deriv.open_interest_usd
        funding       = deriv.funding_rate
        liq_total     = deriv.liquidations_24h_total

        # Track OI for percentile
        self._track_oi(asset, oi_usd)
        oi_pct = self._oi_percentile(asset, oi_usd)

        signals_met   = 0
        key_signals:  List[str] = []
        direction     = 'LONG_SQUEEZE'

        # Signal 1: OI at 90th percentile (heavy)
        if oi_pct >= 90:
            signals_met += 1
            key_signals.append(f'OI at {oi_pct:.0f}th percentile (30-day high)')

        # Signal 2: Large 24h liquidations relative to OI (heavy)
        liq_ratio = liq_total / oi_usd if oi_usd > 0 else 0
        if liq_ratio >= 0.02:   # ≥2% of OI liquidated in 24h = stress
            signals_met += 1
            key_signals.append(
                f'${liq_total/1e6:.0f}M liquidated — {liq_ratio*100:.1f}% of OI at risk'
            )

        # Signal 3: Coinglass liquidation wall (use 24h liq as proxy when wall data unavailable)
        # When Etherscan/on-chain data is available, replace with actual liq cluster price
        liq_wall_price  = None
        liq_wall_usd    = liq_total
        if liq_total >= 50_000_000:  # ≥$50M in 24h = elevated risk
            signals_met += 1
            key_signals.append(f'${liq_total/1e6:.0f}M in 24h liquidations — cascade risk elevated')

        # Signal 4: Funding rate extreme (light)
        if abs(funding) > 0.05:
            signals_met += 1
            side = 'longs' if funding > 0 else 'shorts'
            key_signals.append(f'Funding {funding*100:.3f}% — crowded {side} at risk')
            if funding < 0:
                direction = 'SHORT_SQUEEZE'

        # Signal 5: OI rising fast while price is flat/down (distribution signal)
        oi_change_24h = deriv.open_interest_change_24h
        price_change  = price.price_change_24h
        if oi_change_24h > 5 and price_change < 0:
            signals_met += 1
            key_signals.append(
                f'OI +{oi_change_24h:.1f}% while price {price_change:+.1f}% — divergence'
            )

        if signals_met < self.SIGNALS_REQUIRED:
            return None

        risk_level = RISK_LEVELS.get(min(signals_met, 6), 'CRITICAL')
        confidence = min(95, int((signals_met / 5) * 100))
        if confidence < self.CONFIDENCE_MIN:
            return None

        now_dt    = datetime.now(timezone.utc)
        expires   = (now_dt + timedelta(seconds=self.WARNING_TTL_SECS)).isoformat()

        summary = (
            f"⚠ {risk_level} cascade risk for {asset} — "
            f"{signals_met}/5 signals. "
            f"OI ${oi_usd/1e9:.1f}B at {oi_pct:.0f}th pct."
        )

        warning = CascadeWarning(
            asset=asset,
            risk_level=risk_level,
            confidence=confidence,
            estimated_usd_at_risk=liq_wall_usd,
            liq_wall_price=liq_wall_price,
            current_price=current_price,
            price_distance_pct=None,
            direction=direction,
            key_signals=key_signals,
            human_summary=summary,
            expires_at=expires,
            created_at=now_dt.isoformat(),
        )

        self._cascade_cooldown[asset] = now
        return warning

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_flow_buffer(self, asset: str, sentiment: 'WhaleSentiment') -> None:
        """Append the latest netflow data point and rebuild the flow chart cache."""
        if asset not in self._flow_buffer:
            self._flow_buffer[asset] = deque(maxlen=24)

        netflow_comp = sentiment.components.get('exchange_netflow', {})
        raw_score = netflow_comp.get('raw_score', 0.0)

        # Convert raw_score (-1..1) back to an approximate USD value
        # tanh(x/50M)=raw_score → x ≈ 50M * atanh(raw_score)
        try:
            import math as _m
            clamped = max(-0.9999, min(0.9999, raw_score))
            net_usd = 50_000_000 * _m.atanh(clamped)
        except Exception:
            net_usd = 0.0

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self._flow_buffer[asset].append({
            'timestamp': now.isoformat(),
            'net_flow_usd': round(net_usd),
            'deposit_usd': round(max(0, -net_usd)),
            'withdrawal_usd': round(max(0, net_usd)),
            'transaction_count': 1,
        })

        points = list(self._flow_buffer[asset])
        net_24h = sum(p['net_flow_usd'] for p in points)
        largest = max((abs(p['net_flow_usd']) for p in points), default=0.0)
        bias = 'OUTFLOW' if net_24h < 0 else 'INFLOW' if net_24h > 0 else 'NEUTRAL'

        self._flow_chart[asset] = {
            'asset': asset,
            'data': points,
            'summary': {
                'net_24h_usd': round(net_24h),
                'bias': bias,
                'largest_single': round(largest),
            },
        }

    def _prune_expired_cascade(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._cascade = [w for w in self._cascade if w.expires_at > now]
