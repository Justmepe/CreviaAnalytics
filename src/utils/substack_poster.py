"""
SubstackPoster — Post notes to Substack using unofficial web API.

Three classes:
1. NoteBuilder   — Builds ProseMirror-compatible JSON documents for Notes
2. ContentTransformer — Adapts engine content (tweets/memos) to Substack tone
3. SubstackPoster — Main poster: auth, cookie persistence, rate limiting

Auth: email/password login → session cookies (stored in data/substack_cookies.json)
Rate limit: self-imposed max N notes/day with jitter delays
"""

import os
import re
import json
import time
import random
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import requests

# Import Playwright auth (optional, for browser automation fallback)
try:
    from .substack_playwright_auth import authenticate_substack
    HAS_PLAYWRIGHT_AUTH = True
except ImportError:
    HAS_PLAYWRIGHT_AUTH = False

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / 'data'
COOKIE_FILE = DATA_DIR / 'substack_cookies.json'
NOTES_LOG_FILE = DATA_DIR / 'substack_notes_log.json'


# =============================================================================
# 1. NoteBuilder — ProseMirror JSON for Substack Notes
# =============================================================================

class NoteBuilder:
    """
    Builds a ProseMirror-compatible JSON document for Substack Notes.

    Substack Notes uses a subset of ProseMirror schema:
    - doc → { type: "doc", content: [...] }
    - paragraph → { type: "paragraph", content: [{ type: "text", text: "..." }] }
    - text with marks → { type: "text", text: "...", marks: [{ type: "bold" }] }
    - hard_break → { type: "hard_break" }
    """

    def __init__(self):
        self.content: List[dict] = []

    def add_paragraph(self, text: str, bold: bool = False) -> 'NoteBuilder':
        """Add a paragraph node."""
        if not text:
            # Empty paragraph (line break)
            self.content.append({"type": "paragraph"})
            return self

        text_node: Dict[str, Any] = {"type": "text", "text": text}
        if bold:
            text_node["marks"] = [{"type": "bold"}]

        self.content.append({
            "type": "paragraph",
            "content": [text_node]
        })
        return self

    def add_rich_paragraph(self, parts: List[Dict[str, Any]]) -> 'NoteBuilder':
        """
        Add a paragraph with mixed formatting.

        parts: list of dicts like:
          {"text": "Hello", "bold": True}
          {"text": " world"}
          {"text": "link text", "href": "https://..."}
        """
        content = []
        for part in parts:
            node: Dict[str, Any] = {"type": "text", "text": part["text"]}
            marks = []
            if part.get("bold"):
                marks.append({"type": "bold"})
            if part.get("italic"):
                marks.append({"type": "italic"})
            if part.get("href"):
                marks.append({"type": "link", "attrs": {"href": part["href"]}})
            if marks:
                node["marks"] = marks
            content.append(node)

        self.content.append({"type": "paragraph", "content": content})
        return self

    def build(self) -> dict:
        """Return the final ProseMirror document."""
        return {
            "type": "doc",
            "content": self.content
        }

    def build_json(self) -> str:
        """Return the document as a JSON string."""
        return json.dumps(self.build())


# =============================================================================
# 2. ContentTransformer — Adapt engine content for Substack
# =============================================================================

class ContentTransformer:
    """
    Transforms engine-generated content (tweets, memos, threads)
    into Substack Notes format.

    Key adaptations:
    - Strip hashtags (Substack isn't Twitter)
    - Make tone conversational/analytical (not clickbaity)
    - Add engagement hooks ("What's your take?")
    - Respect 5000-char Note limit
    """

    MAX_NOTE_LENGTH = 5000

    @staticmethod
    def _strip_hashtags(text: str) -> str:
        """Remove #hashtags from text."""
        return re.sub(r'#\w+', '', text).strip()

    @staticmethod
    def _strip_emojis_excess(text: str) -> str:
        """Reduce emoji density (keep max 3)."""
        # Find all emoji sequences
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U0001f900-\U0001f9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "]+", flags=re.UNICODE
        )
        emojis_found = emoji_pattern.findall(text)
        if len(emojis_found) > 3:
            # Keep only the first 3 emoji occurrences
            count = 0
            def replacer(match):
                nonlocal count
                count += 1
                return match.group() if count <= 3 else ''
            text = emoji_pattern.sub(replacer, text)
        return text

    @classmethod
    def transform_memo(cls, ticker: str, memo: str,
                       current_price: Optional[float] = None) -> str:
        """
        Transform a market memo into a Substack Note.

        Keeps analytical tone, strips hashtags, adds price context.
        """
        text = cls._strip_hashtags(memo)
        text = cls._strip_emojis_excess(text)

        # Add price header if available
        if current_price:
            header = f"{ticker} @ ${current_price:,.2f}\n\n"
            text = header + text

        # Add engagement hook
        hooks = [
            f"\n\nWhat's your outlook on {ticker}?",
            f"\n\nAgree or disagree? Let me know below.",
            f"\n\nFull analysis on creviaanalytics.com",
            f"\n\nMore at creviaanalytics.com",
        ]
        text += random.choice(hooks)

        # Truncate if needed
        if len(text) > cls.MAX_NOTE_LENGTH:
            text = text[:cls.MAX_NOTE_LENGTH - 3] + '...'

        return text

    @classmethod
    def transform_news_tweet(cls, tweet_text: str) -> str:
        """
        Expand a 280-char tweet into a 500-1000 char Substack Note.

        Since the tweet is already concise, we add context and
        remove Twitter-specific formatting.
        """
        text = cls._strip_hashtags(tweet_text)
        text = cls._strip_emojis_excess(text)

        # Add a brief intro
        text = f"{text}\n\nFollow for real-time crypto market intelligence."

        return text

    @classmethod
    def transform_thread_to_note(cls, thread_data: dict) -> str:
        """
        Condense a multi-tweet thread into a single Substack Note.

        Takes the first 3-4 tweets (the hook + key points), joins
        them into a flowing narrative, drops thread numbering.
        """
        tweets = thread_data.get('tweets', [])
        if not tweets:
            return ''

        # Take first 4 tweets for the note (hook + main points)
        selected = tweets[:4]

        parts = []
        for tweet in selected:
            # Strip thread numbering (1/, 2/, etc.)
            clean = re.sub(r'^\d+/\s*', '', tweet).strip()
            clean = cls._strip_hashtags(clean)
            clean = cls._strip_emojis_excess(clean)
            if clean:
                parts.append(clean)

        text = '\n\n'.join(parts)

        # Add CTA
        text += f"\n\nFull thread with {len(tweets)} insights at creviaanalytics.com"

        if len(text) > cls.MAX_NOTE_LENGTH:
            text = text[:cls.MAX_NOTE_LENGTH - 3] + '...'

        return text


# =============================================================================
# 3. SubstackPoster — Main poster class
# =============================================================================

class SubstackPoster:
    """
    Post notes to Substack using unofficial web endpoints.

    Follows the same pattern as XPoster/DiscordNotifier/WebPublisher:
    - Constructor reads env vars
    - enabled flag
    - post methods return result or None
    - verify_credentials() for startup check

    Auth methods (in priority order):
    1. Saved cookies from data/substack_cookies.json (persists across restarts)
    2. SUBSTACK_SID env var (manual cookie from browser DevTools)
    3. Password login (may be blocked by CAPTCHA)

    To get SUBSTACK_SID:
    1. Login to substack.com in your browser
    2. Open DevTools → Application → Cookies → substack.com
    3. Copy the value of 'substack.sid' cookie
    4. Set SUBSTACK_SID=<value> in .env

    Cookie persistence: saved to data/substack_cookies.json
    Rate limit: self-imposed max N notes/day with random jitter
    """

    BASE_URL = 'https://substack.com'

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        subdomain: Optional[str] = None,
        max_notes_per_day: int = None,
    ):
        self.email = email or os.getenv('SUBSTACK_EMAIL', '')
        self.password = password or os.getenv('SUBSTACK_PASSWORD', '')
        self.subdomain = subdomain or os.getenv('SUBSTACK_SUBDOMAIN', 'creviaanalytics')
        self.max_notes_per_day = max_notes_per_day or int(os.getenv('SUBSTACK_MAX_NOTES_PER_DAY', '5'))
        self.substack_sid = os.getenv('SUBSTACK_SID', '')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

        # Enabled if we have any auth method available
        self.enabled = bool(self.substack_sid or (self.email and self.password))
        self.authenticated = False
        self.publication_id = os.getenv('SUBSTACK_PUBLICATION_ID')  # Can be cached in env

        # Rate limiting state
        self._notes_today: List[str] = []  # timestamps of notes posted today
        self._load_notes_log()

        if not self.enabled:
            logger.info("[SubstackPoster] Not configured (set SUBSTACK_SID or EMAIL+PASSWORD)")

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _load_cookies(self) -> bool:
        """Load session cookies from disk."""
        try:
            if COOKIE_FILE.exists():
                with open(COOKIE_FILE, 'r') as f:
                    cookie_data = json.load(f)
                for name, value in cookie_data.get('cookies', {}).items():
                    self.session.cookies.set(name, value, domain='.substack.com')
                self.publication_id = cookie_data.get('publication_id')
                logger.info("[SubstackPoster] Loaded saved cookies")
                return True
        except Exception as e:
            logger.warning(f"[SubstackPoster] Failed to load cookies: {e}")
        return False

    def _save_cookies(self):
        """Save session cookies to disk."""
        try:
            DATA_DIR.mkdir(exist_ok=True)
            cookie_data = {
                'cookies': {c.name: c.value for c in self.session.cookies},
                'publication_id': self.publication_id,
                'saved_at': datetime.now(timezone.utc).isoformat(),
            }
            with open(COOKIE_FILE, 'w') as f:
                json.dump(cookie_data, f)
            logger.info("[SubstackPoster] Cookies saved")
        except Exception as e:
            logger.warning(f"[SubstackPoster] Failed to save cookies: {e}")

    def _apply_sid_cookie(self) -> bool:
        """Apply the SUBSTACK_SID env var as a session cookie."""
        if not self.substack_sid:
            return False
        self.session.cookies.set('substack.sid', self.substack_sid, domain='.substack.com')
        logger.info("[SubstackPoster] Applied SUBSTACK_SID cookie")
        return True

    def _login(self) -> bool:
        """Login to Substack with email/password."""
        if not self.email or not self.password:
            return False
        try:
            url = f'{self.BASE_URL}/api/v1/login'
            payload = {
                'email': self.email,
                'password': self.password,
                'for_pub': self.subdomain,
            }
            resp = self.session.post(url, json=payload, timeout=15)

            if resp.status_code == 200:
                logger.info("[SubstackPoster] Login successful")
                self._save_cookies()
                return True
            elif resp.status_code in (400, 401):
                body = resp.text[:300]
                if 'captcha' in body.lower():
                    logger.warning("[SubstackPoster] Login blocked by CAPTCHA")
                    logger.warning("[SubstackPoster] Use SUBSTACK_SID instead: login in browser, copy substack.sid cookie")
                else:
                    logger.warning(f"[SubstackPoster] Login failed ({resp.status_code}): {body}")
                return False
            else:
                logger.warning(f"[SubstackPoster] Login failed: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"[SubstackPoster] Login error: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid session.

        Priority:
        1. Already authenticated → return True
        2. Saved cookies from disk → test session (FASTEST)
        3. Playwright browser automation (slower but reliable)
        4. SUBSTACK_SID env var → test session
        5. Password login → test session (may fail with CAPTCHA)
        """
        if self.authenticated:
            return True

        # 1. Try saved cookies from disk FIRST (fastest)
        if self._load_cookies():
            # Only test session if we have the critical substack.sid cookie
            if self.session.cookies.get('substack.sid'):
                if self._test_session():
                    self.authenticated = True
                    # Try to fetch publication ID if not set
                    if not self.publication_id:
                        self._fetch_publication_id()
                    return True
            # If no substack.sid in saved cookies, skip testing and try Playwright instead

        # 2. Try Playwright next (reliable, browser control)
        if HAS_PLAYWRIGHT_AUTH and self.email and self.password:
            logger.info("[SubstackPoster] Using Playwright browser automation for fresh session...")
            try:
                cookies = authenticate_substack(self.email, self.password, headless=True)
                if cookies:
                    # Apply the cookies to session
                    for name, value in cookies.items():
                        self.session.cookies.set(name, value, domain='.substack.com')
                    
                    # Playwright succeeded - trust it without testing (avoid extra API calls that trigger 429)
                    self._save_cookies()
                    self.authenticated = True
                    
                    # Fetch publication ID (needed for posting)
                    self._fetch_publication_id()
                    
                    logger.info("[SubstackPoster] ✓ Playwright authentication successful!")
                    return True
                else:
                    logger.warning("[SubstackPoster] Playwright automation did not return cookies")
            except Exception as e:
                logger.warning(f"[SubstackPoster] Playwright automation error: {e}")

        # 3. Try SUBSTACK_SID env var
        if self._apply_sid_cookie():
            if self._test_session():
                self._save_cookies()  # Persist for next time
                self.authenticated = True
                return True

        # 4. Fall back to password login
        if self._login():
            if self._test_session():
                self.authenticated = True
                return True

        logger.warning("[SubstackPoster] All auth methods failed")
        logger.warning("[SubstackPoster] QUICKEST FIX - Get fresh cookie manually:")
        logger.warning("[SubstackPoster]")
        logger.warning("[SubstackPoster]   1. Go to https://substack.com/auth/login")
        logger.warning("[SubstackPoster]   2. Enter: " + self.email)
        logger.warning("[SubstackPoster]   3. Enter password")
        logger.warning("[SubstackPoster]   4. After login, press F12 -> Application -> Cookies")
        logger.warning("[SubstackPoster]   5. Find 'substack.sid' and copy the VALUE")
        logger.warning("[SubstackPoster]   6. Run: python paste_substack_cookie.py")
        logger.warning("[SubstackPoster]   7. Paste the cookie value when prompted")
        return False

    def _test_session(self) -> bool:
        """Test if the current session is valid by fetching user info."""
        try:
            resp = self.session.get(f'{self.BASE_URL}/api/v1/user/self', timeout=10)
            if resp.status_code == 200:
                user_data = resp.json()
                logger.info(f"[SubstackPoster] Session valid (user: {user_data.get('email', '?')})")

                # Get publication ID if not set
                if not self.publication_id:
                    self._fetch_publication_id()
                return True
            return False
        except Exception:
            return False

    def _fetch_publication_id(self):
        """Fetch the publication ID for our subdomain."""
        try:
            resp = self.session.get(
                f'https://{self.subdomain}.substack.com/api/v1/publication',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self.publication_id = data.get('id')
                logger.info(f"[SubstackPoster] Publication ID: {self.publication_id}")
                self._save_cookies()
            elif resp.status_code == 429:
                # Rate limited - silently skip, will retry on next auth
                logger.debug("[SubstackPoster] Skipping publication ID fetch (rate limited)")
        except Exception as e:
            logger.debug(f"[SubstackPoster] Failed to fetch publication ID: {e}")

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _load_notes_log(self):
        """Load today's notes log from disk."""
        try:
            if NOTES_LOG_FILE.exists():
                with open(NOTES_LOG_FILE, 'r') as f:
                    data = json.load(f)
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                if data.get('date') == today:
                    self._notes_today = data.get('note_ids', [])
                else:
                    self._notes_today = []
        except Exception:
            self._notes_today = []

    def _save_notes_log(self):
        """Save today's notes log to disk."""
        try:
            DATA_DIR.mkdir(exist_ok=True)
            data = {
                'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'note_ids': self._notes_today,
            }
            with open(NOTES_LOG_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _check_rate_limit(self) -> bool:
        """Check if we're under the daily note limit."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        # Reset if new day
        if NOTES_LOG_FILE.exists():
            try:
                with open(NOTES_LOG_FILE, 'r') as f:
                    data = json.load(f)
                if data.get('date') != today:
                    self._notes_today = []
            except Exception:
                pass

        if len(self._notes_today) >= self.max_notes_per_day:
            logger.info(f"[SubstackPoster] Rate limit reached ({len(self._notes_today)}/{self.max_notes_per_day} notes today)")
            return False
        return True

    def _jitter_delay(self):
        """Add random delay between posts (30-120 seconds)."""
        delay = random.uniform(30, 120)
        logger.info(f"[SubstackPoster] Jitter delay: {delay:.0f}s")
        time.sleep(delay)

    # ------------------------------------------------------------------
    # Posting Methods (TEXT, NOTE, THREAD formats)
    # ------------------------------------------------------------------

    def post_text(self, title: str, body_text: str, is_published: bool = False) -> Optional[str]:
        """
        Post a long-form TEXT article/newsletter to Substack.
        
        Args:
            title: Article title (required)
            body_text: Full article body
            is_published: Publish immediately or save as draft
            
        Returns:
            article_id string or None on failure
        """
        if not self.enabled:
            return None
        
        if not self._check_rate_limit():
            return None
        
        if not self._ensure_authenticated():
            logger.error("[SubstackPoster] Not authenticated, cannot post TEXT")
            return None
        
        if not title or not title.strip():
            logger.error("[SubstackPoster] TEXT posts require a title")
            return None
        
        try:
            # Build ProseMirror document from plain text
            builder = NoteBuilder()
            paragraphs = body_text.split('\n\n')
            for para in paragraphs:
                lines = para.split('\n')
                if len(lines) == 1:
                    builder.add_paragraph(lines[0])
                else:
                    parts = []
                    for line in lines:
                        if line.strip():
                            parts.append({"text": line})
                    if parts:
                        builder.add_rich_paragraph(parts)
            
            body_json = builder.build_json()
            
            # Post to Substack Posts API
            url = f'{self.BASE_URL}/api/v1/posts'
            payload = {
                'title': title,
                'body_html': body_json,
                'status': 'published' if is_published else 'draft',
                'post_type': 'article',
                'audience': 'all',
            }
            
            # Include publication_id if available
            if self.publication_id:
                payload['publication_id'] = self.publication_id
            
            resp = self.session.post(url, json=payload, timeout=15)
            
            if resp.status_code in (200, 201):
                data = resp.json()
                post_id = str(data.get('id', ''))
                logger.info(f"[SubstackPoster] TEXT article posted (ID: {post_id}, title: {title[:30]}...)")
                
                if is_published:
                    self._notes_today.append(post_id)
                    self._save_notes_log()
                
                return post_id
            
            elif resp.status_code == 401:
                logger.warning("[SubstackPoster] Session expired, re-authenticating...")
                self.authenticated = False
                if self._ensure_authenticated():
                    resp2 = self.session.post(url, json=payload, timeout=15)
                    if resp2.status_code in (200, 201):
                        data = resp2.json()
                        post_id = str(data.get('id', ''))
                        if is_published:
                            self._notes_today.append(post_id)
                            self._save_notes_log()
                        logger.info(f"[SubstackPoster] TEXT article posted on retry (ID: {post_id})")
                        return post_id
                logger.error("[SubstackPoster] Re-auth failed, TEXT article not posted")
                return None
            
            elif resp.status_code == 429:
                logger.warning("[SubstackPoster] Rate limited (429)")
                return None
            
            else:
                logger.error(f"[SubstackPoster] TEXT post failed: HTTP {resp.status_code} — {resp.text[:200]}")
                return None
        
        except Exception as e:
            logger.error(f"[SubstackPoster] TEXT post error: {e}")
            return None

    def post_as_thread(self, thread_content: str) -> Optional[str]:
        """
        Post content as a THREAD (X/Twitter thread format).
        
        Args:
            thread_content: Thread text (parts separated by newlines)
            
        Returns:
            thread_id string or None on failure
        """
        if not self.enabled:
            return None
        
        if not self._check_rate_limit():
            return None
        
        if not self._ensure_authenticated():
            logger.error("[SubstackPoster] Not authenticated, cannot post THREAD")
            return None
        
        try:
            # Split thread into individual parts
            parts = [p.strip() for p in thread_content.split('\n\n') if p.strip()]
            
            if len(parts) < 2:
                logger.warning("[SubstackPoster] THREAD requires 2+ parts, using NOTE instead")
                return self.post_note(thread_content)
            
            # Build ProseMirror document
            builder = NoteBuilder()
            for part in parts:
                builder.add_paragraph(part)
            
            body_json = builder.build_json()
            
            # Post as thread type
            url = f'{self.BASE_URL}/api/v1/posts'
            payload = {
                'body': body_json,
                'post_type': 'thread',
                'audience': 'all',
                'status': 'published',
            }
            
            # Include publication_id if available
            if self.publication_id:
                payload['publication_id'] = self.publication_id
            
            resp = self.session.post(url, json=payload, timeout=15)
            
            if resp.status_code in (200, 201):
                data = resp.json()
                thread_id = str(data.get('id', ''))
                logger.info(f"[SubstackPoster] THREAD posted (ID: {thread_id}, parts: {len(parts)})")
                
                self._notes_today.append(thread_id)
                self._save_notes_log()
                
                return thread_id
            
            elif resp.status_code == 401:
                logger.warning("[SubstackPoster] Session expired, re-authenticating...")
                self.authenticated = False
                if self._ensure_authenticated():
                    resp2 = self.session.post(url, json=payload, timeout=15)
                    if resp2.status_code in (200, 201):
                        data = resp2.json()
                        thread_id = str(data.get('id', ''))
                        self._notes_today.append(thread_id)
                        self._save_notes_log()
                        logger.info(f"[SubstackPoster] THREAD posted on retry (ID: {thread_id})")
                        return thread_id
                return None
            
            elif resp.status_code == 429:
                logger.warning("[SubstackPoster] Rate limited (429)")
                return None
            
            else:
                logger.error(f"[SubstackPoster] THREAD post failed: HTTP {resp.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"[SubstackPoster] THREAD post error: {e}")
            return None

    def post_note(self, body_text: str) -> Optional[str]:
        """
        Post a text note to Substack.

        Args:
            body_text: Plain text content for the note

        Returns:
            note_id string or None on failure
        """
        if not self.enabled:
            return None

        if not self._check_rate_limit():
            return None

        if not self._ensure_authenticated():
            logger.error("[SubstackPoster] Not authenticated, cannot post")
            return None

        try:
            # Build ProseMirror document from plain text
            builder = NoteBuilder()
            paragraphs = body_text.split('\n\n')
            for para in paragraphs:
                # Handle single newlines as line breaks within paragraphs
                lines = para.split('\n')
                if len(lines) == 1:
                    builder.add_paragraph(lines[0])
                else:
                    # Join with hard breaks
                    parts = []
                    for i, line in enumerate(lines):
                        if line.strip():
                            parts.append({"text": line})
                    if parts:
                        builder.add_rich_paragraph(parts)

            body_json = builder.build_json()

            # Post to Substack Notes API
            url = f'{self.BASE_URL}/api/v1/comment'
            payload = {
                'body': body_json,
                'type': 'note',
            }
            
            # Include publication_id if available
            if self.publication_id:
                payload['publication_id'] = self.publication_id

            resp = self.session.post(url, json=payload, timeout=15)

            if resp.status_code in (200, 201):
                data = resp.json()
                note_id = str(data.get('id', ''))
                logger.info(f"[SubstackPoster] Note posted successfully (ID: {note_id})")

                # Track for rate limiting
                self._notes_today.append(note_id)
                self._save_notes_log()

                return note_id
            elif resp.status_code == 401:
                logger.warning("[SubstackPoster] Session expired, re-authenticating...")
                self.authenticated = False
                # Retry once
                if self._ensure_authenticated():
                    resp2 = self.session.post(url, json=payload, timeout=15)
                    if resp2.status_code in (200, 201):
                        data = resp2.json()
                        note_id = str(data.get('id', ''))
                        self._notes_today.append(note_id)
                        self._save_notes_log()
                        logger.info(f"[SubstackPoster] Note posted on retry (ID: {note_id})")
                        return note_id
                logger.error("[SubstackPoster] Re-auth failed, note not posted")
                return None
            elif resp.status_code == 429:
                logger.warning("[SubstackPoster] Rate limited by Substack (429)")
                return None
            else:
                logger.error(f"[SubstackPoster] Post failed: HTTP {resp.status_code} — {resp.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"[SubstackPoster] Post error: {e}")
            return None

    def post_memo_as_note(self, ticker: str, memo: str,
                          current_price: Optional[float] = None) -> Optional[str]:
        """Transform a market memo and post as a Substack Note."""
        if not self.enabled:
            return None

        text = ContentTransformer.transform_memo(ticker, memo, current_price)
        if not text:
            return None

        # Add jitter if not the first note
        if self._notes_today:
            self._jitter_delay()

        note_id = self.post_note(text)
        if note_id:
            logger.info(f"[SubstackPoster] Memo note posted for {ticker}")
        return note_id

    def post_thread_as_note(self, thread_data: dict) -> Optional[str]:
        """Condense a thread and post as a Substack Note."""
        if not self.enabled:
            return None

        text = ContentTransformer.transform_thread_to_note(thread_data)
        if not text:
            return None

        # Add jitter if not the first note
        if self._notes_today:
            self._jitter_delay()

        note_id = self.post_note(text)
        if note_id:
            logger.info("[SubstackPoster] Thread note posted")
        return note_id

    def post_news_as_note(self, ticker: str, tweet_text: str) -> Optional[str]:
        """Transform a news tweet and post as a Substack Note."""
        if not self.enabled:
            return None

        text = ContentTransformer.transform_news_tweet(tweet_text)
        if not text:
            return None

        if self._notes_today:
            self._jitter_delay()

        note_id = self.post_note(text)
        if note_id:
            logger.info(f"[SubstackPoster] News note posted for {ticker}")
        return note_id

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_credentials(self) -> bool:
        """Test Substack session/credentials on startup."""
        if not self.enabled:
            logger.info("[SubstackPoster] Not configured (no credentials)")
            return False

        if self._ensure_authenticated():
            logger.info(f"[SubstackPoster] Authenticated for {self.subdomain}.substack.com")
            logger.info(f"[SubstackPoster] Notes today: {len(self._notes_today)}/{self.max_notes_per_day}")
            return True
        else:
            logger.warning("[SubstackPoster] Authentication failed — notes will be skipped")
            return False

    def verify_note_posted(self, note_id: str) -> bool:
        """Verify a note is publicly visible after posting."""
        if not note_id:
            return False
        try:
            resp = self.session.get(
                f'{self.BASE_URL}/api/v1/comment/{note_id}',
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"[SubstackPoster] Note {note_id} confirmed visible")
                return True
            return False
        except Exception:
            return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()
