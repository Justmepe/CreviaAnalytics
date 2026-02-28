"""
Substack Browser-Based Poster using Playwright

Posts to Substack via the publisher dashboard's "Create new" dropdown:
  - Article: Long-form news articles and market analysis
  - New note: Short single notes
  - New chat thread: Thread-style multi-message content

Run setup_substack_session.py once to log in manually, then this module
reuses that session for all subsequent posts.
"""

import os
import re
import time
import json
import random
import logging
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

try:
    from patchright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False

# Project root
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SESSION_DIR = str(PROJECT_ROOT / "substack_browser_session")
NOTES_LOG_FILE = str(PROJECT_ROOT / "data" / "substack_notes_log.json")


class SubstackBrowserPoster:
    """
    Post to Substack using Playwright browser automation via the publisher
    dashboard's "Create new" dropdown menu.

    Supports three content types:
      - Article: Long-form content with title + body
      - Note: Short single-post notes
      - Chat thread: Multi-message thread content

    Uses a persistent Chromium session (substack_browser_session/) that stores
    cookies/login state. Run setup_substack_session.py once to log in manually.
    """

    MAX_NOTE_LENGTH = 5000
    MAX_ARTICLE_LENGTH = 50000

    def __init__(
        self,
        session_dir: Optional[str] = None,
        max_notes_per_day: int = None,
        headless: bool = True,
    ):
        self.session_dir = session_dir or SESSION_DIR
        self.max_notes_per_day = max_notes_per_day or int(
            os.getenv('SUBSTACK_MAX_NOTES_PER_DAY', '5')
        )
        self.headless = headless
        self.subdomain = os.getenv('SUBSTACK_SUBDOMAIN', 'petergikonyo')
        self.lock = Lock()

        # Rate limiting
        self._posts_today: List[str] = []
        self._load_notes_log()

        # Check prerequisites
        self.enabled = False
        self.authenticated = False

        if not HAS_PLAYWRIGHT:
            logger.warning("[SubstackBrowser] playwright not installed - disabled")
            return

        if not Path(self.session_dir).exists():
            logger.warning(
                f"[SubstackBrowser] Session dir not found: {self.session_dir}. "
                "Run setup_substack_session.py first."
            )
            return

        self.enabled = True
        logger.info("[SubstackBrowser] Initialized (Playwright browser automation)")

    # ─── Rate limiting / logging ──────────────────────────────────────

    def _load_notes_log(self):
        """Load today's post count from log."""
        try:
            log_path = Path(NOTES_LOG_FILE)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    data = json.load(f)
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                if data.get('date') == today:
                    self._posts_today = data.get('note_ids', [])
                else:
                    self._posts_today = []
        except Exception:
            self._posts_today = []

    def _save_notes_log(self):
        """Save today's post count to log."""
        try:
            log_path = Path(NOTES_LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'note_ids': self._posts_today,
            }
            with open(log_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _check_rate_limit(self) -> bool:
        """Check daily post limit."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        try:
            log_path = Path(NOTES_LOG_FILE)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    data = json.load(f)
                if data.get('date') != today:
                    self._posts_today = []
        except Exception:
            pass

        if len(self._posts_today) >= self.max_notes_per_day:
            logger.info(
                f"[SubstackBrowser] Rate limit: {len(self._posts_today)}/{self.max_notes_per_day} posts today"
            )
            return False
        return True

    def _record_post(self, post_id: str):
        """Record a successful post."""
        self._posts_today.append(post_id)
        self._save_notes_log()

    # ─── Browser launch helpers ───────────────────────────────────────

    def _kill_orphaned_chrome(self):
        """Kill any Chrome processes holding the session lock (Linux VPS only)."""
        if platform.system() != "Linux":
            return
        try:
            result = subprocess.run(
                ["pgrep", "-f", self.session_dir],
                capture_output=True, text=True, timeout=5
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], timeout=3)
                    logger.info(f"[SubstackBrowser] Killed orphaned Chrome PID {pid}")
                except Exception:
                    pass
            if pids:
                time.sleep(1)
        except Exception:
            pass

    def _clear_network_state(self):
        """Delete Chrome lock files and network cache before each launch."""
        session = Path(self.session_dir)
        for name in [
            "SingletonLock", "SingletonCookie", "SingletonSocket",
            "TransportSecurity", "NEL",
        ]:
            try:
                (session / name).unlink(missing_ok=True)
            except Exception:
                pass
        try:
            (session / "Default" / "LOCK").unlink(missing_ok=True)
        except Exception:
            pass

    def _get_launch_kwargs(self) -> dict:
        """Return common Playwright launch kwargs including VPS-compatible Chrome flags."""
        if platform.system() == "Linux":
            os.environ.setdefault('DISPLAY', ':99')
        args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-popup-blocking',
            '--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade',
            '--disable-quic',
            '--no-zygote',
            '--disable-gpu',
            '--disable-gpu-sandbox',
        ]
        return dict(
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            locale='en-US',
            ignore_default_args=['--enable-automation'],
            args=args,
        )

    # ─── Core browser helpers ─────────────────────────────────────────

    def _navigate_and_check_login(self, page) -> bool:
        """
        Navigate to the publisher dashboard first to verify the publisher session.
        Falls back to reader if publisher redirect fails (useful for note flow).
        Returns True if logged in, False if session expired.
        """
        logger.info("[SubstackBrowser] Navigating to publisher dashboard...")
        pub_url = f"https://{self.subdomain}.substack.com/publish"
        try:
            page.goto(pub_url, timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            time.sleep(random.uniform(2, 3))
        except Exception as nav_e:
            logger.error(f"[SubstackBrowser] Publisher nav failed: {nav_e}")
            return False

        url = page.url
        if "sign-in" in url.lower() or "login" in url.lower():
            logger.error(
                "[SubstackBrowser] Publisher session expired — run setup_substack_session.py "
                f"and log in at https://{self.subdomain}.substack.com/publish"
            )
            return False

        if "/publish" in url:
            logger.info(f"[SubstackBrowser] Publisher dashboard loaded: {url}")
            return True

        # Unexpected redirect — try reader as fallback (notes only need reader session)
        logger.warning(f"[SubstackBrowser] Publisher redirected to: {url} — checking reader session")
        try:
            page.goto("https://substack.com/home", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            time.sleep(random.uniform(1, 2))
        except Exception:
            pass
        url2 = page.url
        if "login" in url2.lower() or "auth" in url2.lower() or "sign-in" in url2.lower():
            logger.error("[SubstackBrowser] Reader session also expired")
            return False
        logger.info(f"[SubstackBrowser] Using reader session (publisher unavailable): {url2}")
        return True

    def _click_create_new(self, page, option_text: str) -> bool:
        """
        Click the 'Create new' dropdown and select an option.

        Args:
            page: Playwright page
            option_text: 'Article', 'New note', or 'New chat thread'

        Returns True if the option was clicked successfully.
        """
        # Dismiss any overlays before attempting to find the button
        self._dismiss_overlays(page)

        # Step 1: Find and click the "Create new" / "New post" button
        # Substack has used several labels over time: "Create new", "Create", "New", "New post"
        _CREATE_SELS = [
            "button:has-text('Create new')",
            "a:has-text('Create new')",
            "button:has-text('New post')",
            "button:has-text('Create')",
            "a:has-text('New post')",
            "[aria-label*='Create']",
            "[aria-label*='New post']",
            "button[class*='create']",
        ]
        create_btn = None
        for sel in _CREATE_SELS:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    create_btn = btn
                    logger.info(f"[SubstackBrowser] Found 'Create new': {sel}")
                    break
            except Exception:
                continue

        if not create_btn:
            logger.warning("[SubstackBrowser] 'Create new' button not found on current page")
            # Try navigating to publisher dashboard
            try:
                pub_url = f"https://{self.subdomain}.substack.com/publish"
                logger.info(f"[SubstackBrowser] Trying publisher dashboard: {pub_url}")
                page.goto(pub_url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                time.sleep(random.uniform(2, 3))
                self._dismiss_overlays(page)

                for sel in _CREATE_SELS:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=3000):
                            create_btn = btn
                            logger.info(f"[SubstackBrowser] Found on publisher dashboard: {sel}")
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.error(f"[SubstackBrowser] Publisher dashboard navigation failed: {e}")

        if not create_btn:
            logger.error("[SubstackBrowser] 'Create new' button not found anywhere")
            try:
                self._screenshot_debug(page, "create_new_not_found")
                # Log all visible buttons to diagnose the issue
                btns = page.locator("button").all()
                for b in btns[:20]:
                    try:
                        if b.is_visible(timeout=200):
                            logger.info(f"[SubstackBrowser] Visible button: '{b.text_content().strip()[:40]}'")
                    except Exception:
                        pass
            except Exception:
                pass
            return False

        # Click the dropdown
        try:
            create_btn.click()
        except Exception:
            create_btn.evaluate("el => el.click()")
        time.sleep(random.uniform(0.8, 1.5))

        # Step 2: Select the option from the dropdown menu
        # Substack periodically renames menu items — try all known aliases
        _ALIASES = {
            'Article':         ['Article', 'Post', 'New post', 'Story', 'Long-form'],
            'New chat thread': ['New chat thread', 'New chat', 'Chat thread', 'Chat', 'Thread'],
            'New note':        ['New note', 'Note', 'Short post'],
        }
        candidates = _ALIASES.get(option_text, [option_text])

        option_clicked = False
        for label in candidates:
            if option_clicked:
                break
            for sel in [
                f"a:has-text('{label}')",
                f"button:has-text('{label}')",
                f"div[role='menuitem']:has-text('{label}')",
                f"li:has-text('{label}')",
                f"span:has-text('{label}')",
            ]:
                try:
                    opt = page.locator(sel).first
                    if opt.is_visible(timeout=2000):
                        opt.click()
                        time.sleep(random.uniform(1.5, 2.5))
                        option_clicked = True
                        logger.info(f"[SubstackBrowser] Selected '{label}' (alias for '{option_text}')")
                        break
                except Exception:
                    continue

        if not option_clicked:
            logger.error(f"[SubstackBrowser] Could not find '{option_text}' in dropdown")
            # Log all visible dropdown items to diagnose future renames
            try:
                items = page.locator("div[role='menuitem'], li, a").all()
                for item in items[:20]:
                    try:
                        if item.is_visible(timeout=200):
                            txt = item.text_content().strip()[:60]
                            if txt:
                                logger.info(f"[SubstackBrowser] Dropdown item visible: '{txt}'")
                    except Exception:
                        pass
            except Exception:
                pass
            return False

        return True

    def _type_human_like(self, page, text: str, min_delay=0.02, max_delay=0.05):
        """Type text with human-like random delays between keystrokes."""
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(min_delay, max_delay))

    def _inject_session_cookies(self, context) -> None:
        """
        Auto-inject fresh Substack session cookie from SUBSTACK_SID env var.

        Called after every launch_persistent_context() so the session stays
        alive even if the browser profile's cookies get corrupted or rotated.
        Silently skips if the env var is not set.
        """
        sid = os.getenv("SUBSTACK_SID", "").strip().strip('"').strip("'")
        if not sid:
            return
        from datetime import timedelta
        cookie = {
            "name": "substack.sid",
            "value": sid,
            "domain": ".substack.com",
            "path": "/",
            "expires": int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp()),
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
        try:
            context.add_cookies([cookie])
            logger.info("[SubstackBrowser] Auto-injected SUBSTACK_SID from env")
        except Exception as e:
            logger.warning(f"[SubstackBrowser] Cookie auto-inject skipped: {e}")

    def _dismiss_overlays(self, page):
        """Remove backdrop/overlay elements and dismiss cookie banners."""
        # Disable backdrop pointer-events
        try:
            page.evaluate("""
                document.querySelectorAll('[class*="backdrop"]').forEach(el => {
                    if (getComputedStyle(el).pointerEvents !== 'none') {
                        el.style.pointerEvents = 'none';
                    }
                });
            """)
        except Exception:
            pass
        # Dismiss cookie policy / consent banners (blocks Post button clicks)
        for sel in [
            "button:has-text('Reject')",
            "button:has-text('Accept')",
            "button:has-text('I accept')",
            "button:has-text('Got it')",
            "button:has-text('OK')",
            "[class*='cookie'] button",
            "[id*='cookie'] button",
            "[class*='consent'] button",
        ]:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=400):
                    btn.evaluate("el => el.click()")
                    time.sleep(0.5)
                    break
            except Exception:
                continue

    def _screenshot_debug(self, page, name: str):
        """Save a debug screenshot."""
        try:
            path = str(PROJECT_ROOT / f"substack_debug_{name}.png")
            page.screenshot(path=path)
            logger.info(f"[SubstackBrowser] Debug screenshot: {path}")
        except Exception:
            pass

    # ─── Note posting (Create new → New note) ────────────────────────

    def _post_note_via_browser(self, note_text: str) -> Optional[str]:
        """
        Post a single note: Create new → New note → type → Post.
        Returns timestamp ID on success, None on failure.
        """
        with self.lock:
            try:
                self._kill_orphaned_chrome()
                self._clear_network_state()
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        **self._get_launch_kwargs(),
                    )
                    self._inject_session_cookies(context)
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → New note
                        if not self._click_create_new(page, "New note"):
                            # Fallback: navigate to Notes tab where compose box lives
                            logger.info("[SubstackBrowser] Falling back to Notes tab compose...")
                            try:
                                page.goto("https://substack.com/notes", timeout=30000)
                                page.wait_for_load_state("domcontentloaded", timeout=15000)
                                time.sleep(random.uniform(2, 3))
                            except Exception:
                                pass

                            # Try clicking the "Write a note" / "What's on your mind?" compose area
                            fallback_found = False
                            for sel in [
                                "button:has-text(\"What's on your mind\")",
                                "button:has-text('on your mind')",
                                "div[contenteditable='true'][placeholder]",
                                "[placeholder*='mind']",
                                "[placeholder*='note']",
                            ]:
                                try:
                                    btn = page.locator(sel).first
                                    if btn.is_visible(timeout=3000):
                                        btn.click()
                                        time.sleep(random.uniform(1.5, 2.5))
                                        fallback_found = True
                                        logger.info(f"[SubstackBrowser] Notes tab compose found: {sel}")
                                        break
                                except Exception:
                                    continue

                            if not fallback_found:
                                self._screenshot_debug(page, "note_no_compose")
                                context.close()
                                return None

                        # Wait for compose area to appear
                        time.sleep(random.uniform(1, 2))

                        # Find the compose text area
                        compose_el = None
                        for sel in [
                            "div[contenteditable='true']",
                            "div[role='textbox']",
                            "[class*='ProseMirror']",
                            "textarea",
                        ]:
                            try:
                                els = page.locator(sel)
                                if els.count() > 0 and els.first.is_visible(timeout=3000):
                                    compose_el = els.first
                                    logger.info(f"[SubstackBrowser] Note compose found: {sel}")
                                    break
                            except Exception:
                                continue

                        if not compose_el:
                            logger.error("[SubstackBrowser] Note compose area not found")
                            self._screenshot_debug(page, "note_compose_missing")
                            context.close()
                            return None

                        # Click and type the note
                        compose_el.click()
                        time.sleep(random.uniform(0.3, 0.5))

                        text = note_text[:self.MAX_NOTE_LENGTH]
                        self._type_human_like(page, text)
                        logger.info(f"[SubstackBrowser] Typed note: {text[:60]}...")
                        time.sleep(random.uniform(1, 2))

                        # Find and click Post button
                        post_clicked = False

                        # First try: find Post button in compose container
                        for container_sel in [
                            "div[class*='dialog']",
                            "div[class*='modal']",
                            "div[class*='editor']",
                            "div[class*='compose']",
                            "div[class*='textEditor']",
                            "div[data-state='open']",
                        ]:
                            try:
                                containers = page.locator(container_sel)
                                for ci in range(containers.count()):
                                    container = containers.nth(ci)
                                    if container.is_visible(timeout=500):
                                        btn = container.locator("button:has-text('Post')").first
                                        if btn.is_visible(timeout=500) and btn.is_enabled():
                                            self._dismiss_overlays(page)
                                            time.sleep(random.uniform(0.3, 0.5))
                                            try:
                                                btn.click(force=True)
                                            except Exception:
                                                btn.evaluate("el => el.click()")
                                            post_clicked = True
                                            logger.info(f"[SubstackBrowser] Post clicked in {container_sel}")
                                            break
                                if post_clicked:
                                    break
                            except Exception:
                                continue

                        # Fallback: find Post/Share/Publish button, skip nav buttons
                        if not post_clicked:
                            for sel in [
                                "button:has-text('Post')",
                                "button:has-text('Share')",
                                "button:has-text('Publish')",
                                "button[type='submit']",
                            ]:
                                try:
                                    btns = page.locator(sel)
                                    for i in range(btns.count()):
                                        btn = btns.nth(i)
                                        try:
                                            if not (btn.is_visible(timeout=1000) and btn.is_enabled()):
                                                continue
                                        except Exception:
                                            continue
                                        href = btn.get_attribute('data-href') or ''
                                        if '/share-center' in href or '/detail/' in href:
                                            continue
                                        # Skip navigation-level buttons (small text, large page area)
                                        txt = btn.text_content().strip().lower() if btn.text_content() else ''
                                        if txt in ('home', 'settings', 'stats', 'dashboard'):
                                            continue
                                        self._dismiss_overlays(page)
                                        time.sleep(random.uniform(0.3, 0.5))
                                        try:
                                            btn.click(force=True)
                                        except Exception:
                                            btn.evaluate("el => el.click()")
                                        post_clicked = True
                                        logger.info(f"[SubstackBrowser] Clicked Post ('{txt}'): {sel}")
                                        break
                                    if post_clicked:
                                        break
                                except Exception:
                                    continue

                        # Last resort: JS — find the submit/post button near the compose area
                        if not post_clicked:
                            try:
                                clicked = page.evaluate("""(() => {
                                    const btns = [...document.querySelectorAll('button')];
                                    const postBtn = btns.find(b => {
                                        const t = b.textContent.trim().toLowerCase();
                                        return (t === 'post' || t === 'share' || t === 'publish') && b.offsetParent !== null;
                                    });
                                    if (postBtn) { postBtn.click(); return true; }
                                    return false;
                                })()""")
                                if clicked:
                                    post_clicked = True
                                    logger.info("[SubstackBrowser] JS fallback: clicked Post/Share button")
                            except Exception:
                                pass

                        if not post_clicked:
                            logger.error("[SubstackBrowser] Post button not found for note")
                            self._screenshot_debug(page, "note_post_btn")
                            context.close()
                            return None

                        # Wait for confirmation
                        time.sleep(random.uniform(4, 6))

                        note_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_note')
                        logger.info(f"[SubstackBrowser] Note posted (ID: {note_id})")
                        context.close()
                        return note_id

                    except Exception as e:
                        logger.error(f"[SubstackBrowser] Note posting error: {e}")
                        self._screenshot_debug(page, "note_error")
                        context.close()
                        return None

            except Exception as e:
                logger.error(f"[SubstackBrowser] Playwright launch error: {e}")
                return None

    # ─── Article posting (Create new → Article) ──────────────────────

    def _post_article_via_browser(self, title: str, body: str) -> Optional[str]:
        """
        Post a long-form article: Create new → Article → fill title + body → Publish.
        Returns timestamp ID on success, None on failure.
        """
        with self.lock:
            try:
                self._kill_orphaned_chrome()
                self._clear_network_state()
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        **self._get_launch_kwargs(),
                    )
                    self._inject_session_cookies(context)
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → Article (with direct URL fallback)
                        if not self._click_create_new(page, "Article"):
                            logger.warning("[SubstackBrowser] Dropdown failed — trying direct editor URLs")
                            editor_found = False
                            # Substack has used several URL patterns for the post editor over time
                            direct_urls = [
                                f"https://{self.subdomain}.substack.com/publish/post",
                                f"https://{self.subdomain}.substack.com/publish/posts/new",
                                f"https://{self.subdomain}.substack.com/publish/new-post",
                                f"https://{self.subdomain}.substack.com/publish/p/new",
                            ]
                            for direct_url in direct_urls:
                                try:
                                    page.goto(direct_url, timeout=30000)
                                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                                    time.sleep(random.uniform(2, 3))
                                    cur = page.url
                                    # Accept any /publish/ URL that isn't just the dashboard home
                                    # (editor URLs contain /post, /posts, /p/, /edit/, or /new)
                                    is_editor = (
                                        '/publish/post' in cur
                                        or '/publish/posts' in cur
                                        or '/publish/p/' in cur
                                        or '/edit/' in cur
                                        or '/publish/new' in cur
                                    )
                                    is_dashboard_only = cur.rstrip('/').endswith('/publish')
                                    if is_editor or (
                                        '/publish' in cur
                                        and not is_dashboard_only
                                        and 'sign-in' not in cur
                                        and 'login' not in cur
                                    ):
                                        logger.info(f"[SubstackBrowser] Direct URL worked: {cur}")
                                        editor_found = True
                                        break
                                    logger.info(f"[SubstackBrowser] {direct_url} → {cur} (not an editor)")
                                except Exception as url_e:
                                    logger.warning(f"[SubstackBrowser] {direct_url} failed: {url_e}")
                                    continue
                            if not editor_found:
                                logger.error(f"[SubstackBrowser] All direct URLs failed. Last URL: {page.url}")
                                self._screenshot_debug(page, "article_no_editor")
                                context.close()
                                return None

                        # Wait for article editor to load
                        time.sleep(random.uniform(3, 5))
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                        except Exception:
                            pass

                        logger.info(f"[SubstackBrowser] Article editor URL: {page.url}")

                        # Find and fill the title field
                        title_filled = False
                        for sel in [
                            "textarea[placeholder*='Title']",
                            "input[placeholder*='Title']",
                            "div[data-placeholder*='Title']",
                            "h1[contenteditable='true']",
                            "div[role='textbox'][aria-label*='title' i]",
                            "[class*='post-title'] textarea",
                            "[class*='post-title'] input",
                            "[class*='title'] textarea",
                            "[class*='title'] div[contenteditable='true']",
                        ]:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible(timeout=3000):
                                    el.click()
                                    time.sleep(0.3)
                                    # Use fill for input/textarea, keyboard for contenteditable
                                    tag = el.evaluate("el => el.tagName.toLowerCase()")
                                    if tag in ('input', 'textarea'):
                                        el.fill(title)
                                    else:
                                        self._type_human_like(page, title)
                                    title_filled = True
                                    logger.info(f"[SubstackBrowser] Title filled: {sel}")
                                    break
                            except Exception:
                                continue

                        if not title_filled:
                            logger.error("[SubstackBrowser] Could not find article title field")
                            self._screenshot_debug(page, "article_title")
                            context.close()
                            return None

                        time.sleep(random.uniform(0.5, 1.0))

                        # Find and fill the body/content area
                        body_filled = False

                        # Press Tab to move to body area from title
                        page.keyboard.press("Tab")
                        time.sleep(random.uniform(0.5, 1.0))

                        # Look for the body editor
                        for sel in [
                            "[class*='ProseMirror']",
                            "div[contenteditable='true'][class*='body']",
                            "div[contenteditable='true'][role='textbox']",
                            "div[contenteditable='true']",
                        ]:
                            try:
                                els = page.locator(sel)
                                # Skip the title field, find the body editor
                                for i in range(els.count()):
                                    el = els.nth(i)
                                    if el.is_visible(timeout=2000):
                                        # Check it's not the title by its content
                                        current_text = el.text_content().strip()
                                        if title in current_text:
                                            continue  # This is the title, skip
                                        el.click()
                                        time.sleep(0.3)

                                        # Type the body content
                                        body_text = body[:self.MAX_ARTICLE_LENGTH]
                                        # For articles, type in chunks (faster than char-by-char)
                                        # Split by paragraphs and type each
                                        paragraphs = body_text.split('\n\n')
                                        for j, para in enumerate(paragraphs):
                                            if j > 0:
                                                page.keyboard.press("Enter")
                                                page.keyboard.press("Enter")
                                                time.sleep(0.1)
                                            # Type paragraph with slight delay
                                            self._type_human_like(page, para, 0.01, 0.03)
                                            time.sleep(random.uniform(0.1, 0.3))

                                        body_filled = True
                                        logger.info(f"[SubstackBrowser] Body filled: {sel} (idx {i})")
                                        break
                                if body_filled:
                                    break
                            except Exception:
                                continue

                        if not body_filled:
                            logger.error("[SubstackBrowser] Could not find article body editor")
                            self._screenshot_debug(page, "article_body")
                            context.close()
                            return None

                        time.sleep(random.uniform(1, 2))

                        # Click Publish / Continue button
                        publish_clicked = False

                        # Step 1: Click the initial "Publish" or "Continue" button
                        for sel in [
                            "button:has-text('Publish')",
                            "button:has-text('Continue')",
                            "button:has-text('Save & publish')",
                        ]:
                            try:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=3000) and btn.is_enabled():
                                    self._dismiss_overlays(page)
                                    btn.click(force=True)
                                    time.sleep(random.uniform(2, 3))
                                    publish_clicked = True
                                    logger.info(f"[SubstackBrowser] Clicked: {sel}")
                                    break
                            except Exception:
                                continue

                        if not publish_clicked:
                            logger.error("[SubstackBrowser] Publish button not found")
                            self._screenshot_debug(page, "article_publish")
                            context.close()
                            return None

                        # Step 2: Handle confirmation dialog (if present)
                        # Substack shows "Send to everyone now" for articles
                        time.sleep(random.uniform(1, 2))

                        # Step 2a: Select "Publish" mode if there's a toggle/radio/tab
                        # (Substack may default to "Save as draft")
                        publish_mode_set = False

                        # Try radio buttons, tabs, or toggles for "Publish" option
                        for sel in [
                            "input[type='radio'][value*='publish' i]",
                            "label:has-text('Publish now'):not(:has-text('Send'))",
                            "[role='tab']:has-text('Publish'):not([aria-selected='true'])",
                            "button[aria-selected='false']:has-text('Publish')",
                        ]:
                            try:
                                elem = page.locator(sel).first
                                if elem.is_visible(timeout=2000):
                                    self._dismiss_overlays(page)
                                    elem.click(force=True)
                                    time.sleep(random.uniform(0.5, 1))
                                    publish_mode_set = True
                                    logger.info(f"[SubstackBrowser] Selected publish mode: {sel}")
                                    break
                            except Exception:
                                continue

                        # Try unchecking "Save as draft" checkbox if present
                        if not publish_mode_set:
                            for sel in [
                                "input[type='checkbox']:checked + label:has-text('draft' i)",
                                "input[type='checkbox']:checked[value*='draft' i]",
                            ]:
                                try:
                                    elem = page.locator(sel).first
                                    if elem.is_visible(timeout=2000) and elem.is_checked():
                                        self._dismiss_overlays(page)
                                        elem.click(force=True)
                                        time.sleep(random.uniform(0.5, 1))
                                        publish_mode_set = True
                                        logger.info(f"[SubstackBrowser] Unchecked draft mode: {sel}")
                                        break
                                except Exception:
                                    continue

                        if publish_mode_set:
                            logger.info("[SubstackBrowser] Publish mode activated")

                        # Step 2b: Click the send/publish button
                        url_before = page.url
                        publish_confirmed = False

                        for sel in [
                            "button:has-text('Send to everyone now')",  # CORRECT for articles
                            "button:has-text('Publish now')",
                            "button:has-text('Publish')",
                            "button:has-text('Confirm')",
                            "button:has-text('Send')",
                        ]:
                            try:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=3000) and btn.is_enabled():
                                    self._dismiss_overlays(page)
                                    btn.click(force=True)
                                    logger.info(f"[SubstackBrowser] Clicked publish button: {sel}")
                                    publish_confirmed = True
                                    break
                            except Exception:
                                continue

                        if not publish_confirmed:
                            logger.error("[SubstackBrowser] No publish button found!")
                            self._screenshot_debug(page, "no_publish_button")
                            context.close()
                            return None

                        # Wait for page navigation or confirmation
                        time.sleep(random.uniform(3, 5))

                        # Check if URL changed (redirect to posts list = success)
                        url_after = page.url
                        logger.info(f"[SubstackBrowser] URL before: {url_before}")
                        logger.info(f"[SubstackBrowser] URL after: {url_after}")

                        if '/publish/posts' in url_after:
                            logger.info("[SubstackBrowser] ✅ Redirected to posts list - PUBLISHED!")
                        elif '/publish/post' in url_after and '/publish/post' in url_before:
                            logger.info("[SubstackBrowser] Still on editor - checking for second confirmation dialog...")

                            # Step 2c: Handle "Add subscribe buttons" dialog (appears after "Send to everyone now")
                            # This is the missing step that prevents articles from publishing!
                            time.sleep(2)  # Wait for dialog to appear

                            subscribe_dialog_handled = False
                            for sel in [
                                "button:has-text('Publish without buttons')",  # Preferred: skip subscribe buttons
                                "button:has-text('Add subscribe buttons')",    # Alternative: add buttons then publish
                                "button:has-text('Continue')",                  # Generic continue button
                            ]:
                                try:
                                    btn = page.locator(sel).first
                                    if btn.is_visible(timeout=3000):
                                        logger.info(f"[SubstackBrowser] Found second confirmation: {sel}")
                                        btn.click(force=True)
                                        logger.info(f"[SubstackBrowser] Clicked: {sel}")
                                        subscribe_dialog_handled = True

                                        # Wait for URL to change (redirect to posts list)
                                        try:
                                            page.wait_for_url("**/publish/posts**", timeout=15000)
                                            logger.info("[SubstackBrowser] ✅ Article PUBLISHED - redirected to posts list!")
                                        except:
                                            # Fallback: check URL manually after waiting
                                            time.sleep(5)
                                            url_final = page.url
                                            logger.info(f"[SubstackBrowser] URL after second confirmation: {url_final}")

                                            if '/publish/posts' in url_final or '/publish/post/' not in url_final:
                                                logger.info("[SubstackBrowser] ✅ Article appears to be published!")
                                            else:
                                                logger.warning(f"[SubstackBrowser] Still on: {url_final}")
                                                self._screenshot_debug(page, "after_second_confirmation")
                                        break
                                except:
                                    continue

                            if not subscribe_dialog_handled:
                                logger.warning("[SubstackBrowser] No second confirmation dialog found!")
                                self._screenshot_debug(page, "no_second_dialog")

                        # Wait a bit more for any final processing
                        time.sleep(random.uniform(2, 3))

                        article_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_article')
                        logger.info(f"[SubstackBrowser] Article ID: {article_id}")
                        context.close()
                        return article_id

                    except Exception as e:
                        logger.error(f"[SubstackBrowser] Article posting error: {e}")
                        self._screenshot_debug(page, "article_error")
                        context.close()
                        return None

            except Exception as e:
                logger.error(f"[SubstackBrowser] Playwright launch error: {e}")
                return None

    # ─── Chat thread posting (Create new → New chat thread) ──────────

    def _post_chat_thread_via_browser(self, title: str, messages: List[str]) -> Optional[str]:
        """
        Post a chat thread: Create new → New chat thread → fill title + messages → Post.
        Returns timestamp ID on success, None on failure.
        """
        with self.lock:
            try:
                self._kill_orphaned_chrome()
                self._clear_network_state()
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        **self._get_launch_kwargs(),
                    )
                    self._inject_session_cookies(context)
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → New chat thread
                        self._click_create_new(page, "New chat thread")
                        time.sleep(random.uniform(2, 3))

                        # Verify we landed on the publication chat page (not reader inbox)
                        # If dropdown navigated to wrong place, go directly to publish/chat
                        current_url = page.url
                        if "/publish/chat" not in current_url and f"{self.subdomain}.substack.com/chat" not in current_url:
                            logger.info(f"[SubstackBrowser] Chat dropdown went to wrong URL ({current_url}), navigating directly to publish/chat...")
                            try:
                                page.goto(f"https://{self.subdomain}.substack.com/publish/chat", timeout=30000)
                                page.wait_for_load_state("domcontentloaded", timeout=15000)
                                time.sleep(random.uniform(2, 3))
                            except Exception as nav_e:
                                logger.error(f"[SubstackBrowser] Publish chat nav failed: {nav_e}")
                                context.close()
                                return None

                        self._dismiss_overlays(page)

                        # Fill the thread title/topic if there's a title field
                        for sel in [
                            "textarea[placeholder*='title' i]",
                            "textarea[placeholder*='topic' i]",
                            "input[placeholder*='title' i]",
                            "input[placeholder*='topic' i]",
                            "div[data-placeholder*='title' i]",
                            "div[data-placeholder*='topic' i]",
                        ]:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible(timeout=2000):
                                    el.click()
                                    time.sleep(0.3)
                                    tag = el.evaluate("el => el.tagName.toLowerCase()")
                                    if tag in ('input', 'textarea'):
                                        el.fill(title)
                                    else:
                                        self._type_human_like(page, title)
                                    logger.info(f"[SubstackBrowser] Thread title filled: {sel}")
                                    time.sleep(random.uniform(0.5, 1.0))
                                    break
                            except Exception:
                                continue

                        # Find the message compose area
                        compose_el = None
                        for sel in [
                            "div[contenteditable='true']",
                            "div[role='textbox']",
                            "[class*='ProseMirror']",
                            "textarea",
                        ]:
                            try:
                                els = page.locator(sel)
                                # Get the last visible one (likely the message input, not title)
                                for i in range(els.count() - 1, -1, -1):
                                    el = els.nth(i)
                                    if el.is_visible(timeout=2000):
                                        compose_el = el
                                        logger.info(f"[SubstackBrowser] Thread compose found: {sel} (idx {i})")
                                        break
                                if compose_el:
                                    break
                            except Exception:
                                continue

                        if not compose_el:
                            logger.error("[SubstackBrowser] Thread compose area not found")
                            self._screenshot_debug(page, "thread_compose_missing")
                            context.close()
                            return None

                        # Type the first message (combine all messages into one if needed)
                        compose_el.click()
                        time.sleep(random.uniform(0.3, 0.5))

                        # Join messages with paragraph breaks
                        full_text = "\n\n".join(messages)
                        if len(full_text) > self.MAX_NOTE_LENGTH:
                            full_text = full_text[:self.MAX_NOTE_LENGTH - 3] + "..."

                        self._type_human_like(page, full_text)
                        logger.info(f"[SubstackBrowser] Typed thread: {full_text[:60]}...")
                        time.sleep(random.uniform(1, 2))

                        # Find and click Post/Start button
                        post_clicked = False
                        for sel in [
                            "button:has-text('Start thread')",
                            "button:has-text('Post')",
                            "button:has-text('Publish')",
                            "button:has-text('Start')",
                            "button[type='submit']",
                        ]:
                            try:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=2000) and btn.is_enabled():
                                    self._dismiss_overlays(page)
                                    time.sleep(random.uniform(0.3, 0.5))
                                    btn.click(force=True)
                                    post_clicked = True
                                    logger.info(f"[SubstackBrowser] Clicked: {sel}")
                                    break
                            except Exception:
                                continue

                        if not post_clicked:
                            logger.error("[SubstackBrowser] Post button not found for thread")
                            self._screenshot_debug(page, "thread_post_btn")
                            context.close()
                            return None

                        # Handle Send confirmation dialog
                        time.sleep(random.uniform(2, 3))
                        for sel in [
                            "button:has-text('Send')",
                            "button:has-text('Post')",
                            "button:has-text('Confirm')",
                        ]:
                            try:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=3000):
                                    self._dismiss_overlays(page)
                                    btn.click(force=True)
                                    logger.info(f"[SubstackBrowser] Thread confirmed: {sel}")
                                    break
                            except Exception:
                                continue

                        # Wait for confirmation
                        time.sleep(random.uniform(4, 6))

                        thread_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_thread')
                        logger.info(f"[SubstackBrowser] Chat thread posted (ID: {thread_id})")
                        context.close()
                        return thread_id

                    except Exception as e:
                        logger.error(f"[SubstackBrowser] Thread posting error: {e}")
                        self._screenshot_debug(page, "thread_error")
                        context.close()
                        return None

            except Exception as e:
                logger.error(f"[SubstackBrowser] Playwright launch error: {e}")
                return None

    # ─── Public API ───────────────────────────────────────────────────

    def post_note(self, body_text: str) -> Optional[str]:
        """
        Post a short text note to Substack (Create new → New note).

        Args:
            body_text: Plain text content for the note

        Returns:
            post_id string or None on failure
        """
        if not self.enabled:
            return None
        if not self._check_rate_limit():
            return None

        post_id = self._post_note_via_browser(body_text)
        if post_id:
            self._record_post(post_id)
        return post_id

    def post_article(self, title: str, body: str) -> Optional[str]:
        """
        Post a long-form article to Substack (Create new → Article).

        Args:
            title: Article title/headline
            body: Full article body text

        Returns:
            post_id string or None on failure
        """
        if not self.enabled:
            return None
        if not self._check_rate_limit():
            return None

        post_id = self._post_article_via_browser(title, body)
        if post_id:
            self._record_post(post_id)
        return post_id

    def post_chat_thread(self, title: str, messages: List[str]) -> Optional[str]:
        """
        Post a chat thread to Substack (Create new → New chat thread).

        Args:
            title: Thread title/topic
            messages: List of message strings for the thread

        Returns:
            post_id string or None on failure
        """
        if not self.enabled:
            return None
        if not self._check_rate_limit():
            return None

        post_id = self._post_chat_thread_via_browser(title, messages)
        if post_id:
            self._record_post(post_id)
        return post_id

    def post_memo_as_note(
        self, ticker: str, memo: str, current_price: Optional[float] = None
    ) -> Optional[str]:
        """
        Post a market memo as a short Substack Note.

        For mid-day and closing bell updates - short form content.
        """
        if not self.enabled:
            return None

        # Build note text (short format with ticker/price prefix)
        if current_price:
            note_text = f"📊 {ticker} @ ${current_price:,.2f}\n\n{memo}"
        else:
            note_text = f"📊 {ticker} Update\n\n{memo}"

        # Add engagement footer (keep it short for notes)
        note_text += f"\n\n💭 What's your take on {ticker}?"

        return self.post_note(note_text)

    def post_thread_as_note(self, thread_data: dict) -> Optional[str]:
        """
        Post a thread as a Substack Chat Thread.

        Thread data with multiple tweets → routed to New chat thread.
        """
        if not self.enabled:
            return None

        tweets = thread_data.get("tweets", [])
        if not tweets:
            return None

        # Clean up tweet text
        messages = []
        for tweet in tweets:
            clean = re.sub(r'^\d+/\s*', '', tweet).strip()
            clean = re.sub(r'#\w+', '', clean).strip()
            if clean:
                messages.append(clean)

        if not messages:
            return None

        # Build title from first tweet
        title = messages[0][:80]
        if len(messages[0]) > 80:
            title = title[:77] + "..."

        # Add footer to last message
        messages.append(f"Full thread with {len(tweets)} insights at creviaanalytics.com")

        return self.post_chat_thread(title, messages)

    def verify_credentials(self) -> bool:
        """Verify the browser session is still valid."""
        if not self.enabled:
            return False

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 900},
                )
                self._inject_session_cookies(context)
                page = context.new_page()

                page.goto("https://substack.com/home", timeout=20000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(2)

                url = page.url
                if "login" in url.lower() or "auth" in url.lower():
                    logger.warning("[SubstackBrowser] Session expired")
                    context.close()
                    return False

                # Check for publisher indicators
                logged_in = False
                for sel in [
                    "button:has-text('Create new')",
                    "button:has-text('Create')",
                    "button:has-text('on your mind')",
                ]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=3000):
                            logged_in = True
                            logger.info(f"[SubstackBrowser] Login confirmed via: {sel}")
                            break
                    except Exception:
                        continue

                context.close()

                if logged_in:
                    self.authenticated = True
                    return True

                logger.warning(f"[SubstackBrowser] Could not verify login at: {url}")
                return False

        except Exception as e:
            logger.error(f"[SubstackBrowser] Session check failed: {e}")
            return False

    def close(self):
        """No persistent resources to close."""
        pass
