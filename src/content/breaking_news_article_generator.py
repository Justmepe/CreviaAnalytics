"""
Breaking News Article Generator - Long-form Breaking News Articles

Generates comprehensive breaking news articles for:
- X Articles (long-form posts on X/Twitter)
- Substack Articles (email newsletters)

Uses Claude AI to create professional, in-depth analysis of breaking news events.
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def generate_breaking_news_article(
    headline: str,
    summary: str,
    source: str = "Unknown",
    current_price: Optional[float] = None,
    ticker: str = "BTC",
    relevance_score: float = 0.0
) -> Dict[str, str]:
    """
    Generate comprehensive breaking news article (long-form).

    This creates a professional breaking news analysis article suitable for:
    - X Articles (x.com/compose/articles)
    - Substack Articles (email newsletters)

    Args:
        headline: Breaking news headline
        summary: News summary/description
        source: News source
        current_price: Current price of relevant asset
        ticker: Relevant ticker symbol
        relevance_score: Relevance score (0.0-1.0)

    Returns:
        Dict with 'title', 'body' (markdown formatted), 'metadata'
    """

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        # Fallback template
        return _generate_template_article(headline, summary, source, current_price, ticker)

    try:
        return _generate_with_claude(
            api_key,
            headline,
            summary,
            source,
            current_price,
            ticker,
            relevance_score
        )
    except Exception as e:
        print(f"[WARN] Claude breaking news article generation failed: {e}. Using template.")
        return _generate_template_article(headline, summary, source, current_price, ticker)


def _generate_with_claude(
    api_key: str,
    headline: str,
    summary: str,
    source: str,
    current_price: Optional[float],
    ticker: str,
    relevance_score: float
) -> Dict[str, str]:
    """Generate breaking news article with Claude AI"""
    from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%B %d, %Y')
    time_str = now.strftime('%H:%M UTC')

    # Build context
    price_context = ""
    if current_price is not None:
        price_context = f"- **Current {ticker} Price:** ${current_price:,.2f}\n"

    context = {
        'headline': headline,
        'summary': summary,
        'source': source,
        'date': date_str,
        'time': time_str,
        'ticker': ticker,
        'current_price': current_price,
        'relevance_score': relevance_score
    }

    context_json = json.dumps(context, indent=2)

    # Comprehensive breaking news article prompt
    prompt = f"""You are a PROFESSIONAL crypto market analyst writing a breaking news analysis article.

BREAKING NEWS EVENT:
{context_json}

TASK: Write a COMPREHENSIVE breaking news article following this structure:

# {headline}

**{date_str} at {time_str}**
**Source:** {source}

## 🚨 What Happened

[2-3 paragraphs explaining the event in detail. What are the facts? Who is involved? What changed?]

## 📊 Market Context

{price_context}
[Provide current market context. How does this news relate to recent price action? What were the market conditions leading up to this?]

## 💥 Impact Analysis

### Immediate Impact
[What happens in the next few hours/days? Direct consequences?]

### Medium-Term Impact (1-4 weeks)
[What could this mean over the coming weeks? Secondary effects?]

### Long-Term Implications
[What does this mean for the industry/market structure? Precedent setting?]

## 🧠 Our Analysis

[Professional take on this event:
- Is this a continuation or reversal of existing trends?
- Who benefits and who loses?
- What are the contrarian perspectives?
- What would surprise the market?]

## 🎯 Key Levels to Watch

[If price-related news, provide specific levels. Otherwise, key metrics/developments to monitor]

- **Bullish above:** [Level or condition]
- **Bearish below:** [Level or condition]
- **Invalidation:** [What would change this thesis]

## ⚠️ Risk Factors

[What could go wrong with this thesis? What are we watching?]

## 🔍 Bottom Line

[2-3 sentence summary: What does this mean for crypto investors/traders RIGHT NOW?]

CRITICAL RULES:
1. Use ONLY the data provided above
2. Do NOT invent prices, percentages, or numbers not in the context
3. If current_price is null, skip price-specific analysis
4. Write in professional Bloomberg/Reuters/CoinDesk style
5. Be factual and objective - this is breaking news, not speculation
6. Each section should be substantial (50-150 words)
7. Total article should be 800-1500 words
8. Use markdown formatting (headers, bold, lists)
9. Focus on "what happened" → "what it means" → "what to watch"
10. Provide actionable insights for traders/investors
11. If the news is not price-related (e.g., regulation, technology), focus on industry impact
12. Do NOT use em-dashes (—), en-dashes (–), or spaced hyphens ( - ) between words. Use commas, periods, or restructure sentences instead
13. Do NOT use horizontal rules (---) to separate sections, just use headers

OUTPUT FORMAT:
Return the complete article in markdown format with the exact structure above.
Do NOT include any preamble or explanation - ONLY the article content.
"""

    # Call Claude
    claude_engine = ClaudeResearchEngine(api_key)
    response = claude_engine._call_model(prompt, max_tokens=3000)

    # Extract text
    article_body = ""
    for block in response.content:
        if hasattr(block, 'text'):
            article_body += block.text

    # Extract title (first line after # header)
    title = headline
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
        'generated_by': 'Claude AI',
        'relevance_score': relevance_score,
        'ticker': ticker
    }


def _generate_template_article(
    headline: str,
    summary: str,
    source: str,
    current_price: Optional[float],
    ticker: str
) -> Dict[str, str]:
    """Fallback template article"""

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%B %d, %Y')
    time_str = now.strftime('%H:%M UTC')

    price_line = ""
    if current_price is not None:
        price_line = f"\n**Current {ticker} Price:** ${current_price:,.2f}\n"

    body = f"""# {headline}

**{date_str} at {time_str}**
**Source:** {source}

## What Happened

{summary}
{price_line}

## Impact

This is a developing story. We're monitoring market reaction and will provide updates as more information becomes available.

## Key Takeaways

- Breaking news event detected with high market relevance
- Monitoring price action and on-chain metrics
- Stay tuned for detailed analysis

*This article was generated using a template fallback (Claude API not available)*
"""

    return {
        'title': headline,
        'body': body,
        'date': date_str,
        'generated_at': now.isoformat(),
        'generated_by': 'Template (fallback)',
        'ticker': ticker
    }
