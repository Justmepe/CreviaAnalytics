"""
X/Twitter HTTP Poster using twikit (X internal GraphQL API)

Posts tweets and threads via X's internal API using session cookies.
No browser required — works reliably on VPS without display/DNS issues.

Uses twikit: https://github.com/d60/twikit
Cookies loaded from x_cookies.json (exported from Chrome via export_x_cookies.py).
"""

import os
import json
import time
import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
COOKIES_FILE = PROJECT_ROOT / "x_cookies.json"

try:
    from twikit import Client as TwikitClient
    HAS_TWIKIT = True
except ImportError:
    HAS_TWIKIT = False


def _run_async(coro):
    """
    Run an async coroutine in a dedicated thread with its own event loop.
    Avoids conflicts with the main asyncio event loop in main.py.
    """
    result_box = [None]
    error_box = [None]

    def _thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_box[0] = loop.run_until_complete(coro)
        except Exception as exc:
            error_box[0] = exc
        finally:
            loop.close()

    t = threading.Thread(target=_thread, daemon=True)
    t.start()
    t.join(timeout=120)  # 2-minute timeout per API call

    if t.is_alive():
        raise TimeoutError("Twikit API call timed out after 120s")
    if error_box[0]:
        raise error_box[0]
    return result_box[0]


def _load_cookies_as_dict(cookies_file: Path) -> Dict[str, str]:
    """Convert x_cookies.json list format to {name: value} dict for twikit."""
    with open(cookies_file) as f:
        cookies_list = json.load(f)
    return {c["name"]: c["value"] for c in cookies_list}


class XHttpPoster:
    """
    Post tweets and threads to X using twikit (X internal GraphQL API).

    Drop-in replacement for XBrowserPoster.post_tweet() and .post_thread().
    Does NOT support articles (use XBrowserPoster for those).

    Loads session cookies from x_cookies.json. Run scripts/export_x_cookies.py
    to refresh cookies when they expire (~90 days).
    """

    def __init__(self, cookies_file: Optional[str] = None):
        self.cookies_file = Path(cookies_file) if cookies_file else COOKIES_FILE
        self.enabled = False
        self._client: Optional[TwikitClient] = None
        self._lock = threading.Lock()

        if not HAS_TWIKIT:
            logger.warning("[XHttpPoster] twikit not installed — run: pip install twikit")
            return

        if not self.cookies_file.exists():
            logger.warning(
                f"[XHttpPoster] Cookies file not found: {self.cookies_file}. "
                "Run scripts/export_x_cookies.py first."
            )
            return

        try:
            self._init_client()
            self.enabled = True
            logger.info("[XHttpPoster] Initialized (twikit HTTP API with cookie auth)")
        except Exception as e:
            logger.error(f"[XHttpPoster] Failed to initialize: {e}")

    def _init_client(self):
        """Initialize and authenticate the twikit client."""
        cookies = _load_cookies_as_dict(self.cookies_file)

        async def _setup():
            client = TwikitClient('en-US')
            # Set cookies directly instead of file-based load
            client.set_cookies(cookies)
            return client

        self._client = _run_async(_setup())
        logger.info(f"[XHttpPoster] Loaded {len(cookies)} cookies, client ready")

    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
        """
        Post a single tweet.

        Args:
            text: Tweet text (max 280 chars)
            reply_to_id: Tweet ID to reply to (for threading)

        Returns:
            Tweet ID string on success, None on failure
        """
        if not self.enabled or not self._client:
            return None

        text = text[:280]

        with self._lock:
            try:
                async def _post():
                    kwargs = {}
                    if reply_to_id:
                        kwargs['reply_to'] = reply_to_id
                    return await self._client.create_tweet(text=text, **kwargs)

                tweet = _run_async(_post())
                tweet_id = tweet.id if hasattr(tweet, 'id') else str(tweet)
                logger.info(f"[XHttpPoster] Posted tweet: {tweet_id}")
                return tweet_id

            except Exception as e:
                logger.error(f"[XHttpPoster] post_tweet failed: {e}")
                # If auth error, mark as needing cookie refresh
                if "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                    logger.error(
                        "[XHttpPoster] Auth error — cookies may have expired. "
                        "Run scripts/export_x_cookies.py to refresh."
                    )
                return None

    def post_thread(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post a full thread as connected replies.

        Args:
            thread_data: Dict with 'tweets' list, 'type', 'tweet_count'

        Returns:
            Dict with 'success', 'posted_count', 'tweet_ids', 'error'
        """
        result = {
            'success': False,
            'posted_count': 0,
            'tweet_ids': [],
            'thread_url': None,
            'error': None,
        }

        if not self.enabled or not self._client:
            result['error'] = 'XHttpPoster not enabled'
            return result

        tweets: List[str] = thread_data.get('tweets', [])
        if not tweets:
            result['error'] = 'No tweets to post'
            return result

        logger.info(f"[XHttpPoster] Posting thread ({len(tweets)} tweets)...")

        reply_to_id = None
        for i, tweet_text in enumerate(tweets):
            tweet_text = tweet_text.strip()
            if not tweet_text:
                continue

            # Small delay between thread tweets (avoid rate limiting)
            if i > 0:
                time.sleep(3)

            tweet_id = self.post_tweet(tweet_text[:280], reply_to_id=reply_to_id)

            if tweet_id:
                result['posted_count'] += 1
                result['tweet_ids'].append(tweet_id)
                reply_to_id = tweet_id  # Next tweet replies to this one
                logger.info(f"[XHttpPoster] [{i + 1}/{len(tweets)}] Posted {tweet_id}")
            else:
                result['error'] = f'Failed at tweet {i + 1}/{len(tweets)}'
                logger.error(f"[XHttpPoster] Thread broken at tweet {i + 1}")
                break

        non_empty = [t for t in tweets if t.strip()]
        result['success'] = result['posted_count'] == len(non_empty)

        if result['tweet_ids']:
            first_id = result['tweet_ids'][0]
            result['thread_url'] = f'https://x.com/i/web/status/{first_id}'

        status = "complete" if result['success'] else "partial"
        logger.info(
            f"[XHttpPoster] Thread {status} "
            f"({result['posted_count']}/{len(non_empty)} tweets)"
        )

        return result

    def verify_session(self) -> bool:
        """Check if the session cookies are still valid by fetching own profile."""
        if not self.enabled or not self._client:
            return False

        try:
            async def _check():
                # get_user_by_screen_name on self is a light read-only call
                me = await self._client.user()
                return me

            user = _run_async(_check())
            if user:
                logger.info(f"[XHttpPoster] Session valid (user: {getattr(user, 'screen_name', '?')})")
                return True
            return False
        except Exception as e:
            logger.error(f"[XHttpPoster] Session check failed: {e}")
            return False
