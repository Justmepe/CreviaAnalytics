"""
File: src/content/news_narrator.py
Purpose: Transform raw RSS lists into human-written, fact-checked market narratives.
Dependencies: ClaudeResearchEngine (lazy), data_fetchers for live price
"""

import json
import os
import re
from typing import List, Dict, Optional


class NewsNarrator:
    def __init__(self):
        # Lazy init for ClaudeResearchEngine to avoid heavy imports on module load
        self.editor_engine = None

    def _init_editor_engine(self):
        if self.editor_engine is None:
            try:
                api_key = os.getenv('ANTHROPIC_API_KEY', '')
                if not api_key:
                    return
                from src.utils.enhanced_data_fetchers import ClaudeResearchEngine
                # Use Haiku for news memos/tweets — fast and cost-efficient
                model = os.getenv('CLAUDE_CONTENT_MODEL', 'claude-haiku-4-5-20251001')
                self.editor_engine = ClaudeResearchEngine(api_key, model=model)
            except Exception:
                # If import fails, keep editor_engine as None and rely on fallback
                self.editor_engine = None

    def _extract_price_from_title(self, title: str) -> Optional[float]:
        """Extract first USD-like price from a headline, e.g. $76K, $80,000."""
        if not title:
            return None
        # Normalize common shorthand like $76K -> 76000
        m = re.search(r"\$\s?([0-9.,]+)\s?K", title, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(',', '')) * 1000
            except Exception:
                pass
        m = re.search(r"\$\s?([0-9,]+(?:\.[0-9]+)?)", title)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except Exception:
                pass
        return None

    def _build_price_discrepancy_note(self, titles: List[str], current_price: Optional[float]) -> str:
        if current_price is None:
            return "(No real-time price available to fact-check headlines.)"

        notes = []
        for t in titles:
            p = self._extract_price_from_title(t)
            if p:
                # compute relative difference
                rel = abs(p - current_price) / max(current_price, 1)
                if rel >= 0.02:  # >2% difference worth noting
                    notes.append((t, p))
        if not notes:
            return "Most headlines are consistent with the current price."

        lines = ["Headlines mentioning historic prices that differ from current price:"]
        for t, p in notes:
            lines.append(f"- \"{t}\" mentions ${p:,.0f} (current: ${current_price:,.0f})")
        return "\n".join(lines)

    def _fallback_formatter(self, ticker: str, articles: List[Dict], current_price: Optional[float]) -> str:
        # Human-friendly fallback that includes fact-checking notes
        top = articles[:7]
        titles = [a.get('title', '') for a in top]

        out = []
        out.append(f"📊 Market Update — {ticker}")
        out.append("=" * 60)
        if current_price is not None:
            out.append(f"Current Price (source of truth): ${current_price:,.2f}")
        out.append("")

        # Lead: synthesize top theme by looking for keywords
        lead_points = []
        lead_points.append("Top headlines:")
        for t in titles[:5]:
            out.append(f"• {t}")

        out.append("")
        # Fact-check notes
        out.append(self._build_price_discrepancy_note(titles, current_price))
        out.append("")
        out.append("Key developments:")
        for i, a in enumerate(top[:5], 1):
            s = a.get('source', 'Unknown')
            out.append(f"{i}. {a.get('title', '')}\n   └─ via {s}")

        out.append("=" * 60)
        return "\n".join(out)

    def generate_market_memo(self, ticker: str, articles: List[Dict], current_price: Optional[float] = None) -> str:
        """
        Takes raw articles + REAL TIME DATA and generates a fact-checked narrative.
        If an Anthropic/Claude key is configured, attempt AI generation; otherwise use fallback.
        """
        if not articles:
            return "No significant news found."

        # Prepare context
        top_articles = articles[:10]
        context_items = [{
            'title': a.get('title'),
            'source': a.get('source'),
            'time_ago': a.get('published_at', 'Unknown'),
            'url': a.get('url', ''),
            'relevance': a.get('relevance', ''),
            'sentiment': a.get('sentiment', ''),
        } for a in top_articles]
        context_str = json.dumps(context_items, indent=2)

        # News memos are file-only artifacts — use template formatter to avoid Claude token burn
        # (Claude is reserved for the 5 daily anchor content sessions)
        return self._fallback_formatter(ticker, top_articles, current_price)

        # Else try AI path (disabled — re-enable if memos are ever published)
        try:
            self._init_editor_engine()
            if self.editor_engine is None:
                return self._fallback_formatter(ticker, top_articles, current_price)

            price_context = ''
            if current_price is not None:
                price_context = f"CRITICAL REAL-TIME DATA: The ACTUAL current price of {ticker} is ${current_price:,.2f}.\n"

            prompt = f"""
You are a senior crypto market analyst. Write a concise, fact-checked "Market Memo" for {ticker}.

{price_context}
RAW NEWS FEED:
{context_str}

GUIDELINES:
- Use the current price as the source of truth. If headlines mention older prices, contextualize them (e.g., "dipped to $X but recovered to $Y").
- Be concise: HEADLINE (1 line), THE LEAD (2-3 sentences), KEY DEVELOPMENTS (bullets with sources).
- Tone: professional, objective (Bloomberg/Terminal style).

Output: Plain text only.
"""

            response = self.editor_engine._call_model(prompt, max_tokens=600)
            result_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    result_text += block.text
            return result_text
        except Exception as e:
            return f"Error generating narrative: {e}\n\nFallback:\n" + self._fallback_formatter(ticker, top_articles, current_price)

    def generate_news_tweet(self, ticker: str, articles: List[Dict],
                            current_price: Optional[float] = None) -> Optional[str]:
        """
        Generate a condensed 280-char tweet summarizing the top news for a ticker.

        Uses Claude if available, otherwise builds a simple template tweet.
        Returns None if there's nothing worth tweeting.
        """
        if not articles:
            return None

        top = articles[:5]
        titles = [a.get('title', '') for a in top]

        # News tweets use template fallback — Claude reserved for anchor content sessions
        if False and os.getenv('ANTHROPIC_API_KEY'):
            try:
                self._init_editor_engine()
                if self.editor_engine:
                    price_line = ''
                    if current_price is not None:
                        price_line = f"Current {ticker} price: ${current_price:,.2f}\n"

                    headlines = "\n".join(f"- {t}" for t in titles)
                    prompt = f"""Write ONE tweet (max 270 chars) summarizing the most important crypto/{ticker} news right now.

{price_line}Headlines:
{headlines}

Rules:
- Must be under 270 characters total
- Professional tone, no clickbait
- Include the price if relevant
- End with 1-2 relevant hashtags like #Bitcoin #Crypto #ETH
- No emojis spam, max 1-2 emojis
- Do NOT use quotation marks around the tweet

Output the tweet text only, nothing else."""

                    response = self.editor_engine._call_model(prompt, max_tokens=100)
                    tweet = ""
                    for block in response.content:
                        if hasattr(block, 'text'):
                            tweet += block.text
                    tweet = tweet.strip().strip('"').strip("'")
                    # Reject "no news" responses — don't post them publicly
                    _no_news_signals = [
                        'no major', 'not available', 'no crypto', 'no defi',
                        'no relevant', 'stay tuned', 'all stories relate',
                        'traditional equities', 'no significant', 'nothing to report',
                    ]
                    if any(s in tweet.lower() for s in _no_news_signals):
                        return None
                    if tweet and len(tweet) <= 280:
                        return tweet
            except Exception:
                pass

        # Fallback: template-based tweet
        top_headline = titles[0] if titles else ''
        if not top_headline:
            return None

        price_str = f" | ${current_price:,.0f}" if current_price else ""
        hashtag = f"#{ticker}" if ticker else "#Crypto"
        tweet = f"{top_headline}{price_str} {hashtag} #Crypto"

        # Trim to 280
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet
