"""
Smart Money Tracker (Free APIs)

Aggregates signals from free data sources to detect institutional/whale activity:
- Funding rate extremes (Binance) — institutional positioning proxy
- Liquidation spikes — cascade/stress events
- OI changes — leverage positioning
- Stablecoin supply changes (CoinGecko) — new capital entering
- Volume anomalies (Binance) — unusual activity

No paid APIs (CryptoQuant, Whale Alert) required.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class SmartMoneySignal:
    """A single smart money signal."""
    signal_type: str        # funding_rate, liquidation_spike, oi_change, stablecoin_flow, volume_anomaly
    asset: str              # BTC, ETH, MARKET
    data: Dict[str, Any]    # Raw data values
    interpretation: str     # Human-readable explanation
    impact: str             # bullish, bearish, neutral
    confidence: str         # high, medium, low
    timestamp: Optional[str] = None


# Thresholds for signal detection
FUNDING_HIGH = 0.05       # 0.05% — elevated, longs paying
FUNDING_LOW = -0.03       # -0.03% — elevated, shorts paying
LIQUIDATION_SPIKE = 100_000_000    # $100M in 24h
LIQUIDATION_EXTREME = 300_000_000  # $300M — cascade territory
OI_CHANGE_PCT = 5.0       # 5% change in 24h is significant
VOLUME_SPIKE_MULTIPLIER = 2.0  # 2x average volume


class SmartMoneyTracker:
    """
    Aggregates free-tier signals to approximate smart money activity.
    Uses data from DataAggregator (Binance, CoinGecko).
    """

    def __init__(self):
        self._last_signals: List[SmartMoneySignal] = []

    def scan_signals(
        self,
        global_metrics: Dict[str, Any],
        derivatives_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Scan all available data sources for smart money signals.

        Args:
            global_metrics: Dict from MarketMetrics.to_dict()
            derivatives_data: Optional additional derivatives data

        Returns:
            Dict with signals list, net sentiment, and interpretation
        """
        signals: List[SmartMoneySignal] = []
        now = datetime.now(timezone.utc).isoformat()

        # 1. Funding Rate Signals
        signals.extend(self._check_funding_rates(global_metrics, now))

        # 2. Liquidation Signals
        signals.extend(self._check_liquidations(global_metrics, now))

        # 3. Open Interest Signals
        signals.extend(self._check_open_interest(global_metrics, now))

        # 4. Stablecoin / Capital Flow Signals
        signals.extend(self._check_stablecoin_flows(global_metrics, now))

        # 5. Volume Anomaly Signals
        signals.extend(self._check_volume_anomalies(global_metrics, now))

        # Compute net sentiment
        net_sentiment = self._compute_net_sentiment(signals)

        # Generate aggregate interpretation
        interpretation = self._aggregate_interpretation(signals, net_sentiment)

        self._last_signals = signals

        return {
            'signals': [self._signal_to_dict(s) for s in signals],
            'signal_count': len(signals),
            'net_sentiment': net_sentiment,
            'aggregate_interpretation': interpretation,
            'scanned_at': now,
        }

    def _check_funding_rates(self, metrics: Dict, ts: str) -> List[SmartMoneySignal]:
        """Check BTC and ETH funding rates for extremes."""
        signals = []

        for asset, key in [('BTC', 'btc_funding_rate'), ('ETH', 'eth_funding_rate')]:
            rate = metrics.get(key)
            if rate is None:
                continue

            rate_pct = rate * 100  # Convert to percentage

            if rate_pct > FUNDING_HIGH:
                signals.append(SmartMoneySignal(
                    signal_type='funding_rate',
                    asset=asset,
                    data={'rate': rate, 'rate_pct': round(rate_pct, 4), 'status': 'elevated'},
                    interpretation=f"{asset} funding at {rate_pct:.4f}% — longs paying shorts. Overleveraged long positions.",
                    impact='bearish',
                    confidence='high' if rate_pct > FUNDING_HIGH * 2 else 'medium',
                    timestamp=ts,
                ))
            elif rate_pct < FUNDING_LOW:
                signals.append(SmartMoneySignal(
                    signal_type='funding_rate',
                    asset=asset,
                    data={'rate': rate, 'rate_pct': round(rate_pct, 4), 'status': 'negative'},
                    interpretation=f"{asset} funding at {rate_pct:.4f}% — shorts paying longs. Bearish overcrowding.",
                    impact='bullish',  # Contrarian — extreme negative funding often precedes bounces
                    confidence='high' if rate_pct < FUNDING_LOW * 2 else 'medium',
                    timestamp=ts,
                ))

        return signals

    def _check_liquidations(self, metrics: Dict, ts: str) -> List[SmartMoneySignal]:
        """Check for liquidation spikes."""
        signals = []
        liq = metrics.get('total_liquidations_24h')
        if liq is None:
            return signals

        if liq > LIQUIDATION_EXTREME:
            signals.append(SmartMoneySignal(
                signal_type='liquidation_spike',
                asset='MARKET',
                data={'liquidations_24h': liq, 'level': 'extreme'},
                interpretation=f"Extreme liquidations: ${liq/1e6:.0f}M in 24h. Cascade event — weak hands being flushed.",
                impact='bearish',
                confidence='high',
                timestamp=ts,
            ))
        elif liq > LIQUIDATION_SPIKE:
            signals.append(SmartMoneySignal(
                signal_type='liquidation_spike',
                asset='MARKET',
                data={'liquidations_24h': liq, 'level': 'elevated'},
                interpretation=f"Elevated liquidations: ${liq/1e6:.0f}M in 24h. Overleveraged positions being cleared.",
                impact='bearish',
                confidence='medium',
                timestamp=ts,
            ))

        return signals

    def _check_open_interest(self, metrics: Dict, ts: str) -> List[SmartMoneySignal]:
        """Check open interest levels for leverage signals."""
        signals = []
        oi = metrics.get('total_open_interest')
        if oi is None:
            return signals

        # High OI combined with other signals
        if oi > 25_000_000_000:  # $25B+ — very high leverage
            signals.append(SmartMoneySignal(
                signal_type='oi_change',
                asset='MARKET',
                data={'open_interest': oi, 'level': 'very_high'},
                interpretation=f"Total OI at ${oi/1e9:.1f}B — extremely high leverage. Cascade risk elevated.",
                impact='bearish',
                confidence='medium',
                timestamp=ts,
            ))
        elif oi > 18_000_000_000:  # $18B+ — elevated
            funding = metrics.get('btc_funding_rate', 0) or 0
            if funding * 100 > FUNDING_HIGH:
                signals.append(SmartMoneySignal(
                    signal_type='oi_change',
                    asset='MARKET',
                    data={'open_interest': oi, 'funding': funding, 'level': 'elevated'},
                    interpretation=f"OI at ${oi/1e9:.1f}B with elevated funding — leverage building aggressively.",
                    impact='bearish',
                    confidence='high',
                    timestamp=ts,
                ))

        return signals

    def _check_stablecoin_flows(self, metrics: Dict, ts: str) -> List[SmartMoneySignal]:
        """Check stablecoin supply signals using CoinGecko data."""
        signals = []

        # BTC dominance shifts indicate capital rotation
        btc_dom = metrics.get('btc_dominance')
        if btc_dom is not None:
            if btc_dom > 58:
                signals.append(SmartMoneySignal(
                    signal_type='stablecoin_flow',
                    asset='MARKET',
                    data={'btc_dominance': btc_dom, 'direction': 'risk_off'},
                    interpretation=f"BTC dominance at {btc_dom:.1f}% — capital fleeing to BTC/stables. Risk-off rotation.",
                    impact='bearish',
                    confidence='medium',
                    timestamp=ts,
                ))
            elif btc_dom < 45:
                signals.append(SmartMoneySignal(
                    signal_type='stablecoin_flow',
                    asset='MARKET',
                    data={'btc_dominance': btc_dom, 'direction': 'risk_on'},
                    interpretation=f"BTC dominance at {btc_dom:.1f}% — capital rotating into alts aggressively.",
                    impact='bullish',
                    confidence='medium',
                    timestamp=ts,
                ))

        return signals

    def _check_volume_anomalies(self, metrics: Dict, ts: str) -> List[SmartMoneySignal]:
        """Check for unusual volume patterns."""
        signals = []
        volume = metrics.get('total_volume_24h')
        market_cap = metrics.get('total_market_cap')

        if volume is not None and market_cap is not None and market_cap > 0:
            # Volume/Market Cap ratio — high ratio suggests unusual activity
            ratio = volume / market_cap
            if ratio > 0.08:  # >8% of market cap traded in 24h
                signals.append(SmartMoneySignal(
                    signal_type='volume_anomaly',
                    asset='MARKET',
                    data={'volume_24h': volume, 'market_cap': market_cap, 'ratio': round(ratio, 4)},
                    interpretation=f"Volume/MCap ratio at {ratio*100:.1f}% — significantly above normal. High conviction moves underway.",
                    impact='neutral',
                    confidence='medium',
                    timestamp=ts,
                ))

        return signals

    def _compute_net_sentiment(self, signals: List[SmartMoneySignal]) -> str:
        """Compute net sentiment from all signals."""
        if not signals:
            return 'NEUTRAL'

        score = 0
        for signal in signals:
            weight = 2 if signal.confidence == 'high' else 1
            if signal.impact == 'bullish':
                score += weight
            elif signal.impact == 'bearish':
                score -= weight

        if score >= 3:
            return 'BULLISH'
        elif score >= 1:
            return 'NEUTRAL-BULLISH'
        elif score <= -3:
            return 'BEARISH'
        elif score <= -1:
            return 'NEUTRAL-BEARISH'
        return 'NEUTRAL'

    def _aggregate_interpretation(self, signals: List[SmartMoneySignal], sentiment: str) -> str:
        """Generate a summary interpretation."""
        if not signals:
            return "No significant smart money signals detected. Market activity within normal ranges."

        n = len(signals)
        bearish = sum(1 for s in signals if s.impact == 'bearish')
        bullish = sum(1 for s in signals if s.impact == 'bullish')

        parts = []
        if bearish > bullish:
            parts.append("Defensive positioning detected.")
        elif bullish > bearish:
            parts.append("Aggressive positioning detected.")
        else:
            parts.append("Mixed signals detected.")

        # Highlight high-confidence signals
        high_conf = [s for s in signals if s.confidence == 'high']
        if high_conf:
            types = set(s.signal_type for s in high_conf)
            type_labels = {
                'funding_rate': 'funding rate extremes',
                'liquidation_spike': 'liquidation cascade',
                'oi_change': 'high leverage',
                'stablecoin_flow': 'capital rotation',
                'volume_anomaly': 'unusual volume',
            }
            labels = [type_labels.get(t, t) for t in types]
            parts.append(f"Key drivers: {', '.join(labels)}.")

        parts.append(f"Overall stance: {sentiment.lower().replace('-', ' ')}.")
        return " ".join(parts)

    def _signal_to_dict(self, signal: SmartMoneySignal) -> Dict[str, Any]:
        """Convert a signal to a serializable dict."""
        return {
            'signal_type': signal.signal_type,
            'asset': signal.asset,
            'data': signal.data,
            'interpretation': signal.interpretation,
            'impact': signal.impact,
            'confidence': signal.confidence,
            'timestamp': signal.timestamp,
        }


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    from src.data.aggregator import DataAggregator

    print("=" * 70)
    print("SMART MONEY TRACKER — Live Test")
    print("=" * 70)

    agg = DataAggregator()
    gm = agg.get_global_metrics()

    if gm is None:
        print("ERROR: Could not fetch global metrics")
    else:
        tracker = SmartMoneyTracker()
        result = tracker.scan_signals(gm.to_dict())

        print(f"\nNet Sentiment: {result['net_sentiment']}")
        print(f"Signals Found: {result['signal_count']}")
        print(f"\n{result['aggregate_interpretation']}")

        for signal in result['signals']:
            impact_icon = {'bullish': '+', 'bearish': '-', 'neutral': '~'}
            icon = impact_icon.get(signal['impact'], '?')
            print(f"\n  [{icon}] {signal['signal_type'].upper()} ({signal['asset']})")
            print(f"      {signal['interpretation']}")
            print(f"      Impact: {signal['impact']} | Confidence: {signal['confidence']}")

    print("\n" + "=" * 70)
    print("Done")
