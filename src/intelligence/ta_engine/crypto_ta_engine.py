"""
Crypto TA Engine
================
Orchestrator that ties together OHLCV fetching, structure analysis,
zone identification, and entry filter alignment into one TAResult dict.

Usage:
    engine = CryptoTAEngine()
    result = await engine.analyze(ticker='BTC', htf='4h', exchange='binance')
    # or (convenience)
    result = await analyze_asset('ETH', htf='1h')
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from .ohlcv_fetcher import fetch_ohlcv, get_ltf, get_structure_label
from .indicators import run_entry_filters
from .structure_engine import StructureEngine
from .zone_identifier import ZoneIdentifier

logger = logging.getLogger(__name__)


class CryptoTAEngine:
    """
    Orchestrates multi-timeframe TA for crypto assets.

    Workflow:
    1. Fetch HTF OHLCV (for structure + zones)
    2. Fetch LTF OHLCV (for entry filters)
    3. StructureEngine → trend, swings, key levels, CHoCH
    4. ZoneIdentifier → supply/demand zones with quality scores
    5. Entry filters → EMA/VWAP/VWV/ADX alignment score
    6. Composite setup_quality (0-100)
    """

    def __init__(self):
        self._structure_engine = StructureEngine()
        self._zone_identifier = ZoneIdentifier()

    async def analyze(
        self,
        ticker: str,
        htf: str = '4h',
        ltf: Optional[str] = None,
        exchange: str = 'binance',
        htf_limit: int = 300,
        ltf_limit: int = 300,
    ) -> Dict[str, Any]:
        """
        Run full multi-timeframe TA analysis for one asset.

        Returns:
            TAResult dict with keys: ticker, htf, ltf, exchange, direction,
            setup_quality, structure, zones, entry_filters, current_price, atr
        """
        if ltf is None:
            ltf = get_ltf(htf)

        htf_label = get_structure_label(htf)

        # 1. Fetch HTF + LTF concurrently
        try:
            htf_df, ltf_df = await asyncio.gather(
                fetch_ohlcv(ticker, htf, exchange, htf_limit),
                fetch_ohlcv(ticker, ltf, exchange, ltf_limit),
            )
        except Exception as e:
            logger.error(f"[CryptoTAEngine] OHLCV fetch failed for {ticker}: {e}")
            return self._error_result(ticker, htf, ltf, str(e))

        # 2. StructureEngine on HTF
        structure_state = None
        try:
            structure_state = self._structure_engine.analyze_structure(
                data=htf_df,
                timeframe=htf_label,
                symbol=ticker,
            )
        except Exception as e:
            logger.error(f"[CryptoTAEngine] StructureEngine failed for {ticker}: {e}")

        # 3. Directional bias from structure (BULLISH → LONG)
        direction = 'LONG'
        if structure_state is not None:
            struct_val = getattr(structure_state.market_structure, 'value', 'BULLISH')
            direction = 'LONG' if struct_val == 'BULLISH' else 'SHORT'

        # 4. ZoneIdentifier on HTF
        zones_result: Dict = {'active': [], 'broken': []}
        if structure_state is not None:
            try:
                zones_result = self._zone_identifier.identify_zones(
                    df=htf_df,
                    structure=structure_state,
                    timeframe=htf_label,
                    symbol=ticker,
                )
            except Exception as e:
                logger.error(f"[CryptoTAEngine] ZoneIdentifier failed for {ticker}: {e}")

        # 5. Entry filters on LTF
        entry_filters: Dict = {
            'alignment_score': 0,
            'filters_passed': 0,
            'filters_total': 5,
            'direction': direction,
        }
        try:
            entry_filters = run_entry_filters(ltf_df, direction)
        except Exception as e:
            logger.error(f"[CryptoTAEngine] Entry filters failed for {ticker}: {e}")

        # 6. Serialize + score
        structure_summary = self._serialize_structure(structure_state)
        zones_summary = self._serialize_zones(zones_result, entry_filters.get('current_price', 0.0))
        setup_quality = self._compute_setup_quality(structure_state, zones_result, entry_filters)

        current_price = entry_filters.get('current_price', float(htf_df.iloc[-1]['close']))
        atr = entry_filters.get('atr', 0.0)

        return {
            'ticker': ticker,
            'htf': htf,
            'ltf': ltf,
            'exchange': exchange,
            'direction': direction,
            'setup_quality': setup_quality,
            'structure': structure_summary,
            'zones': zones_summary,
            'entry_filters': entry_filters,
            'current_price': current_price,
            'atr': atr,
        }

    # -------------------------------------------------------------------------
    # Serializers
    # -------------------------------------------------------------------------

    def _serialize_structure(self, state) -> Dict[str, Any]:
        """Convert StructureState to a clean JSON-serializable dict."""
        if state is None:
            return {
                'available': False,
                'trend': 'UNKNOWN',
                'health': 'UNKNOWN',
            }

        def _swing_price(sp) -> Optional[float]:
            return round(float(sp.price), 6) if sp is not None else None

        return {
            'available': True,
            'trend': getattr(state.market_structure, 'value', 'BULLISH'),
            'health': state.health_status,
            'adx': round(state.adx_value, 1),
            'atr': round(state.atr_value, 6),
            'choch_detected': state.choch_detected,
            'choch_is_fresh': state.choch_is_fresh,
            'choch_direction': getattr(state, 'choch_direction', None),
            'choch_bars_ago': state.choch_bars_ago,
            'macro_trend': state.macro_trend_direction,
            'macro_confidence': round(state.macro_trend_confidence, 2),
            'key_levels': {
                'last_HH': _swing_price(state.last_HH),
                'last_HL': _swing_price(state.last_HL),
                'last_LH': _swing_price(state.last_LH),
                'last_LL': _swing_price(state.last_LL),
            },
        }

    def _serialize_zones(self, zones_result: Dict, current_price: float) -> Dict[str, Any]:
        """Convert Zone objects to serializable dicts, sorted by quality."""

        def _zone_dict(z) -> Dict[str, Any]:
            mid = float(z.mid_price)
            dist_pct = round((current_price - mid) / mid * 100, 2) if mid else 0.0
            return {
                'type': z.type.value,                       # 'demand' | 'supply'
                'price_top': round(float(z.price_top), 6),
                'price_bottom': round(float(z.price_bottom), 6),
                'mid_price': round(mid, 6),
                'protection_price': round(float(z.protection_price), 6),
                'quality_score': round(float(z.quality_score), 1),
                'status': z.status.value,                   # 'fresh' | 'tested' | 'broken'
                'location_label': z.location_label,         # 'Premium' | 'Discount' | ...
                'touch_count': z.touch_count,
                'role': z.role,
                'distance_pct': dist_pct,                   # + = above price, - = below
            }

        active_zones = [_zone_dict(z) for z in zones_result.get('active', [])]
        broken_zones = [_zone_dict(z) for z in zones_result.get('broken', [])]

        demand = sorted(
            [z for z in active_zones if z['type'] == 'demand'],
            key=lambda x: -x['quality_score'],
        )
        supply = sorted(
            [z for z in active_zones if z['type'] == 'supply'],
            key=lambda x: -x['quality_score'],
        )

        return {
            'active_count': len(active_zones),
            'broken_count': len(broken_zones),
            'demand_zones': demand,
            'supply_zones': supply,
            'best_demand': demand[0] if demand else None,
            'best_supply': supply[0] if supply else None,
            'all_active': active_zones,
        }

    # -------------------------------------------------------------------------
    # Composite quality score
    # -------------------------------------------------------------------------

    def _compute_setup_quality(
        self,
        structure_state,
        zones_result: Dict,
        entry_filters: Dict,
    ) -> int:
        """
        Composite setup quality: 0-100.

        Components:
          Structure health / ADX trend strength:  max 35 pts
          Best zone quality score:                max 35 pts
          Entry filter alignment:                 max 30 pts
        """
        score = 0

        # --- Structure (0-35) ---
        if structure_state is not None:
            adx = structure_state.adx_value
            if adx > 20:
                score += 10  # Trending (not ranging)
            if adx > 25:
                score += 5   # Strong trend
            if adx > 30:
                score += 5   # Very strong trend
            if structure_state.choch_is_fresh:
                score += 10  # Fresh Change of Character = high-probability flip
            if structure_state.macro_trend_confidence > 0.5:
                score += 5   # Macro alignment adds conviction

        # --- Zones (0-35) ---
        active = zones_result.get('active', [])
        if active:
            best_q = max((getattr(z, 'quality_score', 0) for z in active), default=0)
            score += int(best_q / 100 * 35)

        # --- Entry filters (0-30) ---
        alignment = entry_filters.get('alignment_score', 0)
        score += int(alignment / 100 * 30)

        return min(100, max(0, score))

    # -------------------------------------------------------------------------
    # Error fallback
    # -------------------------------------------------------------------------

    def _error_result(self, ticker: str, htf: str, ltf: str, error: str) -> Dict[str, Any]:
        return {
            'ticker': ticker,
            'htf': htf,
            'ltf': ltf,
            'exchange': 'unknown',
            'direction': 'UNKNOWN',
            'setup_quality': 0,
            'structure': {'available': False, 'trend': 'UNKNOWN', 'health': 'UNKNOWN'},
            'zones': {
                'active_count': 0,
                'broken_count': 0,
                'demand_zones': [],
                'supply_zones': [],
                'best_demand': None,
                'best_supply': None,
                'all_active': [],
            },
            'entry_filters': {},
            'current_price': 0.0,
            'atr': 0.0,
            'error': error,
        }


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

async def analyze_asset(
    ticker: str,
    htf: str = '4h',
    ltf: Optional[str] = None,
    exchange: str = 'binance',
) -> Dict[str, Any]:
    """
    Convenience function: run full TA analysis for a single asset.

    Example:
        import asyncio
        result = asyncio.run(analyze_asset('BTC', htf='4h'))
        print(result['setup_quality'], result['direction'])
    """
    engine = CryptoTAEngine()
    return await engine.analyze(ticker=ticker, htf=htf, ltf=ltf, exchange=exchange)
