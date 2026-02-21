"""
X Thread Generator - Mode-Aware Thread Generation with Claude AI

Generates professional crypto market threads using Claude AI and comprehensive
data from DataAggregator. Supports multiple modes (morning scan, mid-day, closing).

Uses ThreadBuilder with enhanced Claude prompts matching Bloomberg-level analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from src.utils.x_thread_builder import ThreadBuilder


def generate_x_thread(
    btc_analysis: Dict[str, Any],
    market_context: Dict[str, Any] = None,
    thread_mode: str = 'morning_scan',  # 'morning_scan' | 'mid_day_update' | 'closing_bell'
    previous_context: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate comprehensive X/Twitter thread using Claude AI.

    Args:
        btc_analysis: BTC analysis data from analyzers
        market_context: Global market metrics (cap, dominance, sentiment, liquidations)
        thread_mode: 'morning_scan' (12+ tweets) | 'mid_day_update' (5-7 tweets) | 'closing_bell' (5-7 tweets)
        previous_context: Summary of previous thread (for mid-day reference)
        **kwargs: Additional data (eth_analysis, sector_analyses, all_analyses)

    Returns:
        Dict with 'tweets' (List[str]), 'thread', 'tweet_count', 'copy_paste_ready'
    """

    # Extract additional analyses
    eth_analysis = kwargs.get('eth_analysis', {})
    sector_analyses = kwargs.get('sector_analyses', {})
    all_analyses = kwargs.get('all_analyses', {})

    # Build comprehensive data payload for Claude
    analysis_data = _build_analysis_payload(
        btc_analysis=btc_analysis,
        eth_analysis=eth_analysis,
        market_context=market_context,
        sector_analyses=sector_analyses,
        all_analyses=all_analyses,
        thread_mode=thread_mode,
        previous_context=previous_context
    )

    # Use ThreadBuilder with Claude AI
    builder = ThreadBuilder()

    # Determine thread type based on mode
    if thread_mode == 'morning_scan':
        thread_type = 'comprehensive'  # 12+ tweets
        max_tweets = 15
    elif thread_mode == 'mid_day_update':
        thread_type = 'quick'  # 5-7 tweets
        max_tweets = 7
    elif thread_mode == 'closing_bell':
        thread_type = 'quick'  # 5-7 tweets
        max_tweets = 7
    else:
        thread_type = 'focused'  # 3-5 tweets
        max_tweets = 5

    # Generate thread with Claude AI
    result = builder.build_with_claude_ai(
        analysis_data=analysis_data,
        thread_type=thread_type,
        max_tweets=max_tweets
    )

    # Ensure tweets are returned as list of strings
    tweets = result.get('tweets', [])
    if tweets and isinstance(tweets[0], dict):
        # ThreadBuilder sometimes returns dicts, normalize to strings
        tweets = [t.get('text', str(t)) if isinstance(t, dict) else str(t) for t in tweets]
        result['tweets'] = tweets

    # Add mode metadata
    result['thread_mode'] = thread_mode
    result['previous_context'] = previous_context

    return result


def _build_analysis_payload(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    sector_analyses: Dict[str, Any],
    all_analyses: Dict[str, Any],
    thread_mode: str,
    previous_context: Optional[str]
) -> Dict[str, Any]:
    """
    Build comprehensive data payload from all analysis sources.

    Extracts and organizes:
    - Market overview (cap, dominance, sentiment, liquidations)
    - Majors (BTC, ETH, SOL, BNB) with prices, funding, structure
    - Sector data (DeFi, Memecoins, Privacy)
    - Derivatives data (funding, OI, liquidations)
    - On-chain metrics (if available)
    """

    # Extract market overview data
    market_overview = {
        'total_market_cap': market_context.get('total_market_cap', 0) if market_context else 0,
        'btc_dominance': market_context.get('btc_dominance', 0) if market_context else 0,
        'eth_dominance': market_context.get('eth_dominance', 0) if market_context else 0,
        'fear_greed_index': market_context.get('fear_greed_value', 0) if market_context else 0,
        'fear_greed_label': market_context.get('fear_greed_classification', 'Neutral') if market_context else 'Neutral',
        'total_liquidations_24h': market_context.get('total_liquidations_24h', 0) if market_context else 0,
    }

    # Extract majors data (BTC, ETH, SOL, BNB)
    majors = {}
    for symbol in ['BTC', 'ETH', 'SOL', 'BNB']:
        if symbol in all_analyses:
            analysis = all_analyses[symbol]
            majors[symbol] = {
                'price': analysis.get('snapshot', {}).get('price', {}).get('mark_price', 0),
                'change_24h': analysis.get('snapshot', {}).get('price', {}).get('change_24h_pct', 0),
                'change_7d': analysis.get('snapshot', {}).get('price', {}).get('change_7d_pct', 0),
                'funding_rate': analysis.get('snapshot', {}).get('derivatives', {}).get('funding_rate_pct', 0),
                'open_interest': analysis.get('snapshot', {}).get('derivatives', {}).get('open_interest', 0),
                'liquidations_long': analysis.get('snapshot', {}).get('derivatives', {}).get('liquidations_24h_long', 0),
                'liquidations_short': analysis.get('snapshot', {}).get('derivatives', {}).get('liquidations_24h_short', 0),
                'market_cap': analysis.get('snapshot', {}).get('market', {}).get('market_cap', 0),
            }

    # Extract sector data
    defi_tokens = sector_analyses.get('defi', [])
    memecoin_tokens = sector_analyses.get('memecoins', [])
    privacy_tokens = sector_analyses.get('privacy', [])

    # Build final payload
    payload = {
        'market_context': market_overview,
        'majors': majors,
        'defi': defi_tokens,
        'memecoins': memecoin_tokens,
        'privacy_coins': privacy_tokens,
        'thread_mode': thread_mode,
        'previous_context': previous_context,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return payload
