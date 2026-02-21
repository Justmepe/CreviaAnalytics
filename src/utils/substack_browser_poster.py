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
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

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

    # ─── Core browser helpers ─────────────────────────────────────────

    def _navigate_and_check_login(self, page) -> bool:
        """
        Navigate to Substack home and verify we're logged in.
        Returns True if logged in, False if session expired.
        """
        logger.info("[SubstackBrowser] Navigating to Substack...")
        page.goto("https://substack.com/home", timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(random.uniform(2, 3))

        url = page.url
        if "login" in url.lower() or "auth" in url.lower():
            logger.error("[SubstackBrowser] Session expired! Run setup_substack_session.py")
            return False

        logger.info(f"[SubstackBrowser] Logged in, URL: {url}")
        return True

    def _click_create_new(self, page, option_text: str) -> bool:
        """
        Click the 'Create new' dropdown and select an option.

        Args:
            page: Playwright page
            option_text: 'Article', 'New note', or 'New chat thread'

        Returns True if the option was clicked successfully.
        """
        # Step 1: Find and click the "Create new" button
        create_btn = None
        for sel in [
            "button:has-text('Create new')",
            "button:has-text('Create')",
            "a:has-text('Create new')",
        ]:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=5000):
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

                for sel in [
                    "button:has-text('Create new')",
                    "button:has-text('Create')",
                    "a:has-text('Create new')",
                ]:
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
            return False

        # Click the dropdown
        create_btn.click()
        time.sleep(random.uniform(0.8, 1.5))

        # Step 2: Select the option from the dropdown menu
        option_clicked = False
        for sel in [
            f"a:has-text('{option_text}')",
            f"button:has-text('{option_text}')",
            f"div[role='menuitem']:has-text('{option_text}')",
            f"li:has-text('{option_text}')",
            f"span:has-text('{option_text}')",
        ]:
            try:
                opt = page.locator(sel).first
                if opt.is_visible(timeout=3000):
                    opt.click()
                    time.sleep(random.uniform(1.5, 2.5))
                    option_clicked = True
                    logger.info(f"[SubstackBrowser] Selected '{option_text}' from dropdown")
                    break
            except Exception:
                continue

        if not option_clicked:
            logger.error(f"[SubstackBrowser] Could not find '{option_text}' in dropdown")
            # Debug: log visible dropdown items
            try:
                items = page.locator("div[role='menuitem'], li, a").all()
                for item in items[:15]:
                    try:
                        if item.is_visible(timeout=200):
                            txt = item.text_content().strip()[:50]
                            if txt:
                                logger.debug(f"[SubstackBrowser] Dropdown item: '{txt}'")
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

    def _dismiss_overlays(self, page):
        """Remove backdrop/overlay elements that block clicks."""
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
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        headless=self.headless,
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → New note
                        if not self._click_create_new(page, "New note"):
                            # Fallback: try "What's on your mind?" button (reader view)
                            logger.info("[SubstackBrowser] Falling back to 'What's on your mind?' flow")
                            fallback_found = False
                            for sel in [
                                "button:has-text(\"What's on your mind\")",
                                "button:has-text('on your mind')",
                            ]:
                                try:
                                    btn = page.locator(sel).first
                                    if btn.is_visible(timeout=3000):
                                        btn.click()
                                        time.sleep(random.uniform(1.5, 2.5))
                                        fallback_found = True
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
                                            btn.click(force=True)
                                            post_clicked = True
                                            logger.info(f"[SubstackBrowser] Post clicked in {container_sel}")
                                            break
                                if post_clicked:
                                    break
                            except Exception:
                                continue

                        # Fallback: find Post button, skip dashboard nav buttons
                        if not post_clicked:
                            for sel in [
                                "button:has-text('Post')",
                                "button:has-text('Publish')",
                                "button[type='submit']:has-text('Post')",
                            ]:
                                try:
                                    btns = page.locator(sel)
                                    for i in range(btns.count()):
                                        btn = btns.nth(i)
                                        if btn.is_visible(timeout=1000) and btn.is_enabled():
                                            href = btn.get_attribute('data-href') or ''
                                            if '/share-center' in href or '/detail/' in href:
                                                continue
                                            self._dismiss_overlays(page)
                                            time.sleep(random.uniform(0.3, 0.5))
                                            btn.click(force=True)
                                            post_clicked = True
                                            logger.info(f"[SubstackBrowser] Clicked Post: {sel}")
                                            break
                                    if post_clicked:
                                        break
                                except Exception:
                                    continue

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
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        headless=self.headless,
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → Article
                        if not self._click_create_new(page, "Article"):
                            logger.error("[SubstackBrowser] Could not open Article editor")
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
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        self.session_dir,
                        headless=self.headless,
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()

                    try:
                        # Navigate and check login
                        if not self._navigate_and_check_login(page):
                            context.close()
                            return None

                        # Click Create new → New chat thread
                        if not self._click_create_new(page, "New chat thread"):
                            logger.error("[SubstackBrowser] Could not open chat thread editor")
                            self._screenshot_debug(page, "thread_no_editor")
                            context.close()
                            return None

                        # Wait for thread compose to load
                        time.sleep(random.uniform(2, 3))

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
