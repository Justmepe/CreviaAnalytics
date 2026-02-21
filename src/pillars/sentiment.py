"""
File 6: Pillar A - Market Sentiment
Dependencies: DataAggregator (unified data layer)
Status: ✅ COMPLETE - Updated to use DataAggregator

Purpose:
- Analyze global market sentiment
- Fear & Greed Index, funding rates, social volume

This pillar applies to ALL assets - it's the global market context
"""

from typing import Dict, Any, Optional
from src.utils.helpers import categorize_funding_rate, get_current_timestamp

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
# PILLAR A: MARKET SENTIMENT ANALYSIS
# =============================================================================

def analyze_sentiment(reference_ticker: str = 'BTC') -> Dict[str, Any]:
    """
    Analyze global market sentiment
    
    This pillar provides context for ALL assets. It answers:
    "What kind of market are we in right now?"
    
    Args:
        reference_ticker: Use this ticker for funding rate (default: BTC)
    
    Returns:
        dict: {
            'environment': 'risk-on' | 'risk-off' | 'neutral',
            'crowd_level': 'quiet' | 'moderate' | 'crowded',
            'leverage_intensity': 'low' | 'medium' | 'high',
            'fear_greed_index': 45,
            'fear_greed_classification': 'Fear',
            'btc_funding_rate': 0.0001,
            'funding_signal': 'neutral' | 'long_heavy' | 'short_heavy',
            'market_phase': 'accumulation' | 'markup' | 'distribution' | 'markdown',
            'timestamp': 1640000000,
            'interpretation': 'Detailed explanation...'
        }
    """
    
    # Fetch sentiment data from unified data layer
    aggregator = _get_aggregator()

    # Get global metrics (includes Fear & Greed)
    global_metrics = aggregator.get_global_metrics()

    # Get BTC derivatives (includes funding rate)
    btc_deriv = aggregator.get_derivatives(reference_ticker)

    # Extract values from new data layer
    if global_metrics:
        fg_value = global_metrics.fear_greed_index
        fg_classification = global_metrics.fear_greed_classification
        fear_greed_data = {
            'value': fg_value,
            'value_classification': fg_classification
        }
    else:
        fg_value = 50
        fg_classification = 'Neutral'
        fear_greed_data = None

    if btc_deriv:
        funding_rate = btc_deriv.funding_rate
        btc_funding = {
            'funding_rate': funding_rate,
            'mark_price': btc_deriv.mark_price
        }
    else:
        funding_rate = 0
        btc_funding = None

    funding_analysis = categorize_funding_rate(funding_rate)
    
    # Determine market environment
    environment = _determine_environment(fg_value, funding_rate)
    
    # Determine crowd level
    crowd_level = _determine_crowd_level(fg_value, abs(funding_rate))
    
    # Determine leverage intensity
    leverage_intensity = funding_analysis['risk_level']
    
    # Determine market phase
    market_phase = _determine_market_phase(fg_value, funding_rate)
    
    # Generate interpretation
    interpretation = _generate_interpretation(
        environment, crowd_level, leverage_intensity,
        fg_value, fg_classification, funding_rate
    )
    
    return {
        'environment': environment,
        'crowd_level': crowd_level,
        'leverage_intensity': leverage_intensity.lower(),
        'fear_greed_index': fg_value,
        'fear_greed_classification': fg_classification,
        'btc_funding_rate': funding_rate,
        'funding_signal': funding_analysis['signal'],
        'market_phase': market_phase,
        'timestamp': get_current_timestamp(),
        'interpretation': interpretation,
        'raw_data': {
            'fear_greed': fear_greed_data,
            'btc_funding': btc_funding
        }
    }


# =============================================================================
# SENTIMENT ANALYSIS LOGIC
# =============================================================================

def _determine_environment(fg_value: int, funding_rate: float) -> str:
    """
    Determine if market is risk-on, risk-off, or neutral
    
    Logic:
    - Risk-on: High greed + positive funding
    - Risk-off: High fear + negative funding
    - Neutral: Balanced sentiment
    """
    
    if fg_value >= 70 and funding_rate > 0:
        return 'risk-on'
    elif fg_value <= 30 and funding_rate < 0:
        return 'risk-off'
    elif fg_value >= 60:
        return 'risk-on'
    elif fg_value <= 40:
        return 'risk-off'
    else:
        return 'neutral'


def _determine_crowd_level(fg_value: int, abs_funding: float) -> str:
    """
    Determine how crowded the market is
    
    Logic:
    - Crowded: Extreme sentiment + high leverage
    - Moderate: Normal activity
    - Quiet: Low activity, balanced sentiment
    """
    
    is_extreme_sentiment = fg_value > 75 or fg_value < 25
    is_high_leverage = abs_funding > 0.02
    
    if is_extreme_sentiment and is_high_leverage:
        return 'crowded'
    elif is_extreme_sentiment or is_high_leverage:
        return 'moderate'
    else:
        return 'quiet'


def _determine_market_phase(fg_value: int, funding_rate: float) -> str:
    """
    Identify which phase of market cycle
    
    Phases:
    - Accumulation: Low fear, negative funding
    - Markup: Rising greed, positive funding building
    - Distribution: Extreme greed, high funding
    - Markdown: Rising fear, negative funding
    """
    
    if fg_value < 40 and funding_rate < 0:
        return 'accumulation'
    elif 40 <= fg_value < 70 and funding_rate >= 0:
        return 'markup'
    elif fg_value >= 70 and funding_rate > 0.01:
        return 'distribution'
    elif fg_value < 40 and funding_rate >= 0:
        return 'markdown'
    else:
        return 'transition'


def _generate_interpretation(
    environment: str,
    crowd_level: str,
    leverage_intensity: str,
    fg_value: int,
    fg_classification: str,
    funding_rate: float
) -> str:
    """
    Generate human-readable interpretation of sentiment
    
    Returns:
        str: Clear explanation of current market conditions
    """
    
    parts = []
    
    # Environment interpretation
    env_text = {
        'risk-on': 'The market is in a risk-on environment with investors showing appetite for speculative assets.',
        'risk-off': 'The market is in a risk-off environment with investors showing caution and defensive positioning.',
        'neutral': 'The market sentiment is relatively balanced, without strong directional bias.'
    }
    parts.append(env_text[environment])
    
    # Fear & Greed context
    parts.append(f"The Fear & Greed Index is at {fg_value} ({fg_classification}), ")
    
    if fg_value < 25:
        parts.append("indicating extreme fear in the market.")
    elif fg_value < 45:
        parts.append("showing cautious sentiment.")
    elif fg_value < 55:
        parts.append("reflecting neutral sentiment.")
    elif fg_value < 75:
        parts.append("indicating greed is building.")
    else:
        parts.append("showing extreme greed.")
    
    # Funding rate context
    if abs(funding_rate) < 0.005:
        parts.append(" Funding rates are neutral, suggesting balanced positioning.")
    elif funding_rate > 0.01:
        parts.append(f" Funding rates are elevated at {funding_rate*100:.3f}%, indicating overcrowded long positions.")
    elif funding_rate < -0.01:
        parts.append(f" Funding rates are negative at {funding_rate*100:.3f}%, indicating overcrowded short positions.")
    elif funding_rate > 0:
        parts.append(f" Funding rates are slightly positive at {funding_rate*100:.3f}%, with more longs than shorts.")
    else:
        parts.append(f" Funding rates are slightly negative at {funding_rate*100:.3f}%, with more shorts than longs.")
    
    # Crowd level warning
    if crowd_level == 'crowded':
        parts.append(" ⚠️ Market appears crowded - risk of sudden reversals is elevated.")
    
    return ''.join(parts)


# =============================================================================
# SENTIMENT TRENDS (Optional Enhancement)
# =============================================================================

def analyze_sentiment_trend(days: int = 7) -> Dict[str, Any]:
    """
    Analyze sentiment trends over time (future enhancement)
    
    Args:
        days: Number of days to analyze
    
    Returns:
        dict: Trend analysis
    
    Note: Currently returns basic data. Can be enhanced with historical data.
    """
    
    current = analyze_sentiment()
    
    return {
        'current': current,
        'trend': 'stable',  # TODO: Calculate from historical data
        'days_analyzed': days,
        'note': 'Historical trend analysis requires time-series data storage'
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Pillar A: Market Sentiment...")
    print("=" * 70)
    
    # Analyze current sentiment
    sentiment = analyze_sentiment()
    
    print("\n📊 MARKET SENTIMENT ANALYSIS")
    print("-" * 70)
    print(f"Environment:          {sentiment['environment'].upper()}")
    print(f"Crowd Level:          {sentiment['crowd_level'].title()}")
    print(f"Leverage Intensity:   {sentiment['leverage_intensity'].title()}")
    print(f"Market Phase:         {sentiment['market_phase'].title()}")
    print()
    print(f"Fear & Greed Index:   {sentiment['fear_greed_index']} ({sentiment['fear_greed_classification']})")
    print(f"BTC Funding Rate:     {sentiment['btc_funding_rate']*100:.4f}%")
    print(f"Funding Signal:       {sentiment['funding_signal'].replace('_', ' ').title()}")
    print()
    print("Interpretation:")
    print(sentiment['interpretation'])
    print()
    print("=" * 70)
    print("✅ Pillar A: Market Sentiment - COMPLETE")
    print()
    print("This pillar provides global context for all asset analysis.")