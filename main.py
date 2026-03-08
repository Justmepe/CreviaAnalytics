#!/usr/bin/env python3
"""
Crypto Analysis Engine - Main Orchestrator (v2.0)

IMPORTANT ARCHITECTURE CHANGE:
- Data fetching: Uses DataAggregator (Binance, CoinGecko, etc.) - NO Claude
- Content writing: Uses Claude AI (threads, reports) - Claude ONLY for writing

This separation ensures:
1. Reliable data from multiple free API sources
2. No Claude API limits for data research
3. Claude tokens used efficiently for content generation only

Run this script to start the entire analysis engine.
"""

import os
import re
import sys
import time
import json
import signal
import hashlib
import logging
import httpx
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# =============================================================================
# IMPORTS - NEW DATA LAYER
# =============================================================================

# NEW: Data aggregator (replaces Claude for data fetching)
from src.data.aggregator import DataAggregator

# Keep Claude ONLY for content writing
from src.utils.enhanced_data_fetchers import ClaudeResearchEngine, CreditExhaustedError

# Discord notifications
from src.utils.discord_notifier import DiscordNotifier

# Notion content management (write once, post anywhere)
from src.utils.notion_content_manager import get_content_manager

# X/Twitter direct posting (API + HTTP + browser fallback)
from src.utils.x_poster import XPoster
from src.utils.x_browser_poster import XBrowserPoster
from src.utils.x_http_poster import XHttpPoster

# Web API publishing
from src.utils.web_publisher import WebPublisher
from src.utils.chart_generator import generate_chart_image, pick_chart_ticker

# Content deduplication tracker
from src.utils.content_tracker import ContentTracker

# Substack Notes posting (API + browser fallback)
from src.utils.substack_poster import SubstackPoster
from src.utils.substack_browser_poster import SubstackBrowserPoster

# Analyzers (use new data layer internally)
from src.analyzers.majors_analyzer import analyze_major
from src.analyzers.memecoin_analyzer import analyze_memecoin
from src.analyzers.privacy_analyzer import analyze_privacy_coin
from src.analyzers.defi_analyzer import analyze_defi_protocol

# Intelligence layer
from src.intelligence.regime_detector import RegimeDetector
from src.intelligence.correlation_engine import CorrelationEngine
from src.intelligence.smart_money_tracker import SmartMoneyTracker
from src.intelligence.trade_setup_generator import TradeSetupGenerator
from src.intelligence.opportunity_scanner import OpportunityScanner
from src.intelligence.ta_engine import CryptoTAEngine

# Output
from src.content.x_thread_generator import generate_x_thread
from src.content.news_narrator import NewsNarrator
from src.pillars.news import get_rss_engine, _calculate_relevance
from src.utils.x_thread_builder import ThreadBuilder
from src.content.post_decorator import PostDecorator
from src.content.content_session import ContentSession
from src.content.marketing_post_generator import MarketingPostGenerator


# =============================================================================
# CONFIGURATION
# =============================================================================

load_dotenv()

# Ensure stdout supports UTF-8 for emoji characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Logging setup
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('crypto_engine.log', encoding='utf-8')
file_handler.setFormatter(log_formatter)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# API Keys
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET_KEY', '')
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
COINGLASS_API_KEY = os.getenv('COINGLASS_API_KEY', '')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
GLASSNODE_API_KEY = os.getenv('GLASSNODE_API_KEY', '')

# Intervals
RESEARCH_INTERVAL = int(os.getenv('RESEARCH_INTERVAL', '60'))
ANALYSIS_INTERVAL = int(os.getenv('ANALYSIS_INTERVAL', '300'))
THREAD_GENERATION_INTERVAL = int(os.getenv('THREAD_INTERVAL', '3600'))
# Trade setup generation throttle — Sonnet is expensive; once per hour per asset is plenty
TRADE_SETUP_INTERVAL = int(os.getenv('TRADE_SETUP_INTERVAL', '3600'))

# Assets to track (22 total)
MAJOR_ASSETS = ['BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'AVAX', 'SUI', 'LINK']  # 8 large-caps
MEMECOIN_ASSETS = ['DOGE', 'SHIB', 'PEPE', 'FLOKI']                          # 4 memecoins
PRIVACY_ASSETS = ['XMR', 'ZEC', 'DASH', 'SCRT']                              # 4 privacy coins
DEFI_ASSETS = ['AAVE', 'UNI', 'CRV', 'LDO']                                  # 4 DeFi protocols
COMMODITIES_ASSETS = ['XAU', 'TSLA']                                          # 2 commodities/tokenized stocks (Binance Futures)

# =============================================================================
# TIME-AWARE SCHEDULING
# =============================================================================

ANCHOR_SLOTS = [
    {"hour": 8,  "mode": "morning_scan",    "label": "Morning Scan",    "full_article": False},
    {"hour": 12, "mode": "news_digest",     "label": "News Digest",     "full_article": False},
    {"hour": 15, "mode": "whale_activity",  "label": "Whale Activity",  "full_article": False},
    {"hour": 18, "mode": "macro_tie_in",    "label": "Macro Tie-In",    "full_article": False},
    {"hour": 21, "mode": "evening_outlook", "label": "Evening Outlook", "full_article": False},
]
# Weekly deep-dive — Sunday 20:00 UTC, compiles the week into one long-form Substack article
WEEKLY_SLOT = {"weekday": 6, "hour": 20, "mode": "weekly_review", "label": "Week in Review"}
ANCHOR_WINDOW_MINUTES = 15        # Minutes BEFORE slot hour to trigger early
ANCHOR_CATCHUP_MINUTES = 180      # Minutes AFTER slot to catch up (3h covers PM2 restarts)
BREAKING_NEWS_INTERVAL = 900      # 15 min between breaking news checks
BREAKING_NEWS_THRESHOLD = 0.72    # Relevance score threshold for breaking (was 0.85 — too strict)
ANCHOR_COOLDOWN_MINUTES = 30      # Suppress breaking news right after anchor (was 45)

# Marketing post slots — standalone sales posts, separate from anchor content
MARKETING_SLOTS = [
    {"hour": 9,  "post_type": "pain_led",      "label": "Sales: Pain-Led"},
    {"hour": 15, "post_type": "value_stack",   "label": "Sales: Value Stack"},
    {"hour": 21, "post_type": "social_proof",  "label": "Sales: Social Proof"},
    {"hour": 1,  "post_type": "risk_reversal", "label": "Sales: Risk Reversal"},
]
MARKETING_WINDOW_MINUTES = 30    # Catch-up window for marketing slots (missed by PM2 restart)

# Directories
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path('output')
OUTPUT_DIR.mkdir(exist_ok=True)


# =============================================================================
# MAIN ORCHESTRATOR CLASS
# =============================================================================

class CryptoAnalysisOrchestrator:
    """
    Main orchestrator for the crypto analysis engine

    Architecture:
    - DataAggregator: Fetches ALL data (prices, derivatives, on-chain, etc.)
    - ClaudeResearchEngine: ONLY used for writing content (threads, reports)
    """

    def __init__(self):
        """Initialize the orchestrator"""

        logger.info("=" * 80)
        logger.info("CRYPTO ANALYSIS ENGINE v2.0 - STARTING")
        logger.info("=" * 80)

        # Initialize NEW data aggregator (replaces Claude for data)
        logger.info("Initializing data aggregator...")
        logger.info(f"   Binance API Key: {'✅ Configured' if BINANCE_API_KEY else '❌ Missing'}")
        logger.info(f"   Binance Secret: {'✅ Configured' if BINANCE_SECRET else '❌ Missing'}")
        logger.info(f"   Coinglass API Key: {'✅ Configured' if COINGLASS_API_KEY else '❌ Missing'}")
        self.data = DataAggregator(
            binance_key=BINANCE_API_KEY,
            binance_secret=BINANCE_SECRET,
            coingecko_key=COINGECKO_API_KEY,
            coinglass_key=COINGLASS_API_KEY,
            etherscan_key=ETHERSCAN_API_KEY,
            glassnode_key=GLASSNODE_API_KEY,
        )

        # Health check
        health = self.data.health_check()
        working = sum(1 for v in health.values() if v)
        logger.info(f"   Data sources: {working}/{len(health)} working")
        for source, status in health.items():
            logger.info(f"      {'[OK]' if status else '[--]'} {source}")

        # Liquidation aggregator status
        if self.data.liquidation_aggregator:
            liq_stats = self.data.liquidation_aggregator.get_stats()
            logger.info(f"   Liquidation Aggregator: {'✅ Connected' if liq_stats['connected'] else '⚠️  Connecting...'}")
            logger.info(f"      Tracking {liq_stats['symbols_tracked']} symbols via WebSocket (FREE)")

        # Initialize Claude ONLY for content writing (optional)
        self.claude_writer = None
        if ANTHROPIC_API_KEY:
            logger.info("Initializing Claude for content writing...")
            self.claude_writer = ClaudeResearchEngine(ANTHROPIC_API_KEY)
            logger.info("   Claude: Ready for thread/report generation")
        else:
            logger.warning("   Claude: Not configured (threads will use templates)")

        # News narrator (Claude for writing market memos)
        self.news_narrator = NewsNarrator()

        # RSS engine reference (shared singleton from news pillar, for image selection)
        self.rss_engine = get_rss_engine()

        # Discord notifications
        self.discord = DiscordNotifier()

        # Notion content management (NEW: write once, post anywhere!)
        self.notion_manager = get_content_manager()
        if self.notion_manager.is_available():
            logger.info("   Notion Content Manager: ✅ Connected")
            logger.info("      All content will be saved to Notion database")
        else:
            logger.warning("   Notion Content Manager: ⚠️  Not configured")
            logger.warning("      Set NOTION_API_KEY and NOTION_DATABASE_ID in .env to enable")

        # X/Twitter posting — browser (Playwright/patchright) for all X posts
        self.x_poster = None  # Official API disabled (403 Forbidden)
        self.x_http_poster = XHttpPoster()  # Keep initialized (reserved for future residential proxy)
        self.x_browser_poster = XBrowserPoster(headless=False)  # Primary: tweets, threads, articles
        self.x_use_browser = self.x_browser_poster.enabled

        if self.x_use_browser:
            logger.info("   X Browser Poster: enabled (tweets/threads/articles via browser)")
        else:
            logger.warning("   X Browser Poster: disabled (session missing or Patchright not installed)")

        # X Account 2 — CreviaCockpit (breaking news only, posts after primary)
        cockpit_session = str(Path(__file__).parent / "x_browser_session_cockpit")
        self.x_cockpit_poster = XBrowserPoster(session_dir=cockpit_session, headless=True, env_prefix="X_COCKPIT")
        if self.x_cockpit_poster.enabled:
            logger.info("   X Cockpit Poster: enabled (@CreviaCockpit — breaking news)")
        else:
            logger.info("   X Cockpit Poster: disabled (run setup_x_session_cockpit.py to activate)")

        # Web API publishing (for landing page)
        self.web_publisher = WebPublisher()
        if self.web_publisher.enabled:
            self.web_publisher.verify_connection()

        # Content deduplication tracker
        self.tracker = ContentTracker()

        # Substack Notes poster (FORCE browser mode - API is broken)
        self.substack = SubstackPoster()
        self.substack_browser = SubstackBrowserPoster()
        # FORCE browser mode - Substack API is unreliable
        self.substack_use_browser = True
        logger.info("   Substack: Using browser automation (API disabled)")

        if self.substack_use_browser and self.substack_browser.enabled:
            if self.substack_browser.verify_credentials():
                logger.info("   Substack Browser: Enabled (Playwright)")
            else:
                logger.warning("   Substack Browser: Session expired (run setup_substack_session.py)")
        elif self.substack_use_browser and not self.substack_browser.enabled:
            logger.warning("   Substack Browser: Not available (run setup_substack_session.py first)")

        # Thread builder (for breaking news threads)
        self.thread_builder = ThreadBuilder()

        # Content decorator (CTAs, hashtags, site links on every post)
        self.post_decorator = PostDecorator()

        # Marketing post generator (Hormozi-framework sales posts, 4 slots/day)
        self.marketing_gen = MarketingPostGenerator()
        logger.info("   Marketing Post Generator: Ready (pain_led / value_stack / social_proof / risk_reversal)")

        # Intelligence layer — regime detection + correlation + smart money
        self.regime_detector = RegimeDetector(aggregator=self.data)
        self.correlation_engine = CorrelationEngine()
        self.smart_money_tracker = SmartMoneyTracker()
        self.trade_setup_gen = TradeSetupGenerator()
        self.opportunity_scanner = OpportunityScanner()
        self.ta_engine = CryptoTAEngine()
        self.current_regime = None
        logger.info("   Regime Detector: Ready")
        logger.info("   Correlation Engine: Ready")
        logger.info("   Smart Money Tracker: Ready")
        logger.info(f"   Trade Setup Generator: {'Ready' if self.trade_setup_gen._enabled else 'Disabled (no API key)'}")
        logger.info("   Opportunity Scanner: Ready")
        logger.info("   CryptoTAEngine: Ready (Binance/Bybit OHLCV + Structure/Zones)")

        # State
        self.running = False
        self.latest_research = {}
        self.latest_analyses = {}
        self.cycle_count = 0

        # Timing
        self.last_research_time = 0
        self.last_analysis_time = 0
        self.last_thread_time = 0

        # Scheduling state
        self.last_anchor_date = {}            # Dict[hour] -> date when last executed
        self.last_anchor_time = None          # Timestamp of last anchor execution
        self.last_breaking_check = 0          # Timestamp of last breaking news check
        self.last_marketing_date = {}         # Dict[hour] -> date when marketing post last ran
        self.morning_context = None           # Stored thread summary for mid-day reference
        self.posted_breaking_headlines = set()  # Dedup breaking news (title hashes)
        self.recent_breaking_headlines: list = []  # [(headline_str, timestamp)] for topic similarity
        self.last_btc_price = None            # For price crash/spike detection
        self.last_price_alert_time = 0        # Cooldown for price alerts
        self.last_trade_setup_time: Dict[str, float] = {}  # Per-asset throttle for TradeSetupGenerator
        self.last_weekly_review_date: Optional[str] = None  # YYYY-MM-DD of last weekly review run
        self.credit_exhausted = False         # Set True when Anthropic credits run out

        # Weekly narrative store — path where each day's narrative is accumulated
        self.weekly_narratives_path = Path('data/weekly_narratives.json')

        logger.info("Components initialized")

    def start(self):
        """Start the orchestrator main loop with time-aware scheduling.

        Schedule:
        - 08:00 UTC: Morning Scan (full thread + X Article + Substack Article)
        - 16:00 UTC: Mid-Day Update (thread + Substack Note)
        - 00:00 UTC: Closing Bell (thread + Substack Note)
        - Between anchors: Breaking news scan every 15 min
        """

        self.running = True

        logger.info("")
        logger.info("Starting main orchestration loop (TIME-AWARE SCHEDULING)")
        logger.info(f"   Research interval: {RESEARCH_INTERVAL}s")
        logger.info(f"   Analysis interval: {ANALYSIS_INTERVAL}s")
        logger.info(f"   Anchor slots: {', '.join(f'{s['hour']:02d}:00 ({s['label']})' for s in ANCHOR_SLOTS)}")
        logger.info(f"   Breaking news interval: {BREAKING_NEWS_INTERVAL}s (threshold: {BREAKING_NEWS_THRESHOLD})")
        logger.info("")
        logger.info("Press Ctrl+C to stop gracefully")
        logger.info("=" * 80)

        try:
            while self.running:
                try:
                    self.cycle_count += 1
                    current_time = time.time()
                    now_utc = datetime.now(timezone.utc)

                    logger.info(f"\n{'='*80}")
                    logger.info(f"CYCLE #{self.cycle_count} - {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    logger.info(f"{'='*80}")

                    # 1. Research Phase (data fetching - NO Claude)
                    if current_time - self.last_research_time >= RESEARCH_INTERVAL:
                        logger.info("Starting research phase...")
                        self._run_research_phase()
                        self.last_research_time = current_time
                        logger.info("Research phase complete")

                    # 2. Analysis Phase
                    if current_time - self.last_analysis_time >= ANALYSIS_INTERVAL:
                        logger.info("Starting analysis phase...")
                        self._run_analysis_phase()
                        self.last_analysis_time = current_time
                        logger.info("Analysis phase complete")

                    # 3. Content Generation — Time-Aware Scheduling
                    anchor = self._get_current_anchor_slot()
                    if anchor:
                        # Check if this anchor has already run today
                        anchor_hour = anchor["hour"]
                        today = now_utc.strftime('%Y-%m-%d')
                        last_run = self.last_anchor_date.get(anchor_hour)

                        if last_run != today:
                            logger.info(f"ANCHOR SLOT TRIGGERED: {anchor['label']} ({anchor_hour:02d}:00 UTC)")
                            self._run_anchor_content(anchor)
                            self.last_anchor_date[anchor_hour] = today  # Mark as run today
                            self.last_anchor_time = current_time
                            self.last_thread_time = current_time
                        else:
                            logger.debug(f"Anchor {anchor['label']} already ran today ({today})")
                    # Breaking news individual posts disabled — aggregated into noon News Digest
                    # elif current_time - self.last_breaking_check > BREAKING_NEWS_INTERVAL:
                    #     self._check_and_post_breaking_news()
                    #     self._check_price_alert()
                    #     self.last_breaking_check = current_time

                    # Weekly Review — Sunday 20:00 UTC, runs once per week
                    ws = WEEKLY_SLOT
                    if now_utc.weekday() == ws["weekday"] and now_utc.hour == ws["hour"]:
                        today = now_utc.strftime('%Y-%m-%d')
                        if self.last_weekly_review_date != today:
                            logger.info(f"WEEKLY REVIEW TRIGGERED: {ws['label']}")
                            self._run_weekly_review()
                            self.last_weekly_review_date = today

                    # Marketing posts — standalone sales posts, run independently of anchors
                    mkt_slot = self._get_current_marketing_slot()
                    if mkt_slot:
                        mkt_hour = mkt_slot["hour"]
                        today = now_utc.strftime('%Y-%m-%d')
                        if self.last_marketing_date.get(mkt_hour) != today:
                            logger.info(f"MARKETING SLOT TRIGGERED: {mkt_slot['label']} ({mkt_hour:02d}:00 UTC)")
                            self._run_marketing_post(mkt_slot)
                            self.last_marketing_date[mkt_hour] = today

                    # Sleep 60s — check every minute for anchors and breaking news
                    logger.info(f"\nNext check in 60s (UTC: {now_utc.strftime('%H:%M')})...")
                    time.sleep(60)

                except CreditExhaustedError as credit_err:
                    logger.error(f"[Cycle] Anthropic credits exhausted: {credit_err}")
                    if not self.credit_exhausted:
                        self.credit_exhausted = True
                        self.discord.send_system_alert(
                            title="Anthropic Credits Exhausted",
                            message=(
                                "The engine has run out of Anthropic API credits.\n\n"
                                "**All content generation has been paused.**\n\n"
                                "To resume: top up credits at console.anthropic.com and restart the engine "
                                "(`pm2 restart crevia-engine --update-env`)."
                            ),
                            level='error',
                        )
                    continue
                except Exception as cycle_error:
                    logger.error(f"Error in cycle: {cycle_error}", exc_info=True)
                    time.sleep(5)
                    continue

        except KeyboardInterrupt:
            logger.info("\nShutdown signal received...")
            self.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.stop()

    # =========================================================================
    # TIME-AWARE SCHEDULING METHODS
    # =========================================================================

    def _get_current_anchor_slot(self) -> Optional[Dict]:
        """Check if UTC time is near an anchor slot (early trigger + 3h catch-up).

        Triggers within ANCHOR_WINDOW_MINUTES BEFORE the slot time, or within
        ANCHOR_CATCHUP_MINUTES AFTER it — so PM2 restarts don't silently miss
        morning/mid-day scans. Already-run anchors (same calendar day) are
        skipped automatically via last_anchor_date.
        """
        now = datetime.now(timezone.utc)
        today = now.strftime('%Y-%m-%d')

        for slot in ANCHOR_SLOTS:
            anchor_hour = slot["hour"]

            # Skip if already ran today
            if self.last_anchor_date.get(anchor_hour) == today:
                continue

            slot_time = now.replace(hour=anchor_hour, minute=0, second=0, microsecond=0)
            # Signed diff: positive = we're past the slot, negative = slot is in the future
            diff_seconds = (now - slot_time).total_seconds()

            # For midnight (hour=0): slot_time = today 00:00.
            # At 23:55 diff ≈ +86100s — that's 24h past, not the upcoming midnight.
            # At 00:05 diff = +300s — triggers correctly. ✓
            pre_window = ANCHOR_WINDOW_MINUTES * 60   # e.g. 900s (15 min early)
            catch_up   = ANCHOR_CATCHUP_MINUTES * 60  # e.g. 10800s (3h catch-up)

            if -pre_window <= diff_seconds <= catch_up:
                return slot

        return None

    def _get_current_marketing_slot(self) -> Optional[Dict]:
        """Check if UTC time is within the trigger window of a marketing post slot.

        Uses a narrow ±30 min window (no 3h catch-up — marketing posts are time-sensitive).
        Already-run slots (same calendar day) are skipped via last_marketing_date.
        """
        now = datetime.now(timezone.utc)
        today = now.strftime('%Y-%m-%d')
        window = MARKETING_WINDOW_MINUTES * 60

        for slot in MARKETING_SLOTS:
            hour = slot["hour"]

            if self.last_marketing_date.get(hour) == today:
                continue

            slot_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            diff = (now - slot_time).total_seconds()

            # Trigger within 30 min after the slot time (no early trigger for sales posts)
            if 0 <= diff <= window:
                return slot

        return None

    def _run_marketing_post(self, slot: Dict):
        """Generate and post a standalone marketing/sales post for X (@CreviaCockpit).

        Fires at 09:00, 15:00, 21:00, 01:00 UTC alongside regular content.
        Never touches the market intelligence thread/article pipeline.
        """
        if self.credit_exhausted:
            logger.warning(f"[Marketing] Skipping {slot['label']} — Anthropic credits exhausted")
            return

        post_type = slot["post_type"]
        label = slot["label"]

        logger.info(f"\n{'='*60}")
        logger.info(f"MARKETING POST: {label}")
        logger.info(f"{'='*60}")

        # Build lightweight market context for Claude
        try:
            global_metrics = self.data.get_global_metrics()
            market_data = global_metrics.to_dict() if global_metrics else {}
        except Exception:
            market_data = {}

        # Add regime to context
        if self.current_regime:
            market_data['regime_name'] = self.current_regime.get('regime', 'NEUTRAL')

        # Generate post
        post = None
        try:
            if post_type == 'pain_led':
                post = self.marketing_gen.generate_pain_led(market_data)
            elif post_type == 'value_stack':
                post = self.marketing_gen.generate_value_stack(market_data)
            elif post_type == 'social_proof':
                post = self.marketing_gen.generate_social_proof(market_data)
            elif post_type == 'risk_reversal':
                post = self.marketing_gen.generate_risk_reversal(market_data)
        except Exception as e:
            logger.error(f"   ❌ Marketing post generation failed: {e}", exc_info=True)
            return

        if not post or not post.get('tweets'):
            logger.warning(f"   ⚠️  No post content generated for {label}")
            return

        tweets = post['tweets']
        logger.info(f"   Generated {post['tweet_count']} tweet(s) [{post_type}]")
        for i, t in enumerate(tweets, 1):
            logger.info(f"   Tweet {i} ({len(t)} chars): {t[:80]}...")

        # Post to X via @CreviaCockpit browser poster
        if not self.x_cockpit_poster or not self.x_cockpit_poster.enabled:
            logger.warning("   ⚠️  @CreviaCockpit poster not enabled — skipping X post")
            return

        try:
            if len(tweets) == 1:
                result = self.x_cockpit_poster.post_tweet(tweets[0])
            else:
                result = self.x_cockpit_poster.post_thread({'tweets': tweets, 'tweet_count': len(tweets)})

            if result:
                logger.info(f"   ✅ Marketing post published to @CreviaCockpit")
            else:
                logger.error(f"   ❌ @CreviaCockpit post returned False")
        except Exception as e:
            logger.error(f"   ❌ @CreviaCockpit post exception: {e}", exc_info=True)

    def _run_anchor_content(self, slot: Dict):
        """Execute full content pipeline for an anchor time slot."""

        if self.credit_exhausted:
            logger.warning(f"[Anchor] Skipping {slot['label']} — Anthropic credits exhausted")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"ANCHOR SLOT: {slot['label']} ({slot['hour']:02d}:00 UTC)")
        logger.info(f"{'='*80}")

        # 1. Ensure research + analysis are fresh
        current_time = time.time()
        if current_time - self.last_research_time >= RESEARCH_INTERVAL:
            self._run_research_phase()
            self.last_research_time = current_time

        if current_time - self.last_analysis_time >= ANALYSIS_INTERVAL:
            self._run_analysis_phase()
            self.last_analysis_time = current_time

        # 2. ContentSession — ONE Claude call generates ALL content for this slot.
        session_content = self._run_content_session(slot["mode"])

        # Guard: ContentSession may have exhausted credits — abort before any fallback Claude calls
        if self.credit_exhausted:
            logger.warning(f"[Anchor] Credits exhausted after ContentSession — aborting {slot['label']}")
            return

        sector_threads = session_content.get('sector_threads', {}) if session_content else {}

        mode = slot["mode"]

        # 3. All slots: post sector threads to X + Substack note (no daily articles)
        if sector_threads:
            logger.info(f"[{slot['label']}] Posting {len(sector_threads)} sector threads...")
            if mode == "morning_scan":
                majors_tweets = sector_threads.get('majors', [])
                if majors_tweets:
                    self.morning_context = majors_tweets[0][:200]
            self._post_sector_threads(sector_threads, session_content)
        else:
            logger.warning(f"[{slot['label']}] No sector_threads — falling back to single thread")
            thread_data = self._run_thread_generation(
                thread_mode=mode if mode in ('morning_scan', 'mid_day_update', 'closing_bell') else 'morning_scan',
                previous_context=self.morning_context,
                session_content=session_content,
            )
            if thread_data and mode == "morning_scan":
                tweets = thread_data.get('tweets', [])
                if tweets:
                    self.morning_context = tweets[0][:200]

        # Post Substack note for all slots
        self._post_anchor_note(None, slot, session_content=session_content)

        # Store narrative for weekly compilation
        self._store_daily_narrative(mode, session_content)

        self._run_news_memo_generation()
        logger.info(f"Anchor slot {slot['label']} complete")

    def _post_anchor_article(self, thread_data: Dict, session_content: Optional[Dict] = None):
        """Post full article to X Articles + Substack Article (morning slot)."""
        try:
            logger.info(f"\n{'='*80}")
            logger.info("📰 POSTING MORNING SCAN ARTICLE")
            logger.info(f"{'='*80}")

            from src.content.newsletter_generator import generate_daily_scan_newsletter

            title = "Daily Crypto Market Scan"
            body = ""

            # Path 1: Reuse ContentSession output — zero extra Claude calls
            if session_content and session_content.get('x_article', {}).get('body'):
                logger.info("\n📝 Step 1: Using pregenerated article from ContentSession...")
                art = session_content['x_article']
                title = art.get('title', 'Daily Crypto Market Scan')
                body = art.get('body', '')
                logger.info(f"   ✅ Article from ContentSession: {len(body.split())} words")

            # Path 2: Generate fresh via newsletter generator (no ContentSession available)
            if not body:
                if not hasattr(self, 'latest_analyses') or 'BTC' not in self.latest_analyses:
                    logger.warning("⚠️  No analysis data available - using fallback")
                    body = self._build_article_body(thread_data)
                    title = "Daily Crypto Market Scan"
                else:
                    logger.info("\n📝 Step 1: Generating article with Claude AI...")

                    sector_analyses = {
                        'memecoins': [self.latest_analyses.get(t) for t in MEMECOIN_ASSETS if t in self.latest_analyses],
                        'privacy': [self.latest_analyses.get(t) for t in PRIVACY_ASSETS if t in self.latest_analyses],
                        'defi': [self.latest_analyses.get(t) for t in DEFI_ASSETS if t in self.latest_analyses],
                        'commodities': [self.latest_analyses.get(t) for t in COMMODITIES_ASSETS if t in self.latest_analyses],
                    }
                    logger.info(f"   Sector data: {len(sector_analyses['memecoins'])} memecoins, {len(sector_analyses['privacy'])} privacy, {len(sector_analyses['defi'])} DeFi, {len(sector_analyses['commodities'])} commodities")

                    global_metrics = self.data.get_global_metrics()
                    market_context = global_metrics.to_dict() if global_metrics else {}

                    try:
                        newsletter = generate_daily_scan_newsletter(
                            btc_analysis=self.latest_analyses.get('BTC', {}),
                            eth_analysis=self.latest_analyses.get('ETH', {}),
                            market_context=market_context,
                            sector_analyses=sector_analyses,
                            all_analyses=self.latest_analyses
                        )

                        title = newsletter.get('title', 'Daily Crypto Market Scan')
                        body = newsletter.get('body', '')
                        word_count = newsletter.get('word_count', 0)

                        if body:
                            logger.info(f"   ✅ Article generated: {word_count} words by {newsletter.get('generated_by', 'Unknown')}")
                        else:
                            logger.warning("   ❌ Newsletter returned empty - using fallback")
                            body = self._build_article_body(thread_data)
                    except Exception as e:
                        logger.error(f"   ❌ Newsletter generation failed: {e}")
                        logger.info("   Falling back to thread-based article")
                        body = self._build_article_body(thread_data)
                        title = "Daily Crypto Market Scan"

            if not body:
                logger.error("❌ Could not generate article body - aborting")
                return

            # Apply PostDecorator — Substack gets its own CTA variant
            assets = session_content.get('mentioned_assets', ['BTC', 'ETH']) if session_content else ['BTC', 'ETH']
            _, sub_body, _ = self.post_decorator.decorate_substack_article(title, body, assets)

            # Save to Notion first (write once, post anywhere)
            if self.notion_manager and self.notion_manager.is_available():
                try:
                    notion_result = self.notion_manager.save_news_post(
                        title=title,
                        content=body,
                        tags=['morning_scan', 'article', 'daily']
                    )
                    logger.info(f"   ✅ Notion: Morning article saved (ID: {notion_result})")
                except Exception as e:
                    logger.warning(f"   ⚠️  Notion save failed: {e}")

            # X Article — DISABLED: X focuses on threads only
            logger.info("\n📤 Step 2: X Article skipped (X = threads only)")

            # Substack Article
            logger.info("\n📤 Step 3: Posting article to Substack...")
            if self.substack_use_browser and self.substack_browser.enabled:
                try:
                    sub_result = self.substack_browser.post_article(title, sub_body)
                    if sub_result:
                        logger.info("   ✅ Substack Article posted successfully")
                    else:
                        logger.error("   ❌ Substack Article posting returned False")
                except Exception as e:
                    logger.error(f"   ❌ Substack Article exception: {e}", exc_info=True)
            else:
                logger.warning("   ⚠️  Substack Article posting disabled")

            # Publish morning article to web analysis feed
            logger.info("\n🌐 Web: Publishing morning article to analysis feed...")
            if self.web_publisher.enabled and body:
                try:
                    mentioned = session_content.get('mentioned_assets', ['BTC', 'ETH']) if session_content else ['BTC', 'ETH']
                    morning_chart = generate_chart_image('BTC', '1d')
                    web_result = self.web_publisher.publish_article(
                        title=title,
                        body=body,
                        sector='global',
                        tickers=mentioned,
                        image_url=morning_chart,
                        market_snapshot={'mode': 'morning_scan'},
                    )
                    if web_result:
                        logger.info(f"   ✅ Morning article published to web: /post/{web_result.get('slug', '?')}")
                    else:
                        logger.warning("   ⚠️  Web morning article publish failed")
                except Exception as e:
                    logger.warning(f"   ⚠️  Web morning article publish exception: {e}")
            else:
                logger.debug("   Web publisher disabled or no body — skipping")

            logger.info(f"\n{'='*80}")
            logger.info("✅ Morning scan article posting complete")
            logger.info(f"{'='*80}\n")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Anchor article posting error: {e}", exc_info=True)

    def _post_sector_threads(self, sector_threads: Dict, session_content: Dict):
        """
        Morning scan: post each sector thread to X (main + @CreviaCockpit) with a delay
        between them so they don't flood the timeline, then post the long-form article.

        Order: majors → altcoins → memecoins → privacy → defi → commodities
        """
        # Sector ordering: dict preserves insertion order — use whatever sectors Claude returned
        SECTOR_LABELS = {
            # Morning scan
            'majors':            '🏛️  MAJORS',
            'altcoins':          '🪙  ALTCOINS',
            'memecoins':         '🐸  MEMECOINS',
            'privacy':           '🔒  PRIVACY',
            'defi':              '🏦  DeFi',
            'commodities':       '🌍  COMMODITIES & MACRO',
            # Mid-day
            'majors_update':     '🏛️  MAJORS UPDATE',
            'alts_flow':         '🪙  ALTS & MOVERS',
            'derivatives_flow':  '📊  DERIVATIVES & FLOW',
            # Closing
            'day_summary':       '🌅  DAY SUMMARY',
            'sector_wrap':       '🔍  SECTOR WRAP',
            'overnight_watch':   '🌙  OVERNIGHT WATCH',
            # News Digest (12:00)
            'top_stories':       '🗞️  NEWS DIGEST',
            'market_impact':     '📊  MARKET IMPACT',
            'what_to_watch':     '👀  WHAT TO WATCH',
            # Whale Activity (15:00)
            'whale_sentiment':   '🐋  WHALE WATCH',
            'cascade_risk':      '⚠️  CASCADE RISK',
            'market_read':       '📖  WHALE READ',
            # Macro Tie-In (18:00)
            'macro_snapshot':    '🌍  MACRO TIE-IN',
            'crypto_correlation':'📈  CRYPTO CORRELATION',
            'positioning':       '🎯  POSITIONING',
            # Evening Outlook (21:00)
            'current_state':     '🌙  EVENING OUTLOOK',
            'overnight_risk':    '⚡  OVERNIGHT RISK',
            'key_levels':        '📍  KEY LEVELS',
        }
        SECTOR_ORDER = list(sector_threads.keys())   # preserves Claude's insertion order
        DELAY_BETWEEN = 120  # 2 minutes between sector threads

        # Representative tickers per sector — used for chart + web tickers field
        SECTOR_TICKERS = {
            'majors':            ['BTC', 'ETH', 'BNB', 'XRP'],
            'altcoins':          ['SOL', 'AVAX', 'LINK', 'SUI'],
            'memecoins':         ['DOGE', 'SHIB', 'PEPE', 'FLOKI'],
            'privacy':           ['XMR', 'ZEC', 'DASH'],
            'defi':              ['AAVE', 'UNI', 'CRV', 'LDO'],
            'commodities':       ['BTC', 'ETH'],
            'majors_update':     ['BTC', 'ETH'],
            'alts_flow':         ['SOL', 'AVAX', 'LINK'],
            'derivatives_flow':  ['BTC', 'ETH'],
            'day_summary':       ['BTC', 'ETH'],
            'sector_wrap':       ['BTC', 'ETH'],
            'overnight_watch':   ['BTC', 'ETH'],
            # News Digest
            'top_stories':       ['BTC', 'ETH'],
            'market_impact':     ['BTC', 'ETH'],
            'what_to_watch':     ['BTC', 'ETH'],
            # Whale Activity
            'whale_sentiment':   ['BTC', 'ETH', 'SOL'],
            'cascade_risk':      ['BTC', 'ETH'],
            'market_read':       ['BTC', 'ETH'],
            # Macro Tie-In
            'macro_snapshot':    ['BTC', 'ETH'],
            'crypto_correlation':['BTC', 'ETH'],
            'positioning':       ['BTC', 'ETH'],
            # Evening Outlook
            'current_state':     ['BTC', 'ETH'],
            'overnight_risk':    ['BTC', 'ETH'],
            'key_levels':        ['BTC', 'ETH'],
        }

        posted_count = 0
        for sector in SECTOR_ORDER:
            tweets = sector_threads.get(sector, [])
            if not tweets:
                logger.warning(f"[SectorThreads] No tweets for '{sector}' — skipping")
                continue

            label = SECTOR_LABELS.get(sector, sector.upper())
            logger.info(f"\n{'='*60}")
            logger.info(f"📡 {label} thread ({len(tweets)} tweets)...")

            body = '\n'.join(tweets)

            # Dedup check — skip if content already posted
            if self.tracker.is_duplicate(body):
                logger.info(f"   ↩️  {label} duplicate detected — skipping")
                continue

            thread_data = {'tweets': tweets, 'tweet_count': len(tweets)}

            # ── Main account ──────────────────────────────────────────────
            result = None
            if getattr(self.x_browser_poster, 'enabled', False):
                result = self.x_browser_poster.post_thread(thread_data)

            if result and result.get('success'):
                logger.info(f"   ✅ {label} posted (main)")
                self.tracker.record_post(
                    body=body,
                    content_type='sector_thread',
                    ticker='MARKET',
                    sector=sector,
                )
                posted_count += 1
            else:
                logger.warning(f"   ❌ {label} main account failed")

            # ── @CreviaCockpit ────────────────────────────────────────────
            if getattr(self.x_cockpit_poster, 'enabled', False):
                cockpit_result = self.x_cockpit_poster.post_thread(thread_data)
                if cockpit_result and cockpit_result.get('success'):
                    logger.info(f"   ✅ {label} posted (@CreviaCockpit)")
                else:
                    logger.warning(f"   ⚠️  {label} @CreviaCockpit failed")

            # ── Publish to web feed ───────────────────────────────────────
            if self.web_publisher.enabled:
                try:
                    sector_tickers = SECTOR_TICKERS.get(sector, ['BTC', 'ETH'])
                    sector_chart = generate_chart_image(pick_chart_ticker(sector_tickers), '4h')
                    web_result = self.web_publisher.publish_thread(
                        thread_data=thread_data,
                        tickers=sector_tickers,
                        sector=sector,
                        image_url=sector_chart,
                    )
                    if web_result:
                        logger.info(f"   ✅ {label} published to web: /post/{web_result.get('slug', '?')}")
                    else:
                        logger.warning(f"   ⚠️  {label} web publish returned None")
                except Exception as e:
                    logger.warning(f"   ⚠️  {label} web publish exception: {e}")

            # Wait before next sector (skip delay after the last one)
            if sector != SECTOR_ORDER[-1]:
                logger.info(f"   ⏳ Waiting {DELAY_BETWEEN}s before next sector...")
                time.sleep(DELAY_BETWEEN)

        logger.info(f"\n[SectorThreads] Done — {posted_count}/{len(sector_threads)} threads posted")

    def _post_anchor_note(self, thread_data: Optional[Dict], slot: Dict,
                          session_content: Optional[Dict] = None):
        """Post summary note to Substack (mid-day/closing slots)."""
        try:
            # Prefer ContentSession's pre-generated note; fall back to thread-based builder
            if session_content and session_content.get('substack_note'):
                summary = session_content['substack_note']
            else:
                summary = self._build_note_summary(thread_data, slot) if thread_data else None

            if not summary:
                return

            # Decorate with CTA
            summary = self.post_decorator.decorate_substack_note(summary, ['BTC', 'ETH'])

            # Save to Notion (write once, post anywhere)
            if self.notion_manager and self.notion_manager.is_available():
                try:
                    notion_result = self.notion_manager.save_tweet_thread(
                        title=f"{slot['label']} Update",
                        content=summary,
                        tags=['anchor_note', slot['mode']]
                    )
                    logger.info(f"   ✅ Notion: {slot['label']} note saved (ID: {notion_result})")
                except Exception as e:
                    logger.warning(f"   ⚠️  Notion save failed: {e}")

            if self.substack_use_browser and self.substack_browser.enabled:
                note_id = self.substack_browser.post_memo_as_note(
                    ticker="MARKET", memo=summary
                )
                if note_id:
                    logger.info(f"{slot['label']} Substack Note posted")
            elif self.substack.enabled:
                self.substack.post_memo_as_note(
                    ticker="MARKET", memo=summary
                )

        except Exception as e:
            logger.error(f"Anchor note posting error: {e}")

    def _in_anchor_cooldown(self) -> bool:
        """Return True if within ANCHOR_COOLDOWN_MINUTES after last anchor."""
        if self.last_anchor_time is None:
            return False
        elapsed = (time.time() - self.last_anchor_time) / 60
        return elapsed < ANCHOR_COOLDOWN_MINUTES

    # ── Topic similarity dedup ─────────────────────────────────────────────────

    _TOPIC_STOPWORDS = {
        'that', 'this', 'with', 'from', 'have', 'been', 'will', 'they', 'their',
        'about', 'more', 'news', 'says', 'said', 'into', 'also', 'some', 'hits',
        'amid', 'over', 'after', 'just', 'only', 'than', 'were', 'when', 'what',
        'most', 'high', 'rise', 'fell', 'fall', 'drop', 'jump', 'gain',
    }

    def _significant_words(self, text: str) -> set:
        """Extract significant words from a headline (>3 chars, not stopwords)."""
        return {
            w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', text)
            if w.lower() not in self._TOPIC_STOPWORDS
        }

    def _is_same_topic(self, headline: str, window_hours: float = 4.0) -> bool:
        """
        Return True if headline is semantically similar to a recently posted
        breaking news headline (same story, different source or wording).

        Uses word-overlap: if >= 3 significant words match AND overlap ratio > 40%,
        treat as same topic.
        """
        cutoff = time.time() - window_hours * 3600
        # Prune old entries first
        self.recent_breaking_headlines = [
            (h, t) for h, t in self.recent_breaking_headlines if t >= cutoff
        ]
        new_words = self._significant_words(headline)
        if len(new_words) < 3:
            return False
        for posted_h, _ in self.recent_breaking_headlines:
            posted_words = self._significant_words(posted_h)
            overlap = new_words & posted_words
            if len(overlap) >= 3 and len(overlap) / max(len(new_words), 1) >= 0.4:
                logger.info(
                    f"[BreakingDedup] Same topic blocked — overlap {overlap} "
                    f"with: '{posted_h[:60]}...'"
                )
                return True
        return False

    def _run_content_session(self, mode: str, news_context: Optional[str] = None) -> Optional[Dict]:
        """
        Run ContentSession for the given mode — ONE Claude call covers thread + article + note.
        Pass news_context for breaking_news mode (headline + summary of the event).
        Returns the content dict or None on failure.
        """
        try:
            global_context = self.latest_research.get('global', {})

            # Inject fresh prices so altcoin data is never stale
            all_tickers = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS + COMMODITIES_ASSETS
            try:
                fresh_prices = self.data.get_prices_batch(all_tickers)
                analyses = self._inject_prices(self.latest_analyses.copy(), fresh_prices)
            except Exception as _price_err:
                logger.warning(f"[ContentSession] Fresh price fetch failed: {_price_err} — using cached")
                analyses = self.latest_analyses

            analysis_data = {
                'market_context': global_context,
                'majors': {t: analyses.get(t, {}) for t in MAJOR_ASSETS if t in analyses},
                'defi': [analyses.get(t, {}) for t in DEFI_ASSETS if t in analyses],
                'memecoins': [analyses.get(t, {}) for t in MEMECOIN_ASSETS if t in analyses],
                'privacy_coins': [analyses.get(t, {}) for t in PRIVACY_ASSETS if t in analyses],
                'commodities': [analyses.get(t, {}) for t in COMMODITIES_ASSETS if t in analyses],
            }

            # Mode-specific extra context
            if mode == 'news_digest':
                analysis_data['news_feed'] = self._collect_recent_news(hours=12)
            elif mode == 'whale_activity':
                analysis_data['whale_data'] = self._collect_whale_context()
            elif mode in ('macro_tie_in', 'evening_outlook'):
                analysis_data['macro_news'] = self._collect_recent_news(hours=6)

            logger.info(f"[ContentSession] Running {mode} master brief (single Claude call)...")
            session = ContentSession(analysis_data, mode=mode, news_context=news_context)
            content = session.generate_all()
            headline = content.get('headline', '')
            tweet_count = len(content.get('x_thread', []))
            logger.info(f"[ContentSession] Done — '{headline[:60]}...' ({tweet_count} tweets)")
            return content
        except CreditExhaustedError as e:
            logger.error(f"[ContentSession] Anthropic credits exhausted: {e}")
            if not self.credit_exhausted:
                self.credit_exhausted = True
                self.discord.send_system_alert(
                    title="Anthropic Credits Exhausted",
                    message=(
                        "The engine has run out of Anthropic API credits.\n\n"
                        "**All content generation has been paused.**\n\n"
                        "To resume: top up credits at console.anthropic.com and restart the engine "
                        "(`pm2 restart crevia-engine --update-env`)."
                    ),
                    level='error',
                )
            return None
        except Exception as e:
            logger.warning(f"[ContentSession] Failed: {e} — pipeline will use legacy generators")
            return None

    def _check_price_alert(self):
        """Detect significant BTC price moves (>3% per cycle) and post breaking alert."""
        try:
            # Cooldown: don't fire price alerts more than once per 2 hours
            if time.time() - self.last_price_alert_time < 7200:
                return

            if not hasattr(self, 'data_aggregator') or not self.data_aggregator:
                return

            btc_snapshot = self.data_aggregator.get_asset_snapshot('BTC')
            if not btc_snapshot or not btc_snapshot.price:
                return

            current_price = btc_snapshot.price.mark_price
            change_24h = btc_snapshot.price.price_change_24h or 0

            # Update tracked price
            prev_price = self.last_btc_price
            self.last_btc_price = current_price

            if prev_price is None:
                return

            # Cycle-over-cycle change
            cycle_change_pct = ((current_price - prev_price) / prev_price) * 100

            # Trigger on >3% move per cycle OR >8% 24h move
            threshold_cycle = 3.0
            threshold_24h = 8.0

            if abs(cycle_change_pct) >= threshold_cycle or abs(change_24h) >= threshold_24h:
                direction = "CRASH" if cycle_change_pct < 0 else "SPIKE"
                alert_headline = (
                    f"Bitcoin {direction}: BTC {'drops' if cycle_change_pct < 0 else 'surges'} "
                    f"{abs(cycle_change_pct):.1f}% to ${current_price:,.0f} "
                    f"(24h: {change_24h:+.1f}%)"
                )
                logger.info(f"⚡ PRICE ALERT: {alert_headline}")

                # Build synthetic item for breaking news pipeline
                price_item = {
                    'title': alert_headline,
                    'summary': (
                        f"Bitcoin has moved {cycle_change_pct:+.1f}% in the last cycle, "
                        f"currently trading at ${current_price:,.0f}. "
                        f"24-hour change: {change_24h:+.1f}%. "
                        f"This significant price action warrants immediate attention."
                    ),
                    'source': 'Crevia Price Monitor',
                    'published_at': datetime.now(timezone.utc),
                    'currencies': ['BTC'],
                }
                self._post_breaking_news(price_item, 0.95)
                self.last_price_alert_time = time.time()

        except Exception as e:
            logger.warning(f"Price alert check error: {e}")

    def _store_daily_narrative(self, mode: str, session_content: Optional[Dict]) -> None:
        """
        Append today's narrative to weekly_narratives.json so the Sunday
        Week in Review can compile them into one long-form article.
        Keeps only the last 35 entries (7 days × 5 slots).
        """
        if not session_content:
            return
        narrative = session_content.get('narrative', '') or session_content.get('key_insight', '')
        headline  = session_content.get('headline', '')
        if not narrative:
            return
        try:
            self.weekly_narratives_path.parent.mkdir(parents=True, exist_ok=True)
            entries: list = []
            if self.weekly_narratives_path.exists():
                try:
                    entries = json.loads(self.weekly_narratives_path.read_text(encoding='utf-8'))
                except Exception:
                    entries = []
            entries.append({
                'date':      datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'time':      datetime.now(timezone.utc).strftime('%H:%M UTC'),
                'mode':      mode,
                'headline':  headline,
                'narrative': narrative[:3000],  # cap per entry so file stays manageable
            })
            # Keep last 35 entries (7 days × 5 slots)
            entries = entries[-35:]
            self.weekly_narratives_path.write_text(json.dumps(entries, indent=2), encoding='utf-8')
            logger.debug(f"[WeeklyStore] Stored {mode} narrative ({len(narrative)} chars). Total entries: {len(entries)}")
        except Exception as e:
            logger.warning(f"[WeeklyStore] Failed to store narrative: {e}")

    def _run_weekly_review(self) -> None:
        """
        Sunday 20:00 UTC — compile the week's narratives into one long-form
        Substack article and a summary thread on X.
        """
        if self.credit_exhausted:
            logger.warning("[WeeklyReview] Skipping — Anthropic credits exhausted")
            return

        logger.info(f"\n{'='*80}")
        logger.info("WEEKLY REVIEW: Compiling week into long-form article")
        logger.info(f"{'='*80}")

        # Load stored narratives
        entries: list = []
        try:
            if self.weekly_narratives_path.exists():
                entries = json.loads(self.weekly_narratives_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"[WeeklyReview] Could not load narratives: {e}")

        if not entries:
            logger.warning("[WeeklyReview] No narratives stored yet — skipping")
            return

        logger.info(f"[WeeklyReview] Compiling {len(entries)} entries from the past week")

        # Pass compiled narratives as news_context to ContentSession
        compiled = "\n\n---\n\n".join(
            f"[{e['date']} {e['time']} | {e['mode'].upper()}]\nHeadline: {e['headline']}\n{e['narrative']}"
            for e in entries
        )

        try:
            session = ContentSession(
                analysis_data={
                    'market_context': self.latest_research.get('global', {}),
                    'majors': {},
                    'defi': [], 'memecoins': [], 'privacy_coins': [], 'commodities': [],
                },
                mode='weekly_review',
                news_context=compiled,
            )
            content = session.generate_all()
        except Exception as e:
            logger.error(f"[WeeklyReview] ContentSession failed: {e}")
            return

        if self.credit_exhausted:
            return

        title    = content.get('headline', f"Week in Review — {datetime.now(timezone.utc).strftime('%B %d, %Y')}")
        article  = content.get('x_article', {})
        body     = article.get('body', '') or content.get('narrative', '')
        tweets   = content.get('x_thread', [])

        # Post X thread summarising the week
        if tweets and self.x_use_browser and self.x_poster:
            try:
                logger.info(f"[WeeklyReview] Posting X thread ({len(tweets)} tweets)...")
                self.x_poster.post_thread(tweets)
                logger.info("   ✅ X thread posted")
            except Exception as e:
                logger.error(f"   ❌ X thread error: {e}")

        # Post full Substack article
        if body and self.substack_use_browser and self.substack_browser.enabled:
            _, sub_body, _ = self.post_decorator.decorate_substack_article(title, body, ['BTC', 'ETH'])
            try:
                logger.info("[WeeklyReview] Posting Substack article...")
                result = self.substack_browser.post_article(title, sub_body)
                if result:
                    logger.info(f"   ✅ Substack article posted: '{title}'")
                else:
                    logger.error("   ❌ Substack article returned False")
            except Exception as e:
                logger.error(f"   ❌ Substack article error: {e}")

        # Clear the weekly narratives file so next week starts fresh
        try:
            self.weekly_narratives_path.write_text('[]', encoding='utf-8')
            logger.info("[WeeklyReview] Narratives file cleared for next week")
        except Exception:
            pass

        logger.info("[WeeklyReview] Complete")

    def _collect_recent_news(self, hours: int = 12) -> list:
        """Collect RSS news articles from the last N hours for digest/macro prompts."""
        try:
            cutoff = time.time() - hours * 3600
            articles = []
            rss_articles = getattr(self.rss_engine, 'articles', []) if hasattr(self, 'rss_engine') else []
            for item in rss_articles:
                pub = item.get('published_at')
                if pub:
                    ts = pub.timestamp() if hasattr(pub, 'timestamp') else pub
                    if ts >= cutoff:
                        articles.append({
                            'title': item.get('title', ''),
                            'summary': item.get('summary', '')[:300],
                            'source': item.get('source', ''),
                            'currencies': item.get('currencies', []),
                        })
            return articles[:50]  # cap at 50 articles
        except Exception as e:
            logger.warning(f"[_collect_recent_news] Error: {e}")
            return []

    def _collect_whale_context(self) -> dict:
        """Collect whale analyzer data for the whale_activity content session."""
        try:
            from api.routers.whale import get_whale_engine
            engine = get_whale_engine()
            if not engine:
                return {}
            summary = engine.get_summary()
            recent = engine.get_recent_transactions(limit=20, chain='all', flow_type='all')
            return {
                'summary': summary,
                'recent_transactions': recent,
            }
        except Exception as e:
            logger.warning(f"[_collect_whale_context] Error: {e}")
            return {}

    def _check_and_post_breaking_news(self):
        """Scan RSS feeds for high-impact news, post immediately if found."""

        if self.credit_exhausted:
            logger.warning("[BreakingNews] Skipping — Anthropic credits exhausted")
            return

        # Skip if within cooldown after anchor slot
        if self._in_anchor_cooldown():
            logger.info("Breaking news check skipped (anchor cooldown)")
            return

        try:
            # Widen recency window to 90 min — RSS feeds can lag, and we check
            # every 15 min so a 20-min window frequently misses valid articles.
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=90)
            recent_items = []
            for item in self.rss_engine.articles[:200]:  # Check top 200 most recent
                pub = item.get('published_at')
                if pub and hasattr(pub, 'tzinfo'):
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    if pub >= cutoff:
                        recent_items.append(item)
                elif pub is None:
                    # No date — include if in first batch (likely recent)
                    recent_items.append(item)

            if not recent_items:
                logger.info(f"Breaking news check: no recent items (checked {len(self.rss_engine.articles)} total)")
                return

            # All tracked assets — not just majors
            ALL_TRACKED = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS + COMMODITIES_ASSETS

            # Explicit crypto keywords — title MUST contain at least one of these
            # to be considered for breaking news (prevents meatball recalls, defense
            # stocks, and other irrelevant news from slipping through).
            CRYPTO_KEYWORDS = [
                'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
                'blockchain', 'defi', 'nft', 'web3', 'solana', 'sol', 'binance',
                'coinbase', 'tether', 'usdt', 'usdc', 'stablecoin', 'altcoin',
                'dogecoin', 'doge', 'shiba', 'monero', 'xmr', 'uniswap',
                'decentralized', 'wallet', 'exchange', 'mining', 'miner',
                'halving', 'mempool', 'on-chain', 'onchain', 'layer 2', 'l2',
                'sec crypto', 'crypto etf', 'spot etf', 'crypto ban', 'crypto regulation',
                'digital asset', 'virtual currency', 'token', 'liquidation',
                'open interest', 'funding rate', 'futures', 'perp',
            ]

            # Macro events that move crypto regardless of explicit crypto mention
            MACRO_MOVERS = [
                'federal reserve', 'fed rate', 'rate cut', 'rate hike', 'fomc',
                'interest rate decision', 'cpi report', 'inflation data',
                'sec approves', 'sec rejects', 'etf approved', 'etf denied',
                'bitcoin etf', 'spot etf', 'crypto ban', 'crypto regulation',
                'stablecoin bill', 'crypto bill', 'digital asset',
                'ftx', 'tether usdt',
            ]

            breaking_found = 0
            for item in recent_items:
                title = item.get('title', '')
                if not title:
                    continue

                title_hash = hashlib.sha256(title.encode()).hexdigest()[:16]

                # Skip exact-title duplicates (within session)
                if title_hash in self.posted_breaking_headlines:
                    continue

                # Skip same-topic stories already posted recently (cross-source dedup)
                if self._is_same_topic(title):
                    continue

                title_lower = title.lower()

                # Pre-filter: must contain at least one explicit crypto keyword
                # OR be a genuine macro mover. This stops "meatball recalls",
                # "defense stocks", etc. from triggering.
                is_crypto_relevant = any(kw in title_lower for kw in CRYPTO_KEYWORDS)
                is_macro_mover = any(kw in title_lower for kw in MACRO_MOVERS)
                if not is_crypto_relevant and not is_macro_mover:
                    continue

                # Check relevance across ALL tracked assets — collect ALL that score high
                max_score = 0.0
                affected_assets: list = []
                for ticker in ALL_TRACKED:
                    _, score = _calculate_relevance(title, ticker, item)
                    if score >= 0.5:
                        affected_assets.append(ticker)
                    max_score = max(max_score, score)

                # Fallback: mention ticker if it appears literally in title
                for ticker in ALL_TRACKED:
                    if ticker.lower() in title_lower and ticker not in affected_assets:
                        affected_assets.append(ticker)

                if not affected_assets:
                    affected_assets = ['BTC']  # generic crypto news

                # Boost for confirmed macro events (but don't guarantee — just raise floor)
                if is_macro_mover and max_score < 0.8:
                    max_score = 0.8

                if max_score < BREAKING_NEWS_THRESHOLD:
                    continue

                logger.info(
                    f"BREAKING NEWS DETECTED (score={max_score:.2f}, "
                    f"assets={affected_assets}): {title}"
                )
                self.posted_breaking_headlines.add(title_hash)
                self.recent_breaking_headlines.append((title, time.time()))

                # Inject the combined asset list into the item before posting
                item_with_assets = dict(item)
                item_with_assets['currencies'] = affected_assets
                self._post_breaking_news(item_with_assets, max_score)
                breaking_found += 1

            if breaking_found == 0:
                logger.info(f"Breaking news check: {len(recent_items)} items scanned, none above threshold")
            else:
                logger.info(f"Breaking news check: {breaking_found} breaking items posted")

            # Prune old headlines set (keep last 500)
            if len(self.posted_breaking_headlines) > 500:
                self.posted_breaking_headlines = set(list(self.posted_breaking_headlines)[-300:])

        except Exception as e:
            logger.error(f"Breaking news check error: {e}")

    def _post_breaking_news(self, item: Dict, score: float):
        """Build and post breaking news across platforms — ONE Claude call via ContentSession."""
        try:
            headline = item.get('title', '')
            summary = item.get('summary', item.get('description', ''))
            source = item.get('source', 'Unknown')
            breaking_assets = item.get('currencies', ['BTC'])

            logger.info(f"\n{'='*80}")
            logger.info(f"📰 BREAKING NEWS — ContentSession (1 Claude call)")
            logger.info(f"   Headline: {headline[:70]}...")
            logger.info(f"   Source: {source} | Relevance: {score:.0%}")
            logger.info(f"{'='*80}")

            # Build news context string for Claude
            news_context = (
                f"BREAKING NEWS\n"
                f"Headline: {headline}\n"
                f"Summary: {summary[:600] if summary else headline}\n"
                f"Source: {source}\n"
                f"Relevance score: {score:.0%}\n"
                f"Assets affected: {', '.join(breaking_assets)}"
            )

            # ── ONE Claude call → all content formats ──────────────────────────
            logger.info("\n📝 Step 1: ContentSession — generating all content (1 Claude call)...")
            session_content = self._run_content_session('breaking_news', news_context=news_context)

            if not session_content:
                logger.error("   ❌ ContentSession returned None — aborting breaking news")
                return

            # Extract pre-generated content — no more Claude calls after this
            tweet_texts = session_content.get('x_thread', [])
            article_title = session_content.get('x_article', {}).get('title', headline)
            article_body  = session_content.get('x_article', {}).get('body', '')
            sub_note      = session_content.get('substack_note', '')
            tweet_count   = len(tweet_texts)
            logger.info(f"   ✅ ContentSession done — {tweet_count} tweets, {len(article_body.split())} words")

            # Apply CTAs + hashtags to thread
            tweet_texts = self.post_decorator.decorate_x_thread(tweet_texts, breaking_assets)
            thread_data = {
                'tweets': tweet_texts,
                'tweet_count': len(tweet_texts),
                'copy_paste_ready': '\n\n'.join(tweet_texts),
                'type': 'breaking_news',
            }

            # Decorate article for Substack (X Articles paused — X = threads only)
            _, sub_article_body, _ = self.post_decorator.decorate_substack_article(article_title, article_body, breaking_assets)

            # ── Dedup gate: skip posting if content already tracked ────────────
            thread_body = thread_data['copy_paste_ready']
            if self.tracker.is_duplicate(thread_body):
                logger.info("   ↩️  Breaking news content already posted (content tracker) — skipping")
                return

            # ── Post X thread (main account) ───────────────────────────────────
            # ── Generate chart + pick best image for thread ────────────────────
            thread_chart = generate_chart_image(pick_chart_ticker(breaking_assets), '4h')
            thread_image_path = self._pick_breaking_news_image(item, thread_chart)

            logger.info("\n📤 Step 2: Posting thread to X...")
            post_result = None
            if getattr(self.x_browser_poster, 'enabled', False):
                try:
                    post_result = self.x_browser_poster.post_thread(thread_data, image_path=thread_image_path)
                    if post_result and post_result.get('success'):
                        logger.info(f"   ✅ X thread posted ({post_result.get('posted_count', 0)} tweets)")
                    else:
                        logger.error(f"   ❌ X thread failed: {post_result}")
                except Exception as e:
                    logger.error(f"   ❌ X thread exception: {e}", exc_info=True)
                finally:
                    # Clean up temp image file (RSS images downloaded to temp)
                    self._cleanup_temp_image(thread_image_path, thread_chart)
            else:
                logger.warning("   ⚠️  X browser poster disabled")

            # Record in tracker immediately after first post attempt
            self.tracker.record_post(body=thread_body, content_type='breaking_thread', ticker='BREAKING')

            # ── Publish thread to web feed ─────────────────────────────────────
            if self.web_publisher.enabled:
                try:
                    web_result = self.web_publisher.publish_thread(
                        thread_data=thread_data, tickers=breaking_assets, sector='global',
                        image_url=thread_chart,
                        market_snapshot={'headline': headline, 'source': source, 'relevance_score': score},
                    )
                    if web_result:
                        logger.info(f"   ✅ Thread published to web: /post/{web_result.get('slug', '?')}")
                except Exception as e:
                    logger.warning(f"   ⚠️  Web thread publish exception: {e}")

            # ── X Article: DISABLED — X = threads only ────────────────────────
            logger.info("\n📤 Step 3: X Article skipped (X = threads only)")

            # ── Post Substack Article ──────────────────────────────────────────
            logger.info("\n📤 Step 4: Posting article to Substack...")
            if self.substack_use_browser and self.substack_browser.enabled and article_body:
                try:
                    sub_result = self.substack_browser.post_article(article_title, sub_article_body)
                    logger.info("   ✅ Substack Article posted" if sub_result else "   ❌ Substack Article returned False")
                except Exception as e:
                    logger.error(f"   ❌ Substack Article exception: {e}", exc_info=True)

            # ── Post Substack Note (key insight from ContentSession) ───────────
            logger.info("\n📤 Step 5: Posting note to Substack...")
            if self.substack_use_browser and self.substack_browser.enabled and sub_note:
                try:
                    note_id = self.substack_browser.post_note(sub_note)
                    logger.info(f"   ✅ Substack Note posted (ID: {note_id})" if note_id else "   ❌ Substack Note returned None")
                except Exception as e:
                    logger.error(f"   ❌ Substack Note exception: {e}", exc_info=True)

            # ── Publish article to web feed ────────────────────────────────────
            if self.web_publisher.enabled and article_body:
                try:
                    breaking_chart = generate_chart_image(pick_chart_ticker(breaking_assets), '4h')
                    web_memo = self.web_publisher.publish_article(
                        title=article_title, body=article_body, sector='global',
                        tickers=breaking_assets,
                        image_url=breaking_chart,
                        market_snapshot={'headline': headline, 'source': source, 'relevance_score': score},
                    )
                    if web_memo:
                        logger.info(f"   ✅ Article published to web: /post/{web_memo.get('slug', '?')}")
                except Exception as e:
                    logger.warning(f"   ⚠️  Web article publish exception: {e}")

            # ── Post to @CreviaCockpit (thread only — articles paused on X) ───
            if getattr(self.x_cockpit_poster, 'enabled', False):
                logger.info("\n📤 Cockpit: Posting thread to @CreviaCockpit...")
                try:
                    cockpit_thread = self.x_cockpit_poster.post_thread(thread_data)
                    logger.info("   ✅ @CreviaCockpit thread posted" if (cockpit_thread and cockpit_thread.get('success')) else "   ⚠️  @CreviaCockpit thread failed")
                except Exception as e:
                    logger.error(f"   ❌ @CreviaCockpit thread exception: {e}")
            else:
                logger.debug("   @CreviaCockpit poster disabled — skipping")

            logger.info(f"\n{'='*80}")
            logger.info("✅ Breaking news posting complete (1 Claude call total)")
            logger.info(f"{'='*80}\n")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Breaking news posting error: {e}", exc_info=True)

    def _pick_breaking_news_image(self, item: Dict, chart_url: Optional[str]) -> Optional[str]:
        """
        Pick the best image for a breaking news X thread attachment.

        Priority:
        1. RSS article image (already stored on item)
        2. OG image scraped from the article URL
        3. Local chart PNG (already saved to web/public/charts/)
        Returns a local file path string, or None if nothing available.
        """
        import tempfile

        # 1. Try the RSS-embedded image URL
        rss_img_url = item.get('image_url')
        if not rss_img_url:
            # Try fetching OG image from article page
            article_url = item.get('url', '') or item.get('link', '')
            if article_url:
                try:
                    rss_img_url = self.rss_engine.fetch_og_image(article_url)
                except Exception:
                    pass

        if rss_img_url:
            try:
                resp = httpx.get(rss_img_url, timeout=10, follow_redirects=True)
                resp.raise_for_status()
                ctype = resp.headers.get('content-type', 'image/jpeg')
                ext = '.png' if 'png' in ctype else '.jpg'
                tmp = Path(tempfile.mktemp(suffix=ext))
                tmp.write_bytes(resp.content)
                logger.info(f"[BreakingNews] Using RSS image for X thread: {rss_img_url[:60]}")
                return str(tmp)
            except Exception as e:
                logger.debug(f"[BreakingNews] RSS image download failed: {e}")

        # 2. Fall back to local chart PNG
        if chart_url:
            chart_filename = chart_url.lstrip('/').replace('charts/', '')
            chart_file = Path('web') / 'public' / 'charts' / chart_filename
            if chart_file.exists():
                logger.info(f"[BreakingNews] Using chart image for X thread: {chart_filename}")
                return str(chart_file)

        return None

    def _cleanup_temp_image(self, image_path: Optional[str], chart_url: Optional[str]):
        """Delete temp downloaded image (not the chart which we want to keep)."""
        if not image_path:
            return
        try:
            p = Path(image_path)
            # Only delete if it's a temp file (not our charts directory)
            if 'tmp' in str(p) or (p.exists() and 'charts' not in str(p)):
                p.unlink(missing_ok=True)
        except Exception:
            pass

    def _build_article_body(self, thread_data: Optional[Dict]) -> Optional[str]:
        """Convert thread data into long-form article body."""
        if not thread_data:
            return None
        tweets = thread_data.get('tweets', [])
        if not tweets:
            return None

        # Build article from thread tweets
        paragraphs = []
        for i, tweet in enumerate(tweets):
            # Strip thread numbering (1/, 2/, etc.)
            text = tweet.strip()
            text = text.lstrip('0123456789').lstrip('/').lstrip(' ')
            if text:
                paragraphs.append(text)

        if not paragraphs:
            return None

        # Join as flowing article
        body = "\n\n".join(paragraphs)

        # Add timestamp
        now_utc = datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')
        body = f"Published: {now_utc}\n\n{body}"

        return body

    def _build_note_summary(self, thread_data: Dict, slot: Dict) -> Optional[str]:
        """Build concise note from thread for Substack."""
        tweets = thread_data.get('tweets', [])
        if not tweets:
            return None

        # Take first 2-3 tweets as summary
        summary_tweets = tweets[:3]
        summary = "\n\n".join(t.strip() for t in summary_tweets)

        # Prefix with slot label
        summary = f"{slot['label']} - {datetime.now(timezone.utc).strftime('%b %d %H:%M UTC')}\n\n{summary}"

        return summary

    # =========================================================================
    # DATA PHASES
    # =========================================================================

    def _run_research_phase(self):
        """
        Run research on all assets using DataAggregator

        NO CLAUDE CALLS HERE - all data from APIs
        """

        logger.info("\nRESEARCH PHASE (Data from APIs - No Claude)")
        logger.info("-" * 80)

        try:
            # 1. Global market metrics (from DataAggregator)
            logger.info("Fetching global market metrics...")
            global_metrics = self.data.get_global_metrics()

            if global_metrics:
                self.latest_research['global'] = global_metrics.to_dict()

                logger.info(f"   Market Cap: ${global_metrics.total_market_cap/1e12:.2f}T")
                logger.info(f"   24h Volume: ${global_metrics.total_volume_24h/1e9:.2f}B")
                logger.info(f"   BTC Dom: {global_metrics.btc_dominance:.1f}%")
                logger.info(f"   Fear/Greed: {global_metrics.fear_greed_index} ({global_metrics.fear_greed_classification})")
                logger.info(f"   BTC Funding: {global_metrics.btc_funding_rate*100:.4f}%")
                logger.info(f"   BTC OI: ${global_metrics.btc_open_interest/1e9:.2f}B")

            # 2. Fetch all asset prices in batch (efficient)
            logger.info("Fetching asset prices...")
            all_tickers = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS + COMMODITIES_ASSETS
            prices = self.data.get_prices_batch(all_tickers)

            for ticker, price in prices.items():
                self.latest_research[ticker] = {
                    'price': price.to_dict(),
                    'timestamp': int(time.time())
                }
                logger.info(f"   {ticker}: ${price.price_usd:,.2f} ({price.price_change_24h:+.2f}%)")

            # 3. Fetch derivatives for majors + commodities (all on Binance Futures)
            logger.info("Fetching derivatives data...")
            for ticker in MAJOR_ASSETS + COMMODITIES_ASSETS:
                deriv = self.data.get_derivatives(ticker)
                if deriv:
                    if ticker in self.latest_research:
                        self.latest_research[ticker]['derivatives'] = deriv.to_dict()
                    logger.info(f"   {ticker} Funding: {deriv.funding_rate*100:.4f}%, OI: ${deriv.open_interest_usd/1e9:.2f}B")

            # 4. Fetch DeFi TVL
            logger.info("Fetching DeFi TVL...")
            tvl = self.data.get_total_tvl()
            if tvl:
                self.latest_research['defi_tvl'] = tvl
                logger.info(f"   Total DeFi TVL: ${tvl/1e9:.2f}B")

            # 5. Fetch on-chain for BTC
            logger.info("Fetching on-chain data...")
            btc_onchain = self.data.get_onchain('BTC')
            if btc_onchain:
                self.latest_research['btc_onchain'] = btc_onchain.to_dict()
                logger.info(f"   BTC Tx/24h: {btc_onchain.transaction_count_24h:,}")

            # Save research
            self._save_research()

            # Publish to web API (for landing page dashboard)
            if self.web_publisher.enabled:
                try:
                    if global_metrics:
                        self.web_publisher.publish_market_snapshot(global_metrics.to_dict())

                        # Publish individual metrics to time-series for trend analysis
                        gm = global_metrics.to_dict()
                        ts_metrics = {
                            'fear_greed_index': gm.get('fear_greed_index'),
                            'btc_dominance': gm.get('btc_dominance'),
                            'eth_dominance': gm.get('eth_dominance'),
                            'total_market_cap': gm.get('total_market_cap'),
                            'total_volume_24h': gm.get('total_volume_24h'),
                            'total_open_interest': gm.get('total_open_interest'),
                            'total_liquidations_24h': gm.get('total_liquidations_24h'),
                            'btc_price': gm.get('btc_price'),
                            'btc_funding_rate': gm.get('btc_funding_rate'),
                            'btc_open_interest': gm.get('btc_open_interest'),
                            'eth_price': gm.get('eth_price'),
                            'eth_funding_rate': gm.get('eth_funding_rate'),
                            'alt_season_index': gm.get('alt_season_index'),
                        }
                        self.web_publisher.publish_metrics(ts_metrics)

                    for ticker, price in prices.items():
                        self.web_publisher.publish_asset_price(ticker, price.to_dict())
                except Exception as wp_err:
                    logger.warning(f"Web publish (research): {wp_err}")

            # 6. Regime detection (uses global_metrics already fetched)
            logger.info("Detecting market regime...")
            try:
                regime = self.regime_detector.detect_regime(global_metrics)
                self.current_regime = regime
                logger.info(f"   Regime: {regime['regime']} (confidence: {regime['confidence']*100:.0f}%)")
                logger.info(f"   {regime['description']}")

                # Publish regime to web API
                if self.web_publisher.enabled:
                    self.web_publisher.publish_regime(regime)
            except Exception as regime_err:
                logger.warning(f"Regime detection error: {regime_err}")

            # 7. Correlation matrix (uses historical metrics from time-series API)
            try:
                if self.web_publisher.enabled:
                    corr_result = self.correlation_engine.calculate_correlations(period_hours=24)
                    if corr_result.get('matrix'):
                        self.web_publisher.publish_correlations(corr_result)
                        n_pairs = len(corr_result.get('strongest_pairs', []))
                        logger.info(f"   Correlations: {len(corr_result['labels'])} metrics, {n_pairs} strong pairs")
                    else:
                        logger.info(f"   Correlations: {corr_result.get('interpretation', 'No data yet')}")
            except Exception as corr_err:
                logger.warning(f"Correlation engine error: {corr_err}")

            # 8. Smart money tracker (uses global_metrics already fetched)
            try:
                gm = global_metrics.to_dict()
                sm_result = self.smart_money_tracker.scan_signals(gm)
                n_signals = sm_result.get('signal_count', 0)
                sentiment = sm_result.get('net_sentiment', 'NEUTRAL')
                logger.info(f"   Smart Money: {n_signals} signals, sentiment: {sentiment}")

                if self.web_publisher.enabled and n_signals > 0:
                    self.web_publisher.publish_smart_money(sm_result)
            except Exception as sm_err:
                logger.warning(f"Smart money tracker error: {sm_err}")

            # 9. Trade setup generation (Claude Sonnet — throttled to once per hour per asset)
            generated_setups = []
            try:
                if self.trade_setup_gen._enabled and self.web_publisher.enabled:
                    setup_count = 0
                    now_ts = time.time()
                    for ticker in MAJOR_ASSETS:
                        # Skip if this asset was generated within TRADE_SETUP_INTERVAL
                        last_ts = self.last_trade_setup_time.get(ticker, 0)
                        if now_ts - last_ts < TRADE_SETUP_INTERVAL:
                            logger.debug(f"   Trade Setup [{ticker}]: throttled (next in {int(TRADE_SETUP_INTERVAL - (now_ts - last_ts))}s)")
                            continue

                        research = self.latest_research.get(ticker, {})
                        price_data = research.get('price', {})
                        if not price_data.get('price_usd'):
                            continue

                        deriv = research.get('derivatives')

                        # Run TA engine for structure/zone/filter context
                        ta_ctx = None
                        try:
                            ta_ctx = asyncio.run(self.ta_engine.analyze(
                                ticker=ticker,
                                htf='4h',
                                exchange='binance',
                            ))
                            logger.debug(f"   TA [{ticker}]: {ta_ctx.get('direction')} quality={ta_ctx.get('setup_quality')}")
                        except Exception as ta_err:
                            logger.debug(f"   TA [{ticker}] skipped: {ta_err}")

                        setup = self.trade_setup_gen.generate_setup(
                            ticker=ticker,
                            price_data=price_data,
                            regime=self.current_regime,
                            derivatives=deriv,
                            ta_context=ta_ctx,
                        )
                        if setup:
                            self.web_publisher.publish_trade_setup(setup)
                            generated_setups.append(setup)
                            setup_count += 1
                            self.last_trade_setup_time[ticker] = now_ts

                    logger.info(f"   Trade Setups: {setup_count} generated (throttle: {TRADE_SETUP_INTERVAL}s/asset)")
                else:
                    logger.info("   Trade Setups: Skipped (generator or publisher not enabled)")
            except Exception as ts_err:
                logger.warning(f"Trade setup generator error: {ts_err}")

            # 10. Opportunity scanner (ranks setups by composite score)
            try:
                if generated_setups and self.web_publisher.enabled:
                    # Build prices dict for scoring
                    prices_for_scanner = {}
                    for ticker in MAJOR_ASSETS:
                        research = self.latest_research.get(ticker, {})
                        price_data = research.get('price', {})
                        if price_data:
                            prices_for_scanner[ticker] = price_data

                    scan = self.opportunity_scanner.scan_opportunities(
                        setups=generated_setups,
                        regime=self.current_regime,
                        prices=prices_for_scanner,
                    )
                    if scan.get('opportunities'):
                        self.web_publisher.publish_opportunities(scan)
                        top = scan['opportunities'][0]
                        logger.info(f"   Opportunities: {scan['opportunity_count']} ranked — Top: {top['direction']} {top['asset']} ({top['score']}/10)")
                    else:
                        logger.info("   Opportunities: No setups to rank")
                else:
                    logger.info("   Opportunities: Skipped (no setups generated)")
            except Exception as opp_err:
                logger.warning(f"Opportunity scanner error: {opp_err}")

        except Exception as e:
            logger.error(f"Research phase error: {e}")

    def _run_analysis_phase(self):
        """Run full analysis on all tracked assets"""

        logger.info("\nANALYSIS PHASE")
        logger.info("-" * 80)

        try:
            # Analyze majors
            logger.info("Analyzing major assets...")
            for ticker in MAJOR_ASSETS:
                try:
                    analysis = analyze_major(ticker)
                    self.latest_analyses[ticker] = analysis
                    risk = analysis.get('risks', {}).get('overall_assessment', {}).get('risk_level', 'UNKNOWN')
                    logger.info(f"   {ticker}: Risk={risk}")
                except Exception as e:
                    logger.error(f"   {ticker} analysis failed: {e}")

            # Analyze memecoins (all 4)
            logger.info("Analyzing memecoins...")
            for ticker in MEMECOIN_ASSETS:
                try:
                    analysis = analyze_memecoin(ticker)
                    self.latest_analyses[ticker] = analysis
                    logger.info(f"   {ticker}: OK")
                except Exception as e:
                    logger.error(f"   {ticker} failed: {e}")

            # Analyze privacy coins (all 4)
            logger.info("Analyzing privacy coins...")
            for ticker in PRIVACY_ASSETS:
                try:
                    analysis = analyze_privacy_coin(ticker)
                    self.latest_analyses[ticker] = analysis
                    logger.info(f"   {ticker}: OK")
                except Exception as e:
                    logger.error(f"   {ticker} failed: {e}")

            # Analyze DeFi protocols (all 4)
            logger.info("Analyzing DeFi protocols...")
            for ticker in DEFI_ASSETS:
                try:
                    analysis = analyze_defi_protocol(ticker)
                    self.latest_analyses[ticker] = analysis
                    logger.info(f"   {ticker}: OK")
                except Exception as e:
                    logger.error(f"   {ticker} failed: {e}")

            # Analyze commodities/tokenized stocks (XAU, TSLA — Binance Futures)
            logger.info("Analyzing commodities/tokenized stocks...")
            for ticker in COMMODITIES_ASSETS:
                try:
                    analysis = analyze_major(ticker)
                    self.latest_analyses[ticker] = analysis
                    logger.info(f"   {ticker}: OK")
                except Exception as e:
                    logger.error(f"   {ticker} failed: {e}")

            # Save analyses
            self._save_analyses()

        except Exception as e:
            logger.error(f"Analysis phase error: {e}")

    def _run_thread_generation(self, thread_mode: str = 'morning_scan',
                               previous_context: Optional[str] = None,
                               session_content: Optional[Dict] = None) -> Optional[Dict]:
        """
        Generate X/Twitter thread with mode awareness.

        Args:
            thread_mode: 'morning_scan' | 'mid_day_update' | 'closing_bell'
            previous_context: Summary of previous thread (for mid-day reference)

        Returns:
            thread dict or None
        """

        logger.info(f"\nTHREAD GENERATION PHASE (mode: {thread_mode})")
        logger.info("-" * 80)

        try:
            if 'BTC' not in self.latest_analyses:
                logger.warning("No BTC analysis available, skipping thread")
                return None

            # Get fresh prices from data layer
            logger.info("Fetching real-time prices...")
            all_tickers = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS + COMMODITIES_ASSETS
            prices = self.data.get_prices_batch(all_tickers)

            # Inject prices into analyses
            updated_analyses = self._inject_prices(self.latest_analyses.copy(), prices)

            # Build sector analyses
            sector_analyses = {
                'memecoins': [updated_analyses.get(t) for t in MEMECOIN_ASSETS if t in updated_analyses],
                'privacy': [updated_analyses.get(t) for t in PRIVACY_ASSETS if t in updated_analyses],
                'defi': [updated_analyses.get(t) for t in DEFI_ASSETS if t in updated_analyses],
                'commodities': [updated_analyses.get(t) for t in COMMODITIES_ASSETS if t in updated_analyses],
            }

            # Get global context
            global_metrics = self.data.get_global_metrics()
            market_context = global_metrics.to_dict() if global_metrics else self.latest_research.get('global')

            # Generate thread — use ContentSession output if pregenerated, else call Claude
            if session_content and session_content.get('x_thread'):
                logger.info(f"Using pregenerated {thread_mode} thread from ContentSession")
                raw_tweets = session_content['x_thread']
                thread = {
                    'tweets': raw_tweets,
                    'tweet_count': len(raw_tweets),
                    'copy_paste_ready': '\n\n'.join(raw_tweets),
                    'type': thread_mode,
                }
            else:
                logger.info(f"Generating {thread_mode} thread via Claude...")
                thread = generate_x_thread(
                    btc_analysis=updated_analyses['BTC'],
                    market_context=market_context,
                    thread_mode=thread_mode,
                    previous_context=previous_context,
                    eth_analysis=updated_analyses.get('ETH'),
                    sector_analyses=sector_analyses,
                    all_analyses=updated_analyses
                )

            # Dedup check (on raw content, before CTA decoration)
            thread_body = thread.get('copy_paste_ready', '')
            if self.tracker.is_duplicate(thread_body):
                logger.info("   Thread is a duplicate, skipping all channels")
                return None

            # Apply CTAs + hashtags to final tweet only
            mentioned = (
                session_content.get('mentioned_assets', []) if session_content
                else [t for t in (MAJOR_ASSETS + MEMECOIN_ASSETS) if t in updated_analyses]
            )
            tweets = self.post_decorator.decorate_x_thread(list(thread.get('tweets', [])), mentioned)
            thread['tweets'] = tweets
            thread['copy_paste_ready'] = '\n\n'.join(tweets)

            # Save thread
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            thread_file = OUTPUT_DIR / f'x_thread_{timestamp}.txt'

            with open(thread_file, 'w', encoding='utf-8') as f:
                f.write(thread['copy_paste_ready'])

            logger.info(f"   Thread saved: {thread_file}")
            logger.info(f"   Tweets: {thread['tweet_count']}")

            # Save to Notion (write once, post anywhere!)
            if self.notion_manager and self.notion_manager.is_available():
                try:
                    thread_body = thread.get('copy_paste_ready', '')
                    notion_result = self.notion_manager.save_tweet_thread(
                        title=f"{thread_mode.replace('_', ' ').title()} Analysis",
                        content=thread_body,
                        tags=['market_analysis', thread_mode]
                    )
                    logger.info(f"   ✅ Notion: Thread saved (ID: {notion_result})")
                except Exception as e:
                    logger.warning(f"   ⚠️  Notion save failed: {e}")

            # Track channel results
            x_thread_url = None
            discord_sent = False
            web_slug = None
            substack_note_id = None

            # Send to Discord
            if self.discord.enabled:
                self.discord.send_x_thread(thread)
                discord_sent = True

            # Post directly to X/Twitter (API first, browser fallback)
            post_result = None
            # Try API first (faster, no detection)
            if self.x_poster and self.x_poster.enabled:
                try:
                    logger.info("Posting thread to X (API)...")
                    post_result = self.x_poster.post_thread(thread)
                    if post_result and post_result.get('success'):
                        logger.info(f"   X thread posted via API ({post_result.get('posted_count', len(thread))} tweets)")
                    else:
                        post_result = None  # Fall back to browser
                except Exception as e:
                    logger.warning(f"   API thread posting failed: {e}")
                    post_result = None  # Fall back to browser
            
            # Fall back to browser poster if API unavailable
            if not post_result and getattr(self.x_browser_poster, 'enabled', False):
                try:
                    logger.info("Posting thread to X (browser)...")
                    post_result = self.x_browser_poster.post_thread(thread)
                    if post_result and post_result.get('success'):
                        logger.info(f"   X thread posted via browser ({post_result.get('posted_count', 0)} tweets)")
                    else:
                        logger.warning(f"   X browser thread failed: {post_result.get('error', 'No result') if post_result else 'No result'}")
                except Exception as e:
                    logger.warning(f"   X browser thread exception: {e}")
                    post_result = None

            if not post_result:
                logger.warning("   X posting unavailable (API and browser disabled)")

            # Publish to web API
            if self.web_publisher.enabled:
                thread_tickers = list(updated_analyses.keys())
                thread_chart = generate_chart_image(pick_chart_ticker(thread_tickers), '4h')
                web_result = self.web_publisher.publish_thread(
                    thread_data=thread,
                    tickers=thread_tickers,
                    image_url=thread_chart,
                    source_file=str(thread_file),
                    market_snapshot=market_context,
                )
                if web_result:
                    web_slug = web_result.get('slug')

            # Post to Substack Notes (API or browser fallback)
            if self.substack_use_browser and self.substack_browser.enabled:
                substack_note_id = self.substack_browser.post_thread_as_note(thread)
            elif self.substack.enabled:
                substack_note_id = self.substack.post_thread_as_note(thread)
                if substack_note_id is None and self.substack_browser.enabled:
                    substack_note_id = self.substack_browser.post_thread_as_note(thread)

            # Record in tracker
            self.tracker.record_post(
                body=thread_body,
                content_type='thread',
                ticker='BTC',
                x_thread_url=x_thread_url,
                discord_sent=discord_sent,
                web_slug=web_slug,
                substack_note_id=substack_note_id,
                source_file=str(thread_file),
            )

            return thread

        except Exception as e:
            logger.error(f"Thread generation error: {e}")
            return None

    def _run_news_memo_generation(self):
        """
        Generate Claude-written Market Memos from RSS news

        Extracts news articles from pillar data and uses NewsNarrator
        to produce Bloomberg-style fact-checked market narratives.
        """

        logger.info("\nNEWS MEMO GENERATION (Claude for writing)")
        logger.info("-" * 80)

        try:
            if not self.latest_analyses:
                logger.warning("No analyses available, skipping news memos")
                return

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            memos_generated = 0

            # --- 1. Individual memos for each major asset + commodities ---
            for ticker in MAJOR_ASSETS + COMMODITIES_ASSETS:
                memos_generated += self._generate_and_send_memo(ticker, timestamp)

            # --- 2. Sector memos: aggregate news across coins in each sector ---
            sector_map = {
                'MEMECOINS': MEMECOIN_ASSETS,
                'PRIVACY': PRIVACY_ASSETS,
                'DEFI': DEFI_ASSETS,
                'COMMODITIES': COMMODITIES_ASSETS,
            }
            for sector_name, sector_tickers in sector_map.items():
                memos_generated += self._generate_sector_memo(
                    sector_name, sector_tickers, timestamp
                )

            logger.info(f"   News memos generated: {memos_generated}")

        except Exception as e:
            logger.error(f"News memo generation error: {e}")

    def _generate_and_send_memo(self, ticker: str, timestamp: str) -> int:
        """Generate a news memo for a single ticker. Returns 1 on success, 0 on skip."""
        if ticker not in self.latest_analyses:
            return 0

        analysis = self.latest_analyses[ticker]
        news_data = analysis.get('pillar_data', {}).get('news', {})
        events = news_data.get('events', [])

        if not events:
            logger.info(f"   {ticker}: No news events, skipping memo")
            return 0

        price_data = self.data.get_price(ticker)
        current_price = price_data.price_usd if price_data else None

        articles = []
        for event in events[:10]:
            articles.append({
                'title': event.get('title', ''),
                'source': event.get('source', 'Unknown'),
                'summary': event.get('title', ''),
                'published_at': event.get('published_at', ''),
                'url': event.get('url', ''),
                'relevance': event.get('relevance', ''),
                'sentiment': event.get('sentiment', ''),
            })

        logger.info(f"   {ticker}: Generating memo from {len(articles)} articles...")
        memo = self.news_narrator.generate_market_memo(
            ticker=ticker, articles=articles, current_price=current_price
        )

        if not memo:
            return 0

        # Dedup check on memo
        if self.tracker.is_duplicate(memo):
            logger.info(f"   {ticker}: Memo is a duplicate, skipping")
            return 0

        memo_file = OUTPUT_DIR / f'news_memo_{ticker}_{timestamp}.txt'
        with open(memo_file, 'w', encoding='utf-8') as f:
            f.write(f"MARKET MEMO: {ticker}\n{'=' * 60}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if current_price:
                f.write(f"Price at generation: ${current_price:,.2f}\n")
            f.write(f"{'=' * 60}\n\n{memo}")

        logger.info(f"   {ticker}: Memo saved to {memo_file}")

        # Track channel results
        x_tweet_id = None
        discord_sent = False
        web_slug = None
        substack_note_id = None

        # Discord
        if self.discord.enabled:
            lead_image = self.rss_engine.select_best_image(events, ticker=ticker)
            self.discord.send_news_memo(
                ticker=ticker, memo=memo,
                current_price=current_price, image_url=lead_image
            )
            discord_sent = True

        # X tweet + Web news tweet
        x_posting_available = (self.x_poster and self.x_poster.enabled) or getattr(self.x_browser_poster, 'enabled', False)
        news_tweet = None
        if x_posting_available or self.web_publisher.enabled:
            news_tweet = self.news_narrator.generate_news_tweet(
                ticker=ticker, articles=articles, current_price=current_price
            )

        if news_tweet and x_posting_available:
            # Dedup check on news tweet too
            if not self.tracker.is_duplicate(news_tweet):
                tid = None
                # Try official API first (faster)
                if self.x_poster and self.x_poster.enabled:
                    tid = self.x_poster.post_tweet(news_tweet)
                # Fall back to browser poster
                if not tid and getattr(self.x_browser_poster, 'enabled', False):
                    tid = self.x_browser_poster.post_tweet(news_tweet)
                if tid:
                    x_tweet_id = str(tid)
                    logger.info(f"   {ticker}: News tweet posted (ID: {tid})")
                # Record the news tweet separately
                self.tracker.record_post(
                    body=news_tweet, content_type='news_tweet', ticker=ticker,
                    x_tweet_id=x_tweet_id,
                )
            else:
                logger.info(f"   {ticker}: News tweet is a duplicate, skipping X")

        # X Article — DISABLED: X = threads only; articles go to Substack + Web

        # Web API — memo + news tweet
        if self.web_publisher.enabled:
            lead_image = self.rss_engine.select_best_image(events, ticker=ticker)
            chart_url = generate_chart_image(pick_chart_ticker([ticker]), '4h')
            web_result = self.web_publisher.publish_memo(
                ticker=ticker, memo=memo,
                current_price=current_price,
                image_url=chart_url or lead_image,
                source_file=str(memo_file),
            )
            if web_result:
                web_slug = web_result.get('slug')
            if news_tweet and not self.tracker.is_duplicate(news_tweet):
                self.web_publisher.publish_news_tweet(
                    ticker=ticker, tweet_text=news_tweet,
                    current_price=current_price,
                )

        # Post memo to Substack Notes (API or browser fallback)
        if self.substack_use_browser and self.substack_browser.enabled:
            substack_note_id = self.substack_browser.post_memo_as_note(
                ticker=ticker, memo=memo, current_price=current_price
            )
        elif self.substack.enabled:
            substack_note_id = self.substack.post_memo_as_note(
                ticker=ticker, memo=memo, current_price=current_price
            )
            if substack_note_id is None and self.substack_browser.enabled:
                substack_note_id = self.substack_browser.post_memo_as_note(
                    ticker=ticker, memo=memo, current_price=current_price
                )

        # Record the memo in tracker
        self.tracker.record_post(
            body=memo, content_type='memo', ticker=ticker,
            discord_sent=discord_sent,
            web_slug=web_slug,
            substack_note_id=substack_note_id,
            source_file=str(memo_file),
        )

        return 1

    def _generate_sector_memo(self, sector_name: str, tickers: List[str],
                              timestamp: str) -> int:
        """Generate a combined news memo for a sector (memecoins, privacy, DeFi).
        Aggregates news events from all tickers in the sector into one memo.
        Returns 1 on success, 0 on skip."""

        # Collect events + prices across all tickers in the sector
        all_events = []
        prices_str_parts = []
        for ticker in tickers:
            if ticker not in self.latest_analyses:
                continue
            analysis = self.latest_analyses[ticker]
            news_data = analysis.get('pillar_data', {}).get('news', {})
            events = news_data.get('events', [])
            all_events.extend(events[:5])  # Top 5 per coin

            price_data = self.data.get_price(ticker)
            if price_data:
                prices_str_parts.append(f"{ticker}: ${price_data.price_usd:,.4f}")

        if not all_events:
            logger.info(f"   {sector_name}: No news events across sector, skipping")
            return 0

        # De-duplicate by title
        seen_titles = set()
        unique_events = []
        for e in all_events:
            t = e.get('title', '')
            if t not in seen_titles:
                seen_titles.add(t)
                unique_events.append(e)

        articles = []
        for event in unique_events[:12]:
            articles.append({
                'title': event.get('title', ''),
                'source': event.get('source', 'Unknown'),
                'summary': event.get('title', ''),
                'published_at': event.get('published_at', ''),
                'url': event.get('url', ''),
                'relevance': event.get('relevance', ''),
                'sentiment': event.get('sentiment', ''),
            })

        tickers_label = ', '.join(tickers)
        prices_line = ' | '.join(prices_str_parts) if prices_str_parts else None

        logger.info(f"   {sector_name} ({tickers_label}): Generating sector memo from {len(articles)} articles...")
        memo = self.news_narrator.generate_market_memo(
            ticker=f"{sector_name} ({tickers_label})",
            articles=articles,
            current_price=None  # Sector-level, no single price
        )

        if not memo:
            return 0

        # Prepend price summary to memo
        if prices_line:
            memo = f"Prices: {prices_line}\n\n{memo}"

        # Dedup check on sector memo
        if self.tracker.is_duplicate(memo):
            logger.info(f"   {sector_name}: Sector memo is a duplicate, skipping")
            return 0

        memo_file = OUTPUT_DIR / f'news_memo_{sector_name}_{timestamp}.txt'
        with open(memo_file, 'w', encoding='utf-8') as f:
            f.write(f"SECTOR MEMO: {sector_name} ({tickers_label})\n{'=' * 60}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n{memo}")

        logger.info(f"   {sector_name}: Sector memo saved to {memo_file}")

        # Track channel results
        x_tweet_id = None
        discord_sent = False
        web_slug = None
        substack_note_id = None

        # Discord
        if self.discord.enabled:
            lead_image = self.rss_engine.select_best_image(unique_events, ticker=sector_name)
            self.discord.send_news_memo(
                ticker=sector_name, memo=memo,
                current_price=None, image_url=lead_image
            )
            discord_sent = True

        # X tweet + Web news tweet
        x_posting_available = (self.x_poster and self.x_poster.enabled) or getattr(self.x_browser_poster, 'enabled', False)
        news_tweet = None
        if x_posting_available or self.web_publisher.enabled:
            news_tweet = self.news_narrator.generate_news_tweet(
                ticker=sector_name, articles=articles, current_price=None
            )

        if news_tweet and x_posting_available:
            if not self.tracker.is_duplicate(news_tweet):
                tid = None
                # Try official API first (faster)
                if self.x_poster and self.x_poster.enabled:
                    tid = self.x_poster.post_tweet(news_tweet)
                # Fall back to browser poster
                if not tid and getattr(self.x_browser_poster, 'enabled', False):
                    tid = self.x_browser_poster.post_tweet(news_tweet)
                if tid:
                    x_tweet_id = str(tid)
                    logger.info(f"   {sector_name}: Sector tweet posted (ID: {tid})")
                self.tracker.record_post(
                    body=news_tweet, content_type='news_tweet', ticker=sector_name,
                    sector=sector_name.lower(), x_tweet_id=x_tweet_id,
                )
            else:
                logger.info(f"   {sector_name}: Sector tweet is a duplicate, skipping X")

        # X Article — DISABLED: X = threads only; articles go to Substack + Web

        # Web API — memo + news tweet
        if self.web_publisher.enabled:
            lead_image = self.rss_engine.select_best_image(unique_events, ticker=sector_name)
            chart_url = generate_chart_image(pick_chart_ticker(tickers), '4h')
            web_result = self.web_publisher.publish_memo(
                ticker=sector_name, memo=memo,
                sector=sector_name.lower(),
                tickers=tickers,
                image_url=chart_url or lead_image,
                source_file=str(memo_file),
            )
            if web_result:
                web_slug = web_result.get('slug')
            if news_tweet and not self.tracker.is_duplicate(news_tweet):
                self.web_publisher.publish_news_tweet(
                    ticker=sector_name, tweet_text=news_tweet,
                    sector=sector_name.lower(),
                    tickers=tickers,
                )

        # Post sector memo to Substack Notes (API or browser fallback)
        if self.substack_use_browser and self.substack_browser.enabled:
            substack_note_id = self.substack_browser.post_memo_as_note(
                ticker=sector_name, memo=memo
            )
        elif self.substack.enabled:
            substack_note_id = self.substack.post_memo_as_note(
                ticker=sector_name, memo=memo
            )
            if substack_note_id is None and self.substack_browser.enabled:
                substack_note_id = self.substack_browser.post_memo_as_note(
                    ticker=sector_name, memo=memo
                )

        # Record the sector memo in tracker
        self.tracker.record_post(
            body=memo, content_type='memo', ticker=sector_name,
            sector=sector_name.lower(),
            discord_sent=discord_sent,
            web_slug=web_slug,
            substack_note_id=substack_note_id,
            source_file=str(memo_file),
        )

        return 1

    def _inject_prices(self, analyses: Dict, prices: Dict) -> Dict:
        """Inject real-time prices into analyses"""
        for ticker, price in prices.items():
            if ticker in analyses and analyses[ticker]:
                if 'snapshot' not in analyses[ticker]:
                    analyses[ticker]['snapshot'] = {}
                if 'price' not in analyses[ticker]['snapshot']:
                    analyses[ticker]['snapshot']['price'] = {}

                analyses[ticker]['snapshot']['price']['mark_price'] = price.price_usd
                analyses[ticker]['snapshot']['price']['price_change_24h'] = price.price_change_24h

        return analyses

    def _save_research(self):
        """Save latest research to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Convert any dataclass objects to dicts
            research_data = {}
            for key, value in self.latest_research.items():
                if hasattr(value, 'to_dict'):
                    research_data[key] = value.to_dict()
                else:
                    research_data[key] = value

            filename = DATA_DIR / f'research_{timestamp}.json'
            with open(filename, 'w') as f:
                json.dump(research_data, f, indent=2, default=str)

            latest_file = DATA_DIR / 'research_latest.json'
            with open(latest_file, 'w') as f:
                json.dump(research_data, f, indent=2, default=str)

            logger.info(f"   Research saved: {filename}")
        except Exception as e:
            logger.error(f"   Save research failed: {e}")

    def _save_analyses(self):
        """Save latest analyses to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = DATA_DIR / f'analyses_{timestamp}.json'

            with open(filename, 'w') as f:
                json.dump(self.latest_analyses, f, indent=2, default=str)

            latest_file = DATA_DIR / 'analyses_latest.json'
            with open(latest_file, 'w') as f:
                json.dump(self.latest_analyses, f, indent=2, default=str)

            logger.info(f"   Analyses saved: {filename}")
        except Exception as e:
            logger.error(f"   Save analyses failed: {e}")

    def stop(self):
        """Stop the orchestrator gracefully"""
        logger.info("\nStopping orchestrator...")
        self.running = False

        self._save_research()
        self._save_analyses()

        # Save RSS seen state for persistence across restarts
        self.rss_engine.save_seen_state()

        # Close tracker DB connection
        self.tracker.close()

        # Close Substack sessions
        self.substack.close()
        self.substack_browser.close()

        logger.info("")
        logger.info("=" * 80)
        logger.info("SHUTDOWN SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total cycles: {self.cycle_count}")
        logger.info(f"Assets tracked: {len(self.latest_analyses)}")
        logger.info(f"Data directory: {DATA_DIR}")
        logger.info(f"Output directory: {OUTPUT_DIR}")
        logger.info("Orchestrator stopped successfully")
        logger.info("=" * 80)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def print_banner():
    """Print startup banner"""
    banner = """
    ================================================================

          CRYPTO ANALYSIS ENGINE v2.0

      Data: Binance + CoinGecko + DeFiLlama (FREE APIs)
      Content: Claude AI (threads & reports only)

    ================================================================
    """
    print(banner)


def main():
    """Main entry point"""
    # Python 3.13 on Windows: sync_playwright() creates its own event loop via
    # asyncio.new_event_loop(). Without this, the default policy may produce a
    # SelectorEventLoop which doesn't support subprocess transport → NotImplementedError.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    print_banner()

    orchestrator = CryptoAnalysisOrchestrator()

    def signal_handler(sig, frame):
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    orchestrator.start()


if __name__ == '__main__':
    main()
