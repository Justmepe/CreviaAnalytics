"""
src/core/social_manager.py
Mixed-traffic SocialQueueManager (Threads vs News Flash)

This file provides a single clean implementation of SocialQueueManager
with persistence to `data/social_queue.json` and a dry-run mode.
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
from src.core.config import POSTING_SCHEDULE
from src.utils.x_poster import XPoster

QUEUE_FILE = os.path.join('data', 'social_queue.json')


class SocialQueueManager:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.thread_queue: List[Dict[str, Any]] = []
        self.news_queue: List[Dict[str, Any]] = []
        self.history: List[float] = []
        self.last_thread_time: float = 0.0
        self.last_news_time: float = 0.0
        self.posted_threads_today: int = 0
        self.last_reset_day: int = time.localtime().tm_yday

        self.x_poster: Optional[XPoster] = None
        if not dry_run:
            try:
                self.x_poster = XPoster()
            except Exception:
                self.x_poster = None

        self._load_state()

    def add_content(self, content: Dict[str, Any], content_type: str = 'news_flash') -> None:
        item = {
            'id': f"{content_type}_{int(time.time())}",
            'type': content_type,
            'tweets': content.get('tweets') or [content.get('content', '')],
            'added_at': time.time(),
            'asset': content.get('ticker', 'General')
        }

        if content_type == 'thread':
            self.thread_queue.append(item)
            print(f"📥 [Queue] Added THREAD. size={len(self.thread_queue)}")
        else:
            self.news_queue.append(item)
            print(f"📥 [Queue] Added NEWS. size={len(self.news_queue)}")

        self._save_state()

    def process_queue(self) -> None:
        # daily reset
        current_day = time.localtime().tm_yday
        if current_day != self.last_reset_day:
            self.posted_threads_today = 0
            self.last_reset_day = current_day

        # global safety check
        if not self._is_safe_to_post_global():
            return

        now = time.time()

        # LANE 1: THREADS
        thread_gap = POSTING_SCHEDULE['thread']['gap_seconds']
        max_threads = POSTING_SCHEDULE['thread']['max_per_day']
        time_since_thread = now - self.last_thread_time

        if self.thread_queue and time_since_thread > thread_gap and self.posted_threads_today < max_threads:
            item = self.thread_queue.pop(0)
            self._post_item(item)
            return

        # LANE 2: NEWS FLASH (filler)
        news_gap = POSTING_SCHEDULE['news_flash']['gap_seconds']
        time_since_news = now - self.last_news_time

        # require a small buffer since last thread to avoid racing
        if self.news_queue and time_since_news > news_gap and time_since_thread > 600:
            item = self.news_queue.pop(0)
            self._post_item(item)
            return

    def _post_item(self, item: Dict[str, Any]) -> None:
        print(f"\n🚀 LAUNCHING {item['type'].upper()} ({item.get('asset')})")
        ok = self._post_thread_chain(item.get('tweets', []))
        if ok:
            if item['type'] == 'thread':
                self.last_thread_time = time.time()
                self.posted_threads_today += 1
            else:
                self.last_news_time = time.time()
            self._save_state()
            print("✅ Posted")
        else:
            print("❌ Post failed — requeueing")
            if item['type'] == 'thread':
                self.thread_queue.insert(0, item)
            else:
                self.news_queue.insert(0, item)

    def _post_thread_chain(self, tweets: List[str]) -> bool:
        prev_id: Optional[str] = None
        for i, t in enumerate(tweets):
            if not self._is_safe_to_post_global():
                print("⚠️ Global safety — sleeping 60s")
                time.sleep(60)

            try:
                if self.dry_run:
                    print(f"[DRY] {i+1}/{len(tweets)}: {t[:80]}")
                    time.sleep(0.05)
                    new_id = f"dry_{int(time.time())}_{i}"
                else:
                    # prefer a multi-tweet thread API if available
                    if self.x_poster and hasattr(self.x_poster, 'post_thread') and i == 0 and len(tweets) > 1:
                        res = self.x_poster.post_thread({'tweets': tweets}, delay_seconds=2.0)
                        if res.get('success'):
                            ts = time.time()
                            for _ in res.get('tweet_ids', []):
                                self.history.append(ts)
                            self._save_state()
                            return True
                        return False

                    if not self.x_poster:
                        print("Poster unavailable — failing post")
                        return False

                    new_id = self.x_poster.post_tweet(text=t, reply_to_id=prev_id)
                    if not new_id:
                        return False

                self.history.append(time.time())
                self._save_state()
                prev_id = new_id
                if i < len(tweets) - 1:
                    time.sleep(1)

            except Exception as e:
                print(f"Posting error: {e}")
                return False

        return True

    def _is_safe_to_post_global(self) -> bool:
        now = time.time()
        start = now - 1800  # 30 minutes
        recent = [t for t in self.history if t > start]
        # keep history trimmed
        self.history = recent
        limit = POSTING_SCHEDULE.get('global', {}).get('semi_hourly_cap', 40)
        if len(recent) >= limit:
            if len(recent) % 5 == 0:
                print(f"⛔ HARD LIMIT: {len(recent)}/{limit}")
            return False
        return True

    def _save_state(self) -> None:
        os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
        try:
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'thread_queue': self.thread_queue,
                    'news_queue': self.news_queue,
                    'history': self.history,
                    'last_thread_time': self.last_thread_time,
                    'last_news_time': self.last_news_time,
                    'posted_threads_today': self.posted_threads_today
                }, f, indent=2)
        except Exception:
            pass

    def _load_state(self) -> None:
        if not os.path.exists(QUEUE_FILE):
            return
        try:
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                s = json.load(f)
                self.thread_queue = s.get('thread_queue', [])
                self.news_queue = s.get('news_queue', [])
                self.history = s.get('history', [])
                self.last_thread_time = s.get('last_thread_time', 0)
                self.last_news_time = s.get('last_news_time', 0)
                self.posted_threads_today = s.get('posted_threads_today', 0)
        except Exception:
            # ignore load errors and start fresh
            return
"""
src/core/social_manager.py
Mixed-traffic SocialQueueManager (Threads vs News Flash)
"""

import json
import time
import os
from typing import List, Dict, Any
from src.core.config import POSTING_SCHEDULE
from src.utils.x_poster import XPoster

QUEUE_FILE = 'data/social_queue.json'


class SocialQueueManager:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.thread_queue: List[Dict[str, Any]] = []
        self.news_queue: List[Dict[str, Any]] = []
        self.history: List[float] = []
        self.last_thread_time = 0.0
        self.last_news_time = 0.0
        self.posted_threads_today = 0
        self.last_reset_day = time.localtime().tm_yday

        self.x_poster = XPoster() if not dry_run else None
        self._load_state()

    def add_content(self, content: Dict[str, Any], content_type: str = 'news_flash'):
        item = {
            'id': f"{content_type}_{int(time.time())}",
            'type': content_type,
            'tweets': content.get('tweets') or [content.get('content', '')],
            'added_at': time.time(),
            'asset': content.get('ticker', 'General')
        }

        if content_type == 'thread':
            self.thread_queue.append(item)
            print(f"📥 [Queue] Added THREAD. size={len(self.thread_queue)}")
        else:
            self.news_queue.append(item)
            print(f"📥 [Queue] Added NEWS. size={len(self.news_queue)}")

        self._save_state()

    def process_queue(self):
        # daily reset
        current_day = time.localtime().tm_yday
        if current_day != self.last_reset_day:
            self.posted_threads_today = 0
            self.last_reset_day = current_day

        if not self._is_safe_to_post_global():
            return

        now = time.time()
        time_since_thread = now - self.last_thread_time
        thread_gap = POSTING_SCHEDULE['thread']['gap_seconds']

        if self.thread_queue and time_since_thread > thread_gap:
            self._post_item(self.thread_queue.pop(0))
            return

        time_since_news = now - self.last_news_time
        news_gap = POSTING_SCHEDULE['news_flash']['gap_seconds']

        if self.news_queue and time_since_news > news_gap and time_since_thread > 600:
            self._post_item(self.news_queue.pop(0))
            return

    def _post_item(self, item: Dict[str, Any]):
        print(f"\n🚀 LAUNCHING {item['type'].upper()} ({item.get('asset')})")
        ok = self._post_thread_chain(item.get('tweets', []))
        if ok:
            if item['type'] == 'thread':
                self.last_thread_time = time.time()
                self.posted_threads_today += 1
            else:
                self.last_news_time = time.time()
            self._save_state()
            print("✅ Posted")
        else:
            print("❌ Post failed — requeueing")
            if item['type'] == 'thread':
                self.thread_queue.insert(0, item)
            else:
                self.news_queue.insert(0, item)

    def _post_thread_chain(self, tweets: List[str]) -> bool:
        prev_id = None
        for i, t in enumerate(tweets):
            if not self._is_safe_to_post_global():
                print("⚠️ Global safety — sleeping 60s")
                time.sleep(60)

            try:
                if self.dry_run:
                    print(f"[DRY] {i+1}/{len(tweets)}: {t[:80]}")
                    time.sleep(0.2)
                    new_id = f"dry_{int(time.time())}_{i}"
                else:
                    if hasattr(self.x_poster, 'post_thread') and i == 0 and len(tweets) > 1:
                        res = self.x_poster.post_thread({'tweets': tweets}, delay_seconds=2.0)
                        if res.get('success'):
                            ts = time.time()
                            for _ in res.get('tweet_ids', []):
                                self.history.append(ts)
                            self._save_state()
                            return True
                        return False
                    new_id = self.x_poster.post_tweet(text=t, reply_to_id=prev_id)

                    if not new_id:
                        return False

                self.history.append(time.time())
                self._save_state()
                prev_id = new_id
                if i < len(tweets) - 1:
                    time.sleep(1)

            except Exception as e:
                print(f"Posting error: {e}")
                return False

        return True

    def _is_safe_to_post_global(self) -> bool:
        now = time.time()
        start = now - 1800
        recent = [t for t in self.history if t > start]
        self.history = recent
        limit = POSTING_SCHEDULE.get('global', {}).get('semi_hourly_cap', 40)
        if len(recent) >= limit:
            if len(recent) % 5 == 0:
                print(f"⛔ HARD LIMIT: {len(recent)}/{limit}")
            return False
        return True

    def _save_state(self):
        os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
        with open(QUEUE_FILE, 'w') as f:
            json.dump({
                'thread_queue': self.thread_queue,
                'news_queue': self.news_queue,
                'history': self.history,
                'last_thread_time': self.last_thread_time,
                'last_news_time': self.last_news_time,
                'posted_threads_today': self.posted_threads_today
            }, f, indent=2)

    def _load_state(self):
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r') as f:
                    s = json.load(f)
                    self.thread_queue = s.get('thread_queue', [])
                    self.news_queue = s.get('news_queue', [])
                    self.history = s.get('history', [])
                    self.last_thread_time = s.get('last_thread_time', 0)
                    self.last_news_time = s.get('last_news_time', 0)
                    self.posted_threads_today = s.get('posted_threads_today', 0)
            except Exception:
                pass
                    recent = [t for t in self.history if t > start]
                    self.history = recent
                    limit = POSTING_SCHEDULE.get('global', {}).get('semi_hourly_cap', 40)
                    if len(recent) >= limit:
                        if len(recent) % 5 == 0:
                            print(f"⛔ HARD LIMIT: {len(recent)}/{limit}")
                        return False
                    return True

                def _save_state(self):
                    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
                    with open(QUEUE_FILE, 'w') as f:
                        json.dump({
                            'thread_queue': self.thread_queue,
                            'news_queue': self.news_queue,
                            'history': self.history,
                            'last_thread_time': self.last_thread_time,
                            'last_news_time': self.last_news_time,
                            'posted_threads_today': self.posted_threads_today
                        }, f, indent=2)

                def _load_state(self):
                    if os.path.exists(QUEUE_FILE):
                        try:
                            with open(QUEUE_FILE, 'r') as f:
                                s = json.load(f)
                                self.thread_queue = s.get('thread_queue', [])
                                self.news_queue = s.get('news_queue', [])
                                self.history = s.get('history', [])
                                self.last_thread_time = s.get('last_thread_time', 0)
                                self.last_news_time = s.get('last_news_time', 0)
                                self.posted_threads_today = s.get('posted_threads_today', 0)
                        except Exception:
                            pass
        # Do not allow anything if we are near the 50 posts/30 min limit
        if not self._is_safe_to_post_global():
            return

        now = time.time()

        # ---------------------------------------------------------
        # LANE 1: THREADS (The Anchors)
        # ---------------------------------------------------------
        # Rules:
        # 1. Must be a thread in queue
        # 2. Must be X hours since last thread (e.g., 6 hours)
        # 3. Must not exceed daily thread limit (e.g., 4)
        time_since_thread = now - self.last_thread_time
        thread_gap_rule = POSTING_SCHEDULE['thread']['gap_seconds']
        max_threads = POSTING_SCHEDULE['thread']['max_per_day']
        
        if self.thread_queue:
            if time_since_thread > thread_gap_rule and self.posted_threads_today < max_threads:
                # We are cleared for takeoff
                self._post_item(self.thread_queue.pop(0))
                return
            elif self.posted_threads_today >= max_threads:
                print(f"⚠️ Daily thread limit reached ({max_threads}). Holding remaining threads until tomorrow.")

        # ---------------------------------------------------------
        """
        File: src/core/social_manager.py
        Purpose: Advanced scheduling for Threads (Anchors) vs Tweets (News)
        """

        import json
        import time
        import os
        from typing import List, Dict, Any
        from src.core.config import POSTING_SCHEDULE
        from src.utils.x_poster import XPoster

        QUEUE_FILE = 'data/social_queue.json'


        class SocialQueueManager:
            def __init__(self, dry_run: bool = False):
                self.dry_run = dry_run
        
                # Two separate lanes
                self.thread_queue = []
                self.news_queue = []
        
                # Tracking
                self.history = []
                self.last_thread_time = 0
                self.last_news_time = 0
                self.posted_threads_today = 0
                self.last_reset_day = time.localtime().tm_yday
        
                self.x_poster = XPoster() if not dry_run else None
                self._load_state()

            def add_content(self, content: Dict[str, Any], content_type: str = 'news_flash'):
                """
                Unified entry point for all content.
                content_type: 'thread' or 'news_flash'
                """
                item = {
                    'id': f"{content_type}_{int(time.time())}",
                    'type': content_type,
                    'tweets': content['tweets'] if 'tweets' in content else [content['content']],
                    'added_at': time.time(),
                    'asset': content.get('ticker', 'General')
                }

                if content_type == 'thread':
                    self.thread_queue.append(item)
                    print(f"📥 [Queue] Added THREAD (Anchor). Queue size: {len(self.thread_queue)}")
                else:
                    self.news_queue.append(item)
                    print(f"📥 [Queue] Added NEWS (Ticker). Queue size: {len(self.news_queue)}")
        
                self._save_state()

            def process_queue(self):
                """Traffic Controller Logic - Called every minute"""
        
                # 0. Daily Reset Logic
                current_day = time.localtime().tm_yday
                if current_day != self.last_reset_day:
                    self.posted_threads_today = 0
                    self.last_reset_day = current_day

                # 1. Global Safety Check (The Hard Limit)
                if not self._is_safe_to_post_global():
                    return

                now = time.time()

                # ---------------------------------------------------------
                # PRIORITY 1: THREADS (The Anchors)
                # Check if it's time for a thread and we have one ready
                # ---------------------------------------------------------
                time_since_thread = now - self.last_thread_time
                thread_gap_rule = POSTING_SCHEDULE['thread']['gap_seconds']
        
                if self.thread_queue and time_since_thread > thread_gap_rule:
                    # We are cleared to post a thread
                    self._post_item(self.thread_queue.pop(0))
                    return

                # ---------------------------------------------------------
                # PRIORITY 2: NEWS (The Filler)
                # If we didn't post a thread, can we post news?
                # ---------------------------------------------------------
                time_since_news = now - self.last_news_time
                news_gap_rule = POSTING_SCHEDULE['news_flash']['gap_seconds']
        
                # Note: If we just posted a thread, we wait a bit before resuming news
                # to let the thread "breathe" at the top of the feed.
                if self.news_queue and time_since_news > news_gap_rule and time_since_thread > 600:
                    # We are cleared to post news
                    self._post_item(self.news_queue.pop(0))
                    return

                # If we get here, we are just waiting (idling)
                # print("⏳ Traffic Control: Waiting for scheduling windows...")

            def _post_item(self, item):
                """Executes the posting (Single or Thread)"""
                print(f"\n🚀 LAUNCHING {item['type'].upper()}: {item['asset']}")
        
                # Use existing chain logic (works for 1 tweet or 15)
                success = self._post_thread_chain(item['tweets'])
        
                if success:
                    if item['type'] == 'thread':
                        self.last_thread_time = time.time()
                        self.posted_threads_today += 1
                    else:
                        self.last_news_time = time.time()
            
                    self._save_state()
                    print(f"✅ Posted successfully. {item['type']} cooldown active.")
                else:
                    print("❌ Failed. Re-queuing.")
                    # Simple retry logic: put back at front
                    if item['type'] == 'thread':
                        self.thread_queue.insert(0, item)
                    else:
                        self.news_queue.insert(0, item)

            def _post_thread_chain(self, tweets: List[str]) -> bool:
                """Same implementation as before, calling self.x_poster"""
                previous_tweet_id = None

                for i, tweet_text in enumerate(tweets):
                    # Ensure global safety before every tweet
                    if not self._is_safe_to_post_global():
                        print("⚠️ Pausing mid-thread due to global safety. Sleeping 60s...")
                        time.sleep(60)

                    try:
                        if self.dry_run:
                            print(f"   [DRY RUN] Posting {i+1}/{len(tweets)}: {tweet_text[:80]}...")
                            time.sleep(1)
                            new_id = f"dry_{int(time.time())}_{i}"
                        else:
                            # Prefer using XPoster's thread helper if available
                            if hasattr(self.x_poster, 'post_thread') and i == 0 and len(tweets) > 1:
                                # Post entire remaining chain using post_thread for efficiency
                                remaining = tweets[i:]
                                result = self.x_poster.post_thread({'tweets': remaining}, delay_seconds=2.0)
                                if result.get('success'):
                                    # Add timestamps for each posted tweet
                                    ts = time.time()
                                    for _id in result.get('tweet_ids', []):
                                        self.history.append(ts)
                                    self._save_state()
                                    return True
                                else:
                                    print("❌ XPoster failed to post thread")
                                    return False
                            else:
                                new_id = self.x_poster.post_tweet(text=tweet_text, reply_to_id=previous_tweet_id)

                            if not new_id:
                                print(f"❌ API Error on tweet {i+1}")
                                return False

                            print(f"   [LIVE] Posted {i+1}/{len(tweets)} (ID: {new_id})")

                        # Record timestamp
                        self.history.append(time.time())
                        self._save_state()
                        previous_tweet_id = new_id

                        # Small human-like pause between tweets
                        if i < len(tweets) - 1:
                            time.sleep(5)

                    except Exception as e:
                        print(f"❌ Critical Error while posting: {e}")
                        return False

                return True

            def _is_safe_to_post_global(self) -> bool:
                """Checks the 50 posts / 30 mins hard limit"""
                now = time.time()
                window_start = now - 1800
                recent_posts = [t for t in self.history if t > window_start]

                # Prune history
                self.history = recent_posts

                count = len(recent_posts)
                limit = POSTING_SCHEDULE.get('global', {}).get('semi_hourly_cap', 40)

                if count >= limit:
                    # Only occasionally log to avoid noise
                    if count % 5 == 0:
                        print(f"⛔ HARD LIMIT: {count}/{limit} posts in last 30m. Pausing posting.")
                    return False

                return True

            def _save_state(self):
                """Saves both queues and timers"""
                state = {
                    'thread_queue': self.thread_queue,
                    'news_queue': self.news_queue,
                    'history': self.history,
                    'last_thread_time': self.last_thread_time,
                    'last_news_time': self.last_news_time,
                    'posted_threads_today': self.posted_threads_today
                }
                with open(QUEUE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)

            def _load_state(self):
                if os.path.exists(QUEUE_FILE):
                    try:
                        with open(QUEUE_FILE, 'r') as f:
                            state = json.load(f)
                            self.thread_queue = state.get('thread_queue', [])
                            self.news_queue = state.get('news_queue', [])
                            self.history = state.get('history', [])
                            self.last_thread_time = state.get('last_thread_time', 0)
                            self.last_news_time = state.get('last_news_time', 0)
                    except Exception:
                        pass