"""
File 11: Majors (BTC/ETH) Analyzer
Dependencies: All pillars
Active Pillars: A, B, C, D
Status: ✅ COMPLETE

Purpose:
- Analyze BTC and ETH with focus on macro, derivatives, and institutional activity
- Combines global sentiment, news, derivatives pressure, and on-chain flows
"""

from typing import Dict, Any
from src.pillars.sentiment import analyze_sentiment
from src.pillars.news import analyze_news
from src.pillars.derivatives import analyze_derivatives
from src.pillars.onchain import analyze_onchain
from src.utils.helpers import get_current_timestamp


# =============================================================================
# MAJORS ANALYZER (BTC/ETH)
# =============================================================================

def analyze_major(ticker: str, timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    Complete analysis for major assets (BTC, ETH)
    
    Activates Pillars: A (Sentiment), B (News), C (Derivatives), D (On-Chain)
    
    Focus Areas:
    - Macro market sentiment
    - Institutional news and ETF flows
    - Derivatives pressure and leverage
    - Capital flows and holder behavior
    
    Args:
        ticker: 'BTC' or 'ETH'
        timeframe_hours: Analysis window (default 24h)
    
    Returns:
        dict: Complete 4-section analysis
            - snapshot: What changed
            - pressure: Market pressure breakdown
            - events: Event & context mapping
            - risks: Risk & conditions summary
    """
    
    # Validate ticker
    if ticker.upper() not in ['BTC', 'BITCOIN', 'ETH', 'ETHEREUM']:
        return {
            'error': f'{ticker} is not a major asset. Use BTC or ETH.',
            'timestamp': get_current_timestamp()
        }
    
    ticker_symbol = 'BTC' if ticker.upper() in ['BTC', 'BITCOIN'] else 'ETH'
    
    # Run all active pillars
    print(f"Analyzing {ticker_symbol}...")
    
    # Pillar A: Market Sentiment (Global Context)
    sentiment = analyze_sentiment(ticker_symbol)
    
    # Pillar B: News & Events (Causality)
    news = analyze_news(ticker_symbol, timeframe_hours)
    
    # Pillar C: Derivatives & Leverage (Pressure)
    derivatives = analyze_derivatives(ticker_symbol)
    
    # Pillar D: On-Chain & Flow (Capital Behavior)
    onchain = analyze_onchain(ticker_symbol)
    
    # Generate 4-section analysis
    snapshot = _generate_snapshot_section(ticker_symbol, derivatives, onchain)
    pressure = _generate_pressure_section(sentiment, derivatives)
    events = _generate_events_section(news, sentiment)
    risks = _generate_risks_section(derivatives, sentiment, onchain)
    
    # Add major-specific insights
    insights = _generate_major_insights(ticker_symbol, sentiment, news, derivatives, onchain)
    
    return {
        'ticker': ticker_symbol,
        'asset_type': 'MAJORS',
        'active_pillars': ['A', 'B', 'C', 'D'],
        'timeframe_hours': timeframe_hours,
        'timestamp': get_current_timestamp(),
        
        # 4-Section Output
        'snapshot': snapshot,
        'pressure': pressure,
        'events': events,
        'risks': risks,
        
        # Additional context
        'insights': insights,
        
        # Raw pillar data
        'pillar_data': {
            'sentiment': sentiment,
            'news': news,
            'derivatives': derivatives,
            'onchain': onchain
        }
    }


# =============================================================================
# SECTION 1: SNAPSHOT (What Changed)
# =============================================================================

def _generate_snapshot_section(ticker: str, derivatives: Dict, onchain: Dict) -> Dict[str, Any]:
    """
    Section 1: Snapshot - What Changed in Last 24h
    
    Returns:
        dict: Key metrics that changed
    """
    
    # Extract key metrics
    funding_rate = derivatives.get('funding_rate_percent', 0)
    oi_usd = derivatives.get('open_interest_usd', 0)
    oi_formatted = derivatives.get('oi_formatted', '$0')
    mark_price = derivatives.get('mark_price', 0)
    
    velocity = onchain.get('velocity', 0)
    volume_24h = onchain.get('volume_24h', 0)
    volume_formatted = onchain.get('volume_formatted', '$0')
    
    return {
        'title': f'{ticker} 24h Snapshot',
        'price': {
            'mark_price': mark_price,
            'display': f'${mark_price:,.2f}' if mark_price > 0 else 'N/A'
        },
        'volume': {
            'value': volume_24h,
            'display': volume_formatted,
            'velocity': velocity
        },
        'derivatives': {
            'funding_rate': funding_rate,
            'funding_display': f'{funding_rate:.4f}%',
            'open_interest': oi_usd,
            'oi_display': oi_formatted
        },
        'summary': f'{ticker} mark price at ${mark_price:,.2f}. '
                   f'Funding rate: {funding_rate:.4f}%. '
                   f'Open Interest: {oi_formatted}. '
                   f'Volume velocity: {velocity:.3f}.'
    }


# =============================================================================
# SECTION 2: MARKET PRESSURE BREAKDOWN
# =============================================================================

def _generate_pressure_section(sentiment: Dict, derivatives: Dict) -> Dict[str, Any]:
    """
    Section 2: Market Pressure Breakdown
    
    Returns:
        dict: Pressure signals and leverage analysis
    """
    
    # Extract pressure indicators
    environment = sentiment.get('environment', 'neutral')
    crowd_level = sentiment.get('crowd_level', 'moderate')
    leverage_intensity = sentiment.get('leverage_intensity', 'medium')
    
    pressure_signal = derivatives.get('pressure_signal', 'neutral')
    leverage_risk = derivatives.get('leverage_risk', 'Medium')
    funding_analysis = derivatives.get('funding_analysis', {})
    
    # Determine overall pressure
    if pressure_signal in ['leverage_buildup', 'deleverage_risk']:
        overall_pressure = 'HIGH'
    elif pressure_signal in ['potential_short_squeeze', 'short_covering']:
        overall_pressure = 'ELEVATED'
    else:
        overall_pressure = 'MODERATE'
    
    return {
        'title': 'Market Pressure Analysis',
        'environment': {
            'type': environment,
            'crowd_level': crowd_level,
            'description': f'{environment.replace("-", " ").title()} environment with {crowd_level} crowd level'
        },
        'leverage': {
            'intensity': leverage_intensity,
            'risk': leverage_risk,
            'signal': funding_analysis.get('signal', 'neutral')
        },
        'pressure_signal': {
            'type': pressure_signal,
            'level': overall_pressure,
            'description': _pressure_signal_description(pressure_signal)
        },
        'summary': f'Market is {environment} with {crowd_level} positioning. '
                   f'Leverage intensity: {leverage_intensity}. '
                   f'Pressure signal: {pressure_signal.replace("_", " ")}. '
                   f'Overall pressure: {overall_pressure}.'
    }


def _pressure_signal_description(signal: str) -> str:
    """Get description for pressure signal"""
    descriptions = {
        'leverage_buildup': 'New leveraged positions opening - risk of cascade liquidations',
        'deleverage_risk': 'Extreme leverage - vulnerable to sharp moves',
        'potential_short_squeeze': 'Short positioning may create upward pressure',
        'accumulation': 'Organic spot buying without excessive leverage',
        'neutral': 'Balanced market without extreme positioning'
    }
    return descriptions.get(signal, 'No clear directional pressure')


# =============================================================================
# SECTION 3: EVENT & CONTEXT MAPPING
# =============================================================================

def _generate_events_section(news: Dict, sentiment: Dict) -> Dict[str, Any]:
    """
    Section 3: Event & Context Mapping
    
    Returns:
        dict: News correlation and timing analysis
    """
    
    events = news.get('events', [])
    summary = news.get('summary', {})
    
    # Get top 3 most relevant events
    top_events = events[:3]
    
    # Correlate with sentiment
    fg_index = sentiment.get('fear_greed_index', 50)
    market_phase = sentiment.get('market_phase', 'transition')
    
    return {
        'title': 'Event & Context Mapping',
        'event_count': summary.get('total_events', 0),
        'high_relevance_count': summary.get('high_relevance_count', 0),
        'dominant_theme': summary.get('dominant_theme', 'none'),
        'overall_sentiment': summary.get('overall_sentiment', 'neutral'),
        'top_events': [
            {
                'title': e.get('title', ''),
                'relevance': e.get('relevance', 'unknown'),
                'score': e.get('relevance_score', 0),
                'sentiment': e.get('sentiment', 'neutral')
            }
            for e in top_events
        ],
        'context': {
            'fear_greed': fg_index,
            'market_phase': market_phase,
            'sentiment_alignment': _check_sentiment_alignment(
                summary.get('overall_sentiment', 'neutral'),
                fg_index
            )
        },
        'summary': news.get('interpretation', 'No significant news events.')
    }


def _check_sentiment_alignment(news_sentiment: str, fg_index: int) -> str:
    """Check if news sentiment aligns with market sentiment"""
    
    fg_sentiment = 'positive' if fg_index > 55 else 'negative' if fg_index < 45 else 'neutral'
    
    if news_sentiment == fg_sentiment:
        return 'aligned'
    elif news_sentiment == 'neutral' or fg_sentiment == 'neutral':
        return 'neutral'
    else:
        return 'divergent'


# =============================================================================
# SECTION 4: RISK & CONDITIONS SUMMARY
# =============================================================================

def _generate_risks_section(derivatives: Dict, sentiment: Dict, onchain: Dict) -> Dict[str, Any]:
    """
    Section 4: Risk & Conditions Summary
    
    Returns:
        dict: Current risk levels across dimensions
    """
    
    leverage_risk = derivatives.get('leverage_risk', 'Medium')
    pressure_signal = derivatives.get('pressure_signal', 'neutral')
    
    crowd_level = sentiment.get('crowd_level', 'moderate')
    market_phase = sentiment.get('market_phase', 'transition')
    
    holder_behavior = onchain.get('holder_behavior', 'neutral')
    network_activity = onchain.get('network_activity', 'medium')
    
    # Calculate overall risk score
    risk_score = _calculate_risk_score(leverage_risk, crowd_level, pressure_signal)
    
    return {
        'title': 'Risk & Conditions Summary',
        'leverage_risk': {
            'level': leverage_risk,
            'description': f'Leverage risk is {leverage_risk.lower()}'
        },
        'liquidity_risk': {
            'level': _assess_liquidity_risk(network_activity, holder_behavior),
            'description': f'Network activity: {network_activity}, Holder behavior: {holder_behavior.replace("_", " ")}'
        },
        'event_risk': {
            'level': 'Present' if crowd_level == 'crowded' else 'Normal',
            'description': f'Market {crowd_level} - {"elevated" if crowd_level == "crowded" else "normal"} event sensitivity'
        },
        'structural_risk': {
            'level': risk_score,
            'description': _risk_score_description(risk_score)
        },
        'market_conditions': {
            'phase': market_phase,
            'holder_behavior': holder_behavior,
            'recommendation': _generate_condition_recommendation(risk_score, market_phase)
        },
        'summary': f'Overall risk: {risk_score}. '
                   f'Leverage risk: {leverage_risk}. '
                   f'Market phase: {market_phase}. '
                   f'Conditions: {_risk_score_description(risk_score)}'
    }


def _assess_liquidity_risk(network_activity: str, holder_behavior: str) -> str:
    """Assess liquidity risk based on activity and holder behavior"""
    
    if network_activity == 'low' and 'holding' in holder_behavior:
        return 'Low (Stable)'
    elif network_activity == 'high' and 'distribution' in holder_behavior:
        return 'Elevated (Active Distribution)'
    else:
        return 'Moderate'


def _calculate_risk_score(leverage_risk: str, crowd_level: str, pressure_signal: str) -> str:
    """Calculate overall structural risk"""
    
    risk_points = 0
    
    # Leverage risk points
    if leverage_risk == 'High':
        risk_points += 3
    elif leverage_risk == 'Medium':
        risk_points += 2
    else:
        risk_points += 1
    
    # Crowd level points
    if crowd_level == 'crowded':
        risk_points += 2
    elif crowd_level == 'moderate':
        risk_points += 1
    
    # Pressure signal points
    if pressure_signal in ['leverage_buildup', 'deleverage_risk']:
        risk_points += 2
    elif pressure_signal == 'potential_short_squeeze':
        risk_points += 1
    
    # Convert to risk level
    if risk_points >= 6:
        return 'HIGH'
    elif risk_points >= 4:
        return 'MEDIUM'
    else:
        return 'LOW'


def _risk_score_description(risk_score: str) -> str:
    """Get description for risk score"""
    descriptions = {
        'HIGH': 'Elevated risk conditions - market vulnerable to volatility',
        'MEDIUM': 'Moderate risk - normal market conditions',
        'LOW': 'Low risk - stable market structure'
    }
    return descriptions.get(risk_score, 'Normal risk conditions')


def _generate_condition_recommendation(risk_score: str, market_phase: str) -> str:
    """Generate condition-based recommendation"""
    
    if risk_score == 'HIGH':
        return 'Exercise caution - elevated risk of sharp moves'
    elif market_phase == 'distribution':
        return 'Late-stage conditions - monitor for reversal signals'
    elif market_phase == 'accumulation':
        return 'Early-stage conditions - potential for sustained moves'
    else:
        return 'Normal market conditions - standard risk management applies'


# =============================================================================
# MAJOR-SPECIFIC INSIGHTS
# =============================================================================

def _generate_major_insights(ticker: str, sentiment: Dict, news: Dict, derivatives: Dict, onchain: Dict) -> Dict[str, Any]:
    """
    Generate insights specific to major assets (BTC/ETH)
    
    Returns:
        dict: Key insights and observations
    """
    
    insights = []
    
    # Macro correlation insight
    if sentiment.get('environment') == 'risk-off' and derivatives.get('funding_rate', 0) < 0:
        insights.append({
            'type': 'macro_alignment',
            'message': 'Risk-off sentiment with negative funding suggests macro-driven selling pressure'
        })
    
    # Institutional activity hint
    if news.get('summary', {}).get('dominant_theme') == 'institutional':
        insights.append({
            'type': 'institutional',
            'message': 'Significant institutional news detected - monitor for ETF flows or large transactions'
        })
    
    # Leverage warning
    if derivatives.get('leverage_risk') == 'High':
        insights.append({
            'type': 'leverage_warning',
            'message': f'⚠️ High leverage on {ticker} - elevated liquidation risk'
        })
    
    # Holder strength
    if onchain.get('holder_behavior') == 'strong_holding' and sentiment.get('fear_greed_index', 50) < 40:
        insights.append({
            'type': 'holder_conviction',
            'message': 'Strong holder conviction despite fearful sentiment - potential accumulation phase'
        })
    
    return {
        'count': len(insights),
        'items': insights
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Majors Analyzer...")
    print("=" * 70)
    
    # Analyze BTC
    analysis = analyze_major('BTC')
    
    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
    else:
        print(f"\n📊 {analysis['ticker']} ANALYSIS")
        print("=" * 70)
        
        print("\n[1] SNAPSHOT")
        print(analysis['snapshot']['summary'])
        
        print("\n[2] MARKET PRESSURE")
        print(analysis['pressure']['summary'])
        
        print("\n[3] EVENTS & CONTEXT")
        print(analysis['events']['summary'])
        
        print("\n[4] RISK & CONDITIONS")
        print(analysis['risks']['summary'])
        
        if analysis['insights']['count'] > 0:
            print("\n[INSIGHTS]")
            for insight in analysis['insights']['items']:
                print(f"  • {insight['message']}")
        
        print("\n" + "=" * 70)
        print("✅ Majors Analyzer - COMPLETE")
        print(f"Active Pillars: {', '.join(analysis['active_pillars'])}")
