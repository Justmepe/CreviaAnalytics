"""
AdminInboxPoster — posts engine analysis data to the admin portal inbox
instead of calling Claude API directly (manual content generation mode).

Usage in main.py / content_session.py:
    from src.content.admin_inbox_poster import post_to_admin_inbox
    post_to_admin_inbox(
        scan_type='morning_scan',
        headline='Morning Scan — BTC at $95k, Risk Off regime',
        raw_data=analysis_data,          # the full analysis dict
        suggested_prompt='Write a comprehensive morning scan article...',
    )
"""

import logging
import os
import json
import requests

logger = logging.getLogger(__name__)

_API_URL = os.getenv('WEB_API_URL', 'http://localhost:8000')
_SECRET  = os.getenv('WEB_API_SECRET', 'crevia-internal-key')

# Prompt templates per scan type
PROMPT_TEMPLATES = {
    'morning_scan': (
        "Write a comprehensive morning market analysis article (800-1200 words) based on the data above. "
        "Cover: market overview, BTC/ETH analysis, key altcoins, sentiment, key levels to watch. "
        "Use markdown with headers. Be specific with price levels and percentages. "
        "End with 2-3 key scenarios for the session."
    ),
    'mid_day': (
        "Write a concise mid-day market update (400-600 words) based on the data above. "
        "Focus on: what has changed since the open, key moves, momentum shifts. "
        "Keep it punchy and actionable. Use markdown."
    ),
    'closing_bell': (
        "Write a closing bell analysis (600-900 words) based on the data above. "
        "Cover: session recap, winners/losers, overnight risk, key levels for next session. "
        "Use markdown with clear sections."
    ),
    'breaking_news': (
        "Write a breaking news analysis article (500-800 words) based on the event data above. "
        "Cover: what happened, market impact, affected assets, what traders should watch. "
        "Be timely and direct. Use markdown."
    ),
}


def _format_context(scan_type: str, raw_data: dict) -> str:
    """Format the raw analysis data as readable context for Claude."""
    lines = [f"## {scan_type.replace('_', ' ').upper()} — SYSTEM DATA\n"]

    # Market snapshot
    if 'market' in raw_data:
        m = raw_data['market']
        lines.append("### Market Snapshot")
        if m.get('btc_price'):
            lines.append(f"- BTC: ${m['btc_price']:,.0f}")
        if m.get('eth_price'):
            lines.append(f"- ETH: ${m['eth_price']:,.0f}")
        if m.get('total_market_cap'):
            lines.append(f"- Total Market Cap: ${m['total_market_cap']/1e12:.2f}T")
        if m.get('btc_dominance'):
            lines.append(f"- BTC Dominance: {m['btc_dominance']:.1f}%")
        if m.get('fear_greed_index'):
            lines.append(f"- Fear & Greed: {m['fear_greed_index']} ({m.get('fear_greed_label', '')})")
        lines.append('')

    # Regime
    if 'regime' in raw_data:
        r = raw_data['regime']
        lines.append("### Market Regime")
        lines.append(f"- Regime: {r.get('name', 'Unknown')}")
        lines.append(f"- Confidence: {r.get('confidence', 0)*100:.0f}%")
        if r.get('description'):
            lines.append(f"- Description: {r['description']}")
        lines.append('')

    # Asset prices
    if 'prices' in raw_data and raw_data['prices']:
        lines.append("### Asset Prices")
        for ticker, data in raw_data['prices'].items():
            price = data.get('price', data) if isinstance(data, dict) else data
            change = data.get('change_24h', '') if isinstance(data, dict) else ''
            change_str = f" ({change:+.1f}%)" if change != '' else ''
            lines.append(f"- {ticker}: ${price:,.4f}{change_str}" if price < 1 else f"- {ticker}: ${price:,.2f}{change_str}")
        lines.append('')

    # Analysis data (sector analysis, etc.)
    for key in ('sentiment', 'derivatives', 'onchain', 'news_summary', 'sector_analysis'):
        if key in raw_data and raw_data[key]:
            lines.append(f"### {key.replace('_', ' ').title()}")
            val = raw_data[key]
            if isinstance(val, str):
                lines.append(val)
            elif isinstance(val, dict):
                for k, v in val.items():
                    lines.append(f"- {k}: {v}")
            lines.append('')

    # Breaking news
    if 'news' in raw_data and raw_data['news']:
        lines.append("### Recent News")
        news = raw_data['news']
        if isinstance(news, list):
            for item in news[:10]:
                if isinstance(item, dict):
                    lines.append(f"- [{item.get('title', '')}] {item.get('source', '')}")
                else:
                    lines.append(f"- {item}")
        lines.append('')

    return '\n'.join(lines)


def post_to_admin_inbox(
    scan_type: str,
    raw_data: dict,
    headline: str = None,
    suggested_prompt: str = None,
) -> bool:
    """
    Post engine analysis data to the admin inbox.
    Returns True on success, False on failure.
    """
    prompt = suggested_prompt or PROMPT_TEMPLATES.get(scan_type, PROMPT_TEMPLATES['morning_scan'])

    # Format context as the first message Claude will see
    context_text = _format_context(scan_type, raw_data)
    full_prompt = f"{context_text}\n---\n{prompt}"

    payload = {
        'scan_type': scan_type,
        'headline': headline,
        'raw_data': raw_data,
        'suggested_prompt': full_prompt,
    }

    try:
        r = requests.post(
            f'{_API_URL}/api/admin/inbox',
            json=payload,
            headers={'X-Api-Secret': _SECRET},
            params={'x_api_secret': _SECRET},
            timeout=10,
        )
        r.raise_for_status()
        logger.info('AdminInbox: posted %s (id=%s)', scan_type, r.json().get('id'))
        return True
    except Exception as e:
        logger.error('AdminInbox post failed: %s', e)
        return False
