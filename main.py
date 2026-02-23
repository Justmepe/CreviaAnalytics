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
import sys
import time
import json
import signal
import hashlib
import logging
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
from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

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

# Intervals
RESEARCH_INTERVAL = int(os.getenv('RESEARCH_INTERVAL', '60'))
ANALYSIS_INTERVAL = int(os.getenv('ANALYSIS_INTERVAL', '300'))
THREAD_GENERATION_INTERVAL = int(os.getenv('THREAD_INTERVAL', '3600'))

# Assets to track
MAJOR_ASSETS = ['BTC', 'ETH', 'SOL', 'BNB']
MEMECOIN_ASSETS = ['DOGE', 'SHIB', 'PEPE', 'FLOKI']
PRIVACY_ASSETS = ['XMR', 'ZEC', 'DASH', 'SCRT']
DEFI_ASSETS = ['AAVE', 'UNI', 'CRV', 'LDO']

# =============================================================================
# TIME-AWARE SCHEDULING
# =============================================================================

ANCHOR_SLOTS = [
    {"hour": 8,  "mode": "morning_scan",    "label": "Morning Scan",    "full_article": True},
    {"hour": 12, "mode": "mid_day_update",  "label": "Midday Pulse",    "full_article": False},
    {"hour": 16, "mode": "mid_day_update",  "label": "Afternoon Update", "full_article": False},
    {"hour": 20, "mode": "mid_day_update",  "label": "Evening Brief",   "full_article": False},
    {"hour": 0,  "mode": "closing_bell",    "label": "Closing Bell",    "full_article": False},
]
ANCHOR_WINDOW_MINUTES = 15        # How close to slot hour to trigger
BREAKING_NEWS_INTERVAL = 900      # 15 min between breaking news checks
BREAKING_NEWS_THRESHOLD = 0.72    # Relevance score threshold for breaking (was 0.85 — too strict)
ANCHOR_COOLDOWN_MINUTES = 30      # Suppress breaking news right after anchor (was 45)

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
            etherscan_key=ETHERSCAN_API_KEY
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
        self.x_cockpit_poster = XBrowserPoster(session_dir=cockpit_session, headless=False)
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
        self.morning_context = None           # Stored thread summary for mid-day reference
        self.posted_breaking_headlines = set()  # Dedup breaking news (title hashes)
        self.last_btc_price = None            # For price crash/spike detection
        self.last_price_alert_time = 0        # Cooldown for price alerts

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
                    elif current_time - self.last_breaking_check > BREAKING_NEWS_INTERVAL:
                        self._check_and_post_breaking_news()
                        self._check_price_alert()
                        self.last_breaking_check = current_time

                    # Sleep 60s — check every minute for anchors and breaking news
                    logger.info(f"\nNext check in 60s (UTC: {now_utc.strftime('%H:%M')})...")
                    time.sleep(60)

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
        """Check if current UTC time is within ANCHOR_WINDOW_MINUTES of any slot."""
        now = datetime.now(timezone.utc)
        for slot in ANCHOR_SLOTS:
            slot_time = now.replace(hour=slot["hour"], minute=0, second=0, microsecond=0)
            diff_seconds = abs((now - slot_time).total_seconds())
            # Handle midnight wrap (e.g., 23:50 is 10 min from 00:00)
            if diff_seconds > 43200:  # More than 12 hours means we wrapped
                diff_seconds = 86400 - diff_seconds
            if diff_seconds / 60 <= ANCHOR_WINDOW_MINUTES:
                return slot
        return None

    def _run_anchor_content(self, slot: Dict):
        """Execute full content pipeline for an anchor time slot."""

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

        # 2. Generate thread with correct mode
        thread_data = self._run_thread_generation(
            thread_mode=slot["mode"],
            previous_context=self.morning_context
        )

        # 3. Store morning context for mid-day reference
        if slot["mode"] == "morning_scan" and thread_data:
            # Build a short summary of morning thread for mid-day reference
            tweets = thread_data.get('tweets', [])
            if tweets:
                self.morning_context = tweets[0][:200]  # First tweet as summary

        # 4. Platform routing based on slot type
        if slot.get("full_article") and thread_data:
            self._post_anchor_article(thread_data)
        elif thread_data:
            self._post_anchor_note(thread_data, slot)

        # 5. Generate individual asset + sector memos
        self._run_news_memo_generation()

        logger.info(f"Anchor slot {slot['label']} complete")

    def _post_anchor_article(self, thread_data: Dict):
        """Post full article to X Articles + Substack Article (morning slot)."""
        try:
            logger.info(f"\n{'='*80}")
            logger.info("📰 POSTING MORNING SCAN ARTICLE")
            logger.info(f"{'='*80}")

            # Generate proper long-form article with Claude AI
            from src.content.newsletter_generator import generate_daily_scan_newsletter

            # Get analysis data from latest cycle
            if not hasattr(self, 'latest_analyses') or 'BTC' not in self.latest_analyses:
                logger.warning("⚠️  No analysis data available - using fallback")
                # Fallback to thread-based article
                body = self._build_article_body(thread_data)
                title = "Daily Crypto Market Scan"
            else:
                logger.info("\n📝 Step 1: Generating article with Claude AI...")

                # Build sector analyses the same way thread generation does
                sector_analyses = {
                    'memecoins': [self.latest_analyses.get(t) for t in MEMECOIN_ASSETS if t in self.latest_analyses],
                    'privacy': [self.latest_analyses.get(t) for t in PRIVACY_ASSETS if t in self.latest_analyses],
                    'defi': [self.latest_analyses.get(t) for t in DEFI_ASSETS if t in self.latest_analyses]
                }
                logger.info(f"   Sector data: {len(sector_analyses['memecoins'])} memecoins, {len(sector_analyses['privacy'])} privacy, {len(sector_analyses['defi'])} DeFi")

                # Get global market context
                global_metrics = self.data.get_global_metrics()
                market_context = global_metrics.to_dict() if global_metrics else {}

                # Generate newsletter with Claude
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

            # X Article
            logger.info("\n📤 Step 2: Posting article to X...")
            if self.x_use_browser and self.x_browser_poster.enabled:
                try:
                    x_result = self.x_browser_poster.post_article(title, body)
                    if x_result:
                        logger.info("   ✅ X Article posted successfully")
                    else:
                        logger.error("   ❌ X Article posting returned False")
                except Exception as e:
                    logger.error(f"   ❌ X Article exception: {e}", exc_info=True)
            else:
                logger.warning("   ⚠️  X Article posting disabled")

            # Substack Article
            logger.info("\n📤 Step 3: Posting article to Substack...")
            if self.substack_use_browser and self.substack_browser.enabled:
                try:
                    sub_result = self.substack_browser.post_article(title, body)
                    if sub_result:
                        logger.info("   ✅ Substack Article posted successfully")
                    else:
                        logger.error("   ❌ Substack Article posting returned False")
                except Exception as e:
                    logger.error(f"   ❌ Substack Article exception: {e}", exc_info=True)
            else:
                logger.warning("   ⚠️  Substack Article posting disabled")

            logger.info(f"\n{'='*80}")
            logger.info("✅ Morning scan article posting complete")
            logger.info(f"{'='*80}\n")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Anchor article posting error: {e}", exc_info=True)

    def _post_anchor_note(self, thread_data: Dict, slot: Dict):
        """Post summary note to Substack (mid-day/closing slots)."""
        try:
            summary = self._build_note_summary(thread_data, slot)
            if not summary:
                return

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

    def _check_and_post_breaking_news(self):
        """Scan RSS feeds for high-impact news, post immediately if found."""

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
            ALL_TRACKED = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS

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

                # Skip already posted
                if title_hash in self.posted_breaking_headlines:
                    continue

                title_lower = title.lower()

                # Pre-filter: must contain at least one explicit crypto keyword
                # OR be a genuine macro mover. This stops "meatball recalls",
                # "defense stocks", etc. from triggering.
                is_crypto_relevant = any(kw in title_lower for kw in CRYPTO_KEYWORDS)
                is_macro_mover = any(kw in title_lower for kw in MACRO_MOVERS)
                if not is_crypto_relevant and not is_macro_mover:
                    continue

                # Check relevance across ALL tracked assets using whole-word matching
                max_score = 0.0
                for ticker in ALL_TRACKED:
                    _, score = _calculate_relevance(title, ticker, item)
                    max_score = max(max_score, score)

                # Boost for confirmed macro events (but don't guarantee — just raise floor)
                if is_macro_mover and max_score < 0.8:
                    max_score = 0.8

                if max_score < BREAKING_NEWS_THRESHOLD:
                    continue

                logger.info(f"BREAKING NEWS DETECTED (score={max_score:.2f}): {title}")
                self.posted_breaking_headlines.add(title_hash)
                self._post_breaking_news(item, max_score)
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
        """Build and post breaking news across platforms."""
        try:
            headline = item.get('title', '')
            summary = item.get('summary', item.get('description', ''))
            source = item.get('source', 'Unknown')

            logger.info(f"\n{'='*80}")
            logger.info(f"📰 POSTING BREAKING NEWS")
            logger.info(f"   Headline: {headline[:70]}...")
            logger.info(f"   Source: {source}")
            logger.info(f"   Relevance: {score:.0%}")
            logger.info(f"{'='*80}")

            # Get current price for context (try BTC as default)
            current_price = None
            ticker = 'BTC'
            try:
                if hasattr(self, 'data_aggregator') and self.data_aggregator:
                    btc_snapshot = self.data_aggregator.get_asset_snapshot('BTC')
                    if btc_snapshot and btc_snapshot.price:
                        current_price = btc_snapshot.price.mark_price
                        logger.info(f"   Current BTC: ${current_price:,.2f}")
            except Exception as e:
                logger.warning(f"   Could not fetch BTC price: {e}")

            # Build breaking news thread via ThreadBuilder
            logger.info("\n📝 Step 1: Generating thread with Claude AI...")
            raw_thread = self.thread_builder.build_breaking_news_thread(
                headline=headline,
                what_happened=summary[:500] if summary else headline,
                impact=f"High-impact event (relevance: {score:.0%})",
                our_take=f"Source: {source}",
                tags=["crypto", "breaking"]
            )

            if raw_thread:
                tweet_count = len(raw_thread.get('tweets', []))
                logger.info(f"   ✅ Thread generated: {tweet_count} tweets")

                # Normalize tweets to list of strings (ThreadBuilder returns dicts)
                raw_tweets = raw_thread.get('tweets', [])
                tweet_texts = []
                for t in raw_tweets:
                    if isinstance(t, dict):
                        tweet_texts.append(t.get('text', ''))
                    elif isinstance(t, str):
                        tweet_texts.append(t)
                    else:
                        tweet_texts.append(str(t))

                thread_data = {
                    'tweets': tweet_texts,
                    'tweet_count': len(tweet_texts),
                    'copy_paste_ready': '\n\n'.join(tweet_texts),
                    'type': 'breaking_news',
                }

                # Post X thread
                logger.info("\n📤 Step 2: Posting thread to X...")
                post_result = None
                # Try API first (faster, no detection)
                if self.x_poster and self.x_poster.enabled:
                    try:
                        post_result = self.x_poster.post_thread(thread_data)
                        if post_result and post_result.get('success'):
                            posted_count = post_result.get('posted_count', len(tweets))
                            logger.info(f"   ✅ X thread posted via API ({posted_count} tweets)")
                        else:
                            post_result = None  # Fall back to browser
                    except Exception as e:
                        logger.warning(f"   ⚠️  API thread posting failed: {e}")
                        post_result = None  # Fall back to browser
                
                # Fall back to browser poster if API unavailable
                if not post_result and getattr(self.x_browser_poster, 'enabled', False):
                    try:
                        post_result = self.x_browser_poster.post_thread(thread_data)
                        if post_result and post_result.get('success'):
                            logger.info(f"   ✅ X thread posted via browser ({post_result.get('posted_count', 0)} tweets)")
                        else:
                            logger.error(f"   ❌ X thread browser failed: {post_result.get('error', 'Unknown error') if post_result else 'No result'}")
                    except Exception as e:
                        logger.error(f"   ❌ X thread browser exception: {e}", exc_info=True)
                        post_result = None

                if not post_result:
                    logger.warning("   ⚠️  X posting unavailable (API and browser disabled)")

                # Record in tracker
                thread_body = thread_data['copy_paste_ready']
                if not self.tracker.is_duplicate(thread_body):
                    self.tracker.record_post(
                        body=thread_body,
                        content_type='breaking_thread',
                        ticker='BREAKING',
                    )
            else:
                logger.error("   ❌ Thread generation returned None")

            # Generate breaking news article (long-form)
            logger.info("\n📄 Step 3: Generating article with Claude AI...")
            from src.content.breaking_news_article_generator import generate_breaking_news_article

            try:
                article_data = generate_breaking_news_article(
                    headline=headline,
                    summary=summary,
                    source=source,
                    current_price=current_price,
                    ticker=ticker,
                    relevance_score=score
                )

                if article_data:
                    article_title = article_data.get('title', headline)
                    article_body = article_data.get('body', '')
                    word_count = article_data.get('word_count', len(article_body.split()))
                    logger.info(f"   ✅ Article generated: {word_count} words by {article_data.get('generated_by', 'Unknown')}")

                    # Save to Notion first (before posting anywhere)
                    if self.notion_manager and self.notion_manager.is_available():
                        try:
                            notion_result = self.notion_manager.save_news_post(
                                title=article_title,
                                content=article_body,
                                tags=['breaking_news', ticker, source]
                            )
                            logger.info(f"   ✅ Notion: Article saved (ID: {notion_result})")
                        except Exception as e:
                            logger.warning(f"   ⚠️  Notion save failed: {e}")

                    # Post X Article
                    logger.info("\n📤 Step 4: Posting article to X...")
                    if self.x_use_browser and self.x_browser_poster.enabled and article_body:
                        try:
                            x_result = self.x_browser_poster.post_article(article_title, article_body)
                            if x_result:
                                logger.info("   ✅ X Article posted")
                            else:
                                logger.error("   ❌ X Article posting returned False")
                        except Exception as e:
                            logger.error(f"   ❌ X Article exception: {e}", exc_info=True)
                    else:
                        logger.warning("   ⚠️  X Article posting disabled or no content")

                    # Post Substack Article
                    logger.info("\n📤 Step 5: Posting article to Substack...")
                    if self.substack_use_browser and self.substack_browser.enabled and article_body:
                        try:
                            sub_result = self.substack_browser.post_article(article_title, article_body)
                            if sub_result:
                                logger.info("   ✅ Substack Article posted")
                            else:
                                logger.error("   ❌ Substack Article posting returned False")
                        except Exception as e:
                            logger.error(f"   ❌ Substack Article exception: {e}", exc_info=True)
                    else:
                        logger.warning("   ⚠️  Substack Article posting disabled or no content")
                else:
                    logger.error("   ❌ Article generation returned None")
            except Exception as e:
                logger.error(f"   ❌ Article generation exception: {e}", exc_info=True)

            # Post Substack Chat Thread (fast, visible to subscribers)
            logger.info("\n📤 Step 6: Posting chat thread to Substack...")
            if self.substack_use_browser and self.substack_browser.enabled:
                try:
                    chat_title = f"{headline[:80]}"
                    chat_msg = summary[:500] if summary else headline
                    chat_id = self.substack_browser.post_chat_thread(
                        title=chat_title,
                        messages=[chat_msg]
                    )
                    if chat_id:
                        logger.info("   ✅ Substack Chat Thread posted")
                    else:
                        logger.error("   ❌ Substack Chat Thread posting returned None")
                except Exception as e:
                    logger.error(f"   ❌ Substack Chat exception: {e}", exc_info=True)
            else:
                logger.warning("   ⚠️  Substack Chat posting disabled")

            # Post to @CreviaCockpit (breaking news only — thread + article)
            if getattr(self.x_cockpit_poster, 'enabled', False):
                logger.info("\n📤 Cockpit Step 1: Posting thread to @CreviaCockpit...")
                if raw_thread and thread_data:
                    try:
                        cockpit_thread = self.x_cockpit_poster.post_thread(thread_data)
                        if cockpit_thread and cockpit_thread.get('success'):
                            logger.info("   ✅ @CreviaCockpit thread posted")
                        else:
                            logger.warning("   ⚠️  @CreviaCockpit thread failed")
                    except Exception as e:
                        logger.error(f"   ❌ @CreviaCockpit thread exception: {e}")

                logger.info("\n📤 Cockpit Step 2: Posting article to @CreviaCockpit...")
                try:
                    from src.content.breaking_news_article_generator import generate_breaking_news_article as _gen
                    _ad = _gen(
                        headline=headline, summary=summary, source=source,
                        current_price=current_price, ticker=ticker, relevance_score=score
                    )
                    if _ad and _ad.get('body'):
                        cockpit_art = self.x_cockpit_poster.post_article(_ad['title'], _ad['body'])
                        if cockpit_art:
                            logger.info("   ✅ @CreviaCockpit article posted")
                        else:
                            logger.warning("   ⚠️  @CreviaCockpit article failed")
                except Exception as e:
                    logger.error(f"   ❌ @CreviaCockpit article exception: {e}")
            else:
                logger.debug("   @CreviaCockpit poster disabled — skipping")

            logger.info(f"\n{'='*80}")
            logger.info("✅ Breaking news posting complete")
            logger.info(f"{'='*80}\n")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Breaking news posting error: {e}", exc_info=True)

    def _build_article_body(self, thread_data: Dict) -> Optional[str]:
        """Convert thread data into long-form article body."""
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
            all_tickers = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS
            prices = self.data.get_prices_batch(all_tickers)

            for ticker, price in prices.items():
                self.latest_research[ticker] = {
                    'price': price.to_dict(),
                    'timestamp': int(time.time())
                }
                logger.info(f"   {ticker}: ${price.price_usd:,.2f} ({price.price_change_24h:+.2f}%)")

            # 3. Fetch derivatives for majors
            logger.info("Fetching derivatives data...")
            for ticker in MAJOR_ASSETS:
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

            # 9. Trade setup generation (Claude AI — for major assets)
            generated_setups = []
            try:
                if self.trade_setup_gen._enabled and self.web_publisher.enabled:
                    setup_count = 0
                    for ticker in MAJOR_ASSETS:
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

                    logger.info(f"   Trade Setups: {setup_count} generated for major assets")
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

            # Save analyses
            self._save_analyses()

        except Exception as e:
            logger.error(f"Analysis phase error: {e}")

    def _run_thread_generation(self, thread_mode: str = 'morning_scan',
                               previous_context: Optional[str] = None) -> Optional[Dict]:
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
            all_tickers = MAJOR_ASSETS + MEMECOIN_ASSETS + PRIVACY_ASSETS + DEFI_ASSETS
            prices = self.data.get_prices_batch(all_tickers)

            # Inject prices into analyses
            updated_analyses = self._inject_prices(self.latest_analyses.copy(), prices)

            # Build sector analyses
            sector_analyses = {
                'memecoins': [updated_analyses.get(t) for t in MEMECOIN_ASSETS if t in updated_analyses],
                'privacy': [updated_analyses.get(t) for t in PRIVACY_ASSETS if t in updated_analyses],
                'defi': [updated_analyses.get(t) for t in DEFI_ASSETS if t in updated_analyses]
            }

            # Get global context
            global_metrics = self.data.get_global_metrics()
            market_context = global_metrics.to_dict() if global_metrics else self.latest_research.get('global')

            # Generate thread with mode (Claude used internally for writing)
            logger.info(f"Generating {thread_mode} thread...")
            thread = generate_x_thread(
                btc_analysis=updated_analyses['BTC'],
                market_context=market_context,
                thread_mode=thread_mode,
                previous_context=previous_context,
                eth_analysis=updated_analyses.get('ETH'),
                sector_analyses=sector_analyses,
                all_analyses=updated_analyses
            )

            # Dedup check
            thread_body = thread.get('copy_paste_ready', '')
            if self.tracker.is_duplicate(thread_body):
                logger.info("   Thread is a duplicate, skipping all channels")
                return None

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
                web_result = self.web_publisher.publish_thread(
                    thread_data=thread,
                    tickers=list(updated_analyses.keys()),
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

            # --- 1. Individual memos for each major asset ---
            for ticker in MAJOR_ASSETS:
                memos_generated += self._generate_and_send_memo(ticker, timestamp)

            # --- 2. Sector memos: aggregate news across coins in each sector ---
            sector_map = {
                'MEMECOINS': MEMECOIN_ASSETS,
                'PRIVACY': PRIVACY_ASSETS,
                'DEFI': DEFI_ASSETS,
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

        # X Article — post full memo as long-form article (browser only, API doesn't support articles)
        x_article_id = None
        if getattr(self.x_browser_poster, 'enabled', False):
            article_title = f"{ticker} Market Analysis"
            if current_price:
                article_title = f"{ticker} @ ${current_price:,.2f} — Market Analysis"
            x_article_id = self.x_browser_poster.post_article(article_title, memo)
            if x_article_id:
                logger.info(f"   {ticker}: X Article posted")

        # Web API — memo + news tweet
        if self.web_publisher.enabled:
            lead_image = self.rss_engine.select_best_image(events, ticker=ticker)
            web_result = self.web_publisher.publish_memo(
                ticker=ticker, memo=memo,
                current_price=current_price,
                image_url=lead_image,
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

        # X Article — post full sector memo as long-form article
        x_article_id = None
        if self.x_use_browser and self.x_browser_poster.enabled:
            article_title = f"{sector_name} Sector Analysis"
            x_article_id = self.x_browser_poster.post_article(article_title, memo)
            if x_article_id:
                logger.info(f"   {sector_name}: X Article posted")

        # Web API — memo + news tweet
        if self.web_publisher.enabled:
            lead_image = self.rss_engine.select_best_image(unique_events, ticker=sector_name)
            web_result = self.web_publisher.publish_memo(
                ticker=sector_name, memo=memo,
                sector=sector_name.lower(),
                tickers=tickers,
                image_url=lead_image,
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
