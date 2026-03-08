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

THREAD LENGTH — ADAPTIVE, NOT FIXED:
• Write as many tweets as the content genuinely requires — typically 6-10, up to 15 for rich sectors.
• NEVER cut content short to hit a lower count. NEVER pad with filler to hit a higher count.
• A sector with 6 assets + derivatives + sentiment data warrants 10-12 tweets.
• A sector with 2 assets and sparse data warrants 5-6 tweets.
• The array in the JSON output is variable length — write every tweet that adds real value.

TWEET STRUCTURE:
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
  For asset-heavy sectors: give each asset its own tweet (price, %, key level, one-line read).
  For derivatives: OI, funding, liquidation data each deserve their own tweet if the numbers are notable.
• Final tweet (REPLY MAGNET): MUST end with a direct question demanding the reader's opinion.
  Good: "BTC holding $68.5K support — bullish continuation or dead-cat bounce? Drop your take 👇"
  Bad:  "Watch the $68K level closely." (statement, no engagement hook)

FORMAT RULES:
• NEVER include any URL or link in any tweet — links tank algorithmic reach hard.
• Hashtags: 3-4 max, ONLY in the FINAL tweet (e.g. #Bitcoin #BTC #Crypto #Trading). Never mid-thread.
• Each tweet ≤280 chars. Numbered: 1/ 2/ 3/ etc. NEVER cut a thought mid-sentence.
• ZERO em-dashes (—) or en-dashes (–). Use commas or periods instead.
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
                max_tokens = 9000
            elif self.mode == 'whale_activity':
                prompt = self._build_whale_activity_prompt(context_json, date_str, time_str)
                max_tokens = 9000
            elif self.mode == 'macro_tie_in':
                prompt = self._build_macro_tie_in_prompt(context_json, date_str, time_str)
                max_tokens = 9000
            elif self.mode == 'evening_outlook':
                prompt = self._build_evening_outlook_prompt(context_json, date_str, time_str)
                max_tokens = 9000
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
    "majors": [
      "1/ BTC Scan: [hook + dominant BTC metric + 👇]",
      "2/ 💎 BTC: price, 24h %, key support/resistance, one-line read",
      "3/ ⚡ ETH: price, 24h %, ETH/BTC ratio if notable, one-line read",
      "4/ 📊 Derivatives: funding rate, OI trend, liquidation pressure",
      "5/ Fear & Greed + BTC dominance read — what the sentiment picture says",
      "6/ Key level or scenario tweet — what breaks the thesis",
      "... (add more tweets for any additional notable data — up to 12 total)",
      "FINAL/ Direct question + #Bitcoin #BTC #Crypto #ETH"
    ],
    "altcoins": [
      "1/ Alt Scan: [hook + top mover + 👇]",
      "2/ XRP: price, %, key level, read",
      "3/ SOL: price, %, ecosystem note if relevant",
      "4/ BNB: price, % (skip if no data)",
      "5/ AVAX / SUI / LINK: best performer or most notable move",
      "6/ Rotation read — are alts leading or lagging BTC?",
      "... (one tweet per asset that has data, skip empties)",
      "FINAL/ Direct question + #Altcoins #Crypto #SOL #XRP"
    ],
    "memecoins": [
      "1/ Memecoin Pulse: [hook + sector sentiment + 👇]",
      "2/ DOGE: price, 24h % + volume note",
      "3/ SHIB / PEPE / FLOKI: standout mover or biggest drop",
      "4/ Risk appetite read — what memecoin action says about broader sentiment",
      "... (add tweets for notable individual movers)",
      "FINAL/ Direct question + #Memecoins #DOGE #Crypto"
    ],
    "privacy": [
      "1/ Privacy Watch: [hook + narrative context + 👇]",
      "2/ XMR: price, % + any regulatory/delisting note",
      "3/ ZEC / DASH / SCRT: notable mover or narrative development",
      "4/ Privacy sector read — regulatory pressure vs on-chain demand",
      "FINAL/ Direct question + #Monero #PrivacyCoins #Crypto"
    ],
    "defi": [
      "1/ DeFi Scan: [hook + TVL or yield read + 👇]",
      "2/ AAVE: price, %, lending rate or TVL note",
      "3/ UNI / CRV / LDO: standout protocol or notable governance/yield move",
      "4/ DeFi TVL trend — capital rotating in or out?",
      "5/ Yield environment vs TradFi rates if macro relevant",
      "FINAL/ Direct question + #DeFi #Aave #Crypto"
    ],
    "commodities": [
      "1/ Macro Alert: [hook + gold or dollar move + 👇]",
      "2/ Gold (XAU): price, % + what it says about risk appetite",
      "3/ TSLA if notable, or macro rate/dollar context",
      "4/ Cross-asset correlation — how macro is feeding crypto today",
      "FINAL/ Direct question + #Gold #Macro #Bitcoin #Crypto"
    ]
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
    "majors_update": [
      "1/ Majors Scan: [hook + what changed since morning + key number + 👇]",
      "2/ 💎 BTC: current price vs morning open, % change, level holding or breaking",
      "3/ ⚡ ETH: same treatment — what changed and why it matters",
      "4/ 📊 Mid-day derivatives snapshot: funding shift, OI change since open",
      "5/ Intraday narrative — is this morning trend continuation or reversal?",
      "... (add more if significant intraday developments)",
      "FINAL/ Direct question + hashtags"
    ],
    "alts_flow": [
      "1/ Rotation Watch: [hook + top intraday mover + 👇]",
      "2/ Best performing alt mid-day: price, %, what's driving it",
      "3/ Worst performing alt: is it bleeding or just lagging?",
      "4/ BTC dominance mid-day — alts gaining or losing ground vs BTC?",
      "5/ Any notable volume spike or rotation signal mid-session",
      "FINAL/ Direct question + hashtags"
    ],
    "derivatives_flow": [
      "1/ Derivatives Watch: [hook + OI/funding mid-day read + 👇]",
      "2/ Open interest change since morning — longs adding or covering?",
      "3/ Funding rates mid-session — crowded long or short?",
      "4/ Notable liquidation events today (if any)",
      "5/ What the derivatives tape says about conviction",
      "FINAL/ Direct question + hashtags"
    ]
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
    "day_summary": [
      "1/ Closing Bell: [hook + day's dominant theme + key price move + 👇]",
      "2/ 💎 BTC full-day arc: open vs close, dominant move, key level tested",
      "3/ ⚡ ETH full-day: performance vs BTC, key development",
      "4/ 📊 Day's derivatives picture: total liquidations, OI change, funding end-of-day",
      "5/ Fear & Greed end-of-day read vs morning — did sentiment shift?",
      "6/ Day's defining moment — the single event or level that set the tone",
      "... (more tweets if significant daily developments warrant it)",
      "FINAL/ Direct question about tomorrow + hashtags"
    ],
    "sector_wrap": [
      "1/ Sector Wrap: [hook + today's best and worst sector + 👇]",
      "2/ Best sector today: what performed and why",
      "3/ Worst sector: what bled and whether it's structural or just noise",
      "4/ Memecoins vs majors ratio — risk appetite read for the day",
      "5/ DeFi TVL or yield change on the day if notable",
      "FINAL/ Direct question + hashtags"
    ],
    "overnight_watch": [
      "1/ Night Watch: [hook + the one level that matters overnight + 👇]",
      "2/ BTC key level to hold — what happens if it breaks or holds",
      "3/ ETH overnight watch level + altcoin implications",
      "4/ Asia session setup — what the macro/time-zone dynamic suggests",
      "5/ Funding rates overnight — long squeeze or short squeeze territory?",
      "6/ Key catalyst tomorrow (if known: CPI, FOMC, expiry, unlock)",
      "FINAL/ Direct question about the overnight setup + hashtags"
    ]
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
      "1/ News Digest [date]: [attention-grabbing hook — the dominant headline + the single most important number from it] 👇",
      "2/ Story 1 — headline in plain English: what exactly happened, who is involved, what number defines it",
      "3/ Story 1 market impact — how price reacted, which assets moved and by how much, any volume spike",
      "4/ Story 2 — second-biggest development: what happened + how it connects to or diverges from story 1",
      "5/ Story 3 or macro/regulatory angle if present — what it adds to the narrative",
      "6/ Cross-asset picture — what BTC, ETH, and major alts are doing in the context of today's news collectively",
      "7/ Sentiment layer — fear/greed shift, Reddit/Twitter tone, whether retail is reacting or ignoring",
      "8/ The thesis: synthesise all stories into one coherent market read — is today's news flow net bullish, bearish, or noise?",
      "9/ FINAL tweet: end with a direct engaging question — e.g. 'News flow today is running [bullish/bearish] — are you adding exposure or waiting for the dust to settle? 👇' + 3-4 relevant hashtags",
      "... (add more tweets if additional stories or angles in the data genuinely warrant it — up to 12 total)"
    ],
    "market_impact": [
      "1/ Market Reaction: [hook — how markets responded to today's dominant story + key price level] 👇",
      "2/ Immediate price response — which assets pumped or dumped hardest and by how much",
      "3/ Volume context — was the reaction backed by real volume or a thin-market move?",
      "4/ Sector rotation — which sectors benefited, which got sold, and what that implies",
      "5/ Fear & Greed and sentiment metrics — did the number move on today's news?",
      "6/ FINAL tweet: direct question — e.g. 'News-driven move or algo reaction to headlines? What is your read? 👇' + hashtags"
    ],
    "what_to_watch": [
      "1/ Still Live: [hook — the key catalyst that has NOT fully resolved yet into this afternoon] 👇",
      "2/ The pending reaction — what the market has not yet priced in from today's news",
      "3/ Key level to watch — the price that confirms or denies the narrative from today's stories",
      "4/ Upcoming events in the next 24 hours relevant to today's news flow (if any in data)",
      "5/ The risk: what would make today's bullish/bearish read wrong — what is the counter-scenario?",
      "6/ FINAL tweet: direct question — e.g. 'Which story today is the market most underreacting to? Drop your take 👇' + hashtags"
    ]
  }},
  "narrative": "700-900 word digest article: synthesise today's news flow, market reaction, and what it means going forward. Cover the 3-4 biggest stories, how price reacted, what sentiment shows, and the key thing to watch. Professional tone, no hype.",
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
      "1/ Whale Watch [date]: [hook — dominant whale direction, total flow amount, and what it says about smart money conviction] 👇",
      "2/ Exchange net flow summary — total BTC/ETH inflows vs outflows in last 12 hours, which direction dominates",
      "3/ Largest individual transaction: wallet size, amount, direction (exchange deposit = distribution signal, withdrawal = accumulation)",
      "4/ Second-largest move or cluster pattern if present — are multiple wallets doing the same thing?",
      "5/ OTC desk or wallet-to-wallet patterns if any — cold storage moves, genesis wallet activity, miner flows",
      "6/ Correlation with price: is the whale flow confirming current price action or diverging from it?",
      "7/ Derivatives layer — does futures positioning (OI, funding) align with the on-chain whale read?",
      "8/ Historical context — what did this same flow pattern precede the last time it appeared?",
      "9/ The thesis: is smart money accumulating, distributing, or in stasis? State it plainly.",
      "10/ FINAL tweet: direct engaging question — e.g. 'Smart money is moving [X] BTC off exchanges — are you following the whales or fading this move? 👇' + 3-4 relevant hashtags",
      "... (include additional tweets for notable altcoin whale activity or DeFi protocol flows if data warrants — up to 13 total)"
    ],
    "cascade_risk": [
      "1/ Leverage Watch: [hook — current leverage state, dominant risk direction, key liquidation level] 👇",
      "2/ Open interest total and trend — growing (more leverage building) or shrinking (deleveraging)?",
      "3/ Funding rates by exchange — who is paying who, and what the skew tells us about crowded positioning",
      "4/ Long liquidation cluster above current price — what price triggers a short squeeze cascade",
      "5/ Short liquidation cluster below current price — what price triggers a long liquidation cascade",
      "6/ Recent liquidation events in last 12 hours — which side got wrecked and the dollar amount",
      "7/ The risk-reward: at current funding and OI levels, which direction has the higher cascade risk?",
      "8/ FINAL tweet: direct question — e.g. '$[X]K is the liquidation magnet — do you think longs or shorts get squeezed first? 👇' + hashtags"
    ],
    "market_read": [
      "1/ On-Chain Read: [hook — the single most important thing on-chain data tells us about current market positioning] 👇",
      "2/ Accumulation vs distribution verdict — based on exchange flows + whale behaviour combined",
      "3/ SOPR or realised profit/loss context if available — are holders selling at profit or loss?",
      "4/ MVRV or long-term holder behaviour if available — are experienced holders buying or exiting?",
      "5/ What this positioning pattern historically preceded — reference comparable data periods",
      "6/ The 24-48 hour implication — what does current on-chain setup suggest about near-term price direction?",
      "7/ FINAL tweet: direct question — e.g. 'On-chain says [bullish/bearish] but price has not confirmed it yet — which do you trust more? 👇' + hashtags"
    ]
  }},
  "narrative": "700-900 word on-chain narrative: what whales did today, the full flow picture, leverage positioning, and what it all implies for price over the next 24-48 hours. Data-led, no vibes.",
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
      "1/ Macro Tie-In [date]: [hook — dominant macro theme today and the single number that defines it] 👇",
      "2/ DXY: current level, direction today, and what dollar strength/weakness means for BTC specifically right now",
      "3/ Gold: price and direction today — is BTC tracking it (inflation hedge mode) or diverging (risk asset mode)?",
      "4/ Real yields: 10Y Treasury or TIPS move today — higher real yields = risk-off pressure on BTC",
      "5/ SPX and NDX: risk-on or risk-off session, by how much, and crypto's correlation coefficient to that move",
      "6/ Any Fed language, FOMC minutes, rate expectations shift, or macro data print today — impact on rate-sensitive assets",
      "7/ Commodity context: oil, copper (risk appetite proxies) — confirming or contradicting the dominant macro theme?",
      "8/ The synthesis: one macro regime label (risk-on / risk-off / stagflation / rate-pivot) and why today's data earns it",
      "9/ Crypto implication: given today's macro regime, what is the directional bias for BTC and ETH over next 24-48 hours?",
      "10/ FINAL tweet: direct engaging question — e.g. 'Macro is running [tailwind/headwind] for crypto right now — are you sizing up or reducing exposure? 👇' + 3-4 relevant hashtags",
      "... (add a tweet for any major macro event — CPI print, FOMC decision, jobs data — if present in data)"
    ],
    "crypto_correlation": [
      "1/ Cross-Asset Read: [hook — is crypto tracking TradFi today or doing its own thing, and why that matters] 👇",
      "2/ BTC 1-day correlation to SPX: tight or loose, and what regime that suggests",
      "3/ ETH beta vs BTC today — outperforming or underperforming risk, and what that implies for alts",
      "4/ Altcoin sector behaviour vs macro risk: which sectors are acting as risk-on plays today?",
      "5/ Dollar/gold/BTC triangle: when all three are moving, who is leading?",
      "6/ FINAL tweet: direct question — e.g. 'Crypto decoupling from equities today or still following the tape? What is your read? 👇' + hashtags"
    ],
    "positioning": [
      "1/ Regime Read: [hook — which macro regime we are in right now and what it means for allocators] 👇",
      "2/ The current macro regime classification — risk-on, risk-off, transition, or stagflation — and the evidence",
      "3/ What this regime historically means for BTC: average return, drawdown risk, typical duration",
      "4/ Altcoin positioning implication: in this regime, do alts outperform or underperform BTC?",
      "5/ Institutional perspective: what TradFi portfolios are likely doing with crypto exposure in this environment",
      "6/ The trigger: what single macro event or data print would flip the current regime to the opposite?",
      "7/ FINAL tweet: direct question — e.g. 'Given today is macro [tailwind/headwind], are you increasing crypto allocation or staying cautious? 👇' + hashtags"
    ]
  }},
  "narrative": "700-900 word macro analysis: connect today's traditional market moves to crypto. Cover dollar, gold, real yields, equities, and any macro data prints. Identify the dominant macro regime and its concrete implication for BTC, ETH, and alt positioning.",
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
      "1/ Evening Outlook [date]: [hook — today's single defining move, the exact price it reached, and why it matters] 👇",
      "2/ Today's full price arc: where we opened, key levels hit intraday, where we are closing and the % move",
      "3/ The dominant driver today: was it news, liquidation cascade, macro catalyst, or organic accumulation/distribution?",
      "4/ BTC market structure verdict: is the current trend intact, reversing, or range-bound? One sentence, one verdict.",
      "5/ ETH behaviour vs BTC today — higher beta move (altcoin season building) or lower beta (risk aversion)?",
      "6/ Best and worst performing sectors today + what the rotation implies about risk appetite",
      "7/ Volume and liquidity picture: was today's move high-conviction (volume confirms) or low-conviction (thin-market noise)?",
      "8/ Current market structure: key support level below + resistance level above, and what each means for overnight",
      "9/ Next catalyst on the horizon: tomorrow's macro events, options expiry, token unlock, or earnings if any in data",
      "10/ FINAL tweet: direct engaging question — e.g. 'BTC closing at $[X]K heading into the Asia session — do you think it carries through overnight or fades back? 👇' + 3-4 relevant hashtags",
      "... (add a tweet for any notable altcoin closing setup or DeFi/derivatives development worth flagging overnight)"
    ],
    "overnight_risk": [
      "1/ Night Watch: [hook — the dominant overnight risk, direction of risk, and the level that triggers it] 👇",
      "2/ Asia session tendency with this type of setup: historically does this pattern hold or fade in Tokyo/Hong Kong hours?",
      "3/ Funding rate state entering the overnight session — positive (longs paying) or negative (shorts paying), and the implication",
      "4/ Long liquidation cluster: the price level that triggers a cascade of long stops, and the estimated liquidation volume",
      "5/ Short liquidation cluster: the price level that triggers a short squeeze, and the estimated liquidation volume",
      "6/ Dominant overnight risk: is it a breakdown below support, a squeeze above resistance, or sideways chop?",
      "7/ FINAL tweet: direct question — e.g. 'Funding is [positive/negative] and leveraged [longs/shorts] are the crowded trade — are you sleeping with stops set or closing out? 👇' + hashtags"
    ],
    "key_levels": [
      "1/ Key Levels Tonight: [hook — the ONE level that determines whether bulls or bears win the overnight session] 👇",
      "2/ BTC primary support: the level, why it matters (previous structure, high-volume node, liquidation cluster), what break means",
      "3/ BTC primary resistance: the level, what triggers a break, and the next target above if it clears",
      "4/ ETH key level: the single most important level for ETH tonight and why",
      "5/ Altcoin domino: if BTC breaks down through support, which alt is most at risk? If BTC breaks up, which alt leads?",
      "6/ The scenario map: describe BULL scenario (holds support + target) vs BEAR scenario (breaks support + target) in one tweet each",
      "7/ FINAL tweet: direct question — e.g. '$[X]K is the line in the sand tonight — bulls hold it and we go higher, bears crack it and we revisit $[Y]K. Do you think it holds? 👇' + hashtags"
    ]
  }},
  "narrative": "700-900 word evening wrap: today's full price action, market structure, sector performance, key levels, overnight risk, and upcoming catalysts. Give traders a concrete framework for the next 12-18 hours — not just description, but context for decisions.",
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
