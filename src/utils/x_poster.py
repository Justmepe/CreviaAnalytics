"""
X/Twitter Poster Module
Posts threads and individual tweets directly to X via API v2.

Authentication: OAuth 1.0a User Context (4 keys required)
- Consumer Key + Consumer Secret (app-level)
- Access Token + Access Token Secret (user-level)

Rate limits:
- Free tier: 17 tweets per 24h window
- Basic tier: 100 tweets per 24h window
- Premium tier: 10,000+ tweets per 24h window

X Rate Limit Details:
- Hard limit: 2,400 posts per 24 hours
- Semi-hourly window: ~50 posts per 30 minutes
- Recommended: 1-2 posts per minute spacing (human-like, safe)
"""

import os
import time
import random
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import deque
from typing import Optional, List, Dict, Any
from threading import Thread, Lock
try:
    import tweepy
except Exception:
    tweepy = None


class RateLimitTracker:
    """Track semi-hourly rate limits (50 posts per 30-minute window)"""
    
    WINDOW_SIZE = 1800  # 30 minutes in seconds
    POSTS_PER_WINDOW = 50
    
    def __init__(self):
        self.post_timestamps: deque = deque()  # Timestamps of posts
        self.lock = Lock()
    
    def can_post(self) -> bool:
        """Check if we can post without hitting rate limit"""
        with self.lock:
            now = datetime.now(timezone.utc).timestamp()
            
            # Remove old timestamps outside current window
            while self.post_timestamps and (now - self.post_timestamps[0]) > self.WINDOW_SIZE:
                self.post_timestamps.popleft()
            
            # Check if we're under the limit
            return len(self.post_timestamps) < self.POSTS_PER_WINDOW
    
    def record_post(self):
        """Record that we posted"""
        with self.lock:
            self.post_timestamps.append(datetime.now(timezone.utc).timestamp())
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        with self.lock:
            now = datetime.now(timezone.utc).timestamp()
            active_posts = len([ts for ts in self.post_timestamps if (now - ts) <= self.WINDOW_SIZE])
            return {
                'posts_this_window': active_posts,
                'posts_remaining': max(0, self.POSTS_PER_WINDOW - active_posts),
                'can_post': active_posts < self.POSTS_PER_WINDOW
            }


class XPoster:
    """Post threads and tweets directly to X/Twitter with intelligent rate limiting.
    
    Respects X's semi-hourly 50-post window limit while maintaining human-like
    posting patterns with 1-2 minute delays between posts.
    """

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        log_file: str = "data/x_posting_log.json",
        min_delay: float = 60.0,
        max_delay: float = 120.0
    ):
        """Initialize X Poster with OAuth credentials and rate limiting
        
        Args:
            consumer_key: X App Consumer Key
            consumer_secret: X App Consumer Secret
            access_token: X User Access Token
            access_token_secret: X User Access Token Secret
            log_file: Path to log file for post history
            min_delay: Minimum seconds between posts (default 60s = 1 min)
            max_delay: Maximum seconds between posts (default 120s = 2 min)
        """
        self.consumer_key = consumer_key or os.getenv('X_CONSUMER_KEY') or os.getenv('TWITTER_CONSUMER_KEY', '')
        self.consumer_secret = consumer_secret or os.getenv('X_CONSUMER_SECRET') or os.getenv('TWITTER_CONSUMER_SECRET', '')
        self.access_token = access_token or os.getenv('X_ACCESS_TOKEN') or os.getenv('TWITTER_ACCESS_TOKEN', '')
        self.access_token_secret = access_token_secret or os.getenv('X_ACCESS_TOKEN_SECRET') or os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')

        self.client: Optional[object] = None
        self.enabled = False
        self.log_file = log_file
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.rate_limiter = RateLimitTracker()
        self.last_post_time = time.time()
        
        if not tweepy:
            print("[--] X Poster: `tweepy` not installed — XPoster disabled")
            return

        if all([self.consumer_key, self.consumer_secret,
                self.access_token, self.access_token_secret]):
            try:
                self.client = tweepy.Client(
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_token_secret,
                    wait_on_rate_limit=False  # We manage rate limiting manually
                )
                self.enabled = True
                print("[++] X Poster initialized successfully")
            except Exception as e:
                print(f"[--] X Poster init failed: {e}")
        else:
            print("[--] X Poster: Missing OAuth credentials")

    def verify_credentials(self) -> bool:
        """Test that credentials work by fetching the authenticated user."""
        if not self.enabled:
            return False
        try:
            me = self.client.get_me()
            if me and me.data:
                print(f"[OK] X Poster: Authenticated as @{me.data.username}")
                return True
            print("[ERR] X Poster: Could not verify credentials")
            return False
        except tweepy.Unauthorized:
            print("[ERR] X Poster: 401 Unauthorized - check your tokens")
            self.enabled = False
            return False
        except tweepy.Forbidden:
            print("[ERR] X Poster: 403 Forbidden - check app permissions (need Read+Write)")
            self.enabled = False
            return False
        except Exception as e:
            print(f"[ERR] X Poster: Credential check failed: {e}")
            return False

    def _apply_jitter_delay(self):
        """Wait with jitter between min_delay and max_delay before posting"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        self.last_post_time = time.time()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status for semi-hourly window"""
        return self.rate_limiter.get_status()

    def can_post_now(self) -> bool:
        """Check if we can post without hitting rate limits"""
        return self.rate_limiter.can_post()

    def log_post(self, tweet_id: str, thread_data: Dict[str, Any]) -> None:
        """Log post to history file"""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tweet_id': tweet_id,
                'thread_type': thread_data.get('type', 'unknown'),
                'tweet_count': thread_data.get('tweet_count', 1),
                'content_preview': (thread_data.get('tweets', [''])[0][:100] if thread_data.get('tweets') else '')
            }

            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)

            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[WARN] X Poster: Failed to log post: {e}")

    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
        """
        Post a single tweet with rate limiting and jitter delays.

        Args:
            text: Tweet text (max 280 chars for most users, 4000 for Premium)
            reply_to_id: Tweet ID to reply to (for threading)

        Returns:
            Tweet ID string on success, None on failure
        """
        if not self.enabled:
            return None

        # Wait for rate limit window availability
        max_wait_time = 60  # Max 60 seconds to wait
        wait_start = time.time()
        while not self.can_post_now():
            if time.time() - wait_start > max_wait_time:
                print("[RATE] X Poster: Rate limit window full, skipping post")
                return None
            time.sleep(5)

        # Apply jitter delay before posting (human-like behavior)
        self._apply_jitter_delay()

        try:
            kwargs = {'text': text[:280]}
            if reply_to_id:
                kwargs['in_reply_to_tweet_id'] = reply_to_id

            response = self.client.create_tweet(**kwargs)

            if response and response.data:
                tweet_id = str(response.data['id'])
                self.rate_limiter.record_post()
                return tweet_id

            print("[ERR] X Poster: No data in tweet response")
            return None

        except Exception as e:
            # Tweepy exceptions may not be available if tweepy is missing
            err_name = type(e).__name__
            if 'TooManyRequests' in err_name or 'RateLimit' in err_name:
                print("[RATE] X Poster: Rate limited. Waiting for window reset...")
                return None
            if 'Forbidden' in err_name:
                print(f"[ERR] X Poster: 403 Forbidden - {e}")
                self.enabled = False
                return None
            print(f"[ERR] X Poster: Failed to post tweet: {e}")
            return None

    def post_thread(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post a full thread to X: first tweet, then each reply chained.
        Uses jitter delays (1-2 min) between tweets and respects rate limits.

        Args:
            thread_data: Dict with 'tweets' (list of strings), 'type', 'tweet_count'

        Returns:
            Dict with 'success', 'posted_count', 'tweet_ids', 'thread_url', 'error'
        """
        result = {
            'success': False,
            'posted_count': 0,
            'tweet_ids': [],
            'thread_url': None,
            'error': None,
        }

        if not self.enabled:
            result['error'] = 'X Poster not enabled (missing credentials)'
            return result

        tweets = thread_data.get('tweets', [])
        if not tweets:
            result['error'] = 'No tweets to post'
            return result

        print(f"[...] X Poster: Posting thread ({len(tweets)} tweets, rate-limited)...")

        previous_id = None
        first_tweet_id = None
        first_post_time = None

        for i, tweet_text in enumerate(tweets):
            tweet_text = tweet_text.strip()
            if not tweet_text:
                continue

            # Check rate limit before each tweet
            if not self.can_post_now():
                result['error'] = f'Rate limited at tweet {i + 1}/{len(tweets)}'
                print(f"[RATE] X Poster: Rate limit hit at tweet {i + 1}/{len(tweets)}")
                break

            # Post tweet (reply to previous if threading)
            tweet_id = self.post_tweet(tweet_text, reply_to_id=previous_id)

            if tweet_id is None:
                result['error'] = f'Failed at tweet {i + 1}/{len(tweets)}'
                print(f"[ERR] X Poster: Thread broken at tweet {i + 1}")
                break

            result['tweet_ids'].append(tweet_id)
            result['posted_count'] += 1
            previous_id = tweet_id

            if first_tweet_id is None:
                first_tweet_id = tweet_id
                first_post_time = datetime.now(timezone.utc)

            # Log the post
            self.log_post(tweet_id, thread_data)

            rate_status = self.get_rate_limit_status()
            print(f"   [{i + 1}/{len(tweets)}] Posted (ID: {tweet_id}) | "
                  f"Rate: {rate_status['posts_this_window']}/50 in window")

        if first_tweet_id:
            # Build the thread URL using the authenticated user
            try:
                me = self.client.get_me()
                if me and me.data:
                    result['thread_url'] = f"https://x.com/{me.data.username}/status/{first_tweet_id}"
            except Exception:
                result['thread_url'] = f"https://x.com/i/status/{first_tweet_id}"

        result['success'] = result['posted_count'] == len([t for t in tweets if t.strip()])
        status = "complete" if result['success'] else "partial"
        print(f"[{'OK' if result['success'] else 'WARN'}] X Poster: Thread {status} "
              f"({result['posted_count']}/{len([t for t in tweets if t.strip()])} tweets)")

        if result['thread_url']:
            print(f"   Thread URL: {result['thread_url']}")

        return result
