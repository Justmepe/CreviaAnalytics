"""
X/Twitter Integration Manager
Brings together ThreadBuilder, Poster, RateLimiter, NewsDetector, and Scheduler
for complete automated thread posting to X.

This is the main entry point for running the full X posting system.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Import all X components
try:
    from .x_thread_builder import ThreadBuilder
    from .x_poster import XPoster
    from .x_rate_limiter import XRateLimiter, QueuedPost
    from .x_news_detector import XNewsDetector
    from .x_scheduler import XScheduler
except ImportError:
    # Fallback for testing
    from x_thread_builder import ThreadBuilder
    from x_poster import XPoster
    from x_rate_limiter import XRateLimiter, QueuedPost
    from x_news_detector import XNewsDetector
    from x_scheduler import XScheduler


class XpostingSystem:
    """
    Complete X posting system integrating all components.
    
    Architecture:
    1. Scheduler: Triggers daily_scan, hourly_scan, breaking_news threads
    2. ThreadBuilder: Formats analysis into optimized tweet threads
    3. RateLimiter: Queue management, semi-hourly 50-post window tracking
    4. NewsDetector: Monitors for breaking news triggers
    5. Poster: Posts tweets with jitter delays and logging
    
    Usage:
        system = XpostingSystem()
        await system.start()  # Runs schedulers + async queue
    """
    
    def __init__(
        self,
        consumer_key: str = None,
        consumer_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
        min_post_delay: float = 60.0,
        max_post_delay: float = 120.0
    ):
        """
        Initialize the complete X posting system.
        
        Args:
            consumer_key, consumer_secret, access_token, access_token_secret: OAuth credentials
            min_post_delay: Minimum seconds between posts (default 60s)
            max_post_delay: Maximum seconds between posts (default 120s)
        """
        print("[*] XpostingSystem: Initializing...")
        
        # Core components
        self.thread_builder = ThreadBuilder()
        self.poster = XPoster(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            min_delay=min_post_delay,
            max_delay=max_post_delay
        )
        self.rate_limiter = XRateLimiter()
        self.news_detector = XNewsDetector(
            alert_callback=self._on_breaking_news_alert
        )
        self.scheduler = XScheduler(
            thread_builder_callback=self._build_thread,
            queue_callback=self._queue_post,
            news_detector_callback=self._check_news
        )
        
        # State
        self.running = False
        self.posted_threads: Dict[str, Any] = {}
        
        print("[OK] XpostingSystem: Initialized")
    
    def verify_credentials(self) -> bool:
        """Verify X authentication"""
        print("[...] XpostingSystem: Verifying credentials...")
        return self.poster.verify_credentials()
    
    def _build_thread(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a thread from market data.
        
        Callback for scheduler. Returns thread_data dict with 'tweets' list.
        """
        thread_type = data.get('type', 'analysis')
        
        if thread_type == 'daily_scan':
            # Daily 24-hour market summary
            return self.thread_builder.build_daily_scan_thread(
                period_summary=data.get('period_summary', 'Market update'),
                top_gainers=data.get('top_gainers', []),
                top_losers=data.get('top_losers', []),
                market_highlights=data.get('highlights', []),
                tags=['crypto', 'trading', 'analysis']
            )
        
        elif thread_type == 'hourly_scan':
            # Hourly market monitor
            return self.thread_builder.build_hourly_scan_thread(
                summary=data.get('summary', 'Hourly market update'),
                price_changes=data.get('price_changes', {}),
                key_events=data.get('key_events', []),
                market_sentiment=data.get('sentiment', 'neutral'),
                tags=['realtime', 'trading']
            )
        
        elif thread_type == 'breaking_news':
            # Breaking news analysis with alert context
            alert = data.get('alert', {})
            return self.thread_builder.build_breaking_news_thread(
                title=alert.get('title', 'Market Alert'),
                key_points=[alert.get('description', '')],
                impact_analysis=f"This event impacts {alert.get('asset', 'markets')}",
                affected_assets=[alert.get('asset')] if alert.get('asset') else [],
                tags=['breaking', 'alert', 'crypto']
            )
        
        else:
            # Generic thread
            return self.thread_builder.build_custom_thread(
                title=data.get('title', 'Update'),
                segments=data.get('segments', []),
                tags=data.get('tags', [])
            )
    
    async def _queue_post(self, thread_data: Dict[str, Any]) -> bool:
        """
        Queue a post for async posting.
        
        Callback for scheduler. Returns True if queued successfully.
        """
        queued_post = QueuedPost(
            thread_type=thread_data.get('type', 'analysis'),
            thread_data=thread_data,
            priority=2 if thread_data.get('type') == 'breaking_news' else 0
        )
        
        return await self.rate_limiter.enqueue_post(queued_post)
    
    def _check_news(self) -> Optional[Any]:
        """
        Check for breaking news alerts.
        
        Callback for scheduler (can be sync or async wrapper).
        """
        # In production, integrate with real news source
        # For now, return None (no alerts)
        recent_alerts = self.news_detector.get_recent_alerts(minutes=5)
        if recent_alerts:
            return recent_alerts[0]  # Return most recent
        return None
    
    def _on_breaking_news_alert(self, alert):
        """Called when breaking news alert is detected"""
        print(f"[ALERT] XpostingSystem: Breaking news - {alert.title}")
        # Can trigger immediate queuing here if needed
    
    async def _posting_worker(self):
        """
        Async worker that processes the posting queue.
        
        Respects rate limits, applies jitter delays, and logs posts.
        """
        print("[OK] XpostingSystem: Posting worker started")
        
        async def post_queued(queued_post: QueuedPost) -> tuple:
            """Post a queued thread and return (success, tweet_id)"""
            result = self.poster.post_thread(queued_post.thread_data)
            
            if result and result.get('success') and result.get('tweet_ids'):
                first_id = result['tweet_ids'][0]
                return (True, first_id)
            
            return (False, None)
        
        # Start the rate limiter worker
        await self.rate_limiter.start_worker(post_queued)
    
    async def start(self):
        """
        Start the complete X posting system.
        
        Runs:
        - Daily schedule (8 AM UTC)
        - Hourly monitor (every hour)
        - Breaking news detector (continuous)
        - Async posting queue (continuous)
        """
        print("[*] XpostingSystem: Starting...")
        
        if not self.poster.enabled:
            print("[ERR] XpostingSystem: Poster not enabled. Check credentials.")
            return
        
        if not self.verify_credentials():
            print("[ERR] XpostingSystem: Failed to verify X credentials")
            return
        
        self.running = True
        self.news_detector.start()
        
        # Run scheduler and posting worker concurrently
        try:
            await asyncio.gather(
                self._posting_worker(),
                self.scheduler.start(),
                return_exceptions=True
            )
        except KeyboardInterrupt:
            print("\n[--] XpostingSystem: Interrupted")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the X posting system"""
        print("[--] XpostingSystem: Stopping...")
        self.running = False
        self.scheduler.stop()
        self.rate_limiter.stop_worker()
        self.news_detector.stop()
        print("[OK] XpostingSystem: Stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        return {
            'running': self.running,
            'poster': self.poster.get_rate_limit_status() if self.poster else None,
            'rate_limiter': self.rate_limiter.get_status(),
            'news_detector': self.news_detector.get_status(),
            'scheduler': self.scheduler.get_status(),
            'posted_threads': len(self.posted_threads)
        }
    
    def trigger_daily_scan(self):
        """Manually trigger daily scan (for testing)"""
        print("[...] XpostingSystem: Triggering manual daily scan...")
        return self.scheduler.trigger_manual_scan('daily')
    
    def trigger_hourly_scan(self):
        """Manually trigger hourly scan (for testing)"""
        print("[...] XpostingSystem: Triggering manual hourly scan...")
        return self.scheduler.trigger_manual_scan('hourly')
    
    def build_thread_with_claude(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Build a comprehensive thread using Claude AI.
        
        Requires Claude API key in environment.
        Uses sophisticated prompts for natural, flowing content with:
        - Proper date inclusion
        - Complete data synthesis (majors, DeFi, memecoins, privacy)
        - Strategic emoji usage
        - Narrative flow (12+ tweet structure)
        - Copy-paste ready formatting
        
        Args:
            analysis_data: Dict with structure:
            {
                'majors': {'BTC': {...}, 'ETH': {...}, 'SOL': {...}, 'BNB': {...}},
                'defi': [list of defi protocols],
                'memecoins': [list of memecoins],
                'privacy_coins': [list of privacy coins],
                'market_context': {
                    'total_market_cap': 1500000000000,
                    'btc_dominance': 45.2,
                    'fear_greed_index': 65,
                    ...
                }
            }
        
        Returns:
            Dict with 'thread', 'tweets', 'tweet_count', 'copy_paste_ready'
        """
        print("[...] XpostingSystem: Building comprehensive thread with Claude AI")
        return self.thread_builder.build_with_claude_ai(
            analysis_data=analysis_data,
            thread_type='comprehensive',
            max_tweets=12
        )


# Example usage
if __name__ == "__main__":
    async def main():
        system = XpostingSystem()
        
        # Manual testing
        print("\n=== Testing Thread Building ===")
        daily_thread = system.trigger_daily_scan()
        if daily_thread:
            print(f"Built daily thread: {len(daily_thread.get('tweets', []))} tweets")
        
        hourly_thread = system.trigger_hourly_scan()
        if hourly_thread:
            print(f"Built hourly thread: {len(hourly_thread.get('tweets', []))} tweets")
        
        print("\n=== System Status ===")
        status = system.get_status()
        print(f"Status: {status}")
        
        print("\n=== Starting Full System ===")
        # This would run indefinitely
        # await system.start()
    
    asyncio.run(main())
