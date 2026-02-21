"""
File 9: Pillar D - On-Chain & Flow
Dependencies: DataAggregator (unified data layer)
Status: ✅ COMPLETE - Updated to use DataAggregator

Purpose:
- Analyze capital flows and wallet activity
- Exchange inflows/outflows, holder behavior

This pillar answers: "Who moved capital, and how?"
"""

from typing import Dict, Any, Optional
from src.utils.helpers import (
    calculate_percentage_change,
    format_large_number,
    get_current_timestamp,
    calculate_velocity
)

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
# PILLAR D: ON-CHAIN & FLOW ANALYSIS
# =============================================================================

def analyze_onchain(ticker: str) -> Dict[str, Any]:
    """
    Analyze on-chain metrics and capital flows
    
    This pillar reveals:
    - Where capital is moving (exchanges vs wallets)
    - Holder behavior (accumulation vs distribution)
    - Network activity levels
    
    Args:
        ticker: Asset symbol
    
    Returns:
        dict: {
            'exchange_flow': 'inflow' | 'outflow' | 'neutral',
            'flow_magnitude': 'low' | 'medium' | 'high',
            'holder_behavior': 'accumulation' | 'distribution' | 'neutral',
            'network_activity': 'low' | 'medium' | 'high',
            'velocity': 0.15,  # Volume/Market Cap ratio
            'interpretation': 'Detailed explanation...'
        }
    
    Note: This is a simplified version. Full on-chain analysis requires
    specialized APIs like Glassnode, which provide:
    - Exchange net flows
    - Active addresses
    - Holder distribution changes
    - UTXO age analysis
    """
    
    # Fetch data from unified data layer
    aggregator = _get_aggregator()
    price_data = aggregator.get_price(ticker)
    onchain_data = aggregator.get_onchain(ticker)

    if not price_data:
        return _empty_onchain_result(ticker)

    # Extract available metrics from PriceSnapshot
    price = price_data.price_usd
    volume = price_data.volume_24h
    market_cap = price_data.market_cap
    circulating_supply = price_data.circulating_supply or 0

    # Build coin_data dict for raw_data compatibility
    coin_data = {
        'current_price': price,
        'total_volume': volume,
        'market_cap': market_cap,
        'circulating_supply': circulating_supply
    }

    # Add on-chain specific data if available
    if onchain_data:
        coin_data['transaction_count_24h'] = onchain_data.transaction_count_24h
        coin_data['hashrate'] = onchain_data.hashrate
    
    # Calculate velocity (Volume/Market Cap)
    velocity = calculate_velocity(volume, market_cap)
    
    # Analyze flows (simplified - would use Glassnode in production)
    exchange_flow, flow_magnitude = _analyze_exchange_flow(volume, market_cap, velocity)
    
    # Analyze holder behavior
    holder_behavior = _analyze_holder_behavior(velocity, price)
    
    # Determine network activity
    network_activity = _determine_network_activity(velocity, volume, market_cap)
    
    # Generate interpretation
    interpretation = _generate_onchain_interpretation(
        ticker, exchange_flow, holder_behavior, velocity, volume, market_cap
    )
    
    return {
        'ticker': ticker,
        'exchange_flow': exchange_flow,
        'flow_magnitude': flow_magnitude,
        'holder_behavior': holder_behavior,
        'network_activity': network_activity,
        'velocity': velocity,
        'volume_24h': volume,
        'volume_formatted': format_large_number(volume),
        'market_cap': market_cap,
        'market_cap_formatted': format_large_number(market_cap),
        'interpretation': interpretation,
        'timestamp': get_current_timestamp(),
        'note': 'Full on-chain analysis requires Glassnode or similar APIs',
        'raw_data': coin_data
    }


# =============================================================================
# ON-CHAIN ANALYSIS LOGIC
# =============================================================================

def _analyze_exchange_flow(volume: float, market_cap: float, velocity: float) -> tuple:
    """Analyze exchange flow direction (simplified heuristic)"""
    
    if velocity > 0.3:
        flow_direction = 'high_turnover'
        magnitude = 'high'
    elif velocity > 0.15:
        flow_direction = 'moderate_activity'
        magnitude = 'medium'
    else:
        flow_direction = 'low_activity'
        magnitude = 'low'
    
    return (flow_direction, magnitude)


def _analyze_holder_behavior(velocity: float, price: float) -> str:
    """Analyze holder behavior patterns"""
    
    if velocity < 0.05:
        return 'strong_holding'
    elif velocity < 0.1:
        return 'holding'
    elif velocity > 0.25:
        return 'active_distribution'
    elif velocity > 0.15:
        return 'moderate_distribution'
    else:
        return 'neutral'


def _determine_network_activity(velocity: float, volume: float, market_cap: float) -> str:
    """Determine overall network activity level"""
    
    if velocity > 0.2 and volume > market_cap * 0.2:
        return 'high'
    elif velocity > 0.1 or volume > market_cap * 0.1:
        return 'medium'
    else:
        return 'low'


def _generate_onchain_interpretation(
    ticker: str,
    exchange_flow: str,
    holder_behavior: str,
    velocity: float,
    volume: float,
    market_cap: float
) -> str:
    """Generate human-readable interpretation"""
    
    parts = []
    
    parts.append(f"{ticker} has a volume/market cap velocity of {velocity:.3f}, ")
    
    if velocity < 0.05:
        parts.append("indicating very low turnover with minimal selling. ")
    elif velocity < 0.15:
        parts.append("indicating moderate turnover with normal trading activity. ")
    elif velocity < 0.3:
        parts.append("indicating elevated turnover with active trading. ")
    else:
        parts.append("indicating very high turnover with heavy speculative activity. ")
    
    vol_to_mcap_pct = (volume / market_cap * 100) if market_cap > 0 else 0
    parts.append(f"24h volume represents {vol_to_mcap_pct:.1f}% of market cap. ")
    
    behavior_text = {
        'strong_holding': 'Holders appear to be in strong accumulation mode.',
        'holding': 'Holders are largely holding positions.',
        'neutral': 'Holder behavior appears balanced.',
        'moderate_distribution': 'Some distribution is occurring.',
        'active_distribution': 'Active distribution is underway.'
    }
    parts.append(behavior_text.get(holder_behavior, ''))
    
    return ''.join(parts)


def _empty_onchain_result(ticker: str) -> Dict[str, Any]:
    """Return empty result when data is unavailable"""
    return {
        'ticker': ticker,
        'exchange_flow': 'unknown',
        'flow_magnitude': 'unknown',
        'holder_behavior': 'unknown',
        'network_activity': 'unknown',
        'velocity': 0,
        'interpretation': f"On-chain data unavailable for {ticker}.",
        'timestamp': get_current_timestamp()
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Pillar D: On-Chain & Flow...")
    print("=" * 70)
    
    onchain = analyze_onchain('BTC')
    
    print("\n⛓️  ON-CHAIN & FLOW ANALYSIS - BTC")
    print("-" * 70)
    print(f"Exchange Flow:        {onchain['exchange_flow'].replace('_', ' ').title()}")
    print(f"Holder Behavior:      {onchain['holder_behavior'].replace('_', ' ').title()}")
    print(f"Network Activity:     {onchain['network_activity'].title()}")
    print(f"Velocity:             {onchain['velocity']:.3f}")
    print()
    print("-" * 70)
    print("Interpretation:")
    print(onchain['interpretation'])
    print()
    print("=" * 70)
    print("✅ Pillar D: On-Chain & Flow - COMPLETE")