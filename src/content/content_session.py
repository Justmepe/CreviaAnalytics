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

# ── Algorithm-optimised thread rules (injected into every prompt) ─────────────
# Based on 2026 X algorithm (Grok/Phoenix ranking model):
# Replies = #1 signal (13–27× a like). Questions drive replies.
# Media = huge reach boost (charts attached separately by main.py).
# Burst-posting = author diversity penalty — already fixed (5 posts/day, spaced).
# External links in main tweet = hard reach penalty — links go in first reply.
# Hashtags mid-thread = clutter penalty — 3-4 max, final tweet only.
_ALGO_RULES = """
ALGORITHM-OPTIMISED THREAD FORMAT (2026 X algorithm — follow exactly):
• Tweet 1 (HOOK): Open with a STARTER KEYWORD matching the sector, then hook + one key metric + "👇"
  Starter keywords per sector:
    BTC/ETH majors      → "BTC Scan:" / "ETH Watch:" / "Majors Scan:"
    Altcoins            → "Alt Scan:" / "Rotation Watch:"
    Memecoins           → "Memecoin Pulse:" / "Meme Watch:"
    Privacy coins       → "Privacy Watch:" / "Privacy Scan:"
    DeFi                → "DeFi Scan:" / "DeFi Watch:"
    Commodities/macro   → "Macro Alert:" / "Cross-Asset Watch:"
    News digest         → "News Digest:" / "Noon Briefing:"
    Whale activity      → "Whale Watch:" / "On-Chain Alert:"
    Macro tie-in        → "Macro Tie-In:" / "TradFi vs Crypto:"
    Evening outlook     → "Evening Outlook:" / "Night Watch:"
  Example tweet 1: "BTC Scan: Just slipped under $71K with memecoins getting wrecked — shakeout or real breakdown? 👇"
• Middle tweets: one sharp, data-backed insight per tweet. Lead with a number or emoji, not a word.
• Final tweet (REPLY MAGNET): MUST end with a direct question demanding the reader's opinion.
  Good: "BTC holding $68.5K support — bullish continuation or dead-cat bounce? Drop your take 👇"
  Bad:  "Watch the $68K level closely." (statement, no engagement hook)
• NEVER include any URL or link in any tweet — links tank algorithmic reach hard.
  (The site link is posted as a separate reply by the system — do NOT add creviacockpit.com)
• Hashtags: 3-4 max, ONLY in the FINAL tweet (e.g. #Bitcoin #BTC #Crypto #Trading). Never mid-thread.
• Each tweet ≤280 chars. Numbered: 1/ 2/ 3/ etc. NEVER cut a thought mid-sentence.
"""


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

        morning_scan → sector_threads dict (6 sector threads, adaptive tweet count) + narrative
        all other modes → thread_tweets list + narrative
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("[ContentSession] No ANTHROPIC_API_KEY — using template fallback")
            return self._template_fallback()

        try:
            from src.utils.enhanced_data_fetchers import ClaudeResearchEngine, CreditExhaustedError

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
            elif self.mode == 'news_digest':
                prompt = self._build_news_digest_prompt(context_json, date_str, time_str)
                max_tokens = 7000
            elif self.mode == 'whale_activity':
                prompt = self._build_whale_activity_prompt(context_json, date_str, time_str)
                max_tokens = 6000
            elif self.mode == 'macro_tie_in':
                prompt = self._build_macro_tie_in_prompt(context_json, date_str, time_str)
                max_tokens = 6000
            elif self.mode == 'evening_outlook':
                prompt = self._build_evening_outlook_prompt(context_json, date_str, time_str)
                max_tokens = 6000
            elif self.mode == 'weekly_review':
                # Weekly review uses compiled narratives from news_context, not live market JSON
                prompt = self._build_weekly_review_prompt(self.news_context or '', date_str, time_str)
                max_tokens = 12000
            else:  # breaking_news (kept for compatibility)
                prompt = self._build_breaking_news_prompt(context_json, date_str, time_str)
                max_tokens = 6000

            # Use Haiku for content writing (threads/articles) — much cheaper than Sonnet.
            # Override via CLAUDE_CONTENT_MODEL env var if needed.
            content_model = os.getenv('CLAUDE_CONTENT_MODEL', 'claude-haiku-4-5-20251001')
            engine = ClaudeResearchEngine(api_key, model=content_model)
            response = engine._call_model(prompt, max_tokens=max_tokens)

            raw = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    raw += block.text

            master = self._parse_master_json(raw)
            logger.info(f"[ContentSession] Master brief: '{master.get('headline', '')[:60]}...'")
            return master

        except CreditExhaustedError:
            # Re-raise — caller must halt posting, NOT use template fallback
            raise

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
- If ALL tickers in a sector have no data → omit that sector_thread key entirely from the JSON output. Do NOT write tweets about missing data. Do NOT acknowledge data gaps. Simply omit the sector.
- Only the Fear & Greed index from market_context.fear_greed_index is real — do not create variants of it.

RULES FOR EVERY TWEET:
{_ALGO_RULES}
1. Use EXACT numbers from the data — never say "rising" without a % to back it up.
2. Use emojis deliberately:
   💎 BTC  ⚡ ETH  🪙 alts  🐸 memecoins  🔒 privacy  🏦 DeFi  🌍 macro
   📊 metric  ⬆️ bullish / ⬇️ bearish  🎯 key level  ⚠️ risk/warning
3. Middle tweets: one tweet per asset that HAS data — price, 24h %, one key level, one-line read. Skip assets with no data.
4. ADAPTIVE LENGTH: Write as many tweets as the content genuinely requires. NEVER cram multiple ideas into one tweet. NEVER cut a thought mid-sentence. Each sector thread is POSTED SEPARATELY — keep each self-contained.
5. DO NOT repeat the same data point or insight across different sector threads.
6. ZERO em-dashes (—) or en-dashes (–). ZERO hype. ZERO filler. ZERO "Signal:" / "Trade:" labels.

ALSO write: a full 1500-word narrative article covering all sectors (for X Article + Substack).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Editorial, tension-driven headline for today's full scan — cite the dominant narrative and a specific price or data point",
  "sector_threads": {{
    "majors":      ["1/ BTC Scan: [hook + key metric] 👇", "2/ BTC data tweet", "3/ ETH data tweet", "4/ FINAL tweet ending with a direct question + hashtags"],
    "altcoins":    ["1/ Alt Scan: [hook + key mover] 👇", "2/ top alt tweet", "3/ rotation/flow tweet", "4/ FINAL tweet ending with a direct question + hashtags"],
    "memecoins":   ["1/ Memecoin Pulse: [hook + sentiment read] 👇", "2/ data tweet", "3/ FINAL tweet ending with a direct question + hashtags"],
    "privacy":     ["1/ Privacy Watch: [hook + key narrative] 👇", "2/ data tweet", "3/ FINAL tweet ending with a direct question + hashtags"],
    "defi":        ["1/ DeFi Scan: [hook + TVL or yield read] 👇", "2/ data tweet", "3/ FINAL tweet ending with a direct question + hashtags"],
    "commodities": ["1/ Macro Alert: [hook + gold/macro picture] 👇", "2/ data tweet", "3/ FINAL tweet ending with a direct question + hashtags"]
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
- If ALL tickers in a sector have no data → omit that sector_thread key entirely. Do NOT write tweets about missing data or acknowledge data gaps.
- Do NOT reference any index not in the JSON (no "alt index", "rotation index", etc.)

RULES FOR EVERY TWEET:
{_ALGO_RULES}
1. Use EXACT numbers — never say "higher" without a % or price.
2. Compare to earlier levels where data allows ("was $X this morning, now $Y").
3. Use emojis deliberately:
   💎 BTC  ⚡ ETH  🪙 alts  📊 metrics  ⬆️ bullish / ⬇️ bearish  🎯 key level  ⚠️ risk  🔄 rotation
4. ADAPTIVE LENGTH: Write as many tweets as the content requires. NEVER cut a sentence or thought mid-way.
5. DO NOT repeat the same data point across threads.
6. ZERO em-dashes (—) or en-dashes (–). Zero hype. Authoritative analyst voice.

ALSO write: an 800-word narrative covering all three sectors (for Substack + X Article).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Tension-driven mid-day headline with specific price or % and what it means",
  "sector_threads": {{
    "majors_update":    ["1/ Majors Scan: [hook + key level change since morning] 👇", "2/ BTC data tweet", "3/ ETH data tweet", "4/ FINAL tweet ending with a direct question + hashtags"],
    "alts_flow":        ["1/ Rotation Watch: [hook + top mover] 👇", "2/ rotation/flow tweet", "3/ relative strength tweet", "4/ FINAL tweet ending with a direct question + hashtags"],
    "derivatives_flow": ["1/ Derivatives Watch: [hook + OI/funding read] 👇", "2/ liquidations data tweet", "3/ FINAL tweet ending with a direct question + hashtags"]
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
- If ALL tickers in a sector have no data → omit that sector_thread key entirely. Do NOT write tweets about missing data or acknowledge data gaps.
- Do NOT reference any index not in the JSON (no "alt index", "rotation index", etc.)

RULES FOR EVERY TWEET:
{_ALGO_RULES}
1. Use EXACT numbers — day's open vs close, % moves, key levels.
2. Retrospective tone: "Today, X happened because Y".
3. Use emojis:
   💎 BTC  ⚡ ETH  🪙 alts  🏦 DeFi  🐸 memes  🔒 privacy  🌍 macro
   📊 metrics  ⬆️⬇️ direction  🎯 levels  ⚠️ risk  🌙 overnight
4. ADAPTIVE LENGTH: Write as many tweets as the content requires. NEVER cut a sentence or thought mid-way.
5. DO NOT repeat data points across threads.
6. ZERO em-dashes (—) or en-dashes (–). Zero hype. Zero filler.

ALSO write: an 800-word narrative day wrap (for Substack + X Article).

Return ONLY this JSON object (no preamble, no markdown):
{{
  "headline": "Day-wrap headline — cite the dominant move, the asset, and whether it held",
  "sector_threads": {{
    "day_summary":     ["1/ Closing Bell: [hook + day's dominant move + %] 👇", "2/ BTC/ETH full-day recap tweet", "3/ altcoin/sector recap tweet", "4/ FINAL tweet ending with a direct question + hashtags"],
    "sector_wrap":     ["1/ Sector Wrap: [hook + best and worst sector today] 👇", "2/ sector performance tweet", "3/ FINAL tweet ending with a direct question + hashtags"],
    "overnight_watch": ["1/ Night Watch: [hook + key level for overnight] 👇", "2/ level to hold tweet", "3/ Asia session setup tweet", "4/ FINAL tweet ending with a direct question + hashtags"]
  }},
  "narrative": "800-word professional day-wrap narrative — what happened, why it mattered, what's next",
  "key_insight": "2-sentence hook: the day's defining move and overnight trade angle",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_news_digest_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit writing the NOON NEWS DIGEST for {date_str} at {time_str}.

Aggregate everything that happened in the last 12 hours into ONE cohesive digest. Do NOT treat each story individually — synthesise the narrative. Focus on what the news means for crypto markets collectively.

MARKET DATA + NEWS (JSON):
{context_json}

{_ALGO_RULES}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent prices, indices, or percentages.
- If no meaningful news data → focus on market reaction to whatever is in the data.
- ZERO em-dashes or en-dashes. Zero hype. Zero filler.

OUTPUT — strict JSON, no markdown, no commentary outside the JSON:
{{
  "sector_threads": {{
    "top_stories": [
      "1/ News Digest: [hook — dominant headline + key number] 👇",
      "2/ most significant story — what happened + market impact",
      "3/ second story + how it connects to the first",
      "4/ any macro or regulatory angle from today's news",
      "5/ what it all means for BTC, ETH, and altcoins together",
      "6/ FINAL tweet: end with a direct question — e.g. 'News flow today is [bullish/bearish/mixed] — how are you positioned? 👇' + 3-4 hashtags"
    ],
    "market_impact": [
      "1/ Noon Briefing: [hook — how markets reacted to today's news] 👇",
      "2/ specific price reactions to the biggest stories",
      "3/ sentiment shift — fear/greed, volume flow, sector rotation",
      "4/ FINAL tweet: direct question — e.g. 'News-driven move or algo reaction? What's your read? 👇' + hashtags"
    ],
    "what_to_watch": [
      "1/ Watch: [hook — key catalyst still live into the afternoon] 👇",
      "2/ upcoming events or pending market reactions from today's news",
      "3/ key levels that matter given today's news flow",
      "4/ FINAL tweet: direct question — e.g. 'Which story is the market underreacting to right now? Drop your take 👇' + hashtags"
    ]
  }},
  "narrative": "700-word digest article: synthesise today's news flow, market reaction, and what it means going forward. Professional tone, no hype.",
  "key_insight": "2-sentence hook: the defining headline and its market implication",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "news", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_whale_activity_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior on-chain analyst at CreviaCockpit writing the WHALE ACTIVITY REPORT for {date_str} at {time_str}.

Aggregate whale moves from the last 6-12 hours and synthesise what the smart money is actually doing. Correlate large flows with price action, sentiment, and exchange positioning. Do NOT list every transaction — tell the story.

MARKET DATA + ON-CHAIN DATA (JSON):
{context_json}

{_ALGO_RULES}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent prices, indices, or flow amounts.
- If whale_data is empty → use derivatives data (OI, funding rates, liquidations) as the proxy.
- ZERO em-dashes or en-dashes. Zero hype. No "massive", "insane", "huge". Report data.

OUTPUT — strict JSON, no markdown, no commentary outside the JSON:
{{
  "sector_threads": {{
    "whale_sentiment": [
      "1/ Whale Watch: [hook — dominant whale direction + key flow number] 👇",
      "2/ aggregate exchange inflows/outflows + which direction is winning",
      "3/ largest individual moves of the day + what they indicate",
      "4/ OTC activity or unusual wallet-to-wallet patterns (if present in data)",
      "5/ correlate whale flow with current price action",
      "6/ FINAL tweet: direct question — e.g. 'Smart money is [accumulating/distributing] — do you follow the whales or fade them? 👇' + hashtags"
    ],
    "cascade_risk": [
      "1/ On-Chain Alert: [hook — leverage state + key liquidation level] 👇",
      "2/ current open interest and funding rate picture",
      "3/ key liquidation clusters sitting above and below current price",
      "4/ FINAL tweet: direct question — e.g. 'Leveraged longs at risk below $[X]K — are you holding through this or cutting? 👇' + hashtags"
    ],
    "market_read": [
      "1/ Whale Read: [hook — is on-chain data accumulation, distribution, or neutral?] 👇",
      "2/ pattern interpretation: what historical comparisons say",
      "3/ what this positioning implies for price over the next 24-48 hours",
      "4/ FINAL tweet: direct question — e.g. 'On-chain says [bullish/bearish] but price says the opposite — which do you trust? 👇' + hashtags"
    ]
  }},
  "narrative": "600-word on-chain narrative: what whales did today, why it matters, and what it implies for price. Use data, not vibes.",
  "key_insight": "2-sentence hook: dominant whale behaviour and market implication",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["onchain", "whales", "bitcoin"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_macro_tie_in_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior macro analyst at CreviaCockpit writing the MACRO TIE-IN for {date_str} at {time_str}.

Connect today's macro developments (gold, dollar, equities, Fed, CPI, yield curve) to crypto. Find the correlation. Explain what traditional finance is showing and what it means for Bitcoin, ETH, and risk assets broadly.

MARKET DATA + MACRO DATA (JSON):
{context_json}

{_ALGO_RULES}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent DXY levels, gold prices, or SPX moves.
- If macro data is sparse → use BTC/ETH price action vs commodities as the correlation lens.
- ZERO em-dashes or en-dashes. Zero hype. Analyst voice, not speculation.

OUTPUT — strict JSON, no markdown, no commentary outside the JSON:
{{
  "sector_threads": {{
    "macro_snapshot": [
      "1/ Macro Alert: [hook — dominant macro theme today + one key number] 👇",
      "2/ DXY / dollar strength and what it means for BTC correlation right now",
      "3/ gold and real yields picture — is BTC acting as a hedge or a risk asset today?",
      "4/ equities (SPX/NDX) risk-on or risk-off — and crypto's beta to that move",
      "5/ any Fed language, rate expectations, or macro data release today (skip if none)",
      "6/ FINAL tweet: direct question — e.g. 'Macro is [tailwind/headwind] for crypto right now — are you adjusting your positioning? 👇' + hashtags"
    ],
    "crypto_correlation": [
      "1/ Cross-Asset Watch: [hook — how tightly crypto is tracking TradFi today] 👇",
      "2/ BTC beta to SPX today — moving with it or diverging?",
      "3/ ETH and altcoin behaviour vs macro risk read",
      "4/ FINAL tweet: direct question — e.g. 'Crypto decoupling from equities or still following the tape? What do you see? 👇' + hashtags"
    ],
    "positioning": [
      "1/ TradFi vs Crypto: [hook — current macro regime and what it implies] 👇",
      "2/ which macro regime are we in right now: risk-on, risk-off, or transition?",
      "3/ how to think about crypto positioning given today's macro backdrop",
      "4/ FINAL tweet: direct question — e.g. 'Given macro today, are you adding crypto exposure or waiting for cleaner setup? 👇' + hashtags"
    ]
  }},
  "narrative": "700-word macro analysis: connect today's traditional market moves to crypto. Cover dollar, gold, rates, equities. Identify the dominant macro theme and its crypto implication.",
  "key_insight": "2-sentence hook: the key macro read and its crypto market implication",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["macro", "bitcoin", "markets"],
  "mentioned_assets": ["BTC", "ETH", "GOLD", "DXY"]
}}"""

    def _build_evening_outlook_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto analyst at CreviaCockpit writing the EVENING OUTLOOK for {date_str} at {time_str}.

Summarise today's market action and lay out what might happen overnight and tomorrow. Cover key levels, upcoming catalysts (CPI, FOMC, options expiry, token unlocks), and the dominant overnight risk. Give traders a concrete framework for the next 12-18 hours.

MARKET DATA + CONTEXT (JSON):
{context_json}

{_ALGO_RULES}

DATA DISCIPLINE:
- Every number MUST come from the JSON. Do NOT invent prices, levels, or catalyst dates.
- If no upcoming catalyst data is available → focus on current structure and levels.
- ZERO em-dashes or en-dashes. Zero hype. Traders need levels, not sentiment.

OUTPUT — strict JSON, no markdown, no commentary outside the JSON:
{{
  "sector_threads": {{
    "current_state": [
      "1/ Evening Outlook: [hook — today's defining move + key price level] 👇",
      "2/ today's price action: what moved, what held, and why",
      "3/ current market structure: trending, ranging, or at inflection?",
      "4/ key support and resistance levels that matter tonight",
      "5/ next catalyst on the horizon (data release, event, or expiry if known)",
      "6/ FINAL tweet: direct question — e.g. 'BTC [holding/breaking] $[X]K into the Asia session — bullish carry-through or overnight dump? 👇' + hashtags"
    ],
    "overnight_risk": [
      "1/ Night Watch: [hook — dominant overnight risk + direction] 👇",
      "2/ Asia session dynamic — what typically happens with this kind of setup",
      "3/ active liquidation clusters right now — long squeeze or short squeeze territory?",
      "4/ FINAL tweet: direct question — e.g. 'Funding rates are [positive/negative] — are you sleeping with stops set or closing positions? 👇' + hashtags"
    ],
    "key_levels": [
      "1/ Key Levels: [hook — the two most important levels for tonight] 👇",
      "2/ BTC: support to hold + resistance to break, with what each means for the trend",
      "3/ ETH key level + what alts do if BTC moves either way",
      "4/ FINAL tweet: direct question — e.g. '$[X]K is the line in the sand tonight — do you think it holds? 👇' + hashtags"
    ]
  }},
  "narrative": "600-word evening wrap: today's action, market structure, key levels, and overnight catalysts. Concrete framework — not just description, but actionable context.",
  "key_insight": "2-sentence hook: today's defining move and the overnight risk that matters most",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "trading"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_weekly_review_prompt(self, compiled_narratives: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit writing the WEEK IN REVIEW for the week ending {date_str}.

Your job: synthesise everything that happened this week into ONE authoritative long-form article (2000-2500 words) AND a punchy 6-tweet summary thread for X.

THIS WEEK'S CONTENT (compiled daily narratives — use these as your source of truth):
{compiled_narratives}

{_ALGO_RULES}

ARTICLE REQUIREMENTS:
- Title: compelling, tension-driven, cites the week's dominant theme and a specific price or data point
- Structure: Introduction (dominant weekly theme) → Market Structure (BTC/ETH/alts weekly arc) → Key Stories (3-4 most important events) → On-Chain & Macro (what the data showed) → Week Ahead (key catalysts for next week) → Closing thought
- Length: 2000-2500 words. Professional, Bloomberg-quality. No hype. No em-dashes.
- Every claim backed by numbers from the narratives above.

THREAD REQUIREMENTS (the X summary):
- Tweet 1: "Weekly Recap:" + hook summarising the week's dominant theme + key number + "👇"
- Tweets 2-5: one sharp insight per tweet from the week (biggest move, key story, on-chain read, macro tie-in)
- Tweet 6 (FINAL): direct question to drive replies — e.g. "This week [X] happened — what's your biggest conviction going into next week? 👇" + 4 hashtags

Return ONLY this JSON (no preamble, no markdown):
{{
  "headline": "Week in Review headline — tension-driven, cites dominant theme + key number",
  "thread_tweets": [
    "1/ Weekly Recap: [hook + key number] 👇",
    "2/ tweet",
    "3/ tweet",
    "4/ tweet",
    "5/ tweet",
    "6/ FINAL tweet ending with direct question + hashtags"
  ],
  "narrative": "Full 2000-2500 word article covering the week. Professional, no hype, no em-dashes.",
  "key_insight": "2-sentence hook: the week's defining move and what it sets up for next week",
  "directional_signal": "BULLISH | BEARISH | NEUTRAL | RANGE_BOUND",
  "tags": ["crypto", "bitcoin", "weekinreview", "markets"],
  "mentioned_assets": ["BTC", "ETH", ...]
}}"""

    def _build_breaking_news_prompt(self, context_json: str, date_str: str, time_str: str) -> str:
        return f"""You are a senior crypto market analyst at CreviaCockpit breaking a news story on {date_str} at {time_str}.

Write a breaking news thread + 600-word narrative. This is time-sensitive.
Thread length is ADAPTIVE: write as many tweets as the story requires — 5 if the story is simple, 10+ if it needs full context. NEVER cut a thought mid-sentence. Every tweet must be complete and ≤280 chars.

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
1. Open tweet 1 with 🚨 and "Breaking:" — this flags breaking news to the algorithm.
2. Use relevant asset emojis: 💎 BTC  ⚡ ETH  🪙 alts  🏦 DeFi — match to the affected asset.
3. Every claim must have a number — no "significant move" without a price or %.
4. Numbered: 1/ 2/ 3/ etc. Each tweet ≤280 chars.
5. ZERO em-dashes (—) or en-dashes (–). Use commas or periods instead.
6. ZERO hype words: no "massive", "insane", "moon", "explode", "huge". Report facts.
7. ZERO "Signal:" / "Trade:" labels. State the observation directly.
8. NEVER include any URL or link in any tweet.
9. Hashtags: 3-4 max in the FINAL tweet only.
10. FINAL tweet: end with a direct question that demands a reply — e.g. "Is this a buying opportunity or a warning sign? Drop your read 👇" + hashtags. Sound like Bloomberg terminal, not Telegram.

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
    def _enforce_tweet_lengths(tweets: List[str], limit: int = 278) -> List[str]:
        """
        Ensure every tweet is ≤ limit chars.

        Tweets that exceed the limit are split at the best available boundary
        (sentence end → comma → last space) before the limit.  The remainder
        continues as a new tweet so no content is ever dropped.

        This replaces the old [:280] hard-slice that cut mid-word and the
        fixed per-sector count that forced Claude to cram or omit content.
        """
        result: List[str] = []
        for tweet in tweets:
            tweet = tweet.strip()
            if not tweet:
                continue
            while len(tweet) > limit:
                chunk = tweet[:limit]
                # Prefer splitting after sentence-ending punctuation
                split_at = -1
                for punct in ('.', '!', '?'):
                    pos = chunk.rfind(punct)
                    if pos > limit // 2:
                        split_at = pos + 1  # include the punctuation
                        break
                # Fall back: comma or semicolon
                if split_at == -1:
                    for punct in (',', ';', ':'):
                        pos = chunk.rfind(punct)
                        if pos > limit // 2:
                            split_at = pos + 1
                            break
                # Last resort: last space (word boundary)
                if split_at == -1:
                    last_space = chunk.rfind(' ')
                    split_at = last_space if last_space > limit // 2 else limit
                result.append(tweet[:split_at].rstrip())
                tweet = tweet[split_at:].lstrip()
            if tweet:
                result.append(tweet)
        return result

    @staticmethod
    def _sanitize_body(text: str) -> str:
        """
        Strip em/en dashes from long-form body text (articles, narratives, notes).
        Replaces — and – with commas or periods depending on context.
        """
        if not text:
            return text
        # Em dash → ", " (mid-sentence) or ". " (at end of clause)
        t = text.replace('\u2014', ', ').replace('\u2013', ', ')
        # Spaced hyphen as em-dash surrogate: " - " between words → ", "
        t = re.sub(r'(?<=\w) - (?=\w)', ', ', t)
        # Collapse double commas / extra spaces left behind
        t = re.sub(r',\s*,', ',', t)
        t = re.sub(r'  +', ' ', t)
        return t

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
        SECTOR_MODES = {
            'morning_scan', 'mid_day_update', 'closing_bell',
            'news_digest', 'whale_activity', 'macro_tie_in', 'evening_outlook',
        }
        FIRST_SECTOR = {
            'morning_scan':    'majors',
            'mid_day_update':  'majors_update',
            'closing_bell':    'day_summary',
            'news_digest':     'top_stories',
            'whale_activity':  'whale_sentiment',
            'macro_tie_in':    'macro_snapshot',
            'evening_outlook': 'current_state',
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

        sanitized = [self._sanitize_tweet(str(t)) for t in raw if str(t).strip()]
        sanitized = [s for s in sanitized if s]
        tweets = self._enforce_tweet_lengths(sanitized)
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
            'morning_scan':    ['majors', 'altcoins', 'memecoins', 'privacy', 'defi', 'commodities'],
            'mid_day_update':  ['majors_update', 'alts_flow', 'derivatives_flow'],
            'closing_bell':    ['day_summary', 'sector_wrap', 'overnight_watch'],
            'news_digest':     ['top_stories', 'market_impact', 'what_to_watch'],
            'whale_activity':  ['whale_sentiment', 'cascade_risk', 'market_read'],
            'macro_tie_in':    ['macro_snapshot', 'crypto_correlation', 'positioning'],
            'evening_outlook': ['current_state', 'overnight_risk', 'key_levels'],
        }

        expected = SECTOR_KEYS_BY_MODE.get(self.mode)
        if not expected:
            return {}

        raw = master.get('sector_threads', {})
        result: Dict[str, List[str]] = {}

        for sector in expected:
            tweets = raw.get(sector, [])
            sanitized = [self._sanitize_tweet(str(t)) for t in tweets if str(t).strip()]
            clean = self._enforce_tweet_lengths([s for s in sanitized if s])
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
            'body':  self._sanitize_body(master.get('narrative', '')),
        }

    def _derive_substack_article(self, master: Dict) -> Dict[str, str]:
        """Return title + narrative for Substack Article (same content, same call)."""
        return {
            'title': master.get('headline', 'Crypto Market Analysis'),
            'body':  self._sanitize_body(master.get('narrative', '')),
        }

    def _derive_substack_note(self, master: Dict) -> str:
        """
        Return a 2-3 sentence Substack Note derived from key_insight.
        """
        key = self._sanitize_body(master.get('key_insight', '').strip())
        headline = self._sanitize_body(master.get('headline', '').strip())
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
            f"showing {'elevated risk appetite' if fg > 60 else 'cautious positioning' if fg < 40 else 'neutral sentiment'}. "
            f"Traders should monitor key levels and remain disciplined with position sizing."
        )

        return {
            'headline': headline,
            'thread_tweets': thread_tweets,
            'narrative': narrative,
            'key_insight': f"BTC at ${btc_price:,.0f} ({btc_chg:+.1f}%). F&G: {fg} ({fg_label}). Watch dominance for rotation flow.",
            'directional_signal': 'BULLISH' if btc_chg > 1 else 'BEARISH' if btc_chg < -1 else 'NEUTRAL',
            'tags': ['crypto', 'bitcoin', 'trading', 'markets'],
            'mentioned_assets': list(majors.keys())[:6],
        }
