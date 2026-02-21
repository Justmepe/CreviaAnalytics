"""
File 12: Memecoin Analyzer
Dependencies: All pillars
Active Pillars: A, B, D, E
Status: ✅ COMPLETE

Purpose:
- Analyze memecoins with focus on velocity, speculation, and social dynamics
- No derivatives analysis (often not available for memecoins)
"""

from typing import Dict, Any
from src.pillars.sentiment import analyze_sentiment
from src.pillars.news import analyze_news
from src.pillars.onchain import analyze_onchain
from src.pillars.sector_specific import get_memecoin_metrics
from src.utils.helpers import get_current_timestamp


# =============================================================================
# MEMECOIN ANALYZER
# =============================================================================

def analyze_memecoin(ticker: str, timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    Complete analysis for memecoins
    
    Activates Pillars: A (Sentiment), B (News), D (On-Chain), E (Memecoin-Specific)
    
    Focus Areas:
    - Volume velocity (critical for memes)
    - Speculation intensity
    - Social momentum vs price
    - Pump/dump pattern detection
    
    Args:
        ticker: Memecoin symbol (e.g., 'DOGE', 'SHIB', 'PEPE')
        timeframe_hours: Analysis window
    
    Returns:
        dict: Complete 4-section analysis
    """
    
    print(f"Analyzing memecoin {ticker}...")
    
    # Pillar A: Market Sentiment (Global Context)
    sentiment = analyze_sentiment()
    
    # Pillar B: News & Events
    news = analyze_news(ticker, timeframe_hours)
    
    # Pillar D: On-Chain & Flow
    onchain = analyze_onchain(ticker)
    
    # Pillar E: Memecoin-Specific Metrics
    memecoin_metrics = get_memecoin_metrics(ticker)
    
    # Generate 4-section analysis
    snapshot = _generate_snapshot(ticker, onchain, memecoin_metrics)
    pressure = _generate_pressure(sentiment, memecoin_metrics, onchain)
    events = _generate_events(news, memecoin_metrics)
    risks = _generate_risks(memecoin_metrics, onchain, sentiment)
    
    return {
        'ticker': ticker,
        'asset_type': 'MEMECOIN',
        'active_pillars': ['A', 'B', 'D', 'E'],
        'timeframe_hours': timeframe_hours,
        'timestamp': get_current_timestamp(),
        
        'snapshot': snapshot,
        'pressure': pressure,
        'events': events,
        'risks': risks,
        
        'pillar_data': {
            'sentiment': sentiment,
            'news': news,
            'onchain': onchain,
            'memecoin_metrics': memecoin_metrics
        }
    }


def _generate_snapshot(ticker: str, onchain: Dict, memecoin: Dict) -> Dict[str, Any]:
    """Section 1: Snapshot"""
    
    velocity = memecoin.get('velocity', 0)
    velocity_category = memecoin.get('velocity_category', 'Unknown')
    price_change = memecoin.get('price_change_24h', 0)
    volume = onchain.get('volume_24h', 0)
    volume_formatted = onchain.get('volume_formatted', '$0')
    
    return {
        'title': f'{ticker} Memecoin Snapshot',
        'velocity': {
            'value': velocity,
            'category': velocity_category,
            'interpretation': 'Extreme speculation' if velocity > 0.5 else 'High activity' if velocity > 0.3 else 'Moderate'
        },
        'price_change_24h': price_change,
        'volume': {
            'value': volume,
            'display': volume_formatted
        },
        'speculation_level': memecoin.get('speculation_intensity', 'unknown'),
        'summary': f'{ticker} velocity: {velocity:.3f} ({velocity_category}). '
                   f'Price 24h: {price_change:+.1f}%. '
                   f'Volume: {volume_formatted}. '
                   f'Speculation: {memecoin.get("speculation_intensity", "moderate")}.'
    }


def _generate_pressure(sentiment: Dict, memecoin: Dict, onchain: Dict) -> Dict[str, Any]:
    """Section 2: Market Pressure - Memecoin Focus"""
    
    velocity = memecoin.get('velocity', 0)
    activity_level = memecoin.get('activity_level', 'moderate_activity')
    holder_behavior = onchain.get('holder_behavior', 'neutral')
    
    # Determine if pump/dump pattern
    is_pump_dump = velocity > 0.5 or activity_level == 'extreme_speculation'
    
    return {
        'title': 'Speculation Pressure Analysis',
        'global_environment': sentiment.get('environment', 'neutral'),
        'velocity_pressure': {
            'level': 'EXTREME' if velocity > 0.5 else 'HIGH' if velocity > 0.3 else 'MODERATE',
            'value': velocity,
            'interpretation': 'Pump/dump territory' if velocity > 0.5 else 'Heavy speculation' if velocity > 0.3 else 'Normal trading'
        },
        'holder_dynamics': {
            'behavior': holder_behavior,
            'churn': 'High' if 'distribution' in holder_behavior else 'Low'
        },
        'pump_dump_risk': {
            'detected': is_pump_dump,
            'indicators': _get_pump_dump_indicators(velocity, activity_level)
        },
        'summary': f'Velocity pressure: {"EXTREME" if velocity > 0.5 else "HIGH" if velocity > 0.3 else "MODERATE"}. '
                   f'Holder behavior: {holder_behavior.replace("_", " ")}. '
                   f'{"⚠️ PUMP/DUMP PATTERN DETECTED" if is_pump_dump else "Normal memecoin volatility"}.'
    }


def _get_pump_dump_indicators(velocity: float, activity: str) -> list:
    """Identify pump/dump warning signs"""
    indicators = []
    
    if velocity > 0.5:
        indicators.append('Extreme velocity (>50% daily turnover)')
    if velocity > 0.3:
        indicators.append('Very high velocity (>30% daily turnover)')
    if activity == 'extreme_speculation':
        indicators.append('Extreme speculative activity detected')
    
    return indicators if indicators else ['Normal trading patterns']


def _generate_events(news: Dict, memecoin: Dict) -> Dict[str, Any]:
    """Section 3: Events & Social Context"""
    
    events = news.get('events', [])
    summary = news.get('summary', {})
    
    return {
        'title': 'Events & Social Momentum',
        'news_count': summary.get('total_events', 0),
        'social_correlation': _assess_social_correlation(
            summary.get('overall_sentiment', 'neutral'),
            memecoin.get('price_change_24h', 0)
        ),
        'top_events': [
            {
                'title': e.get('title', ''),
                'sentiment': e.get('sentiment', 'neutral')
            }
            for e in events[:3]
        ],
        'summary': news.get('interpretation', 'Limited news coverage - typical for memecoins.')
    }


def _assess_social_correlation(news_sentiment: str, price_change: float) -> str:
    """Check if social sentiment matches price action"""
    
    if news_sentiment == 'positive' and price_change > 10:
        return 'Strong positive correlation'
    elif news_sentiment == 'negative' and price_change < -10:
        return 'Strong negative correlation'
    elif abs(price_change) > 20:
        return 'Divergent - price moving without news'
    else:
        return 'Weak correlation'


def _generate_risks(memecoin: Dict, onchain: Dict, sentiment: Dict) -> Dict[str, Any]:
    """Section 4: Risks - Memecoin Specific"""
    
    memecoin_risk = memecoin.get('memecoin_risk', 'MEDIUM')
    velocity = memecoin.get('velocity', 0)
    holder_behavior = onchain.get('holder_behavior', 'neutral')
    
    return {
        'title': 'Memecoin Risk Assessment',
        'speculation_risk': {
            'level': memecoin_risk,
            'factors': _get_risk_factors(velocity, memecoin_risk)
        },
        'liquidity_risk': {
            'level': 'CRITICAL' if velocity > 0.5 else 'HIGH' if velocity > 0.3 else 'MODERATE',
            'warning': '⚠️ Liquidity can evaporate instantly' if velocity > 0.5 else 'Monitor liquidity closely'
        },
        'holder_risk': {
            'behavior': holder_behavior,
            'stability': 'Low' if 'distribution' in holder_behavior else 'Moderate'
        },
        'overall_assessment': {
            'risk_level': memecoin_risk,
            'recommendation': _get_memecoin_recommendation(memecoin_risk, velocity)
        },
        'summary': f'Memecoin risk: {memecoin_risk}. '
                   f'Liquidity risk: {"CRITICAL" if velocity > 0.5 else "HIGH" if velocity > 0.3 else "MODERATE"}. '
                   f'{_get_memecoin_recommendation(memecoin_risk, velocity)}'
    }


def _get_risk_factors(velocity: float, risk_level: str) -> list:
    """List risk factors for memecoin"""
    factors = []
    
    if velocity > 0.5:
        factors.append('Extreme speculation - pump/dump characteristics')
    if risk_level == 'EXTREME':
        factors.append('Very high volatility')
        factors.append('Liquidity can disappear instantly')
    
    factors.append('No fundamental value backing')
    factors.append('Sentiment-driven price action')
    
    return factors


def _get_memecoin_recommendation(risk_level: str, velocity: float) -> str:
    """Generate risk-appropriate recommendation"""
    
    if risk_level == 'EXTREME' or velocity > 0.5:
        return '🚨 EXTREME RISK - Avoid or use only with funds you can afford to lose entirely'
    elif risk_level == 'HIGH':
        return '⚠️ HIGH RISK - Highly speculative, extreme caution advised'
    elif risk_level == 'MEDIUM':
        return 'MEDIUM RISK - Speculative asset, appropriate position sizing critical'
    else:
        return 'Typical memecoin risk - speculative by nature'


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Memecoin Analyzer...")
    print("=" * 70)
    
    analysis = analyze_memecoin('DOGE')
    
    print(f"\n🎭 {analysis['ticker']} MEMECOIN ANALYSIS")
    print("=" * 70)
    
    print("\n[1] SNAPSHOT")
    print(analysis['snapshot']['summary'])
    
    print("\n[2] SPECULATION PRESSURE")
    print(analysis['pressure']['summary'])
    
    print("\n[3] EVENTS & SOCIAL")
    print(analysis['events']['summary'])
    
    print("\n[4] RISKS")
    print(analysis['risks']['summary'])
    
    print("\n" + "=" * 70)
    print("✅ Memecoin Analyzer - COMPLETE")
    print(f"Active Pillars: {', '.join(analysis['active_pillars'])}")
