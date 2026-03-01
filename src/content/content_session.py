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

            # Split majors dict into flagship pair (BTC/ETH) and altcoins (XRP, SOL, BNB, AVAX, SUI, LINK)
            # so Claude knows exactly which assets have real data vs which to skip
            all_majors = self.analysis_data.get('majors', {})
            flagship  = {t: v for t, v in all_majors.items() if t in ('BTC', 'ETH')}
            altcoins  = {t: v for t, v in all_majors.items() if t not in ('BTC', 'ETH')}

            context_json = json.dumps({
                'date': date_str,
                'time': time_str,
                'mode': self.mode,
                'market_context': self.analysis_data.get('market_context', {}),
                'majors':         flagship,
                'altcoins':       altcoins,
                'defi':           self.analysis_data.get('defi', []),
                'memecoins':      self.analysis_data.get('memecoins', []),
                'privacy_coins':  self.analysis_data.get('privacy_coins', []),
                'commodities':    self.analysis_data.get('commodities', []),
                'news_context':   self.news_context or '',
            }, indent=2)

            if self.mode == 'morning_scan':
                prompt = self._build_morning_scan_prompt(context_json, date_str, time_str)
                max_tokens = 10000
            elif self.mode == 'mid_day_update':
                prompt = self._build_mid_day_prompt(context_json, date_str, time_str)
                max_tokens = 8000
            elif self.mode == 'closing_bell':
                prompt = self._build_closing_prompt(context_json, date_str, time_str)
                max_tokens = 8000
            else:  # breaking_news
                prompt = self._build_breaking_news_prompt(context_json, date_str, time_str)
                max_tokens = 6000

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

DATA DISCIPLINE — READ THIS FIRST:
- The JSON contains separate keys: `majors` (BTC, ETH only), `altcoins` (XRP, SOL, BNB, AVAX, SUI, LINK), `memecoins`, `privacy_coins`, `defi`, `commodities`
- Every number in a tweet MUST come from the JSON. Do NOT invent prices, percentages, or indices.
- ESPECIALLY: do NOT reference "alt season index", "alt index", "rotation index", or any index not explicitly in the JSON.
- If a ticker's entry in the JSON is empty ({{}}) or has no price/change data → SKIP that asset entirely. Do not write a tweet for it.
- Only the Fear & Greed index from market_context.fear_greed_index is real — do not create variants of it.

RULES FOR EVERY TWEET:
1. Use EXACT numbers from the data — never say "rising" without a % to back it up
2. Use emojis deliberately:
   💎 BTC  ⚡ ETH  🪙 alts  🐸 memecoins  🔒 privacy  🏦 DeFi  🌍 macro
   📊 metric  ⬆️ bullish / ⬇️ bearish  🎯 key level  ⚠️ risk/warning
3. Each tweet ≤280 chars, numbered: 1/ 2/ 3/ etc.
4. TWEET 1 of every thread = sector header + date + 2-3 top metrics from the data + "👇"
   Example: "1/ 🏛️ MAJORS SCAN | {date_str}\\n\\nBTC Dom: 61.4% | Mcap: $2.7T | F&G: 71\\n\\nHere's where the big two stand 👇"
5. Middle tweets: one tweet per asset that HAS data — price, 24h %, one key level, one-line read. Skip assets with no data.
6. Final tweet: what to watch next — a key level or condition. Do NOT label it "Signal:" or "Trade:". State it as an observation.
7. 4-6 tweets per sector. Each sector thread is POSTED SEPARATELY so keep each self-contained.
8. DO NOT repeat the same data point or insight across different sector threads.
9. ZERO em-dashes (—) or en-dashes (–). ZERO hype. ZERO filler. ZERO "Signal:" / "Trade:" labels.

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

    def _build_mid_day_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit writing the MID-DAY UPDATE for {date_str} at {time_str}.

Write 3 SECTOR-SPECIFIC threads covering the mid-day market picture.

SECTOR DEFINITIONS:
  majors_update    → BTC, ETH — what has changed since the morning open, key level holds/breaks
  alts_flow        → XRP, SOL, BNB, AVAX, SUI, LINK — top movers, rotation, relative strength
  derivatives_flow → Funding rates, OI changes, liquidations, DeFi yield update

MARKET DATA (JSON):
{context_json}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent prices, indices, or percentages.
- If a ticker has no data in the JSON → skip it. Do not write about it.
- Do NOT reference any index not in the JSON (no "alt index", "rotation index", etc.)

RULES FOR EVERY TWEET:
1. Use EXACT numbers — never say "higher" without a % or price
2. Compare to earlier levels where data allows ("was $X this morning, now $Y")
3. Use emojis deliberately:
   💎 BTC  ⚡ ETH  🪙 alts  📊 metrics  ⬆️ bullish / ⬇️ bearish  🎯 key level  ⚠️ risk  🔄 rotation
4. Each tweet ≤280 chars, numbered 1/ 2/ 3/ etc.
5. Tweet 1 of each thread: sector header + time + 2-3 top metrics + "👇"
6. Final tweet: key level or condition to watch — no "Signal:" or "Trade:" labels
7. 4-5 tweets per thread — substantive, zero filler
8. DO NOT repeat the same data point across threads
9. ZERO em-dashes (—) or en-dashes (–). Zero hype. Authoritative analyst voice.

ALSO write: an 800-word narrative covering all three sectors (for Substack + X Article).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Tension-driven mid-day headline with specific price or % and what it means",
  "sector_threads": {{
    "majors_update":    ["1/ tweet ≤280 chars", "2/ tweet", "3/ tweet", "4/ tweet", "5/ tweet"],
    "alts_flow":        ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet", "5/ tweet"],
    "derivatives_flow": ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"]
  }},
  "narrative": "800-word professional narrative covering all three sectors — specific numbers, no filler",
  "key_insight": "2-sentence hook: what changed since morning and why it matters",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_closing_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit writing the CLOSING BELL for {date_str} at {time_str}.

Write 3 SECTOR-SPECIFIC threads summarising the day and setting up the overnight/Asian session.

SECTOR DEFINITIONS:
  day_summary     → Full-day performance: BTC, ETH, total market — net change, narrative arc
  sector_wrap     → Best and worst sectors (majors vs alts vs DeFi vs memecoins vs privacy)
  overnight_watch → Key levels to hold/break overnight, macro risk, Asian session setup

MARKET DATA (JSON):
{context_json}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent prices, indices, or percentages.
- If a ticker has no data in the JSON → skip it. Do not write about it.
- Do NOT reference any index not in the JSON (no "alt index", "rotation index", etc.)

RULES FOR EVERY TWEET:
1. Use EXACT numbers — day's open vs close, % moves, key levels
2. Retrospective tone: "Today, X happened because Y"
3. Use emojis:
   💎 BTC  ⚡ ETH  🪙 alts  🏦 DeFi  🐸 memes  🔒 privacy  🌍 macro
   📊 metrics  ⬆️⬇️ direction  🎯 levels  ⚠️ risk  🌙 overnight
4. Each tweet ≤280 chars, numbered 1/ 2/ 3/ etc.
5. Tweet 1 of each thread: sector header + date + 2-3 key day metrics + "👇"
6. Final tweet of overnight_watch: the level to hold vs the level that breaks the thesis. No "Signal:" labels.
7. 4-5 tweets per thread — no padding
8. DO NOT repeat data points across threads
9. ZERO em-dashes (—) or en-dashes (–). Zero hype. Zero filler.

ALSO write: an 800-word narrative day wrap (for Substack + X Article).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Day-wrap headline — cite the dominant move, the asset, and whether it held",
  "sector_threads": {{
    "day_summary":     ["1/ tweet ≤280 chars", "2/ tweet", "3/ tweet", "4/ tweet", "5/ tweet"],
    "sector_wrap":     ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"],
    "overnight_watch": ["1/ tweet", "2/ tweet", "3/ tweet", "4/ tweet"]
  }},
  "narrative": "800-word professional day-wrap narrative — what happened, why it mattered, what's next",
  "key_insight": "2-sentence hook: the day's defining move and overnight trade angle",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_breaking_news_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit breaking a news story on {date_str} at {time_str}.

Write a TIGHT 5-7 tweet thread + 600-word narrative. This is time-sensitive.

MARKET DATA + NEWS (JSON):
{context_json}

THREAD STRUCTURE (strict):
  Tweet 1: 🚨 News hook — WHO did WHAT, one specific number, why it matters NOW
  Tweet 2: Which assets are affected and HOW (price level, % change, direction)
  Tweet 3: Context — why this matters structurally (on-chain, derivatives, narrative)
  Tweet 4: Key levels: support/resistance to watch as this plays out
  Tweet 5: The trade angle — what the smart play is and what invalidates it
  Tweet 6-7 (optional): Risk factors, related assets, broader macro angle

TWEET RULES:
1. Open tweet 1 with 🚨 — this signals breaking news
2. Use relevant asset emojis: 💎 BTC  ⚡ ETH  🪙 alts  🏦 DeFi — match the emoji to the affected asset
3. Every claim must have a number — no "significant move" without a price or %
4. Numbered: 1/ 2/ 3/ etc. Each tweet ≤280 chars
5. ZERO em-dashes (—) or en-dashes (–). Use commas or periods instead.
6. ZERO hype words: no "massive", "insane", "moon", "explode", "huge". Report facts.
7. ZERO "Signal:" / "Trade:" labels. State the observation directly.
8. Sound like a Bloomberg terminal alert, not a Telegram pump group
9. Final tweet: state the key level to watch and what its breach means — no labels, just the condition

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Breaking news headline — factual, specific, cites the asset and event",
  "thread_tweets": [
    "1/ 🚨 tweet ≤280 chars",
    "2/ tweet",
    "3/ tweet",
    "4/ tweet",
    "5/ tweet"
  ],
  "narrative": "600-word professional breaking news analysis — what happened, market impact, trade angle. No em-dashes, no hype.",
  "key_insight": "2-sentence summary: the event and its direct market implication",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "breakingnews", "bitcoin"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    @staticmethod
    def _sanitize_tweet(text: str) -> str:
        """
        Hard-enforce content rules on every tweet after Claude generates it.

        Strips:
        - Em dashes (—) and en dashes (–) → replaced with a comma+space
        - "Signal:" / "Trade:" / "Setup:" / "Alert:" labels → removed entirely
          (these imply financial advice; we state observations, readers draw conclusions)
        - Spaced hyphens used as em-dash surrogates ( - ) between words → comma
        """
        t = text

        # Em dash and en dash → ", "
        t = t.replace('\u2014', ', ').replace('\u2013', ', ')
        # Spaced hyphen as em-dash surrogate: " - " between words → ", "
        t = re.sub(r'(?<=\w) - (?=\w)', ', ', t)

        # Remove explicit signal/trade labels (case-insensitive)
        t = re.sub(r'(?i)^(signal|trade|setup|alert|watch)\s*:\s*', '', t.lstrip())
        t = re.sub(r'(?i)\n(signal|trade|setup|alert|watch)\s*:\s*', '\n', t)

        # Collapse any double commas or spaces left behind
        t = re.sub(r',\s*,', ',', t)
        t = re.sub(r'  +', ' ', t)

        return t.strip()

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
        # Sector-based modes — use first sector thread as the representative x_thread
        SECTOR_MODES = {'morning_scan', 'mid_day_update', 'closing_bell'}
        FIRST_SECTOR = {
            'morning_scan':   'majors',
            'mid_day_update': 'majors_update',
            'closing_bell':   'day_summary',
        }
        if self.mode in SECTOR_MODES:
            sector_threads = master.get('sector_threads', {})
            first_key = FIRST_SECTOR.get(self.mode, '')
            raw = sector_threads.get(first_key, [])
            if not raw:
                for tweets in sector_threads.values():
                    if tweets:
                        raw = tweets
                        break
        else:
            raw = master.get('thread_tweets', [])

        tweets: List[str] = []
        for t in raw:
            s = self._sanitize_tweet(str(t))
            if s:
                tweets.append(s[:280])
        if not tweets:
            tweets = self._split_narrative_to_tweets(master.get('narrative', ''))
        return tweets

    def _derive_sector_threads(self, master: Dict) -> Dict[str, List[str]]:
        """
        Return sector_threads for any scan mode (morning, mid-day, closing).
        Breaking news uses thread_tweets instead — returns empty dict for that mode.
        Tweets cleaned to ≤280 chars each.
        """
        SECTOR_KEYS_BY_MODE: Dict[str, List[str]] = {
            'morning_scan':   ['majors', 'altcoins', 'memecoins', 'privacy', 'defi', 'commodities'],
            'mid_day_update': ['majors_update', 'alts_flow', 'derivatives_flow'],
            'closing_bell':   ['day_summary', 'sector_wrap', 'overnight_watch'],
        }

        expected = SECTOR_KEYS_BY_MODE.get(self.mode)
        if not expected:
            return {}

        raw = master.get('sector_threads', {})
        result: Dict[str, List[str]] = {}

        for sector in expected:
            tweets = raw.get(sector, [])
            clean = [self._sanitize_tweet(str(t))[:280] for t in tweets if str(t).strip()]
            clean = [t for t in clean if t]  # drop any that became empty after sanitize
            if clean:
                result[sector] = clean
            else:
                logger.warning(f"[ContentSession] No tweets for sector '{sector}' — skipped")

        if result:
            counts = {k: len(v) for k, v in result.items()}
            logger.info(f"[ContentSession] Sector threads ({self.mode}): {counts}")

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
