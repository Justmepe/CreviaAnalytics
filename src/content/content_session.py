"""
ContentSession — ONE Claude call per content cycle, cached, derive all formats.

Replaces the pattern of calling Claude separately for:
  - X thread (ThreadBuilder.build_with_claude_ai)
  - X article (newsletter_generator.generate_daily_scan_newsletter)
  - Substack article (same)
  - Substack note (short memo)

Usage:
    session = ContentSession(analysis_data, mode='morning_scan')
    content = session.generate_all()
    # content['x_thread']          → List[str] (tweets)
    # content['x_article']         → {'title': str, 'body': str}
    # content['substack_article']  → {'title': str, 'body': str}
    # content['substack_note']     → str
    # content['headline']          → str
    # content['mentioned_assets']  → List[str]
    # content['directional_signal'] → str
"""

import os
import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SITE_URL = "https://creviacockpit.com"


class ContentSession:
    """
    Generates all content formats from a single Claude API call.

    Master brief returned by Claude:
        headline          – editorial, tension-driven title
        thread_tweets     – list of 12 tweet-sized insights (≤280 chars each)
        narrative         – 1500-word full narrative
        key_insight       – 2-sentence hook for notes
        directional_signal – BULLISH | BEARISH | NEUTRAL | RANGE_BOUND
        tags              – list of relevant hashtags
        mentioned_assets  – list of asset tickers featured
    """

    def __init__(
        self,
        analysis_data: Dict[str, Any],
        mode: str = 'morning_scan',
        news_context: Optional[str] = None,
    ):
        self.analysis_data = analysis_data
        self.mode = mode            # 'morning_scan' | 'mid_day_update' | 'closing_bell' | 'breaking_news'
        self.news_context = news_context
        self._master: Optional[Dict[str, Any]] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_all(self) -> Dict[str, Any]:
        """
        Run ONE Claude call → return all content formats.
        Subsequent calls use the cached master brief.
        """
        master = self._get_master()

        return {
            'headline':          master.get('headline', ''),
            'directional_signal': master.get('directional_signal', 'NEUTRAL'),
            'mentioned_assets':  master.get('mentioned_assets', []),
            'tags':              master.get('tags', []),
            'x_thread':          self._derive_x_thread(master),
            'x_article':         self._derive_x_article(master),
            'substack_article':  self._derive_substack_article(master),
            'substack_note':     self._derive_substack_note(master),
        }

    # ── Master brief ──────────────────────────────────────────────────────────

    def _get_master(self) -> Dict[str, Any]:
        if self._master is not None:
            return self._master
        self._master = self._call_claude_master()
        return self._master

    def _call_claude_master(self) -> Dict[str, Any]:
        """
        Call Claude once and return the master brief as a Python dict.
        Falls back to a template-based brief if the API call fails.
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("[ContentSession] No ANTHROPIC_API_KEY — using template fallback")
            return self._template_fallback()

        try:
            from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

            now = datetime.now(timezone.utc)
            date_str = now.strftime('%B %d, %Y')
            time_str = now.strftime('%H:%M UTC')

            context_json = json.dumps({
                'date': date_str,
                'time': time_str,
                'mode': self.mode,
                'market_context': self.analysis_data.get('market_context', {}),
                'majors':         self.analysis_data.get('majors', {}),
                'defi':           self.analysis_data.get('defi', []),
                'memecoins':      self.analysis_data.get('memecoins', []),
                'privacy_coins':  self.analysis_data.get('privacy_coins', []),
                'news_context':   self.news_context or '',
            }, indent=2)

            mode_instructions = {
                'morning_scan': (
                    "This is the MORNING SCAN (08:00 UTC). "
                    "Generate a comprehensive 12-tweet thread + 1500-word narrative. "
                    "Tone: authoritative, data-driven, Bloomberg-style. "
                    "Cover: market overview, BTC, ETH, alts, DeFi, derivatives, on-chain, scenarios, risk."
                ),
                'mid_day_update': (
                    "This is a MID-DAY UPDATE (12:00 or 16:00 UTC). "
                    "Generate a focused 6-tweet thread + 800-word narrative. "
                    "Compare to morning scan context. Highlight what changed."
                ),
                'closing_bell': (
                    "This is the CLOSING BELL (00:00 UTC). "
                    "Generate a concise 6-tweet thread + 800-word narrative. "
                    "Summarise the day: key moves, regime shift if any, overnight watch levels."
                ),
                'breaking_news': (
                    "This is a BREAKING NEWS post. "
                    "Generate a tight 5-tweet thread + 600-word narrative. "
                    "Lead with the news, explain market impact, give the trade angle."
                ),
            }.get(self.mode, "Generate a concise 6-tweet market update thread and 600-word narrative.")

            prompt = f"""You are a senior crypto market analyst and journalist writing for CreviaCockpit.

{mode_instructions}

MARKET DATA (JSON):
{context_json}

Return a JSON object with EXACTLY these keys:
{{
  "headline": "An editorial, tension-driven headline (e.g. 'BTC Holds $68K as Alts Bleed — Risk-Off or Opportunity?')",
  "thread_tweets": [
    "Tweet 1 text (≤280 chars, starts with '1/')",
    "Tweet 2 text (≤280 chars, starts with '2/')",
    ...
  ],
  "narrative": "Full {'' if self.mode == 'morning_scan' else 'shorter '}narrative (1500 words for morning scan, 800 words otherwise). Professional, specific, no filler.",
  "key_insight": "2-sentence market hook for a social note. State the tension, give the trade angle.",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["tag1", "tag2", "tag3"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}

Requirements:
- thread_tweets: numbered 1/, 2/, 3/... each ≤280 chars
- narrative: no filler, data-specific, cite actual numbers from the data
- headline: must create intellectual tension (not just 'Crypto Market Update')
- Return ONLY the JSON object. No preamble, no explanation."""

            engine = ClaudeResearchEngine(api_key)
            response = engine._call_model(prompt, max_tokens=8000)

            raw = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    raw += block.text

            # Parse JSON from response
            master = self._parse_master_json(raw)
            logger.info(f"[ContentSession] Master brief generated: '{master.get('headline', '')[:60]}...'")
            return master

        except Exception as e:
            logger.error(f"[ContentSession] Claude call failed: {e}. Using template fallback.")
            return self._template_fallback()

    def _parse_master_json(self, raw: str) -> Dict[str, Any]:
        """Extract JSON from Claude's response (handles markdown fences)."""
        # Strip markdown code fences
        text = re.sub(r'```(?:json)?\s*', '', raw).strip()
        # Find the JSON object
        match = re.search(r'\{[\s\S]+\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"[ContentSession] JSON parse error: {e}")

        return self._template_fallback()

    # ── Format derivation ─────────────────────────────────────────────────────

    def _derive_x_thread(self, master: Dict) -> List[str]:
        """Return thread_tweets as a clean list of strings."""
        raw = master.get('thread_tweets', [])
        tweets: List[str] = []
        for t in raw:
            s = str(t).strip()
            if s:
                tweets.append(s[:280])
        if not tweets:
            # Split narrative into tweet-sized chunks as fallback
            tweets = self._split_narrative_to_tweets(master.get('narrative', ''))
        return tweets

    def _derive_x_article(self, master: Dict) -> Dict[str, str]:
        """Return title + narrative body for X Article."""
        return {
            'title': master.get('headline', 'Crypto Market Analysis'),
            'body':  master.get('narrative', ''),
        }

    def _derive_substack_article(self, master: Dict) -> Dict[str, str]:
        """Return title + narrative for Substack Article (same content, same call)."""
        return {
            'title': master.get('headline', 'Crypto Market Analysis'),
            'body':  master.get('narrative', ''),
        }

    def _derive_substack_note(self, master: Dict) -> str:
        """
        Return a 2-3 sentence Substack Note derived from key_insight.
        """
        key = master.get('key_insight', '').strip()
        headline = master.get('headline', '').strip()
        if key:
            return f"{headline}\n\n{key}\n\nFull analysis → {SITE_URL}"
        # Fallback: use first tweet
        tweets = master.get('thread_tweets', [])
        if tweets:
            return f"{str(tweets[0]).strip()}\n\nFull analysis → {SITE_URL}"
        return f"{headline}\n\nFull analysis → {SITE_URL}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _split_narrative_to_tweets(self, narrative: str, max_len: int = 270) -> List[str]:
        """Emergency fallback: split narrative into tweet-sized chunks."""
        sentences = re.split(r'(?<=[.!?])\s+', narrative)
        tweets: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) + 1 <= max_len:
                current = f"{current} {sent}".strip() if current else sent
            else:
                if current:
                    tweets.append(current)
                current = sent[:max_len]
        if current:
            tweets.append(current)
        # Number them
        return [f"{i+1}/ {t}" for i, t in enumerate(tweets[:15])]

    def _template_fallback(self) -> Dict[str, Any]:
        """Minimal template used when Claude is unavailable."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%B %d, %Y')
        market = self.analysis_data.get('market_context', {})
        majors = self.analysis_data.get('majors', {})

        btc = majors.get('BTC', {})
        _btc_price_raw = btc.get('price', 0)
        # price may be a nested dict {'mark_price': ..., 'display': ...}
        if isinstance(_btc_price_raw, dict):
            btc_price = _btc_price_raw.get('mark_price', 0)
        else:
            btc_price = _btc_price_raw or 0
        btc_chg = btc.get('change_24h', 0)
        fg = market.get('fear_greed_index', 50)
        fg_label = market.get('fear_greed_label', 'Neutral')
        mcap = market.get('total_market_cap', 0)
        btc_dom = market.get('btc_dominance', 0)

        headline = (
            f"BTC {'Surges' if btc_chg > 2 else 'Drops' if btc_chg < -2 else 'Consolidates'} "
            f"as Market {'Heats Up' if fg > 60 else 'Cools' if fg < 40 else 'Holds'} — "
            f"{date_str}"
        )

        thread_tweets = [
            f"1/ 📊 CRYPTO MARKET SCAN — {date_str}\n\n"
            f"Total Cap: ${mcap/1e12:.2f}T | BTC Dom: {btc_dom:.1f}%\n"
            f"Fear & Greed: {fg} ({fg_label})",
            f"2/ 💎 BTC: ${btc_price:,.0f} ({btc_chg:+.1f}% 24h)\n\n"
            f"{'Bullish momentum — watch for continuation.' if btc_chg > 0 else 'Bearish pressure — watch key support levels.'}",
            f"3/ 📌 BOTTOM LINE\n\n"
            f"BTC dominance at {btc_dom:.1f}%. "
            f"{'Risk-on: alts may outperform.' if btc_dom < 50 else 'Risk-off: BTC leading.'}",
            f"4/ 🔗 Full live analysis → {SITE_URL}",
        ]

        narrative = (
            f"# {headline}\n\n"
            f"**Date:** {date_str}\n\n"
            f"Bitcoin is trading at ${btc_price:,.0f} ({btc_chg:+.1f}% over 24 hours). "
            f"Total crypto market capitalization stands at ${mcap/1e12:.2f} trillion, "
            f"with Bitcoin dominance at {btc_dom:.1f}%. "
            f"The Fear & Greed Index reads {fg} ({fg_label}), "
            f"signalling {'elevated risk appetite' if fg > 60 else 'cautious positioning' if fg < 40 else 'neutral sentiment'}. "
            f"Traders should monitor key levels and remain disciplined with position sizing."
        )

        return {
            'headline': headline,
            'thread_tweets': thread_tweets,
            'narrative': narrative,
            'key_insight': f"BTC at ${btc_price:,.0f} ({btc_chg:+.1f}%). F&G: {fg} ({fg_label}). Watch dominance for rotation signals.",
            'directional_signal': 'BULLISH' if btc_chg > 1 else 'BEARISH' if btc_chg < -1 else 'NEUTRAL',
            'tags': ['crypto', 'bitcoin', 'trading', 'markets'],
            'mentioned_assets': list(majors.keys())[:6],
        }
