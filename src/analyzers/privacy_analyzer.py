"""
File 13: Privacy Coin Analyzer
Dependencies: All pillars
Active Pillars: A, B, D, E
Status: ✅ COMPLETE

Purpose:
- Analyze privacy coins with focus on regulatory risk and exchange availability
- Monitor delisting threats and jurisdictional restrictions
"""

from typing import Dict, Any
from src.pillars.sentiment import analyze_sentiment
from src.pillars.news import analyze_news
from src.pillars.onchain import analyze_onchain
from src.pillars.sector_specific import get_privacy_metrics
from src.utils.helpers import get_current_timestamp


# =============================================================================
# PRIVACY COIN ANALYZER
# =============================================================================

def analyze_privacy_coin(ticker: str, timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    Complete analysis for privacy coins
    
    Activates Pillars: A (Sentiment), B (News), D (On-Chain), E (Privacy-Specific)
    
    Focus Areas:
    - Regulatory risk and developments
    - Exchange delisting threats
    - Jurisdictional restrictions
    - Volume spikes (often regulatory-driven)
    
    Args:
        ticker: Privacy coin symbol (e.g., 'XMR', 'ZEC', 'DASH')
        timeframe_hours: Analysis window
    
    Returns:
        dict: Complete 4-section analysis
    """
    
    print(f"Analyzing privacy coin {ticker}...")
    
    # Pillar A: Market Sentiment (Global Context)
    sentiment = analyze_sentiment()
    
    # Pillar B: News & Events (Critical for privacy coins)
    news = analyze_news(ticker, timeframe_hours)
    
    # Pillar D: On-Chain & Flow
    onchain = analyze_onchain(ticker)
    
    # Pillar E: Privacy-Specific Metrics
    privacy_metrics = get_privacy_metrics(ticker)
    
    # Generate 4-section analysis
    snapshot = _generate_snapshot(ticker, onchain, privacy_metrics)
    pressure = _generate_pressure(sentiment, onchain, news)
    events = _generate_events(news, privacy_metrics)
    risks = _generate_risks(privacy_metrics, news, sentiment)
    
    return {
        'ticker': ticker,
        'asset_type': 'PRIVACY',
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
            'privacy_metrics': privacy_metrics
        }
    }


def _generate_snapshot(ticker: str, onchain: Dict, privacy: Dict) -> Dict[str, Any]:
    """Section 1: Snapshot"""
    
    volume = onchain.get('volume_24h', 0)
    volume_formatted = onchain.get('volume_formatted', '$0')
    velocity = onchain.get('velocity', 0)
    price_change = privacy.get('price_change_24h', 0)
    
    # Check for unusual volume (potential regulatory event)
    volume_status = 'ELEVATED' if velocity > 0.3 else 'NORMAL'
    
    return {
        'title': f'{ticker} Privacy Coin Snapshot',
        'volume': {
            'value': volume,
            'display': volume_formatted,
            'velocity': velocity,
            'status': volume_status
        },
        'price_change_24h': price_change,
        'regulatory_alert': velocity > 0.3,
        'summary': f'{ticker} volume: {volume_formatted} (velocity: {velocity:.3f}). '
                   f'Price 24h: {price_change:+.1f}%. '
                   f'{"⚠️ Unusual volume - check regulatory news" if velocity > 0.3 else "Normal activity"}.'
    }


def _generate_pressure(sentiment: Dict, onchain: Dict, news: Dict) -> Dict[str, Any]:
    """Section 2: Market Pressure"""
    
    environment = sentiment.get('environment', 'neutral')
    holder_behavior = onchain.get('holder_behavior', 'neutral')
    velocity = onchain.get('velocity', 0)
    
    # Privacy coins often see pressure from regulatory news
    has_regulatory_news = any(
        'regulation' in e.get('categories', [])
        for e in news.get('events', [])
    )
    
    return {
        'title': 'Market Pressure Analysis',
        'global_environment': environment,
        'holder_dynamics': {
            'behavior': holder_behavior,
            'interpretation': _interpret_holder_behavior(holder_behavior, has_regulatory_news)
        },
        'volume_pressure': {
            'level': 'ELEVATED' if velocity > 0.3 else 'NORMAL',
            'regulatory_driven': has_regulatory_news and velocity > 0.2
        },
        'regulatory_pressure': {
            'detected': has_regulatory_news,
            'impact': 'Likely driving current activity' if has_regulatory_news and velocity > 0.2 else 'Background concern'
        },
        'summary': f'Holder behavior: {holder_behavior.replace("_", " ")}. '
                   f'{"Regulatory news detected - likely driving activity" if has_regulatory_news else "No immediate regulatory triggers"}. '
                   f'Volume pressure: {"ELEVATED" if velocity > 0.3 else "NORMAL"}.'
    }


def _interpret_holder_behavior(behavior: str, regulatory_news: bool) -> str:
    """Interpret holder behavior in context of regulatory environment"""
    
    if 'distribution' in behavior and regulatory_news:
        return 'Selling in response to regulatory concerns'
    elif 'holding' in behavior and regulatory_news:
        return 'Strong conviction despite regulatory pressure'
    elif 'distribution' in behavior:
        return 'Profit-taking or delisting concerns'
    else:
        return 'Normal holder behavior'


def _generate_events(news: Dict, privacy: Dict) -> Dict[str, Any]:
    """Section 3: Events - Regulatory Focus"""
    
    events = news.get('events', [])
    summary = news.get('summary', {})
    
    # Filter for regulatory events
    regulatory_events = [
        e for e in events
        if 'regulation' in e.get('categories', [])
    ]
    
    # Check for exchange-related news
    exchange_events = [
        e for e in events
        if any(kw in e.get('title', '').lower() for kw in ['delist', 'exchange', 'remove', 'suspend'])
    ]
    
    return {
        'title': 'Events & Regulatory Context',
        'total_events': summary.get('total_events', 0),
        'regulatory_events': {
            'count': len(regulatory_events),
            'items': [e.get('title', '') for e in regulatory_events[:3]]
        },
        'exchange_events': {
            'count': len(exchange_events),
            'items': [e.get('title', '') for e in exchange_events[:3]],
            'risk_level': 'HIGH' if len(exchange_events) > 0 else 'NORMAL'
        },
        'regulatory_risk_level': privacy.get('regulatory_risk', 'MODERATE'),
        'summary': f"{summary.get('total_events', 0)} events found. "
                   f"{len(regulatory_events)} regulatory, {len(exchange_events)} exchange-related. "
                   f"{'⚠️ Exchange delisting risk detected' if len(exchange_events) > 0 else 'No immediate delisting threats'}."
    }


def _generate_risks(privacy: Dict, news: Dict, sentiment: Dict) -> Dict[str, Any]:
    """Section 4: Risks - Privacy Coin Specific"""
    
    regulatory_risk = privacy.get('regulatory_risk', 'MODERATE')
    
    # Count regulatory events
    events = news.get('events', [])
    reg_event_count = sum(
        1 for e in events
        if 'regulation' in e.get('categories', [])
    )
    
    return {
        'title': 'Privacy Coin Risk Assessment',
        'regulatory_risk': {
            'level': regulatory_risk,
            'recent_events': reg_event_count,
            'description': _describe_regulatory_risk(regulatory_risk, reg_event_count)
        },
        'delisting_risk': {
            'level': _assess_delisting_risk(news),
            'factors': _get_delisting_factors(news)
        },
        'jurisdictional_risk': {
            'level': 'ONGOING',
            'description': 'Privacy coins face regulatory scrutiny in multiple jurisdictions'
        },
        'liquidity_risk': {
            'level': 'ELEVATED',
            'description': 'Delisting events can severely impact liquidity'
        },
        'overall_assessment': {
            'primary_risk': 'Regulatory & Exchange Availability',
            'recommendation': _get_privacy_recommendation(regulatory_risk, reg_event_count)
        },
        'summary': f'Regulatory risk: {regulatory_risk}. '
                   f'{reg_event_count} recent regulatory events. '
                   f'Delisting risk: {_assess_delisting_risk(news)}. '
                   f'{_get_privacy_recommendation(regulatory_risk, reg_event_count)}'
    }


def _describe_regulatory_risk(risk_level: str, event_count: int) -> str:
    """Describe current regulatory risk level"""
    
    if event_count > 2:
        return f'{risk_level} - Active regulatory developments ({event_count} recent events)'
    elif 'ELEVATED' in risk_level:
        return 'Elevated - Unusual activity detected, monitor news closely'
    else:
        return 'Ongoing regulatory scrutiny (standard for privacy coins)'


def _assess_delisting_risk(news: Dict) -> str:
    """Assess current delisting risk"""
    
    events = news.get('events', [])
    
    # Check for delisting keywords
    delisting_keywords = ['delist', 'remove', 'suspend', 'withdraw']
    has_delisting_news = any(
        any(kw in e.get('title', '').lower() for kw in delisting_keywords)
        for e in events
    )
    
    if has_delisting_news:
        return 'HIGH (Active delisting events)'
    else:
        return 'MODERATE (Background risk)'


def _get_delisting_factors(news: Dict) -> list:
    """List delisting risk factors"""
    
    factors = ['Ongoing regulatory pressure']
    
    events = news.get('events', [])
    if any('regulation' in e.get('categories', []) for e in events):
        factors.append('Recent regulatory developments')
    
    factors.append('Limited exchange availability')
    factors.append('Jurisdictional bans possible')
    
    return factors


def _get_privacy_recommendation(risk_level: str, event_count: int) -> str:
    """Generate recommendation based on risk"""
    
    if 'ELEVATED' in risk_level or event_count > 2:
        return '⚠️ Monitor regulatory news daily - conditions can change rapidly'
    else:
        return 'Standard privacy coin risk - monitor for regulatory developments and exchange announcements'


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Privacy Coin Analyzer...")
    print("=" * 70)
    
    analysis = analyze_privacy_coin('XMR')
    
    print(f"\n🔒 {analysis['ticker']} PRIVACY COIN ANALYSIS")
    print("=" * 70)
    
    print("\n[1] SNAPSHOT")
    print(analysis['snapshot']['summary'])
    
    print("\n[2] MARKET PRESSURE")
    print(analysis['pressure']['summary'])
    
    print("\n[3] REGULATORY EVENTS")
    print(analysis['events']['summary'])
    
    print("\n[4] RISKS")
    print(analysis['risks']['summary'])
    
    print("\n" + "=" * 70)
    print("✅ Privacy Coin Analyzer - COMPLETE")
    print(f"Active Pillars: {', '.join(analysis['active_pillars'])}")
