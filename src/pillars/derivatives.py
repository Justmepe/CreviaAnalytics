"""
File 8: Pillar C - Derivatives & Leverage
Dependencies: DataAggregator (unified data layer)
Status: ✅ COMPLETE - Updated to use DataAggregator

Purpose:
- Analyze leverage and positioning in derivatives markets
- Funding rates, open interest, liquidations

This pillar answers: "Was this move driven by leverage, positioning, or real demand?"
"""

from typing import Dict, Any, Optional
from src.utils.helpers import (
    calculate_percentage_change,
    categorize_funding_rate,
    format_large_number,
    get_current_timestamp
)
from src.core.config import RISK_THRESHOLDS

# Use new unified data layer
from src.data.aggregator import DataAggregator

# Module-level aggregator (lazy init)
_aggregator = None

def _get_aggregator() -> DataAggregator:
    """Get or create the shared aggregator instance"""
    global _aggregator
    if _aggregator is None:
        _aggregator = DataAggregator()
    return _aggregator


# =============================================================================
# PILLAR C: DERIVATIVES & LEVERAGE ANALYSIS
# =============================================================================

def analyze_derivatives(ticker: str) -> Dict[str, Any]:
    """
    Analyze derivatives market for an asset
    
    This pillar reveals market pressure and positioning:
    - Is leverage building up?
    - Are longs or shorts crowded?
    - Is this organic demand or leverage-driven?
    
    Args:
        ticker: Asset symbol (e.g., 'BTC', 'ETH')
    
    Returns:
        dict: {
            'funding_rate': 0.0001,
            'funding_24h_change': 0.0005,  # Requires historical data
            'funding_analysis': {
                'risk_level': 'Medium',
                'signal': 'long_heavy',
                'description': '...'
            },
            'open_interest_usd': 15000000000,
            'oi_change_24h': 8.5,  # Percentage
            'pressure_signal': 'leverage_buildup' | 'short_covering' | 'deleverage' | 'neutral',
            'leverage_risk': 'Low' | 'Medium' | 'High',
            'interpretation': 'Detailed explanation...'
        }
    """
    
    # Fetch derivatives data from unified data layer
    aggregator = _get_aggregator()
    deriv_data = aggregator.get_derivatives(ticker)

    # Extract from DerivativesData object
    if deriv_data:
        funding_rate = deriv_data.funding_rate
        mark_price = deriv_data.mark_price
        oi_usd = deriv_data.open_interest_usd
        oi_base = deriv_data.open_interest_usd / mark_price if mark_price > 0 else 0
        funding_data = {
            'funding_rate': funding_rate,
            'mark_price': mark_price
        }
        oi_data = {
            'open_interest_usd': oi_usd,
            'open_interest': oi_base
        }
    else:
        funding_rate = 0
        mark_price = 0
        oi_usd = 0
        oi_base = 0
        funding_data = None
        oi_data = None
    
    # Analyze funding rate
    funding_analysis = categorize_funding_rate(funding_rate)
    
    # Determine pressure signal
    pressure_signal = _determine_pressure_signal(funding_rate, oi_usd, mark_price)
    
    # Determine leverage risk
    leverage_risk = _determine_leverage_risk(funding_rate, oi_usd)
    
    # Generate interpretation
    interpretation = _generate_derivatives_interpretation(
        ticker, funding_rate, funding_analysis, oi_usd, pressure_signal, leverage_risk
    )
    
    return {
        'ticker': ticker,
        'funding_rate': funding_rate,
        'funding_rate_percent': funding_rate * 100,
        'funding_analysis': funding_analysis,
        'mark_price': mark_price,
        'open_interest_usd': oi_usd,
        'open_interest_base': oi_base,
        'oi_formatted': format_large_number(oi_usd),
        'pressure_signal': pressure_signal,
        'leverage_risk': leverage_risk,
        'interpretation': interpretation,
        'timestamp': get_current_timestamp(),
        'raw_data': {
            'funding': funding_data,
            'open_interest': oi_data
        }
    }


# =============================================================================
# DERIVATIVES ANALYSIS LOGIC
# =============================================================================

def _determine_pressure_signal(funding_rate: float, oi_usd: float, price: float) -> str:
    """
    Determine what type of market pressure is present
    
    Signals:
    - leverage_buildup: Rising OI + positive funding → More longs opening
    - short_covering: Price up + OI down → Shorts forced to close
    - deleverage: Funding extreme + OI dropping → Positions closing
    - accumulation: Negative funding + stable OI → Spot buying
    - neutral: No clear pressure
    
    Args:
        funding_rate: Current funding rate
        oi_usd: Open interest in USD
        price: Current mark price
    
    Returns:
        str: Pressure signal type
    """
    
    # Note: Without historical data, we use static heuristics
    # In production, compare to 24h ago values
    
    is_high_oi = oi_usd > 1_000_000_000  # $1B+
    
    # Leverage buildup: High positive funding + significant OI
    if funding_rate > 0.01 and is_high_oi:
        return 'leverage_buildup'
    
    # Deleverage: Extreme funding (either direction)
    if abs(funding_rate) > 0.03:
        return 'deleverage_risk'
    
    # Short covering indicator: Negative funding (shorts paying)
    if funding_rate < -0.01:
        return 'potential_short_squeeze'
    
    # Accumulation: Low funding, low OI
    if abs(funding_rate) < 0.005 and not is_high_oi:
        return 'accumulation'
    
    # Neutral
    return 'neutral'


def _determine_leverage_risk(funding_rate: float, oi_usd: float) -> str:
    """
    Determine overall leverage risk level
    
    Args:
        funding_rate: Current funding rate
        oi_usd: Open interest in USD
    
    Returns:
        str: 'Low', 'Medium', or 'High'
    """
    
    # Get thresholds from config
    leverage_thresholds = RISK_THRESHOLDS.get('leverage', {
        'low': 0.01,
        'medium': 0.03,
        'high': 0.05
    })
    
    abs_funding = abs(funding_rate)
    
    # High OI amplifies risk
    oi_multiplier = 1.0
    if oi_usd > 5_000_000_000:  # $5B+
        oi_multiplier = 1.5
    elif oi_usd > 10_000_000_000:  # $10B+
        oi_multiplier = 2.0
    
    effective_funding = abs_funding * oi_multiplier
    
    if effective_funding < leverage_thresholds['low']:
        return 'Low'
    elif effective_funding < leverage_thresholds['medium']:
        return 'Medium'
    else:
        return 'High'


def _generate_derivatives_interpretation(
    ticker: str,
    funding_rate: float,
    funding_analysis: Dict[str, Any],
    oi_usd: float,
    pressure_signal: str,
    leverage_risk: str
) -> str:
    """
    Generate human-readable interpretation of derivatives data
    
    Returns:
        str: Clear explanation
    """
    
    parts = []
    
    # Funding rate explanation
    funding_pct = funding_rate * 100
    if abs(funding_rate) < 0.005:
        parts.append(f"Funding rates for {ticker} are neutral at {funding_pct:.4f}%, ")
        parts.append("indicating balanced positioning between longs and shorts. ")
    elif funding_rate > 0:
        parts.append(f"Funding rates are positive at {funding_pct:.4f}%, ")
        parts.append("meaning longs are paying shorts. This suggests ")
        if funding_rate > 0.02:
            parts.append("heavily overcrowded long positions. ")
        else:
            parts.append("more longs than shorts in the market. ")
    else:
        parts.append(f"Funding rates are negative at {funding_pct:.4f}%, ")
        parts.append("meaning shorts are paying longs. This suggests ")
        if funding_rate < -0.02:
            parts.append("heavily overcrowded short positions. ")
        else:
            parts.append("more shorts than longs in the market. ")
    
    # Open interest context
    if oi_usd > 0:
        parts.append(f"Open interest stands at {format_large_number(oi_usd)}, ")
        if oi_usd > 10_000_000_000:
            parts.append("which is very high and amplifies liquidation risk. ")
        elif oi_usd > 5_000_000_000:
            parts.append("representing significant leverage in the market. ")
        else:
            parts.append("at moderate levels. ")
    
    # Pressure signal explanation
    signal_text = {
        'leverage_buildup': 'This pattern suggests a leverage buildup, with new positions opening. Risk of cascade liquidations is elevated.',
        'deleverage_risk': '⚠️ Extreme funding rates indicate over-leveraged positions. A sharp move could trigger mass liquidations.',
        'potential_short_squeeze': 'Negative funding with short crowding creates conditions for a potential short squeeze.',
        'accumulation': 'Low leverage and balanced funding suggest organic spot market activity rather than speculation.',
        'neutral': 'Current positioning appears balanced without extreme leverage or crowding.'
    }
    parts.append(signal_text.get(pressure_signal, ''))
    
    # Risk warning
    if leverage_risk == 'High':
        parts.append(' ⚠️ Leverage risk is HIGH - market is vulnerable to volatility.')
    elif leverage_risk == 'Medium':
        parts.append(' Leverage risk is moderate.')
    
    return ''.join(parts)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Pillar C: Derivatives & Leverage...")
    print("=" * 70)
    
    # Analyze BTC derivatives
    derivatives = analyze_derivatives('BTC')
    
    print("\n📈 DERIVATIVES & LEVERAGE ANALYSIS - BTC")
    print("-" * 70)
    print(f"Funding Rate:         {derivatives['funding_rate_percent']:.4f}%")
    print(f"Funding Signal:       {derivatives['funding_analysis']['signal'].replace('_', ' ').title()}")
    print(f"Risk Level:           {derivatives['funding_analysis']['risk_level']}")
    print()
    print(f"Open Interest:        ${derivatives['oi_formatted']}")
    print(f"Mark Price:           ${derivatives['mark_price']:,.2f}")
    print()
    print(f"Pressure Signal:      {derivatives['pressure_signal'].replace('_', ' ').title()}")
    print(f"Leverage Risk:        {derivatives['leverage_risk']}")
    print()
    print("-" * 70)
    print("Interpretation:")
    print(derivatives['interpretation'])
    print()
    print("=" * 70)
    print("✅ Pillar C: Derivatives & Leverage - COMPLETE")
    print()
    print("This pillar reveals whether moves are leverage-driven or organic.")