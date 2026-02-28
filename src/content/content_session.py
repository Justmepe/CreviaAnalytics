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

        Returns dict with keys:
            headline, directional_signal, mentioned_assets, tags,
            x_thread, x_article, substack_article, substack_note,
            docx_path  ← absolute path to the .docx file written to output/newsletters/
        """
        master = self._get_master()

        result = {
            'headline':           master.get('headline', ''),
            'directional_signal': master.get('directional_signal', 'NEUTRAL'),
            'mentioned_assets':   master.get('mentioned_assets', []),
            'tags':               master.get('tags', []),
            'x_thread':           self._derive_x_thread(master),
            'x_article':          self._derive_x_article(master),
            'substack_article':   self._derive_substack_article(master),
            'substack_note':      self._derive_substack_note(master),
            'sector_threads':     self._derive_sector_threads(master),
            'docx_path':          self._write_docx(master),
        }
        return result

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

        morning_scan → sector_threads dict (6 sector threads, 4-6 tweets each) + narrative
        all other modes → thread_tweets list + narrative
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
                'commodities':    self.analysis_data.get('commodities', []),
                'news_context':   self.news_context or '',
            }, indent=2)

            if self.mode == 'morning_scan':
                prompt = self._build_morning_scan_prompt(context_json, date_str, time_str)
                max_tokens = 10000
            else:
                prompt = self._build_standard_prompt(context_json, date_str, time_str)
                max_tokens = 8000

            engine = ClaudeResearchEngine(api_key)
            response = engine._call_model(prompt, max_tokens=max_tokens)

            raw = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    raw += block.text

            master = self._parse_master_json(raw)
            logger.info(f"[ContentSession] Master brief: '{master.get('headline', '')[:60]}...'")
            return master

        except Exception as e:
            logger.error(f"[ContentSession] Claude call failed: {e}. Using template fallback.")
            return self._template_fallback()

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _build_morning_scan_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit writing the MORNING SCAN for {date_str} at {time_str}.

Your job: write 6 SECTOR-SPECIFIC threads that together cover all 22 tracked assets, so readers can choose which sectors matter to them.

SECTOR DEFINITIONS:
  majors      → BTC, ETH          (flagship pair, market structure, dominance, derivatives)
  altcoins    → XRP, SOL, BNB, AVAX, SUI, LINK  (high-cap rotation, relative strength)
  memecoins   → DOGE, SHIB, PEPE, FLOKI          (sentiment, risk appetite, volume)
  privacy     → XMR, ZEC, DASH, SCRT             (privacy narrative, DEX vs CEX flows)
  defi        → AAVE, UNI, CRV, LDO              (TVL, yields, governance)
  commodities → XAU, TSLA + macro context        (cross-asset, rate sensitivity)

MARKET DATA (JSON):
{context_json}

RULES FOR EVERY TWEET:
1. Use EXACT numbers from the data — never say "rising" without a % to back it up
2. Use emojis deliberately:
   💎 BTC  ⚡ ETH  🪙 alts  🐸 memecoins  🔒 privacy  🏦 DeFi  🌍 macro
   📊 metric  ⬆️ bullish / ⬇️ bearish  🎯 key level  ⚠️ risk/warning
3. Each tweet ≤280 chars, numbered: 1/ 2/ 3/ etc.
4. TWEET 1 of every thread = sector header + date + 2-3 top metrics + "👇"
   Example: "1/ 🏛️ MAJORS SCAN | {date_str}\\n\\nBTC Dom: 61.4% | Mcap: $2.7T | F&G: 71\\n\\nHere's where the big two stand 👇"
5. Middle tweets: one tweet per key asset — price, 24h %, one key level, one-line read
6. Final tweet: sector trade angle, rotation signal, or key watch level — give the "so what"
7. 4-6 tweets per sector. Each sector thread is POSTED SEPARATELY so keep each self-contained.
8. DO NOT repeat the same data point or insight across different sector threads.
9. Tone: authoritative analyst, zero hype, zero filler, zero em-dashes

ALSO write: a full 1500-word narrative article covering all sectors (for X Article + Substack).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Editorial, tension-driven headline for today's full scan — cite the dominant narrative and a specific price or data point",
  "sector_threads": {{
    "majors":      ["1/ tweet ≤280 chars", "2/ tweet", "3/ tweet", "4/ tweet", "5/ tweet"],
    "altcoins":    ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet", "5/ tweet"],
    "memecoins":   ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"],
    "privacy":     ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"],
    "defi":        ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"],
    "commodities": ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"]
  }},
  "narrative": "Full 1500-word professional narrative — specific numbers, no filler, covers all sectors",
  "key_insight": "2-sentence hook: state the dominant market tension, give the trade angle",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", "SOL", ...]
}}"""

    def _build_standard_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        mode_instructions = {
            'mid_day_update': (
                f"This is the MID-DAY UPDATE at {time_str}. "
                "Write a focused 6-8 tweet thread + 800-word narrative. "
                "Highlight what has CHANGED since the morning: price moves, news, derivatives shifts. "
                "Be specific — compare to earlier levels."
            ),
            'closing_bell': (
                f"This is the CLOSING BELL at {time_str}. "
                "Write a concise 6-8 tweet thread + 800-word narrative. "
                "Summarise the day: biggest movers, regime signal, overnight watch levels. "
                "Give a clear directional bias for Asian session."
            ),
            'breaking_news': (
                "This is a BREAKING NEWS post. "
                "Write a tight 5-7 tweet thread + 600-word narrative. "
                "Tweet 1: the news hook (who, what, why it matters). "
                "Tweets 2-4: market impact — which assets, which direction, key levels. "
                "Final tweet: trade angle or risk management note."
            ),
        }.get(self.mode, "Write a concise 6-tweet crypto market update thread and 600-word narrative.")

        return f"""You are a senior crypto market analyst at CreviaCockpit. {date_str} at {time_str}.

{mode_instructions}

MARKET DATA (JSON):
{context_json}

TWEET RULES:
- Use emojis: 💎 BTC | ⚡ ETH | 🪙 alts | 📊 metrics | ⬆️⬇️ direction | 🎯 levels | ⚠️ risk
- Every price claim needs an exact number from the data — no vague "rising strongly"
- Numbered: 1/ 2/ 3/ etc. Each tweet ≤280 chars
- Authoritative tone — zero hype, zero em-dashes, zero filler

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Tension-driven headline — must cite a specific asset or data point",
  "thread_tweets": [
    "1/ tweet ≤280 chars",
    "2/ tweet",
    "..."
  ],
  "narrative": "Professional narrative (800 words for update/closing, 600 for breaking news). Specific numbers throughout.",
  "key_insight": "2-sentence hook: dominant tension + trade angle",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

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
        """
        Return the primary thread as a clean list of strings.

        For morning_scan: uses the 'majors' sector thread as the representative
        x_thread (the full set lives in sector_threads).
        For other modes: uses thread_tweets directly.
        """
        # Morning scan — primary thread is the majors sector thread
        if self.mode == 'morning_scan':
            sector_threads = master.get('sector_threads', {})
            raw = sector_threads.get('majors', [])
            if not raw:
                # Try any sector as fallback
                for tweets in sector_threads.values():
                    if tweets:
                        raw = tweets
                        break
        else:
            raw = master.get('thread_tweets', [])

        tweets: List[str] = []
        for t in raw:
            s = str(t).strip()
            if s:
                tweets.append(s[:280])
        if not tweets:
            tweets = self._split_narrative_to_tweets(master.get('narrative', ''))
        return tweets

    def _derive_sector_threads(self, master: Dict) -> Dict[str, List[str]]:
        """
        For morning_scan: return the 6 sector threads from the master brief,
        each cleaned to ≤280 chars per tweet.
        For all other modes: returns an empty dict.
        """
        if self.mode != 'morning_scan':
            return {}

        SECTOR_ORDER = ['majors', 'altcoins', 'memecoins', 'privacy', 'defi', 'commodities']
        raw = master.get('sector_threads', {})
        result: Dict[str, List[str]] = {}

        for sector in SECTOR_ORDER:
            tweets = raw.get(sector, [])
            clean = [str(t).strip()[:280] for t in tweets if str(t).strip()]
            if clean:
                result[sector] = clean
            else:
                logger.warning(f"[ContentSession] No tweets for sector '{sector}' — skipped")

        if result:
            counts = {k: len(v) for k, v in result.items()}
            logger.info(f"[ContentSession] Sector threads: {counts}")

        return result

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

    def _write_docx(self, master: Dict) -> Optional[str]:
        """Format master brief as a Word document and save it. Returns path or None on error."""
        try:
            from src.utils.docx_formatter import DocxFormatter
            formatter = DocxFormatter(output_dir="output/newsletters")
            path = formatter.write(master, mode=self.mode)
            return path
        except Exception as e:
            logger.warning(f"[ContentSession] DocxFormatter failed (non-fatal): {e}")
            return None

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
