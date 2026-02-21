"""
File 10: Pillar E - Sector-Specific Logic
Dependencies: DataAggregator (unified data layer)
Status: ✅ COMPLETE - Updated to use DataAggregator

Purpose:
- Asset-type specific metrics
- Different logic for memecoins, privacy coins, DeFi

This pillar adds specialized analysis that only applies to certain asset types
"""

from typing import Dict, Any
from src.utils.helpers import (
    calculate_velocity,
    format_large_number,
    get_current_timestamp
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


def _get_coin_data(ticker: str) -> dict:
    """Fetch coin data using DataAggregator and convert to legacy format"""
    aggregator = _get_aggregator()
    price_data = aggregator.get_price(ticker)

    if not price_data:
        return None

    return {
        'current_price': price_data.price_usd,
        'total_volume': price_data.volume_24h,
        'market_cap': price_data.market_cap,
        'price_change_percentage_24h': price_data.price_change_24h,
        'circulating_supply': price_data.circulating_supply
    }


# =============================================================================
# PILLAR E: SECTOR-SPECIFIC ANALYSIS
# =============================================================================

def analyze_sector_specific(ticker: str, asset_type: str) -> Dict[str, Any]:
    """
    Perform sector-specific analysis based on asset type
    
    Args:
        ticker: Asset symbol
        asset_type: One of 'MEMECOIN', 'PRIVACY', 'DEFI'
    
    Returns:
        dict: Sector-specific metrics and analysis
    """
    
    if asset_type == 'MEMECOIN':
        return get_memecoin_metrics(ticker)
    elif asset_type == 'PRIVACY':
        return get_privacy_metrics(ticker)
    elif asset_type == 'DEFI':
        return get_defi_metrics(ticker)
    else:
        return {
            'asset_type': asset_type,
            'note': f'No sector-specific analysis for {asset_type}',
            'timestamp': get_current_timestamp()
        }


# =============================================================================
# MEMECOIN METRICS
# =============================================================================

def get_memecoin_metrics(ticker: str) -> Dict[str, Any]:
    """
    Memecoin-specific analysis
    
    Focus:
    - Volume velocity (very important for memes)
    - Holder churn rate
    - Price volatility
    - Social momentum
    
    Returns:
        dict: Memecoin metrics
    """
    
    coin_data = _get_coin_data(ticker)

    if not coin_data:
        return {'error': f'Data unavailable for {ticker}'}

    volume = coin_data.get('total_volume', 0)
    market_cap = coin_data.get('market_cap', 0)
    price_change_24h = coin_data.get('price_change_percentage_24h', 0)

    # Calculate velocity (critical for memecoins)
    velocity = calculate_velocity(volume, market_cap)

    # Categorize memecoin activity
    activity_level = _categorize_memecoin_activity(velocity, price_change_24h)
    
    # Assess risk
    memecoin_risk = _assess_memecoin_risk(velocity, market_cap, price_change_24h)
    
    # Generate interpretation
    interpretation = _generate_memecoin_interpretation(
        ticker, velocity, price_change_24h, activity_level, memecoin_risk
    )
    
    return {
        'asset_type': 'MEMECOIN',
        'ticker': ticker,
        'velocity': velocity,
        'velocity_category': _velocity_category(velocity),
        'price_change_24h': price_change_24h,
        'activity_level': activity_level,
        'speculation_intensity': 'extreme' if velocity > 0.5 else 'high' if velocity > 0.3 else 'moderate',
        'memecoin_risk': memecoin_risk,
        'interpretation': interpretation,
        'timestamp': get_current_timestamp()
    }


def _categorize_memecoin_activity(velocity: float, price_change: float) -> str:
    """Categorize memecoin activity level"""
    
    if velocity > 0.5 and abs(price_change) > 20:
        return 'extreme_speculation'
    elif velocity > 0.3 and abs(price_change) > 10:
        return 'high_activity'
    elif velocity > 0.15:
        return 'moderate_activity'
    else:
        return 'low_activity'


def _assess_memecoin_risk(velocity: float, market_cap: float, price_change: float) -> str:
    """Assess memecoin-specific risks"""
    
    # Very high velocity + small cap = extreme risk
    if velocity > 0.5 and market_cap < 100_000_000:
        return 'EXTREME'
    elif velocity > 0.3 or abs(price_change) > 30:
        return 'HIGH'
    elif velocity > 0.15 or abs(price_change) > 15:
        return 'MEDIUM'
    else:
        return 'LOW'


def _velocity_category(velocity: float) -> str:
    """Categorize velocity for memecoins"""
    if velocity > 0.5:
        return 'Extreme (Pump/Dump Territory)'
    elif velocity > 0.3:
        return 'Very High (Heavy Speculation)'
    elif velocity > 0.15:
        return 'High (Active Trading)'
    elif velocity > 0.05:
        return 'Moderate'
    else:
        return 'Low (Stable Holding)'


def _generate_memecoin_interpretation(
    ticker: str,
    velocity: float,
    price_change: float,
    activity: str,
    risk: str
) -> str:
    """Generate memecoin-specific interpretation"""
    
    parts = []
    
    parts.append(f"{ticker} is showing {_velocity_category(velocity).lower()} with a velocity of {velocity:.3f}. ")
    
    if velocity > 0.5:
        parts.append("⚠️ EXTREME speculation detected - this is pump/dump territory. ")
    elif velocity > 0.3:
        parts.append("Very high speculative activity - exercise extreme caution. ")
    
    if abs(price_change) > 20:
        parts.append(f"Price has moved {price_change:.1f}% in 24h, indicating volatile conditions. ")
    
    parts.append(f"Risk level: {risk}. ")
    
    if risk in ['EXTREME', 'HIGH']:
        parts.append("This asset exhibits characteristics typical of highly speculative memecoins. ")
        parts.append("Liquidity can evaporate quickly.")
    
    return ''.join(parts)


# =============================================================================
# PRIVACY COIN METRICS
# =============================================================================

def get_privacy_metrics(ticker: str) -> Dict[str, Any]:
    """
    Privacy coin-specific analysis
    
    Focus:
    - Exchange availability (delisting risk)
    - Regulatory sensitivity
    - Volume spikes (often regulatory-driven)
    
    Returns:
        dict: Privacy coin metrics
    """
    
    coin_data = _get_coin_data(ticker)

    if not coin_data:
        return {'error': f'Data unavailable for {ticker}'}

    volume = coin_data.get('total_volume', 0)
    market_cap = coin_data.get('market_cap', 0)
    price_change_24h = coin_data.get('price_change_percentage_24h', 0)

    # Regulatory risk indicators
    regulatory_risk = _assess_regulatory_risk(ticker, volume, market_cap)
    
    # Generate interpretation
    interpretation = _generate_privacy_interpretation(ticker, regulatory_risk, volume, price_change_24h)
    
    return {
        'asset_type': 'PRIVACY',
        'ticker': ticker,
        'regulatory_risk': regulatory_risk,
        'volume_24h': volume,
        'volume_formatted': format_large_number(volume),
        'price_change_24h': price_change_24h,
        'interpretation': interpretation,
        'timestamp': get_current_timestamp(),
        'note': 'Monitor regulatory news closely for privacy coins'
    }


def _assess_regulatory_risk(ticker: str, volume: float, market_cap: float) -> str:
    """Assess regulatory risk for privacy coins"""
    
    # Privacy coins face ongoing regulatory scrutiny
    # Volume spikes can indicate regulatory news
    
    velocity = calculate_velocity(volume, market_cap)
    
    if velocity > 0.3:
        return 'ELEVATED (Unusual activity - check news)'
    elif market_cap < 500_000_000:
        return 'HIGH (Small cap + regulatory pressure)'
    else:
        return 'MODERATE (Ongoing regulatory scrutiny)'


def _generate_privacy_interpretation(ticker: str, reg_risk: str, volume: float, price_change: float) -> str:
    """Generate privacy coin interpretation"""
    
    parts = []
    
    parts.append(f"{ticker} is a privacy-focused cryptocurrency facing ongoing regulatory scrutiny. ")
    parts.append(f"Regulatory risk level: {reg_risk}. ")
    
    if abs(price_change) > 15:
        parts.append(f"Significant price movement ({price_change:.1f}%) - check for regulatory news or exchange listings/delistings. ")
    
    parts.append("Key risks: exchange delisting, regulatory actions, jurisdictional bans. ")
    parts.append("Monitor news closely as privacy coins are regulatory targets.")
    
    return ''.join(parts)


# =============================================================================
# DEFI METRICS
# =============================================================================

def get_defi_metrics(ticker: str) -> Dict[str, Any]:
    """
    DeFi protocol-specific analysis
    
    Focus:
    - TVL (Total Value Locked) - not available via CoinGecko
    - Yield/APY changes
    - Governance activity
    - Exploit risks
    
    Returns:
        dict: DeFi metrics
    
    Note: Full DeFi analysis requires DeFiLlama API
    """
    
    aggregator = _get_aggregator()
    coin_data = _get_coin_data(ticker)

    if not coin_data:
        return {'error': f'Data unavailable for {ticker}'}

    market_cap = coin_data.get('market_cap', 0)
    price_change_24h = coin_data.get('price_change_percentage_24h', 0)

    # Get DeFi-specific data from DeFiLlama
    defi_data = aggregator.get_defi_metrics(ticker)
    tvl = 0
    tvl_change_24h = 0
    if defi_data:
        tvl = defi_data.tvl_usd
        tvl_change_24h = defi_data.tvl_change_24h

    # DeFi risk assessment
    defi_risk = _assess_defi_risk(ticker, market_cap, price_change_24h)

    # Generate interpretation
    interpretation = _generate_defi_interpretation(ticker, defi_risk, price_change_24h)

    # Add TVL info to interpretation if available
    if tvl > 0:
        interpretation += f" TVL: ${format_large_number(tvl)} ({tvl_change_24h:+.1f}% 24h)."

    return {
        'asset_type': 'DEFI',
        'ticker': ticker,
        'market_cap': market_cap,
        'market_cap_formatted': format_large_number(market_cap),
        'price_change_24h': price_change_24h,
        'tvl': tvl,
        'tvl_formatted': format_large_number(tvl) if tvl > 0 else 'N/A',
        'tvl_change_24h': tvl_change_24h,
        'defi_risk': defi_risk,
        'interpretation': interpretation,
        'timestamp': get_current_timestamp()
    }


def _assess_defi_risk(ticker: str, market_cap: float, price_change: float) -> str:
    """Assess DeFi-specific risks"""
    
    if abs(price_change) > 20:
        return 'HIGH (Unusual volatility - check for exploits or governance changes)'
    elif market_cap < 500_000_000:
        return 'MEDIUM (Smaller protocols carry higher risk)'
    else:
        return 'LOW-MEDIUM (Established protocol)'


def _generate_defi_interpretation(ticker: str, risk: str, price_change: float) -> str:
    """Generate DeFi protocol interpretation"""
    
    parts = []
    
    parts.append(f"{ticker} is a DeFi protocol token. ")
    parts.append(f"Risk level: {risk}. ")
    
    if abs(price_change) > 15:
        parts.append(f"Significant price movement ({price_change:.1f}%) detected. ")
        parts.append("Check for: protocol exploits, governance proposals, TVL changes, yield adjustments. ")
    
    parts.append("Key metrics to monitor: TVL (Total Value Locked), protocol revenue, active users, ")
    parts.append("governance activity. Full analysis requires DeFiLlama integration.")
    
    return ''.join(parts)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Pillar E: Sector-Specific...")
    print("=" * 70)
    
    # Test memecoin analysis
    print("\n🎭 MEMECOIN ANALYSIS - DOGE")
    print("-" * 70)
    memecoin = get_memecoin_metrics('DOGE')
    print(f"Velocity:             {memecoin['velocity']:.3f}")
    print(f"Category:             {memecoin['velocity_category']}")
    print(f"Activity:             {memecoin['activity_level'].replace('_', ' ').title()}")
    print(f"Risk:                 {memecoin['memecoin_risk']}")
    print("\nInterpretation:")
    print(memecoin['interpretation'])
    
    # Test privacy coin analysis
    print("\n\n🔒 PRIVACY COIN ANALYSIS - XMR")
    print("-" * 70)
    privacy = get_privacy_metrics('XMR')
    print(f"Regulatory Risk:      {privacy['regulatory_risk']}")
    print(f"24h Volume:           ${privacy['volume_formatted']}")
    print("\nInterpretation:")
    print(privacy['interpretation'])
    
    # Test DeFi analysis
    print("\n\n🏦 DEFI ANALYSIS - AAVE")
    print("-" * 70)
    defi = get_defi_metrics('AAVE')
    print(f"Market Cap:           ${defi['market_cap_formatted']}")
    print(f"DeFi Risk:            {defi['defi_risk']}")
    print("\nInterpretation:")
    print(defi['interpretation'])
    
    print("\n\n=" * 70)
    print("✅ Pillar E: Sector-Specific - COMPLETE")
    print("\nThis pillar adds specialized analysis for memecoins, privacy, and DeFi.")
