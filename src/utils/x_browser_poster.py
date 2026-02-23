"""
X/Twitter Browser-Based Poster using Playwright

Provides the same interface as XPoster (post_tweet, post_thread) but uses
Playwright browser automation instead of the tweepy API.

This is the primary posting method when:
- X API returns 403 Forbidden (app permissions issue)
- tweepy is not installed
- API rate limits are hit

Uses a persistent browser session (x_browser_session/) so login
is only needed once via setup_x_session.py.

Now with session persistence and automatic re-authentication support.
"""

import os
import re
import time
import json
import random
import logging
import platform
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

try:
    # Patchright is an undetected fork of Playwright that patches event.isTrusted
    # detection — critical since X now checks isTrusted on all input events (Feb 2026).
    # Drop-in replacement: same API, just fixes the core detection vector.
    from patchright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False

# Project root (two levels up from src/utils/)
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SESSION_DIR = str(PROJECT_ROOT / "x_browser_session")
LOG_FILE = str(PROJECT_ROOT / "data" / "x_posting_log.json")

# Import session manager for persistence
try:
    from src.utils.x_session_manager import XSessionManager
    HAS_SESSION_MANAGER = True
except ImportError:
    HAS_SESSION_MANAGER = False


def find_chrome_executable() -> Optional[str]:
    """
    Detect system Chrome browser (real Chrome, not Chromium).
    This avoids the "Chrome is being controlled by automated test software" detection.
    Falls back to Chromium if not found.
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows Chrome paths
        possible_paths = [
            Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)
    elif system == "Darwin":  # macOS
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path(chrome_path).exists():
            return chrome_path
    elif system == "Linux":
        import shutil
        chrome = shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
        if chrome:
            return chrome
    
    return None  # Fall back to Chromium


def _human_move_and_click(page, element, button: str = 'left'):
    """
    Move the mouse in a curved path to the element then click at a random offset
    within the element bounds. Avoids the 'always clicks dead center' bot pattern.
    """
    try:
        box = element.bounding_box()
        if not box:
            element.click()
            return

        # Random target inside element (20-80% range to avoid edges)
        target_x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
        target_y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)

        # Move mouse in small steps with slight jitter (curved path)
        # Start from a random prior position on screen
        start_x = random.uniform(100, 1100)
        start_y = random.uniform(100, 700)
        page.mouse.move(start_x, start_y)

        steps = random.randint(8, 18)
        for step in range(1, steps + 1):
            t = step / steps
            # Ease-in-out interpolation
            ease = t * t * (3 - 2 * t)
            ix = start_x + (target_x - start_x) * ease + random.uniform(-4, 4)
            iy = start_y + (target_y - start_y) * ease + random.uniform(-4, 4)
            page.mouse.move(ix, iy)
            time.sleep(random.uniform(0.004, 0.018))

        # Arrive at target, brief pause before click
        page.mouse.move(target_x, target_y)
        time.sleep(random.uniform(0.08, 0.22))
        page.mouse.click(target_x, target_y, button=button)
    except Exception:
        # Fallback to regular click if anything fails
        try:
            element.click()
        except Exception:
            element.evaluate("el => el.click()")


def _human_type(page, text: str, wpm: int = 55):
    """
    Type text with human-like variable speed.

    Uses a gaussian distribution around the target WPM with occasional
    burst typing and thinking pauses — avoids the uniform-delay bot pattern.
    """
    if not text:
        return

    # base seconds-per-character from target WPM (avg 5 chars/word)
    base_ms = 60_000 / (wpm * 5) / 1000  # seconds

    i = 0
    while i < len(text):
        char = text[i]

        # Thinking pause (rare, ~1.5% of chars)
        if random.random() < 0.015:
            time.sleep(random.uniform(0.3, 1.2))

        # Burst mode: type next 3-8 chars faster (mimics typing common letter combos)
        if random.random() < 0.12:
            burst_len = random.randint(3, 8)
            for j in range(burst_len):
                if i >= len(text):
                    break
                c = text[i]
                if c == '\n':
                    page.keyboard.press('Enter')
                else:
                    page.keyboard.type(c)
                time.sleep(max(0.01, random.gauss(base_ms * 0.45, base_ms * 0.15)))
                i += 1
            continue

        # Normal character
        if char == '\n':
            page.keyboard.press('Enter')
        else:
            page.keyboard.type(char)

        # Gaussian delay — more natural than uniform
        delay = max(0.018, random.gauss(base_ms, base_ms * 0.35))
        time.sleep(delay)
        i += 1


def add_stealth_scripts(page):
    """
    Add stealth scripts to hide automation signals from detection.

    This must be called IMMEDIATELY after context creation, BEFORE navigation.
    Hides:
    - navigator.webdriver (main detection vector)
    - navigator.plugins
    - navigator.languages
    - chrome automation flags
    """
    try:
        # Override navigator.webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        # Override navigator.plugins (hide headless indicators)
        page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        # Override navigator.languages
        page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        # Remove headless chrome signals
        page.add_init_script("""
            Object.defineProperty(navigator, 'chrome', {
                get: () => ({
                    runtime: {},
                    loadTimes: () => {},
                }),
            });
        """)
        
        logger.debug("[Stealth] Scripts injected successfully")
    except Exception as e:
        logger.warning(f"[Stealth] Failed to inject scripts: {e}")


class XBrowserPoster:
    """
    Post tweets and threads to X using Playwright browser automation.

    Uses a persistent Chromium session (x_browser_session/) that stores
    cookies/login state. Run setup_x_session.py once to log in manually,
    then this class reuses that session for all subsequent posts.

    Human-like behavior:
    - Natural typing speed (30-80ms per char)
    - Random pauses between actions
    - Jitter delays between thread tweets (configurable)
    """

    def __init__(
        self,
        session_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        min_delay: float = 45.0,
        max_delay: float = 90.0,
        headless: bool = False,
        auto_login: bool = False,
    ):
        self.session_dir = session_dir or SESSION_DIR
        self.log_file = log_file or LOG_FILE
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.headless = headless
        self.auto_login = auto_login
        self.lock = Lock()

        # Initialize session manager if available
        self.session_manager = None
        if HAS_SESSION_MANAGER:
            self.session_manager = XSessionManager(self.session_dir)

        # Check prerequisites
        self.enabled = False
        if not HAS_PLAYWRIGHT:
            logger.warning("[XBrowserPoster] playwright not installed — disabled")
            return

        if not Path(self.session_dir).exists():
            logger.warning(
                f"[XBrowserPoster] Session dir not found: {self.session_dir}. "
                "Run tests/setup_x_session.py first to log in."
            )
            return

        self.enabled = True
        
        # Check session health if manager available
        if self.session_manager:
            if self.session_manager.is_session_healthy():
                logger.info("[XBrowserPoster] Session is healthy")
            else:
                logger.warning("[XBrowserPoster] Session may need verification")
                if not self.auto_login:
                    logger.warning("[XBrowserPoster] Set auto_login=True to auto-restore invalid sessions")
        
        logger.info("[XBrowserPoster] Initialized (Playwright browser automation with session management)")

    def _apply_jitter_delay(self):
        """Wait with jitter between min_delay and max_delay before posting."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"[XBrowserPoster] Jitter delay: {delay:.0f}s")
        time.sleep(delay)

    def _handle_session_expired(self) -> bool:
        """
        Called when session is detected as expired.
        
        If auto_login is enabled, attempt automatic recovery.
        Returns True if session was recovered, False otherwise.
        """
        logger.warning("[XBrowserPoster] Session detected as expired")
        
        if self.session_manager:
            self.session_manager.state.mark_error("Session expired during posting")
        
        if self.auto_login:
            logger.info("[XBrowserPoster] Attempting automatic session recovery...")
            try:
                from src.utils.x_auto_login import XAutoLoginHandler
                handler = XAutoLoginHandler(self.session_dir, headless=False)
                success = handler.prompt_re_login()
                if success:
                    logger.info("[XBrowserPoster] Session recovered successfully")
                    return True
            except Exception as e:
                logger.error(f"[XBrowserPoster] Auto-login failed: {e}")
        
        logger.error(
            "[XBrowserPoster] Session expired. To fix:\n"
            "   1. Run: python tests/setup_x_session.py\n"
            "   2. Log in to your X account\n"
            "   3. Close the browser when done\n"
            "   4. Retry your operation"
        )
        return False

    def log_post(self, tweet_text: str, success: bool, thread_data: Optional[Dict] = None):
        """Log post attempt to history file."""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'method': 'playwright_browser',
                'success': success,
                'content_preview': tweet_text[:100] if tweet_text else '',
                'thread_type': thread_data.get('type', 'unknown') if thread_data else 'single',
            }

            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)

            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.warning(f"[XBrowserPoster] Failed to log post: {e}")

    # ── Rich Text Formatting Helpers ───────────────────────────────────

    def _parse_markdown_blocks(self, text: str) -> list:
        """
        Parse markdown text into structured blocks for rich text formatting.

        Returns list of dicts with 'type' and content:
        - heading: {type, level, text}
        - bullet_list: {type, items}
        - paragraph: {type, text}
        - hr: {type}
        - newline: {type}
        """
        blocks = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Empty line
            if not stripped:
                blocks.append({'type': 'newline'})
                i += 1
                continue

            # Horizontal rule → skip (visual noise in X articles)
            if stripped in ('---', '***', '___'):
                i += 1
                continue

            # Headers
            if stripped.startswith('### '):
                blocks.append({'type': 'heading', 'level': 3, 'text': stripped[4:].strip()})
                i += 1
                continue
            elif stripped.startswith('## '):
                blocks.append({'type': 'heading', 'level': 2, 'text': stripped[3:].strip()})
                i += 1
                continue
            elif stripped.startswith('# '):
                blocks.append({'type': 'heading', 'level': 1, 'text': stripped[2:].strip()})
                i += 1
                continue

            # Bullet list (-, *, •)
            if re.match(r'^[-*•]\s', stripped):
                items = []
                while i < len(lines):
                    item_line = lines[i].strip()
                    if re.match(r'^[-*•]\s', item_line):
                        item_text = re.sub(r'^[-*•]\s+', '', item_line)
                        items.append(item_text)
                        i += 1
                    elif item_line == '':
                        break
                    else:
                        break
                blocks.append({'type': 'bullet_list', 'items': items})
                continue

            # Regular paragraph
            blocks.append({'type': 'paragraph', 'text': stripped})
            i += 1

        return blocks

    def _type_inline_formatted(self, page, text: str):
        """
        Type text into the editor with inline bold formatting.

        Converts **bold** markers to actual Ctrl+B toggling so the
        rich text editor renders bold text properly.
        """
        # Split by **bold** markers, keeping them as separate items
        parts = re.split(r'(\*\*.*?\*\*)', text)

        for part in parts:
            if not part:
                continue

            if part.startswith('**') and part.endswith('**') and len(part) > 4:
                # Bold text: toggle Ctrl+B, type, toggle Ctrl+B
                bold_text = part[2:-2]
                page.keyboard.press('Control+b')
                _human_type(page, bold_text, wpm=60)
                page.keyboard.press('Control+b')
            else:
                # Normal text
                _human_type(page, part, wpm=60)

    def _type_formatted_body(self, page, body: str):
        """
        Type article body with proper rich text formatting into X's article editor.

        Parses markdown and applies formatting via keyboard shortcuts:
        - **bold** → Ctrl+B toggle
        - ## Headers → Bold text on its own line
        - - Bullet items → Typed with '- ' prefix (ProseMirror may auto-convert to list)
        - --- → Skipped (horizontal rules add visual noise)
        """
        # Remove leading # title line (already filled in the title field)
        body = re.sub(r'^#\s+[^\n]*\n*', '', body.strip(), count=1).strip()

        # Clean up AI-style hyphen spacing: " — " or " – " → ", "
        # and " - " between words (not bullet markers) → ", "
        body = re.sub(r'\s+—\s+', ', ', body)
        body = re.sub(r'\s+–\s+', ', ', body)
        # Only replace " - " mid-sentence (not at line start for bullets)
        body = re.sub(r'(?<=\w)\s+-\s+(?=\w)', ', ', body)

        # Parse into structured blocks
        blocks = self._parse_markdown_blocks(body)

        # Collapse consecutive newlines
        cleaned = []
        prev_newline = False
        for block in blocks:
            if block['type'] == 'newline':
                if not prev_newline:
                    cleaned.append(block)
                prev_newline = True
            else:
                prev_newline = False
                cleaned.append(block)

        for block in cleaned:
            btype = block['type']

            if btype == 'heading':
                # Make heading text bold (works reliably across all editors)
                text = block['text']
                page.keyboard.press('Control+b')
                _human_type(page, text, wpm=58)
                page.keyboard.press('Control+b')
                page.keyboard.press('Enter')
                page.keyboard.press('Enter')
                time.sleep(random.uniform(0.08, 0.18))

            elif btype == 'bullet_list':
                for item in block['items']:
                    # Type '- ' at start; ProseMirror auto-converts to bullet list
                    page.keyboard.type('-')
                    time.sleep(random.uniform(0.05, 0.12))
                    page.keyboard.type(' ')
                    time.sleep(random.uniform(0.08, 0.18))
                    self._type_inline_formatted(page, item)
                    page.keyboard.press('Enter')
                    time.sleep(0.05)
                # Extra Enter to exit list mode
                page.keyboard.press('Enter')
                time.sleep(0.1)

            elif btype == 'paragraph':
                self._type_inline_formatted(page, block['text'])
                page.keyboard.press('Enter')
                page.keyboard.press('Enter')
                time.sleep(0.1)

            elif btype == 'newline':
                page.keyboard.press('Enter')
                time.sleep(0.03)

    def _clear_network_state(self) -> None:
        """
        Delete Chrome's cached network state before each launch.

        After a successful x.com navigation, Chrome writes network state to
        multiple files: Network Persistent State (QUIC/ECH/alt-services),
        TransportSecurity (HSTS), Reporting and NEL, and Cache. On VPS,
        any of these can cause ERR_NAME_NOT_RESOLVED on the next Chrome launch
        because they contain Cloudflare ECH/QUIC configs unreachable from the
        datacenter. We wipe them all before each launch (Cookies preserved).
        """
        import shutil
        default_dir = Path(self.session_dir) / "Default"

        # Files to delete (singletons)
        state_files = [
            "Network Persistent State",
            "TransportSecurity",
            "Reporting and NEL",
            "Reporting and NEL-journal",
            "SCT Auditing Pending Reports",
        ]
        # Directories to delete (caches — safe to nuke, Chrome rebuilds them)
        state_dirs = [
            "Cache",
            "Code Cache",
            "GPUCache",
            "DawnGraphiteCache",
            "DawnWebGPUCache",
        ]

        deleted = []
        for name in state_files:
            p = default_dir / name
            if p.exists():
                try:
                    p.unlink()
                    deleted.append(name)
                except Exception:
                    pass
        for name in state_dirs:
            p = default_dir / name
            if p.exists():
                try:
                    shutil.rmtree(p, ignore_errors=True)
                    deleted.append(name + "/")
                except Exception:
                    pass

        if deleted:
            logger.debug(f"[XBrowserPoster] Cleared network state: {', '.join(deleted)}")

    def _post_single_tweet_browser(self, tweet_text: str) -> bool:
        """
        Post a single tweet using the browser.

        Opens the persistent session with stealth mode, types the tweet, clicks Post.
        Returns True on success, False on failure.
        """
        with self.lock:
            try:
                # Ensure virtual display is set for headless=False mode on Linux (Xvfb :99)
                if platform.system() == "Linux":
                    os.environ.setdefault('DISPLAY', ':99')

                # Clear cached network state to avoid QUIC/ECH/DoH DNS corruption on VPS
                self._clear_network_state()

                with sync_playwright() as p:
                    chrome_path = find_chrome_executable()
                    launch_kwargs = dict(
                        headless=self.headless,
                        viewport={"width": 1280, "height": 900},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                        locale='en-US',
                        timezone_id='America/New_York',
                        ignore_default_args=['--enable-automation'],
                        args=[
                            '--no-sandbox',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-popup-blocking',
                            # VPS networking fixes:
                            # - NetworkServiceSandbox: Chrome sandbox isolates DNS on Linux VPS
                            # - EncryptedClientHello: ECH/DoH configs from Cloudflare get cached and break DNS
                            # - DnsOverHttpsUpgrade: prevent automatic DoH upgrade that VPS can't reach
                            '--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade',
                            '--disable-quic',  # QUIC/H3 alternative service cached from x.com causes DNS issues
                            '--no-zygote',
                        ],
                    )
                    if chrome_path:
                        launch_kwargs['executable_path'] = chrome_path

                    # Launch with comprehensive anti-detection features
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        **launch_kwargs,
                    )
                    page = context.new_page()

                    try:
                        # Navigate to X home
                        logger.info("[XBrowserPoster] Navigating to X home...")
                        page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=60000)
                        page.wait_for_load_state("domcontentloaded", timeout=20000)

                        # Wait for React SPA to fully render
                        try:
                            page.wait_for_load_state("networkidle", timeout=30000)
                        except Exception:
                            pass
                        time.sleep(random.uniform(3, 5))

                        # Check if we need to log in (redirected to login page)
                        if "login" in page.url.lower() or "flow" in page.url.lower():
                            logger.error(
                                "[XBrowserPoster] Redirected to login - Session expired. "
                            )
                            if self.session_manager:
                                self.session_manager.state.mark_error("Redirected to login page")
                            context.close()
                            return False

                        # Session confirmed active — persist state so session_state.json stays valid
                        if self.session_manager:
                            self.session_manager.state.mark_logged_in()

                        # Wait for timeline to render
                        for sel in [
                            'div[data-testid="primaryColumn"]',
                            'nav[role="navigation"]',
                            'a[aria-label="Profile"]',
                        ]:
                            try:
                                page.locator(sel).first.wait_for(timeout=10000)
                                break
                            except Exception:
                                continue

                        # Dismiss common X popups/overlays
                        for sel in [
                            'button[data-testid="app-bar-close"]',
                            'div[role="button"]:has-text("Not now")',
                            'button:has-text("Not now")',
                            'button:has-text("Maybe later")',
                            'button[aria-label="Close"]',
                        ]:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible(timeout=1500):
                                    el.click()
                                    time.sleep(0.5)
                            except Exception:
                                continue

                        # Press Escape to dismiss remaining overlays
                        page.keyboard.press("Escape")
                        time.sleep(0.5)

                        # Find and click compose area
                        compose_opened = False

                        compose_selectors = [
                            'div[data-testid="tweetTextarea_0"]',
                            'div[contenteditable="true"][role="textbox"]',
                            'div[aria-label*="Post text"]',
                            'div[aria-label*="post text"]',
                            'div[aria-label*="What"]',
                            'div[data-testid="tweetTextarea_0RichTextInputContent"]',
                            'div[contenteditable="true"][data-testid]',
                            'div[contenteditable="true"]',
                        ]

                        for selector in compose_selectors:
                            try:
                                el = page.locator(selector).first
                                if el.is_visible(timeout=3000):
                                    time.sleep(random.uniform(0.5, 1.2))
                                    _human_move_and_click(page, el)
                                    compose_opened = True
                                    logger.info(f"[XBrowserPoster] Compose area found: {selector}")
                                    break
                            except Exception:
                                continue

                        if not compose_opened:
                            logger.error("[XBrowserPoster] Could not find compose area")
                            try:
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_compose.png"))
                            except Exception:
                                pass
                            context.close()
                            return False

                        time.sleep(random.uniform(0.6, 1.2))

                        # Click into contenteditable to ensure focus
                        try:
                            text_input = page.locator('div[contenteditable="true"]').first
                            if text_input.is_visible(timeout=3000):
                                _human_move_and_click(page, text_input)
                                time.sleep(random.uniform(0.3, 0.6))
                        except Exception:
                            pass

                        # Type tweet with human-like speed (gaussian, not uniform)
                        _human_type(page, tweet_text)

                        logger.info(f"[XBrowserPoster] Typed: {tweet_text[:60]}...")
                        time.sleep(random.uniform(1, 2))

                        # Remove overlay masks that block clicks
                        try:
                            page.evaluate("""
                                const layers = document.getElementById('layers');
                                if (layers) {
                                    layers.querySelectorAll('[data-testid="mask"], [class*="r-1p0dtai"]').forEach(el => {
                                        if (!el.closest('[data-testid="tweetButtonInline"]')) {
                                            el.remove();
                                        }
                                    });
                                }
                            """)
                        except Exception:
                            pass

                        # Find and click Post button
                        post_clicked = False

                        # Method 1: data-testid
                        try:
                            post_btn = page.locator('button[data-testid="tweetButtonInline"]').first
                            if post_btn.is_visible(timeout=3000) and post_btn.is_enabled():
                                time.sleep(random.uniform(0.4, 0.9))
                                _human_move_and_click(page, post_btn)
                                post_clicked = True
                                logger.info("[XBrowserPoster] Clicked Post button (testid)")
                        except Exception:
                            pass

                        # Method 2: text search
                        if not post_clicked:
                            try:
                                buttons = page.locator('button')
                                for i in range(min(buttons.count(), 20)):
                                    btn = buttons.nth(i)
                                    if btn.is_visible(timeout=1000):
                                        btn_text = btn.text_content().strip().lower()
                                        if btn_text == "post":
                                            time.sleep(random.uniform(0.4, 0.9))
                                            _human_move_and_click(page, btn)
                                            post_clicked = True
                                            logger.info("[XBrowserPoster] Clicked Post button (text)")
                                            break
                            except Exception:
                                pass

                        if not post_clicked:
                            logger.error("[XBrowserPoster] Could not find Post button")
                            try:
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_post_btn.png"))
                            except Exception:
                                pass
                            context.close()
                            return False

                        # Wait for post confirmation
                        time.sleep(random.uniform(4, 6))
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass

                        logger.info("[XBrowserPoster] Tweet posted successfully")
                        if self.session_manager:
                            self.session_manager.state.mark_verified()
                        context.close()
                        return True

                    except Exception as e:
                        logger.error(f"[XBrowserPoster] Browser error: {e}")
                        try:
                            page.screenshot(path=str(PROJECT_ROOT / "x_debug_error.png"))
                        except Exception:
                            pass
                        context.close()
                        return False

            except Exception as e:
                logger.error(f"[XBrowserPoster] Playwright launch error: {e}")
                return False

    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
        """
        Post a single tweet.

        Args:
            text: Tweet text (max 280 chars)
            reply_to_id: Not supported in browser mode (ignored)

        Returns:
            'browser_posted' on success, None on failure
        """
        if not self.enabled:
            return None

        text = text[:280]
        success = self._post_single_tweet_browser(text)
        
        if not success and self.auto_login:
            # Check if failure was due to session expiration
            if self.session_manager and not self.session_manager.is_session_healthy():
                logger.info("[XBrowserPoster] Session unhealthy - attempting recovery")
                if self._handle_session_expired():
                    # Retry posting with restored session
                    logger.info("[XBrowserPoster] Retrying tweet post with recovered session")
                    success = self._post_single_tweet_browser(text)
        
        self.log_post(text, success)

        if success:
            return 'browser_posted'
        return None

    def _post_article_browser(self, title: str, body: str) -> bool:
        """
        Post an X Article using the browser.

        Navigates to x.com/compose/article, fills title and body, publishes.
        Uses stealth mode to avoid automation detection.
        Returns True on success, False on failure.
        """
        with self.lock:
            try:
                # Ensure virtual display is set for headless=False mode on Linux (Xvfb :99)
                if platform.system() == "Linux":
                    os.environ.setdefault('DISPLAY', ':99')

                # Clear cached network state to avoid QUIC/ECH/DoH DNS corruption on VPS
                self._clear_network_state()

                with sync_playwright() as p:
                    chrome_path = find_chrome_executable()
                    launch_kwargs = dict(
                        headless=self.headless,
                        viewport={"width": 1280, "height": 900},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                        locale='en-US',
                        timezone_id='America/New_York',
                        args=[
                            '--no-sandbox',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-popup-blocking',
                            # VPS networking fixes:
                            # - NetworkServiceSandbox: Chrome sandbox isolates DNS on Linux VPS
                            # - EncryptedClientHello: ECH/DoH configs from Cloudflare get cached and break DNS
                            # - DnsOverHttpsUpgrade: prevent automatic DoH upgrade that VPS can't reach
                            '--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade',
                            '--disable-quic',  # QUIC/H3 alternative service cached from x.com causes DNS issues
                            '--no-zygote',
                        ],
                    )
                    if chrome_path:
                        launch_kwargs['executable_path'] = chrome_path

                    # Launch with anti-detection features
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        **launch_kwargs,
                    )
                    page = context.new_page()

                    try:
                        # Navigate to articles page and click the Write button
                        logger.info("[XBrowserPoster] Navigating to X articles page...")
                        page.goto("https://x.com/compose/articles", timeout=60000)
                        page.wait_for_load_state("domcontentloaded", timeout=20000)

                        try:
                            page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        time.sleep(3)

                        # Check if redirected to login
                        if "login" in page.url.lower() or "flow" in page.url.lower():
                            logger.error(
                                "[XBrowserPoster] Redirected to login - Session expired."
                            )
                            if self.session_manager:
                                self.session_manager.state.mark_error("Redirected to login page")
                            context.close()
                            return False

                        # Dismiss popups
                        page.keyboard.press("Escape")
                        time.sleep(1)

                        # Click the "Write" button/link to create a new article
                        write_clicked = False

                        # Try 1: <a> link with text "Write"
                        for sel in [
                            'a:has-text("Write")',
                            'button:has-text("Write")',
                            '[aria-label*="Write"]',
                            'a[href*="/compose/articles/"]',
                        ]:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible(timeout=3000):
                                    el.click()
                                    time.sleep(5)
                                    write_clicked = True
                                    logger.info(f"[XBrowserPoster] Clicked Write button: {sel}")
                                    break
                            except Exception:
                                continue

                        if not write_clicked:
                            logger.error("[XBrowserPoster] Could not find Write button")
                            page.screenshot(path=str(PROJECT_ROOT / "x_debug_no_write.png"))
                            context.close()
                            return False

                        # Wait for article editor to load
                        try:
                            page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        time.sleep(2)
                        logger.info(f"[XBrowserPoster] Article editor URL: {page.url}")

                        # Wait for article editor to fully render
                        logger.info("[XBrowserPoster] Waiting for article editor to load...")
                        time.sleep(5)

                        # STEP 1: Fill the title field - MUST be textarea, NOT contenteditable
                        # The title field has placeholder="Add a title"
                        logger.info("[XBrowserPoster] Looking for title textarea...")
                        title_filled = False

                        try:
                            # Wait explicitly for the textarea to appear
                            title_field = page.locator('textarea[placeholder*="title"]').first
                            title_field.wait_for(state="visible", timeout=10000)

                            # Human click then type (NOT fill — fill is instant and detectable)
                            _human_move_and_click(page, title_field)
                            time.sleep(random.uniform(0.5, 1.0))
                            _human_type(page, title, wpm=50)
                            title_filled = True
                            logger.info(f"[XBrowserPoster] ✅ Title typed: {title}")
                        except Exception as e:
                            logger.warning(f"[XBrowserPoster] Textarea not found, trying input: {e}")

                            # Fallback to input field
                            try:
                                title_field = page.locator('input[placeholder*="title"]').first
                                title_field.wait_for(state="visible", timeout=5000)
                                _human_move_and_click(page, title_field)
                                time.sleep(random.uniform(0.5, 1.0))
                                _human_type(page, title, wpm=50)
                                title_filled = True
                                logger.info(f"[XBrowserPoster] ✅ Title typed in input: {title}")
                            except Exception as e2:
                                logger.error(f"[XBrowserPoster] ❌ Could not find title field: {e2}")
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_no_title.png"))
                                context.close()
                                return False

                        time.sleep(random.uniform(0.5, 1.0))

                        # Dismiss any tweet compose popup that may have appeared
                        page.keyboard.press("Escape")
                        time.sleep(1)

                        # Close tweet compose overlays via JS
                        try:
                            page.evaluate("""
                                const layers = document.getElementById('layers');
                                if (layers) {
                                    layers.querySelectorAll('button[aria-label="Close"]').forEach(btn => btn.click());
                                }
                            """)
                        except Exception:
                            pass
                        time.sleep(0.5)

                        # Find and click the body editor directly (NOT via Tab which triggers tweet compose)
                        body_filled = False

                        # Use JS to find body contenteditable outside modal layers
                        try:
                            clicked = page.evaluate("""(() => {
                                const editables = document.querySelectorAll('div[contenteditable="true"]');
                                for (const el of editables) {
                                    if (el.closest('#layers')) continue;
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width === 0 || rect.height === 0) continue;
                                    el.click();
                                    el.focus();
                                    return true;
                                }
                                return false;
                            })()"""
                            )

                            if clicked:
                                time.sleep(0.5)

                                # Clear existing content
                                page.keyboard.press("Control+A")
                                page.keyboard.press("Delete")
                                time.sleep(0.3)

                                # Type body with rich text formatting
                                self._type_formatted_body(page, body)

                                body_filled = True
                                logger.info("[XBrowserPoster] Article body filled with formatting via JS click")
                        except Exception as e:
                            logger.warning(f"[XBrowserPoster] JS body click failed: {e}")

                        # Fallback: try Playwright selectors (skip elements inside #layers)
                        if not body_filled:
                            for sel in [
                                'div[contenteditable="true"][role="textbox"]',
                                '[class*="ProseMirror"]',
                                'div[contenteditable="true"]',
                            ]:
                                try:
                                    els = page.locator(sel)
                                    for idx in range(els.count()):
                                        el = els.nth(idx)
                                        if el.is_visible(timeout=2000):
                                            in_layers = el.evaluate("el => !!el.closest('#layers')")
                                            if in_layers:
                                                continue
                                            el.click(force=True)
                                            time.sleep(0.3)

                                            page.keyboard.press("Control+A")
                                            page.keyboard.press("Delete")
                                            time.sleep(0.3)

                                            # Type body with rich text formatting
                                            self._type_formatted_body(page, body)

                                            body_filled = True
                                            logger.info(f"[XBrowserPoster] Article body filled with formatting: {sel}")
                                            break
                                    if body_filled:
                                        break
                                except Exception:
                                    continue

                        if not body_filled:
                            logger.error("[XBrowserPoster] Could not find article body editor")
                            try:
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_article_body.png"))
                            except Exception:
                                pass
                            context.close()
                            return False

                        time.sleep(random.uniform(1, 2))

                        # Wait for editor to settle before publishing
                        time.sleep(2)

                        # STEP 1: Click the article Publish button (top-right blue button)
                        # IMPORTANT: Must click the one in the article editor, NOT any popup
                        publish_clicked = False

                        # Try specific data-testid selectors first
                        for sel in [
                            'button[data-testid="PostArticleButton"]',
                            'button[data-testid="publishButton"]',
                        ]:
                            try:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=3000):
                                    try:
                                        btn.click(timeout=3000)
                                    except Exception:
                                        btn.evaluate("el => el.click()")
                                    publish_clicked = True
                                    logger.info(f"[XBrowserPoster] Publish button clicked: {sel}")
                                    break
                            except Exception:
                                continue

                        # Fallback: find Publish button NOT inside #layers (modal)
                        if not publish_clicked:
                            try:
                                btns = page.locator('button:has-text("Publish")').all()
                                for btn in btns:
                                    try:
                                        if btn.is_visible(timeout=2000):
                                            in_layers = btn.evaluate("el => !!el.closest('#layers')")
                                            if not in_layers:
                                                try:
                                                    btn.click(timeout=3000)
                                                except Exception:
                                                    btn.evaluate("el => el.click()")
                                                publish_clicked = True
                                                logger.info("[XBrowserPoster] Publish button clicked (outside #layers)")
                                                break
                                    except Exception:
                                        continue
                            except Exception:
                                pass

                        if not publish_clicked:
                            logger.error("[XBrowserPoster] Could not find article Publish button")
                            try:
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_article_publish.png"))
                            except Exception:
                                pass
                            context.close()
                            return False

                        # Wait for confirmation dialog to appear
                        logger.info("[XBrowserPoster] Waiting for publish confirmation dialog...")
                        time.sleep(5)

                        # Take debug screenshot after first Publish click
                        try:
                            page.screenshot(path=str(PROJECT_ROOT / "x_debug_after_first_publish.png"))
                        except Exception:
                            pass

                        # Check if redirected to tweet composer (wrong button clicked)
                        current_url = page.url
                        if "/compose/post" in current_url:
                            logger.error(f"[XBrowserPoster] Wrong button! Redirected to tweet composer: {current_url}")
                            context.close()
                            return False

                        # STEP 2: Click Publish button inside the confirmation dialog
                        dialog_published = False

                        # Method 1: Publish button inside [role="dialog"]
                        try:
                            dialog_btn = page.locator('[role="dialog"] button:has-text("Publish")').first
                            if dialog_btn.is_visible(timeout=5000):
                                time.sleep(random.uniform(0.3, 0.7))
                                _human_move_and_click(page, dialog_btn)
                                dialog_published = True
                                logger.info("[XBrowserPoster] Clicked Publish in dialog (role=dialog)")
                        except Exception:
                            pass

                        # Method 2: Publish button inside #layers (dialog shows up in layers)
                        if not dialog_published:
                            try:
                                layers_btn = page.locator('#layers button:has-text("Publish")').first
                                if layers_btn.is_visible(timeout=3000):
                                    time.sleep(random.uniform(0.3, 0.7))
                                    _human_move_and_click(page, layers_btn)
                                    dialog_published = True
                                    logger.info("[XBrowserPoster] Clicked Publish in #layers")
                            except Exception:
                                pass

                        # Method 3: Find all Publish buttons, click the last one
                        if not dialog_published:
                            try:
                                all_publish = page.locator('button:has-text("Publish")').all()
                                logger.info(f"[XBrowserPoster] Found {len(all_publish)} Publish buttons total")
                                if len(all_publish) >= 2:
                                    time.sleep(random.uniform(0.3, 0.7))
                                    _human_move_and_click(page, all_publish[-1])
                                    dialog_published = True
                                    logger.info("[XBrowserPoster] Clicked last Publish button")
                            except Exception:
                                pass

                        if not dialog_published:
                            logger.warning("[XBrowserPoster] Could not find dialog Publish button")
                            try:
                                page.screenshot(path=str(PROJECT_ROOT / "x_debug_no_dialog.png"))
                            except Exception:
                                pass

                        # Wait for publish to complete
                        time.sleep(random.uniform(5, 8))
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass

                        final_url = page.url
                        logger.info(f"[XBrowserPoster] Final URL: {final_url}")

                        # Take final screenshot
                        try:
                            page.screenshot(path=str(PROJECT_ROOT / "x_debug_final_state.png"))
                        except Exception:
                            pass

                        if "compose/articles/edit" not in final_url:
                            logger.info("[XBrowserPoster] Article published successfully")
                        else:
                            logger.warning(f"[XBrowserPoster] Article may still be in draft (URL: {final_url})")
                        
                        if self.session_manager:
                            self.session_manager.state.mark_verified()
                        
                        context.close()
                        return True

                    except Exception as e:
                        logger.error(f"[XBrowserPoster] Article browser error: {e}")
                        try:
                            page.screenshot(path=str(PROJECT_ROOT / "x_debug_article_error.png"))
                        except Exception:
                            pass
                        context.close()
                        return False

            except Exception as e:
                logger.error(f"[XBrowserPoster] Playwright launch error: {e}")
                return False

    def post_article(self, title: str, body: str) -> Optional[str]:
        """
        Post a long-form article on X.

        Args:
            title: Article headline
            body: Article body text

        Returns:
            'article_posted' on success, None on failure
        """
        if not self.enabled:
            return None

        success = self._post_article_browser(title, body)
        
        if not success and self.auto_login:
            # Check if failure was due to session expiration
            if self.session_manager and not self.session_manager.is_session_healthy():
                logger.info("[XBrowserPoster] Session unhealthy - attempting recovery")
                if self._handle_session_expired():
                    # Retry posting with restored session
                    logger.info("[XBrowserPoster] Retrying article post with recovered session")
                    success = self._post_article_browser(title, body)
        
        self.log_post(f"[ARTICLE] {title}", success, {'type': 'article'})

        if success:
            return 'article_posted'
        return None

    def post_thread(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post a full thread to X using browser automation.

        Posts each tweet sequentially with jitter delays between them.
        Note: Browser mode posts individual tweets (not as replies to create
        a connected thread). For true threaded replies, use the API method.

        Args:
            thread_data: Dict with 'tweets' list, 'type', 'tweet_count'

        Returns:
            Dict with 'success', 'posted_count', 'error'
        """
        result = {
            'success': False,
            'posted_count': 0,
            'tweet_ids': [],
            'thread_url': None,
            'error': None,
        }

        if not self.enabled:
            result['error'] = 'XBrowserPoster not enabled'
            return result

        tweets = thread_data.get('tweets', [])
        if not tweets:
            result['error'] = 'No tweets to post'
            return result

        logger.info(f"[XBrowserPoster] Posting thread ({len(tweets)} tweets)...")

        for i, tweet_text in enumerate(tweets):
            tweet_text = tweet_text.strip()
            if not tweet_text:
                continue

            # Jitter delay between tweets (skip for first tweet)
            if i > 0:
                self._apply_jitter_delay()

            success = self._post_single_tweet_browser(tweet_text)
            self.log_post(tweet_text, success, thread_data)

            if success:
                result['posted_count'] += 1
                result['tweet_ids'].append(f'browser_posted_{i}')
                logger.info(f"[XBrowserPoster] [{i + 1}/{len(tweets)}] Posted")
            else:
                result['error'] = f'Failed at tweet {i + 1}/{len(tweets)}'
                logger.error(f"[XBrowserPoster] Thread broken at tweet {i + 1}")
                break

        non_empty = [t for t in tweets if t.strip()]
        result['success'] = result['posted_count'] == len(non_empty)

        status = "complete" if result['success'] else "partial"
        logger.info(
            f"[XBrowserPoster] Thread {status} "
            f"({result['posted_count']}/{len(non_empty)} tweets)"
        )

        return result

    def verify_session(self) -> bool:
        """
        Quick check that the browser session is still valid.

        Opens the browser, navigates to X home, checks we're not
        redirected to login. Closes immediately.
        """
        if not self.enabled:
            return False

        # Ensure virtual display is set for headless=False mode on Linux (Xvfb :99)
        if platform.system() == "Linux":
            os.environ.setdefault('DISPLAY', ':99')

        # Clear cached network state to avoid QUIC/ECH/DoH DNS corruption on VPS
        self._clear_network_state()

        try:
            with sync_playwright() as p:
                chrome_path = find_chrome_executable()
                launch_kwargs = dict(
                    headless=False,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        # VPS networking fixes:
                        # - NetworkServiceSandbox: Chrome sandbox isolates DNS on Linux VPS
                        # - EncryptedClientHello: ECH/DoH configs from Cloudflare get cached and break DNS
                        # - DnsOverHttpsUpgrade: prevent automatic DoH upgrade that VPS can't reach
                        '--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade',
                        '--disable-quic',  # QUIC/H3 alternative service cached from x.com causes DNS issues
                        '--no-zygote',
                    ],
                )
                if chrome_path:
                    launch_kwargs['executable_path'] = chrome_path
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    **launch_kwargs,
                )
                page = context.new_page()

                page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                time.sleep(3)

                url = page.url
                context.close()

                if "login" in url.lower() or "flow" in url.lower():
                    logger.warning("[XBrowserPoster] Session expired (redirected to login)")
                    return False

                logger.info("[XBrowserPoster] Session valid")
                return True

        except Exception as e:
            logger.error(f"[XBrowserPoster] Session check failed: {e}")
            return False

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Compatibility method - browser posting doesn't track rate limits externally."""
        return {
            'method': 'playwright_browser',
            'posts_this_window': 0,
            'posts_remaining': 50,
            'can_post': True,
        }
