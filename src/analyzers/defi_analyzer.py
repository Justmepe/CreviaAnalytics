"""
File 14: DeFi Protocol Analyzer
Dependencies: All pillars
Active Pillars: A, B, D, E
Status: ✅ COMPLETE

Purpose:
- Analyze DeFi protocol tokens with focus on TVL, governance, and protocol health
- Monitor for exploits, yield changes, and liquidity migrations
"""

from typing import Dict, Any
from src.pillars.sentiment import analyze_sentiment
from src.pillars.news import analyze_news
from src.pillars.onchain import analyze_onchain
from src.pillars.sector_specific import get_defi_metrics
from src.utils.helpers import get_current_timestamp


# =============================================================================
# DEFI PROTOCOL ANALYZER
# =============================================================================

def analyze_defi_protocol(ticker: str, timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    Complete analysis for DeFi protocol tokens
    
    Activates Pillars: A (Sentiment), B (News), D (On-Chain), E (DeFi-Specific)
    
    Focus Areas:
    - Protocol health and metrics
    - TVL changes (requires DeFiLlama)
    - Governance activity
    - Exploit risks
    - Yield/APY fluctuations
    
    Args:
        ticker: DeFi protocol symbol (e.g., 'AAVE', 'UNI', 'CRV')
        timeframe_hours: Analysis window
    
    Returns:
        dict: Complete 4-section analysis
    """
    
    print(f"Analyzing DeFi protocol {ticker}...")
    
    # Pillar A: Market Sentiment (Global Context)
    sentiment = analyze_sentiment()
    
    # Pillar B: News & Events (Critical for protocols)
    news = analyze_news(ticker, timeframe_hours)
    
    # Pillar D: On-Chain & Flow
    onchain = analyze_onchain(ticker)
    
    # Pillar E: DeFi-Specific Metrics
    defi_metrics = get_defi_metrics(ticker)
    
    # Generate 4-section analysis
    snapshot = _generate_snapshot(ticker, onchain, defi_metrics)
    pressure = _generate_pressure(sentiment, onchain)
    events = _generate_events(news, defi_metrics)
    risks = _generate_risks(defi_metrics, news, onchain)
    
    return {
        'ticker': ticker,
        'asset_type': 'DEFI',
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
            'defi_metrics': defi_metrics
        }
    }


def _generate_snapshot(ticker: str, onchain: Dict, defi: Dict) -> Dict[str, Any]:
    """Section 1: Snapshot"""
    
    market_cap = defi.get('market_cap', 0)
    market_cap_formatted = defi.get('market_cap_formatted', '$0')
    price_change = defi.get('price_change_24h', 0)
    velocity = onchain.get('velocity', 0)
    
    return {
        'title': f'{ticker} DeFi Protocol Snapshot',
        'market_cap': {
            'value': market_cap,
            'display': market_cap_formatted
        },
        'price_change_24h': price_change,
        'token_velocity': velocity,
        'protocol_size': _categorize_protocol_size(market_cap),
        'summary': f'{ticker} market cap: {market_cap_formatted}. '
                   f'Price 24h: {price_change:+.1f}%. '
                   f'Token velocity: {velocity:.3f}. '
                   f'Protocol size: {_categorize_protocol_size(market_cap)}.'
    }


def _categorize_protocol_size(market_cap: float) -> str:
    """Categorize DeFi protocol by size"""
    
    if market_cap > 5_000_000_000:
        return 'Large (Top-tier)'
    elif market_cap > 1_000_000_000:
        return 'Medium (Established)'
    elif market_cap > 100_000_000:
        return 'Small (Emerging)'
    else:
        return 'Micro (High Risk)'


def _generate_pressure(sentiment: Dict, onchain: Dict) -> Dict[str, Any]:
    """Section 2: Market Pressure"""
    
    environment = sentiment.get('environment', 'neutral')
    holder_behavior = onchain.get('holder_behavior', 'neutral')
    velocity = onchain.get('velocity', 0)
    
    # DeFi-specific pressure interpretation
    is_high_activity = velocity > 0.2
    
    return {
        'title': 'Protocol Activity & Pressure',
        'defi_environment': {
            'global_risk_sentiment': environment,
            'impact': 'DeFi sensitive to risk-off moves' if environment == 'risk-off' else 'Favorable for DeFi'
        },
        'token_dynamics': {
            'velocity': velocity,
            'activity_level': 'HIGH' if is_high_activity else 'MODERATE',
            'holder_behavior': holder_behavior
        },
        'protocol_pressure': {
            'level': _assess_protocol_pressure(velocity, holder_behavior),
            'interpretation': _interpret_protocol_pressure(velocity, holder_behavior)
        },
        'summary': f'Global sentiment: {environment}. '
                   f'Token velocity: {velocity:.3f} ({"HIGH" if is_high_activity else "MODERATE"}). '
                   f'Holder behavior: {holder_behavior.replace("_", " ")}. '
                   f'{_interpret_protocol_pressure(velocity, holder_behavior)}'
    }


def _assess_protocol_pressure(velocity: float, holder_behavior: str) -> str:
    """Assess overall protocol pressure"""
    
    if velocity > 0.3 and 'distribution' in holder_behavior:
        return 'ELEVATED (Selling Pressure)'
    elif velocity > 0.2:
        return 'MODERATE (Active Trading)'
    else:
        return 'LOW (Stable)'


def _interpret_protocol_pressure(velocity: float, holder_behavior: str) -> str:
    """Interpret protocol pressure"""
    
    if velocity > 0.3 and 'distribution' in holder_behavior:
        return 'Token selling pressure detected - monitor for protocol developments'
    elif 'holding' in holder_behavior:
        return 'Token holders showing conviction'
    else:
        return 'Normal protocol token dynamics'


def _generate_events(news: Dict, defi: Dict) -> Dict[str, Any]:
    """Section 3: Events - Protocol Focus"""
    
    events = news.get('events', [])
    summary = news.get('summary', {})
    
    # Categorize DeFi-relevant events
    governance_events = [
        e for e in events
        if any(kw in e.get('title', '').lower() for kw in ['governance', 'proposal', 'vote', 'dao'])
    ]
    
    security_events = [
        e for e in events
        if any(kw in e.get('title', '').lower() for kw in ['hack', 'exploit', 'vulnerability', 'audit', 'security'])
    ]
    
    protocol_events = [
        e for e in events
        if any(kw in e.get('title', '').lower() for kw in ['upgrade', 'tvl', 'yield', 'liquidity', 'integration'])
    ]
    
    return {
        'title': 'Protocol Events & Developments',
        'total_events': summary.get('total_events', 0),
        'governance_activity': {
            'count': len(governance_events),
            'items': [e.get('title', '') for e in governance_events[:2]],
            'level': 'HIGH' if len(governance_events) > 2 else 'MODERATE' if len(governance_events) > 0 else 'LOW'
        },
        'security_events': {
            'count': len(security_events),
            'items': [e.get('title', '') for e in security_events[:2]],
            'alert': len(security_events) > 0
        },
        'protocol_updates': {
            'count': len(protocol_events),
            'items': [e.get('title', '') for e in protocol_events[:2]]
        },
        'summary': f"{summary.get('total_events', 0)} events: "
                   f"{len(governance_events)} governance, "
                   f"{len(security_events)} security, "
                   f"{len(protocol_events)} protocol updates. "
                   f"{'🚨 SECURITY EVENT DETECTED' if len(security_events) > 0 else 'No security concerns'}."
    }


def _generate_risks(defi: Dict, news: Dict, onchain: Dict) -> Dict[str, Any]:
    """Section 4: Risks - DeFi Specific"""
    
    defi_risk = defi.get('defi_risk', 'MEDIUM')
    market_cap = defi.get('market_cap', 0)
    price_change = defi.get('price_change_24h', 0)
    
    # Check for security events
    events = news.get('events', [])
    has_security_concerns = any(
        any(kw in e.get('title', '').lower() for kw in ['hack', 'exploit', 'vulnerability'])
        for e in events
    )
    
    return {
        'title': 'DeFi Protocol Risk Assessment',
        'protocol_risk': {
            'level': defi_risk,
            'market_cap_category': _categorize_protocol_size(market_cap),
            'description': _describe_protocol_risk(defi_risk, market_cap)
        },
        'smart_contract_risk': {
            'level': 'CRITICAL' if has_security_concerns else 'ONGOING',
            'recent_events': has_security_concerns,
            'description': '🚨 Recent security concerns detected' if has_security_concerns else 'Standard smart contract risk'
        },
        'liquidity_risk': {
            'level': _assess_defi_liquidity_risk(market_cap, price_change),
            'factors': _get_liquidity_factors(market_cap)
        },
        'governance_risk': {
            'level': 'STANDARD',
            'description': 'Protocol subject to governance decisions that can affect tokenomics'
        },
        'metrics_to_monitor': {
            'critical': ['TVL changes', 'Yield/APY shifts', 'Security audits', 'Governance proposals'],
            'note': 'Full analysis requires DeFiLlama integration for TVL data'
        },
        'overall_assessment': {
            'risk_level': defi_risk,
            'recommendation': _get_defi_recommendation(defi_risk, has_security_concerns, market_cap)
        },
        'summary': f'Protocol risk: {defi_risk}. '
                   f'Smart contract risk: {"CRITICAL" if has_security_concerns else "ONGOING"}. '
                   f'{_get_defi_recommendation(defi_risk, has_security_concerns, market_cap)}'
    }


def _describe_protocol_risk(risk_level: str, market_cap: float) -> str:
    """Describe current protocol risk"""
    
    size = _categorize_protocol_size(market_cap)
    
    if 'HIGH' in risk_level:
        return f'{risk_level} - Unusual volatility or small protocol size ({size})'
    else:
        return f'{risk_level} - {size} protocol with standard DeFi risks'


def _assess_defi_liquidity_risk(market_cap: float, price_change: float) -> str:
    """Assess liquidity risk for DeFi protocol"""
    
    if market_cap < 100_000_000:
        return 'HIGH (Small protocol, limited liquidity)'
    elif abs(price_change) > 20:
        return 'ELEVATED (High volatility)'
    else:
        return 'MODERATE'


def _get_liquidity_factors(market_cap: float) -> list:
    """List liquidity risk factors"""
    
    factors = []
    
    if market_cap < 500_000_000:
        factors.append('Smaller protocol - liquidity can be limited')
    
    factors.append('Token liquidity tied to protocol usage')
    factors.append('TVL changes can impact token value')
    
    return factors if factors else ['Standard DeFi liquidity risks']


def _get_defi_recommendation(risk_level: str, security_concerns: bool, market_cap: float) -> str:
    """Generate DeFi-specific recommendation"""
    
    if security_concerns:
        return '🚨 SECURITY CONCERNS - Investigate immediately before any action'
    elif 'HIGH' in risk_level:
        return '⚠️ Monitor protocol metrics closely - elevated risk detected'
    elif market_cap < 100_000_000:
        return 'Small protocol - higher risk, monitor TVL and usage metrics'
    else:
        return 'Standard DeFi risks - monitor TVL, yields, governance, and security audits'


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing DeFi Protocol Analyzer...")
    print("=" * 70)
    
    analysis = analyze_defi_protocol('AAVE')
    
    print(f"\n🏦 {analysis['ticker']} DEFI PROTOCOL ANALYSIS")
    print("=" * 70)
    
    print("\n[1] SNAPSHOT")
    print(analysis['snapshot']['summary'])
    
    print("\n[2] PROTOCOL PRESSURE")
    print(analysis['pressure']['summary'])
    
    print("\n[3] PROTOCOL EVENTS")
    print(analysis['events']['summary'])
    
    print("\n[4] RISKS")
    print(analysis['risks']['summary'])
    
    print("\n" + "=" * 70)
    print("✅ DeFi Protocol Analyzer - COMPLETE")
    print(f"Active Pillars: {', '.join(analysis['active_pillars'])}")
