"""
Newsletter Generator - Long-form Daily Scan Articles

Generates comprehensive newsletter articles for:
- X Articles (long-form posts on X/Twitter)
- Substack Articles (email newsletters)

Uses Claude AI to create professional, in-depth market analysis
matching the 12-section daily scan structure.
"""

import os
import json
from typing import Dict, Any
from datetime import datetime, timezone


def generate_daily_scan_newsletter(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    sector_analyses: Dict[str, Any],
    all_analyses: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Generate comprehensive daily scan newsletter (long-form article).

    This creates a professional market analysis article suitable for:
    - X Articles (x.com/compose/articles)
    - Substack Articles (email newsletters)

    Args:
        btc_analysis: BTC analysis data
        eth_analysis: ETH analysis data
        market_context: Global market metrics
        sector_analyses: Sector data (DeFi, memecoins, privacy)
        all_analyses: All asset analyses

    Returns:
        Dict with 'title' and 'body' (markdown formatted)
    """

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        # Fallback template
        return _generate_template_newsletter(btc_analysis, eth_analysis, market_context, sector_analyses)

    try:
        return _generate_with_claude(
            api_key,
            btc_analysis,
            eth_analysis,
            market_context,
            sector_analyses,
            all_analyses or {}
        )
    except Exception as e:
        print(f"[WARN] Claude newsletter generation failed: {e}. Using template.")
        return _generate_template_newsletter(btc_analysis, eth_analysis, market_context, sector_analyses)


def _generate_with_claude(
    api_key: str,
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    sector_analyses: Dict[str, Any],
    all_analyses: Dict[str, Any]
) -> Dict[str, str]:
    """Generate newsletter with Claude AI"""
    from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

    # Build data context
    now = datetime.now(timezone.utc)
    date_str = now.strftime('%B %d, %Y')
    time_str = now.strftime('%H:%M UTC')

    # Extract key data
    btc_price = btc_analysis.get('snapshot', {}).get('price', {}).get('mark_price', 0)
    btc_change_24h = btc_analysis.get('snapshot', {}).get('price', {}).get('change_24h_pct', 0)
    btc_funding = btc_analysis.get('snapshot', {}).get('derivatives', {}).get('funding_rate_pct', 0)
    btc_liquidations = btc_analysis.get('snapshot', {}).get('derivatives', {}).get('liquidations_24h_total', 0)

    eth_price = eth_analysis.get('snapshot', {}).get('price', {}).get('mark_price', 0)
    eth_change_24h = eth_analysis.get('snapshot', {}).get('price', {}).get('change_24h_pct', 0)

    total_cap = market_context.get('total_market_cap', 0)
    btc_dom = market_context.get('btc_dominance', 0)
    fear_greed = market_context.get('fear_greed_index', 0)
    fear_greed_label = market_context.get('fear_greed_classification', 'Neutral')
    total_liquidations = market_context.get('total_liquidations_24h', 0)

    # Build comprehensive data JSON
    context = {
        'date': date_str,
        'time': time_str,
        'market_overview': {
            'total_market_cap': total_cap,
            'btc_dominance': btc_dom,
            'fear_greed_index': fear_greed,
            'fear_greed_label': fear_greed_label,
            'total_liquidations_24h': total_liquidations,
        },
        'btc': {
            'price': btc_price,
            'change_24h_pct': btc_change_24h,
            'funding_rate_pct': btc_funding,
            'liquidations_24h': btc_liquidations,
        },
        'eth': {
            'price': eth_price,
            'change_24h_pct': eth_change_24h,
        },
        'sectors': sector_analyses
    }

    context_json = json.dumps(context, indent=2)

    # Comprehensive newsletter prompt
    prompt = f"""You are a PROFESSIONAL crypto market analyst writing a comprehensive daily market newsletter.

TODAY'S DATE: {date_str} at {time_str}

MARKET DATA (Real-time from Binance/CoinGecko):
{context_json}

TASK: Write a COMPREHENSIVE daily market newsletter following this EXACT structure:

# DAILY CRYPTO MARKET SCAN

**{date_str}**

## 📊 Market Overview (Top-Down Snapshot)

- **Total Market Cap:** ${total_cap/1e12:.2f}T
- **Bitcoin Dominance:** {btc_dom:.1f}%
- **Fear & Greed Index:** {fear_greed} ({fear_greed_label})
- **24h Liquidations:** ${total_liquidations/1e6:.0f}M

**Narrative Summary** (3-5 sentences):
[Write what is happening structurally. Risk-on or risk-off? Who is getting squeezed? What's the dominant narrative?]


## 🪙 Bitcoin (BTC) Analysis

### Price & Structure
- **Current Price:** ${btc_price:,.2f}
- **24h Change:** {btc_change_24h:+.2f}%
- **Trend:** [Bullish/Bearish/Range - based on data]
- **Market Structure:** [HH/HL or LH/LL based on context]

### Key Levels
- **Major Resistance:** [Provide specific level]
- **Major Support:** [Provide specific level]

### Derivatives
- **Funding Rate:** {btc_funding:.3f}%
- **Open Interest:** [From data]
- **Liquidations (24h):** ${btc_liquidations/1e6:.0f}M

**Interpretation:** [2-3 sentences analyzing BTC. Is it leading or lagging? Squeeze setup? Spot vs leverage driven?]


## ⚡ Ethereum (ETH) Analysis

- **Price:** ${eth_price:,.2f}
- **24h Change:** {eth_change_24h:+.2f}%
- **ETH/BTC Pair:** [Analyze relative strength]
- **Key Levels:** [Resistance/Support]

**Interpretation:** [Is ETH gaining relative strength? Capital rotation?]


## 🌐 Altcoin Market & Sector Rotation

### Top Performers (24h)
[List top 3 with percentages from data]

### Worst Performers
[List bottom 3 with percentages from data]

### Sector Breakdown
- **DeFi:** [Analysis from sector_analyses]
- **Memecoins:** [Analysis from sector_analyses]
- **Privacy Coins:** [Analysis from sector_analyses]

**Interpretation:** [Is capital rotating or exiting risk? Which sectors are leading?]


## 📈 Derivatives & Leverage Analysis

- **Total Liquidations (24h):** ${total_liquidations/1e6:.0f}M
- **Long/Short Ratio:** [From data if available, or skip]
- **Funding Extremes:** [Analysis]

**Interpretation:** [Is this a squeeze setup? Spot-driven or leverage-driven move?]


## 💵 Stablecoin Flows & Liquidity

[Analyze if stablecoin data available in market_context, otherwise: "Data unavailable"]


## 🌍 Macro & External Catalysts

[Discuss any macro events, traditional markets correlation, upcoming events. If no specific data, provide general macro context.]


## 🧠 Sentiment & Positioning

- **Fear & Greed:** {fear_greed} ({fear_greed_label})
- **Market Phase:** [Euphoria/Disbelief/Panic/Exhaustion based on F&G and price action]


## 🎯 Scenarios & Trade Setups

### 🟢 Bullish Scenario
- **Trigger:** [What needs to happen]
- **Target 1:** [Specific level]
- **Target 2:** [Specific level]
- **Invalidation:** [What breaks this thesis]

### 🔴 Bearish Scenario
- **Trigger:** [What needs to happen]
- **Target 1:** [Specific level]
- **Target 2:** [Specific level]
- **Invalidation:** [What breaks this thesis]


## ⚠️ Risk Assessment

- **Volatility:** [Expanding/Contracting]
- **Liquidity:** [Thin/Thick]
- **Event Risk:** [Weekend/Macro events]
- **Risk Level Today:** [Low/Medium/High]


## 🧩 Professional Notes

[2-3 insightful observations about:
- Accumulation or distribution?
- Who is trapped (longs or shorts)?
- What would hurt the most participants?
- Contrarian perspectives]


CRITICAL RULES:
1. Use ONLY the data provided in the JSON above
2. Do NOT invent prices, percentages, or numbers
3. If data is missing, write "Data unavailable" for that section
4. Be specific with numbers - include exact prices and percentages
5. Write in professional Bloomberg/Terminal style
6. Each section should be substantial (100-200 words for major sections)
7. Total article should be 1500-2500 words
8. Use markdown formatting (headers, bold, lists)
9. NO predictions - focus on "what is happening" and "why"
10. Provide actionable insights and specific levels
11. Do NOT use em-dashes (—), en-dashes (–), or spaced hyphens ( - ) between words. Use commas, periods, or restructure sentences instead
12. Do NOT use horizontal rules (---) to separate sections, just use headers

OUTPUT FORMAT:
Return the complete article in markdown format with the exact structure above.
Do NOT include any preamble or explanation - ONLY the article content.
"""

    # Call Claude
    claude_engine = ClaudeResearchEngine(api_key)
    response = claude_engine._call_model(prompt, max_tokens=5000)

    # Extract text
    article_body = ""
    for block in response.content:
        if hasattr(block, 'text'):
            article_body += block.text

    # Extract title (first line after # header)
    title = "Daily Crypto Market Scan"
    lines = article_body.strip().split('\n')
    for line in lines[:5]:
        if line.startswith('# '):
            title = line.replace('# ', '').strip()
            break

    return {
        'title': title,
        'body': article_body,
        'date': date_str,
        'generated_at': now.isoformat(),
        'word_count': len(article_body.split()),
        'generated_by': 'Claude AI'
    }


def _generate_template_newsletter(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    sector_analyses: Dict[str, Any]
) -> Dict[str, str]:
    """Fallback template newsletter"""

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%B %d, %Y')

    btc_price = btc_analysis.get('snapshot', {}).get('price', {}).get('mark_price', 0)
    total_cap = market_context.get('total_market_cap', 0)

    body = f"""# Daily Crypto Market Scan

**{date_str}**

## Market Overview

- Total Market Cap: ${total_cap/1e12:.2f}T
- Bitcoin Price: ${btc_price:,.2f}

## Analysis

(Template fallback - Claude API not available for detailed analysis)

Key developments across major cryptocurrencies and market sectors.

## Risk Assessment

Monitor key levels and market sentiment.
"""

    return {
        'title': 'Daily Crypto Market Scan',
        'body': body,
        'date': date_str,
        'generated_at': now.isoformat(),
        'generated_by': 'Template (fallback)'
    }
