"""
File 7: Pillar B - News & Events
Dependencies: data_fetchers.py, helpers.py
Status: ✅ COMPLETE

Purpose:
- Fetch and analyze news events
- Calculate relevance scores
- Detect timing correlation with price moves

This pillar explains CAUSALITY - why something might have happened
"""

from typing import Dict, Any, List, Optional
from src.pillars.rss_engine import CryptoNewsAggregator
from src.utils.helpers import time_ago, get_current_timestamp
import re
import threading
import time


# Module-level RSS engine singleton (initialized on first use by analyze_news)
_rss_engine: Optional[CryptoNewsAggregator] = None


def get_rss_engine() -> CryptoNewsAggregator:
    """Return the shared RSS engine singleton (created on first call to analyze_news)."""
    global _rss_engine
    if _rss_engine is None:
        _rss_engine = CryptoNewsAggregator()
    return _rss_engine


# =============================================================================
# PILLAR B: NEWS & EVENTS ANALYSIS
# =============================================================================

def analyze_news(ticker: str, timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    Analyze news events for an asset
    
    This pillar answers: "What external events could explain the move?"
    
    Args:
        ticker: Asset symbol
        timeframe_hours: How many hours back to look
    
    Returns:
        dict: {
            'events': [
                {
                    'title': 'Bitcoin ETF Approved',
                    'published_at': '2024-01-10T14:30:00Z',
                    'time_ago': '2 hours ago',
                    'source': 'CoinDesk',
                    'url': 'https://...',
                    'relevance': 'direct' | 'indirect' | 'macro',
                    'relevance_score': 0.95,
                    'categories': ['regulation', 'institutional'],
                    'sentiment': 'positive' | 'negative' | 'neutral'
                }
            ],
            'summary': {
                'total_events': 5,
                'high_relevance_count': 2,
                'dominant_theme': 'regulation',
                'overall_sentiment': 'positive'
            },
            'interpretation': 'Detailed explanation...'
        }
    """
    
    # Initialize RSS engine (global instance for persistence)
    global _rss_engine
    if _rss_engine is None:
        _rss_engine = CryptoNewsAggregator()

    if not _rss_engine.articles:
        # Check if we have any cached articles, if not do force fetch for initial setup
        if not _rss_engine.articles:
            print("[...] Loading curated RSS feeds (first time setup)...")
            try:
                _rss_engine.force_fetch_all_feeds()
                print(f"[OK] Curated RSS feeds loaded. {len(_rss_engine.articles)} articles indexed.")
                
                # Start background polling for continuous updates
                _rss_engine.start_background_polling(interval_minutes=1)
                
            except Exception as e:
                print(f"Warning: Initial RSS feed fetch failed: {e}")
                # Continue with empty results
    
    # If still no articles after initial load, return empty result
    if not _rss_engine.articles:
        print("Note: No RSS articles available. Feeds may be temporarily unreachable.")
        return _empty_news_result(ticker, timeframe_hours)
    
    # Search for news using RSS engine (with aliases and broad market padding)
    news_items = _rss_engine.search_news(ticker=ticker, limit=20, include_broad_market=True)
    
    # Convert RSS format to expected format
    converted_items = []
    for item in news_items:
        converted_items.append({
            'title': item['title'],
            'published_at': item['published_at'].isoformat() if item['published_at'] else None,
            'url': item['link'],
            'source': item['source'],
            'currencies': [ticker] if ticker else [],
            'kind': 'news',
            'summary': item['summary'][:200] + '...' if len(item['summary']) > 200 else item['summary'],
            'image_url': item.get('image_url')
        })
    
    # Apply spam filtering
    filtered_items = _filter_spam_news(converted_items)
    
    news_items = filtered_items
    
    if not news_items:
        return _empty_news_result(ticker, timeframe_hours)
    
    # Analyze each news item
    analyzed_events = []
    for item in news_items:
        analyzed = _analyze_news_item(item, ticker)
        if analyzed:
            analyzed_events.append(analyzed)
    
    # Sort by relevance score
    analyzed_events.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # Generate summary
    summary = _generate_news_summary(analyzed_events)
    
    # Generate interpretation
    interpretation = _generate_news_interpretation(analyzed_events, ticker, summary)
    
    return {
        'events': analyzed_events[:10],  # Top 10 most relevant
        'summary': summary,
        'interpretation': interpretation,
        'timeframe_hours': timeframe_hours,
        'ticker': ticker,
        'timestamp': get_current_timestamp()
    }


# =============================================================================
# NEWS ITEM ANALYSIS
# =============================================================================

def _analyze_news_item(item: Dict[str, Any], ticker: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a single news item for relevance and sentiment
    
    Args:
        item: Raw news item from API
        ticker: Asset being analyzed
    
    Returns:
        dict: Analyzed news item with scores
    """
    
    title = item.get('title', '')
    if not title:
        return None
    
    # Calculate relevance
    relevance_type, relevance_score = _calculate_relevance(title, ticker, item)
    
    # Determine categories
    categories = _categorize_news(title)
    
    # Analyze sentiment
    sentiment = _analyze_sentiment_from_title(title)
    
    return {
        'title': title,
        'published_at': item.get('published_at'),
        'time_ago': 'Recently',  # Can enhance with actual timestamp parsing
        'source': item.get('source', 'Unknown'),
        'url': item.get('url', ''),
        'image_url': item.get('image_url'),
        'relevance': relevance_type,
        'relevance_score': relevance_score,
        'categories': categories,
        'sentiment': sentiment,
        'currencies': item.get('currencies', [])
    }


def _calculate_relevance(title: str, ticker: str, item: Dict[str, Any]) -> tuple:
    """
    Calculate how relevant this news is to the asset
    
    Returns:
        tuple: (relevance_type, score)
            relevance_type: 'direct', 'indirect', 'macro'
            score: 0.0 to 1.0
    """
    
    title_lower = title.lower()
    ticker_lower = ticker.lower()
    currencies = [c.lower() for c in item.get('currencies', [])]
    
    # Direct relevance: Ticker mentioned
    if ticker_lower in currencies or ticker_lower in title_lower:
        # Check for high-impact keywords
        high_impact = any(kw in title_lower for kw in [
            'hack', 'exploit', 'sec', 'etf', 'approval', 'lawsuit',
            'partnership', 'mainnet', 'upgrade', 'delisting'
        ])
        
        if high_impact:
            return ('direct', 0.95)
        else:
            return ('direct', 0.85)
    
    # Indirect relevance: Related sector or ecosystem
    if any(kw in title_lower for kw in ['defi', 'nft', 'layer', 'blockchain']):
        if ticker_lower in title_lower or len(currencies) > 0:
            return ('indirect', 0.6)
        else:
            return ('indirect', 0.4)
    
    # Macro relevance: Affects entire market
    macro_keywords = ['regulation', 'sec', 'fed', 'inflation', 'market crash', 'bull run']
    if any(kw in title_lower for kw in macro_keywords):
        return ('macro', 0.5)
    
    # Default: Low relevance
    return ('indirect', 0.3)


def _categorize_news(title: str) -> List[str]:
    """
    Categorize news into themes
    
    Returns:
        list: Categories like ['regulation', 'technical', 'institutional']
    """
    
    title_lower = title.lower()
    categories = []
    
    category_keywords = {
        'regulation': ['sec', 'regulation', 'lawsuit', 'legal', 'compliance'],
        'technical': ['upgrade', 'mainnet', 'fork', 'network', 'protocol'],
        'institutional': ['etf', 'institutional', 'investment', 'fund', 'grayscale'],
        'security': ['hack', 'exploit', 'vulnerability', 'breach', 'security'],
        'adoption': ['adoption', 'partnership', 'integration', 'accepts'],
        'market': ['price', 'rally', 'crash', 'surge', 'drop'],
        'development': ['developer', 'update', 'release', 'launch']
    }
    
    for category, keywords in category_keywords.items():
        if any(kw in title_lower for kw in keywords):
            categories.append(category)
    
    return categories if categories else ['general']


def _analyze_sentiment_from_title(title: str) -> str:
    """
    Analyze sentiment from news title
    
    Returns:
        str: 'positive', 'negative', or 'neutral'
    """
    
    title_lower = title.lower()
    
    positive_keywords = [
        'surge', 'rally', 'approval', 'partnership', 'upgrade', 'adoption',
        'bullish', 'growth', 'gains', 'success', 'breakthrough', 'milestone'
    ]
    
    negative_keywords = [
        'crash', 'hack', 'exploit', 'lawsuit', 'decline', 'drop', 'bearish',
        'warning', 'concern', 'risk', 'threat', 'collapse', 'failure'
    ]
    
    positive_count = sum(1 for kw in positive_keywords if kw in title_lower)
    negative_count = sum(1 for kw in negative_keywords if kw in title_lower)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'


# =============================================================================
# SUMMARY & INTERPRETATION
# =============================================================================

def _generate_news_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for news events
    
    Returns:
        dict: Summary metrics
    """
    
    if not events:
        return {
            'total_events': 0,
            'high_relevance_count': 0,
            'dominant_theme': 'none',
            'overall_sentiment': 'neutral'
        }
    
    high_relevance = [e for e in events if e['relevance_score'] > 0.7]
    
    # Find dominant theme
    all_categories = []
    for event in events:
        all_categories.extend(event['categories'])
    
    if all_categories:
        dominant_theme = max(set(all_categories), key=all_categories.count)
    else:
        dominant_theme = 'general'
    
    # Calculate overall sentiment
    sentiments = [e['sentiment'] for e in events]
    positive_count = sentiments.count('positive')
    negative_count = sentiments.count('negative')
    
    if positive_count > negative_count * 1.5:
        overall_sentiment = 'positive'
    elif negative_count > positive_count * 1.5:
        overall_sentiment = 'negative'
    else:
        overall_sentiment = 'neutral'
    
    return {
        'total_events': len(events),
        'high_relevance_count': len(high_relevance),
        'dominant_theme': dominant_theme,
        'overall_sentiment': overall_sentiment,
        'sentiment_breakdown': {
            'positive': positive_count,
            'negative': negative_count,
            'neutral': sentiments.count('neutral')
        }
    }


def _generate_news_interpretation(
    events: List[Dict[str, Any]],
    ticker: str,
    summary: Dict[str, Any]
) -> str:
    """
    Generate human-readable interpretation of news landscape
    
    Returns:
        str: Clear explanation
    """
    
    if not events:
        return f"No significant news events found for {ticker} in the specified timeframe."
    
    parts = []
    
    # Opening statement
    parts.append(f"Found {summary['total_events']} news items related to {ticker}. ")
    
    # High relevance events
    if summary['high_relevance_count'] > 0:
        parts.append(f"{summary['high_relevance_count']} of these are highly relevant. ")
    
    # Dominant theme
    if summary['dominant_theme'] != 'general':
        theme_text = {
            'regulation': 'Regulatory developments',
            'technical': 'Technical updates',
            'institutional': 'Institutional activity',
            'security': 'Security concerns',
            'adoption': 'Adoption news',
            'market': 'Market movements',
            'development': 'Development progress'
        }
        parts.append(f"The dominant theme is {theme_text.get(summary['dominant_theme'], summary['dominant_theme'])}. ")
    
    # Sentiment
    sentiment = summary['overall_sentiment']
    if sentiment == 'positive':
        parts.append("Overall news sentiment is positive, which may support bullish price action.")
    elif sentiment == 'negative':
        parts.append("Overall news sentiment is negative, which may create selling pressure.")
    else:
        parts.append("News sentiment is mixed or neutral.")
    
    # Top event
    if events and events[0]['relevance_score'] > 0.7:
        top_event = events[0]
        parts.append(f" Most significant: \"{top_event['title']}\"")
    
    return ''.join(parts)


def _filter_spam_news(news_items: List[Dict]) -> List[Dict]:
    """
    Filter out low-quality press releases and spam from RSS feeds
    
    Spam keywords commonly found in crypto press releases:
    - Partnership announcements
    - Token launches
    - Exchange listings
    - Marketing content
    """
    
    # Spam keywords to filter out
    SPAM_KEYWORDS = [
        # Press release indicators
        'announces', 'launches', 'partnership', 'collaboration', 'alliance',
        'integration', 'adoption', 'implementation', 'deployment',
        
        # Marketing content
        'proud to', 'excited to', 'pleased to', 'honored to',
        'leading', 'innovative', 'revolutionary', 'game-changing',
        
        # Token/exchange related
        'listing', 'listed', 'trading', 'available on',
        'token sale', 'ico', 'ido', 'airdrop',
        
        # Generic business speak
        'expands', 'expands its', 'strengthens', 'enhances',
        'leverages', 'utilizes', 'harnesses', 'capitalizes',
        
        # Low-quality sources
        'yahoo finance', 'business wire', 'pr newswire',
        'globenewswire', 'accesswire'
    ]
    
    filtered_items = []
    
    for item in news_items:
        title_lower = item['title'].lower()
        summary_lower = item.get('summary', '').lower()
        source_lower = item.get('source', '').lower()
        
        # Check if any spam keywords are present
        is_spam = False
        for keyword in SPAM_KEYWORDS:
            if keyword in title_lower or keyword in summary_lower or keyword in source_lower:
                is_spam = True
                break
        
        # Additional filters
        if not is_spam:
            # Filter out very short titles (likely spam)
            if len(item['title'].strip()) < 10:
                is_spam = True
            # Filter out titles with excessive caps
            elif item['title'].isupper():
                is_spam = True
            # Filter out titles with too many special characters
            elif sum(1 for c in item['title'] if not c.isalnum() and c not in ' .,-:()') > 5:
                is_spam = True
        
        if not is_spam:
            filtered_items.append(item)
    
    return filtered_items


def _empty_news_result(ticker: str, timeframe_hours: int) -> Dict[str, Any]:
    """Return empty result when no news is available"""
    return {
        'events': [],
        'summary': {
            'total_events': 0,
            'high_relevance_count': 0,
            'dominant_theme': 'none',
            'overall_sentiment': 'neutral'
        },
        'interpretation': f"No news events found for {ticker} in the last {timeframe_hours} hours. This could indicate a quiet period or limited news coverage.",
        'timeframe_hours': timeframe_hours,
        'ticker': ticker,
        'timestamp': get_current_timestamp()
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing Pillar B: News & Events...")
    print("=" * 70)
    
    # Analyze news for BTC
    news_analysis = analyze_news('BTC', timeframe_hours=48)
    
    print("\n📰 NEWS & EVENTS ANALYSIS - BTC")
    print("-" * 70)
    print(f"Timeframe: {news_analysis['timeframe_hours']} hours")
    print(f"Total Events: {news_analysis['summary']['total_events']}")
    print(f"High Relevance: {news_analysis['summary']['high_relevance_count']}")
    print(f"Dominant Theme: {news_analysis['summary']['dominant_theme'].title()}")
    print(f"Overall Sentiment: {news_analysis['summary']['overall_sentiment'].title()}")
    print()
    
    if news_analysis['events']:
        print("Top 3 Events:")
        for i, event in enumerate(news_analysis['events'][:3], 1):
            print(f"\n{i}. {event['title']}")
            print(f"   Source: {event['source']}")
            print(f"   Relevance: {event['relevance']} (score: {event['relevance_score']:.2f})")
            print(f"   Categories: {', '.join(event['categories'])}")
            print(f"   Sentiment: {event['sentiment']}")
    
    print("\n" + "-" * 70)
    print("Interpretation:")
    print(news_analysis['interpretation'])
    print()
    print("=" * 70)
    print("✅ Pillar B: News & Events - COMPLETE")