"""
X/Twitter Rate Limiter with Async Queue
Manages posting cadence to respect X's semi-hourly 50-post window limit
while maintaining a queue for non-blocking post scheduling.

Rate Limits:
- Hard limit: 2,400 posts per 24 hours
- Semi-hourly: 50 posts per 30 minutes (primary constraint)
- Recommended: 1-2 posts per minute (human-like)
- Thread-safe: All queue/tracking operations use locks
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from threading import Thread, Lock, Event
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class QueuedPost:
    """Represents a post waiting to be posted"""
    thread_type: str  # 'daily_scan', 'breaking_news', 'hourly_scan', 'analysis'
    thread_data: Dict[str, Any]
    priority: int = 0  # Higher number = higher priority (for breaking news)
    created_at: str = None
    scheduled_for: str = None  # ISO timestamp when to post
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class SemiHourlyBucket:
    """Track posts in a 30-minute bucket"""
    
    WINDOW_SIZE = 1800  # 30 minutes
    MAX_POSTS = 50
    
    def __init__(self, start_time: float):
        self.start_time = start_time
        self.posts = []
        self.lock = Lock()
    
    def is_active(self, current_time: float) -> bool:
        """Check if this bucket is still active"""
        return (current_time - self.start_time) < self.WINDOW_SIZE
    
    def add_post(self, tweet_id: str) -> bool:
        """Add a post, return True if successful"""
        with self.lock:
            if len(self.posts) < self.MAX_POSTS:
                self.posts.append({
                    'tweet_id': tweet_id,
                    'timestamp': time.time()
                })
                return True
            return False
    
    def get_remaining(self) -> int:
        """Get remaining posts available in this bucket"""
        with self.lock:
            return max(0, self.MAX_POSTS - len(self.posts))
    
    def get_posts(self) -> List[Dict[str, Any]]:
        """Get all posts in this bucket"""
        with self.lock:
            return self.posts.copy()


class XRateLimiter:
    """
    Manage X posting rate limits and queue.
    
    Tracks semi-hourly windows (50 posts per 30 min), manages a queue of pending posts,
    and provides scheduling information for optimal posting times.
    """
    
    def __init__(self, log_file: str = "data/x_rate_limit_log.json"):
        self.log_file = log_file
        self.queue: asyncio.Queue = None
        self.buckets: deque = deque(maxlen=48)  # 48 buckets = 24 hours
        self.current_bucket: Optional[SemiHourlyBucket] = None
        self.daily_count = 0
        self.lock = Lock()
        self.running = False
        self.worker_thread: Optional[Thread] = None
        
        # Load historical data
        self._load_log()
        self._initialize_buckets()
    
    def _initialize_buckets(self):
        """Initialize current bucket"""
        with self.lock:
            now = time.time()
            self.current_bucket = SemiHourlyBucket(now)
    
    def _load_log(self):
        """Load posting history from log file"""
        try:
            log_path = Path(self.log_file)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    data = json.load(f)
                    # Count posts from last 24 hours
                    twenty_four_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).timestamp()
                    recent_posts = [p for p in data if float(p.get('timestamp', 0)) > twenty_four_hours_ago]
                    self.daily_count = len(recent_posts)
        except Exception as e:
            print(f"[WARN] X RateLimiter: Failed to load log: {e}")
    
    def _save_log(self, tweet_id: str, thread_type: str, tweet_count: int):
        """Save post to log file"""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'tweet_id': tweet_id,
                'thread_type': thread_type,
                'tweet_count': tweet_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            
            logs.append(log_entry)
            
            # Keep only last 7 days
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).timestamp()
            logs = [l for l in logs if float(l.get('timestamp', '').split('.')[0].replace('T', ' ').split('-')[0]) or True]
            
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[WARN] X RateLimiter: Failed to save log: {e}")
    
    async def enqueue_post(self, queued_post: QueuedPost) -> bool:
        """
        Add a post to the queue.
        
        Args:
            queued_post: QueuedPost object with thread_type, thread_data, priority
        
        Returns:
            True if queued, False if queue full
        """
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=100)
        
        try:
            self.queue.put_nowait(queued_post)
            print(f"[+] RateLimiter: Queued {queued_post.thread_type} post (priority: {queued_post.priority})")
            return True
        except asyncio.QueueFull:
            print(f"[ERR] RateLimiter: Queue full, post rejected")
            return False
    
    def record_post(self, tweet_id: str, thread_type: str, tweet_count: int):
        """Record that a post was made"""
        with self.lock:
            now = time.time()
            
            # Rotate bucket if needed
            if self.current_bucket and not self.current_bucket.is_active(now):
                self.buckets.append(self.current_bucket)
                self.current_bucket = SemiHourlyBucket(now)
            
            # Add to current bucket
            self.current_bucket.add_post(tweet_id)
            self.daily_count += tweet_count
            
            # Save to log
            self._save_log(tweet_id, thread_type, tweet_count)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        with self.lock:
            current_bucket_posts = 0
            current_bucket_remaining = 50
            
            if self.current_bucket:
                current_bucket_posts = len(self.current_bucket.posts)
                current_bucket_remaining = self.current_bucket.get_remaining()
            
            return {
                'current_window_posts': current_bucket_posts,
                'current_window_remaining': current_bucket_remaining,
                'daily_total': self.daily_count,
                'daily_remaining': max(0, 2400 - self.daily_count),
                'queue_size': self.queue.qsize() if self.queue else 0,
                'can_post': current_bucket_remaining > 0 and self.daily_count < 2400,
                'status': 'OK' if current_bucket_remaining > 0 else 'RATE_LIMITED'
            }
    
    def get_next_available_slot(self) -> float:
        """
        Get timestamp of next available post slot.
        
        Returns:
            Unix timestamp when the next post can be made
        """
        with self.lock:
            status = self.get_status()
            
            if status['current_window_remaining'] > 0:
                # Can post immediately
                return time.time()
            
            if self.current_bucket:
                # Will have to wait for next window
                next_slot = self.current_bucket.start_time + (self.current_bucket.WINDOW_SIZE + 60)
                return next_slot
            
            return time.time()
    
    def should_expedite(self, thread_type: str) -> bool:
        """Check if a thread type should be expedited (higher priority)"""
        expedited_types = ['breaking_news']
        return thread_type in expedited_types
    
    async def start_worker(self, posting_callback: Callable):
        """
        Start the async worker to process queued posts.
        
        Args:
            posting_callback: Async function that takes QueuedPost and posts it
                             Should return (success: bool, tweet_id: str)
        """
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=100)
        
        self.running = True
        print("[OK] RateLimiter: Worker started")
        
        try:
            while self.running:
                try:
                    # Wait for next item with timeout
                    queued_post = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                    
                    # Check rate limits
                    status = self.get_status()
                    if not status['can_post']:
                        # Put back in queue and wait
                        await self.queue.put(queued_post)
                        await asyncio.sleep(10)
                        continue
                    
                    # Post it
                    print(f"[...] RateLimiter: Processing {queued_post.thread_type}...")
                    success, tweet_id = await posting_callback(queued_post)
                    
                    if success:
                        self.record_post(tweet_id, queued_post.thread_type, 
                                       len(queued_post.thread_data.get('tweets', [])))
                        print(f"[OK] RateLimiter: Posted {queued_post.thread_type} (ID: {tweet_id})")
                    else:
                        # Retry later
                        await asyncio.sleep(30)
                        await self.queue.put(queued_post)
                
                except asyncio.TimeoutError:
                    # No items, continue
                    pass
                except Exception as e:
                    print(f"[ERR] RateLimiter: Worker error: {e}")
                    await asyncio.sleep(5)
        
        except Exception as e:
            print(f"[ERR] RateLimiter: Fatal worker error: {e}")
        finally:
            self.running = False
            print("[--] RateLimiter: Worker stopped")
    
    def stop_worker(self):
        """Stop the async worker"""
        self.running = False
        print("[--] RateLimiter: Stopping worker...")
    
    def get_queue_summary(self) -> Dict[str, Any]:
        """Get summary of queued posts by type"""
        if not self.queue:
            return {}
        
        # This is approximate since we can't iterate the queue safely
        return {
            'total_queued': self.queue.qsize() if self.queue else 0,
            'max_size': 100
        }
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics about posting patterns"""
        with self.lock:
            total_buckets = len(self.buckets) + (1 if self.current_bucket else 0)
            total_posts = sum(len(b.posts) for b in self.buckets) + (len(self.current_bucket.posts) if self.current_bucket else 0)
            
            return {
                'active_windows': total_buckets,
                'total_posts_24h': total_posts,
                'avg_posts_per_window': total_posts / max(1, total_buckets),
                'daily_total': self.daily_count,
                'daily_capacity_used': f"{(self.daily_count / 2400 * 100):.1f}%"
            }
