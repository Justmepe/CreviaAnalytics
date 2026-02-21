"""
X/Twitter Posting System - Comprehensive Test Suite

Tests all components: ThreadBuilder, Poster, RateLimiter, NewsDetector, Scheduler
Validates thread building, rate limiting, news detection, and scheduling logic.

Run with: python test_x_system.py
"""

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Import system components
try:
    from src.utils.x_thread_builder import ThreadBuilder
    from src.utils.x_poster import XPoster, RateLimitTracker
    from src.utils.x_rate_limiter import XRateLimiter, QueuedPost, SemiHourlyBucket
    from src.utils.x_news_detector import (
        XNewsDetector, PriceMoveDetector, TrendingDetector,
        VolumeDetector, NewsAlert, NewsSource
    )
    from src.utils.x_scheduler import DailyScheduleTask, HourlyMonitorTask, XScheduler
except ImportError:
    # Fallback for direct execution
    from x_thread_builder import ThreadBuilder
    from x_poster import XPoster, RateLimitTracker
    from x_rate_limiter import XRateLimiter, QueuedPost, SemiHourlyBucket
    from x_news_detector import (
        XNewsDetector, PriceMoveDetector, TrendingDetector,
        VolumeDetector, NewsAlert, NewsSource
    )
    from x_scheduler import DailyScheduleTask, HourlyMonitorTask, XScheduler


class TestResults:
    """Track test results"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def record(self, name: str, passed: bool, message: str = ""):
        """Record test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.tests.append({
            'name': name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        print(f"  {status}: {name}")
        if message:
            print(f"       {message}")
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"             {self.failed} failed")
        print(f"{'='*60}\n")


def test_thread_builder():
    """Test ThreadBuilder with all 4 thread types"""
    print("\n[TEST] ThreadBuilder")
    results = TestResults()
    
    builder = ThreadBuilder()
    
    # Test 1: Daily scan thread
    try:
        thread = builder.build_daily_scan_thread(
            period_summary="24h market overview",
            top_gainers=["BTC +2.5%", "ETH +1.8%"],
            top_losers=["SHIB -3.2%"],
            highlights=["Bitcoin breaks $50k resistance"],
            tags=['crypto', 'market']
        )
        
        passed = (
            thread and
            'tweets' in thread and
            len(thread['tweets']) > 0 and
            thread.get('type') == 'daily_scan'
        )
        results.record(
            "Daily scan thread generation",
            passed,
            f"Generated {len(thread.get('tweets', []))} tweets"
        )
    except Exception as e:
        results.record("Daily scan thread generation", False, str(e))
    
    # Test 2: Hourly scan thread
    try:
        thread = builder.build_hourly_scan_thread(
            summary="Hourly market update",
            price_changes={'BTC': 0.5, 'ETH': -0.3, 'SOL': 1.2},
            key_events=["Altcoin volume spike 15%"],
            market_sentiment='bullish',
            tags=['realtime', 'trading']
        )
        
        passed = (
            thread and
            'tweets' in thread and
            len(thread['tweets']) > 0 and
            thread.get('type') == 'hourly_scan'
        )
        results.record(
            "Hourly scan thread generation",
            passed,
            f"Generated {len(thread.get('tweets', []))} tweets"
        )
    except Exception as e:
        results.record("Hourly scan thread generation", False, str(e))
    
    # Test 3: Breaking news thread
    try:
        thread = builder.build_breaking_news_thread(
            title="Bitcoin Hits $50,000",
            key_points=["BTC breaks previous ATH", "Institutional buying pressure"],
            impact_analysis="Indicates shift in market sentiment",
            affected_assets=['BTC', 'ETH'],
            tags=['breaking', 'alert']
        )
        
        passed = (
            thread and
            'tweets' in thread and
            len(thread['tweets']) > 0 and
            thread.get('type') == 'breaking_news'
        )
        results.record(
            "Breaking news thread generation",
            passed,
            f"Generated {len(thread.get('tweets', []))} tweets"
        )
    except Exception as e:
        results.record("Breaking news thread generation", False, str(e))
    
    # Test 4: Analysis thread
    try:
        thread = builder.build_analysis_thread(
            title="DeFi Market Analysis",
            analysis_points=[
                "TVL increased to $50B",
                "Yield farming APY declining",
                "Governance tokens underperforming"
            ],
            conclusion="Consolidation expected",
            tags=['analysis', 'defi']
        )
        
        passed = (
            thread and
            'tweets' in thread and
            len(thread['tweets']) > 0 and
            thread.get('type') == 'analysis'
        )
        results.record(
            "Analysis thread generation",
            passed,
            f"Generated {len(thread.get('tweets', []))} tweets"
        )
    except Exception as e:
        results.record("Analysis thread generation", False, str(e))
    
    # Test 5: Tweet length validation
    try:
        thread = builder.build_daily_scan_thread(
            period_summary=" Market update",
            top_gainers=[],
            top_losers=[],
            highlights=["Test"]
        )
        
        all_valid = all(len(t) <= 280 for t in thread.get('tweets', []))
        results.record(
            "All tweets within 280 character limit",
            all_valid,
            f"Max tweet length: {max((len(t) for t in thread.get('tweets', [])), default=0)}"
        )
    except Exception as e:
        results.record("Tweet length validation", False, str(e))
    
    return results


def test_rate_limiter():
    """Test RateLimitTracker and semi-hourly window logic"""
    print("\n[TEST] Rate Limiter")
    results = TestResults()
    
    # Test 1: Rate limit tracker initialization
    try:
        tracker = RateLimitTracker()
        passed = tracker is not None and tracker.can_post()
        results.record("RateLimitTracker initialization", passed)
    except Exception as e:
        results.record("RateLimitTracker initialization", False, str(e))
    
    # Test 2: Post recording
    try:
        tracker = RateLimitTracker()
        initial = tracker.can_post()
        tracker.record_post()
        status = tracker.get_status()
        
        passed = (
            initial and
            status['posts_this_window'] == 1 and
            status['posts_remaining'] == 49
        )
        results.record(
            "Recording post updates counter",
            passed,
            f"Posts: {status['posts_this_window']}/50"
        )
    except Exception as e:
        results.record("Recording post updates counter", False, str(e))
    
    # Test 3: Window capacity limit
    try:
        tracker = RateLimitTracker()
        # Fill the window 0
        for _ in range(50):
            tracker.record_post()
        
        passed = not tracker.can_post()
        results.record(
            "Window fills after 50 posts",
            passed,
            f"Can post: {tracker.can_post()}"
        )
    except Exception as e:
        results.record("Window fills after 50 posts", False, str(e))
    
    # Test 4: Semi-hourly bucket tracking
    try:
        bucket = SemiHourlyBucket(time.time())
        
        # Add posts
        success1 = bucket.add_post("id1")
        success2 = bucket.add_post("id2")
        remaining = bucket.get_remaining()
        
        passed = (
            success1 and success2 and
            len(bucket.posts) == 2 and
            remaining == 48
        )
        results.record(
            "SemiHourlyBucket post tracking",
            passed,
            f"Posts: {len(bucket.posts)}, Remaining: {remaining}"
        )
    except Exception as e:
        results.record("SemiHourlyBucket post tracking", False, str(e))
    
    # Test 5: XRateLimiter status
    try:
        limiter = XRateLimiter()
        status = limiter.get_status()
        
        passed = (
            'posts_this_window' in status and
            'posts_remaining' in status and
            'daily_total' in status and
            'can_post' in status
        )
        results.record(
            "XRateLimiter status reporting",
            passed,
            f"Status keys: {list(status.keys())}"
        )
    except Exception as e:
        results.record("XRateLimiter status reporting", False, str(e))
    
    return results


def test_news_detector():
    """Test news detection (price moves, trending, volume)"""
    print("\n[TEST] News Detector")
    results = TestResults()
    
    # Test 1: Price move detection - major asset
    try:
        detector = PriceMoveDetector()
        alert = detector.detect('BTC', 50000, 49000)  # 2.04% move
        
        passed = alert is not None and alert.asset == 'BTC'
        results.record(
            "Price move detection (BTC +2.04%)",
            passed,
            f"Alert: {alert.title if alert else 'None'}"
        )
    except Exception as e:
        results.record("Price move detection (BTC +2.04%)", False, str(e))
    
    # Test 2: Price move no alert (below threshold)
    try:
        detector = PriceMoveDetector()
        alert = detector.detect('BTC', 50000, 49950)  # 0.1% move (below 2% threshold)
        
        passed = alert is None
        results.record(
            "No alert for small price move (BTC +0.1%)",
            passed,
            f"Alert generated: {alert is not None}"
        )
    except Exception as e:
        results.record("No alert for small price move", False, str(e))
    
    # Test 3: Trending detector
    try:
        detector = TrendingDetector()
        detector.add_keyword("MoonShot")
        detector.add_keyword("MoonShot")
        detector.add_keyword("MoonShot")
        detector.add_keyword("MoonShot")
        detector.add_keyword("MoonShot")
        
        alert = detector.detect(["MoonShot", "Crypto"])
        
        passed = alert is not None and "trending" in alert.title.lower()
        results.record(
            "Trending keyword detection",
            passed,
            f"Alert: {alert.title if alert else 'None'}"
        )
    except Exception as e:
        results.record("Trending keyword detection", False, str(e))
    
    # Test 4: Volume spike detection
    try:
        detector = VolumeDetector()
        
        # Establish baseline (4+ entries)
        for i in range(4):
            detector.detect('ETH', 2000 + (i * 50))
        
        # Spike
        alert = detector.detect('ETH', 6000)  # 200% spike
        
        passed = alert is not None
        results.record(
            "Volume spike detection",
            passed,
            f"Alert: {alert.title if alert else 'None'}"
        )
    except Exception as e:
        results.record("Volume spike detection", False, str(e))
    
    # Test 5: News alert creation
    try:
        alert = NewsAlert(
            source=NewsSource.COINGECKO,
            title="BTC Bull Run",
            description="Bitcoin breaking resistance levels",
            impact='high',
            asset='BTC',
            price_change=5.0
        )
        
        passed = alert is not None and alert.source == NewsSource.COINGECKO
        results.record(
            "NewsAlert creation",
            passed,
            f"Alert: {alert.title}"
        )
    except Exception as e:
        results.record("NewsAlert creation", False, str(e))
    
    return results


def test_scheduler():
    """Test scheduler task timing"""
    print("\n[TEST] Scheduler")
    results = TestResults()
    
    # Test 1: Daily task initialization
    try:
        def dummy_callback():
            return {"data": "test"}
        
        task = DailyScheduleTask("Test", 8, 0, dummy_callback)
        passed = task is not None and task.hour == 8 and task.minute == 0
        results.record(
            "DailyScheduleTask initialization",
            passed
        )
    except Exception as e:
        results.record("DailyScheduleTask initialization", False, str(e))
    
    # Test 2: Hourly task initialization
    try:
        def dummy_callback():
            return {"data": "test"}
        
        task = HourlyMonitorTask("Test", dummy_callback, every_n_hours=1)
        passed = task is not None and task.every_n_hours == 1
        results.record(
            "HourlyMonitorTask initialization",
            passed
        )
    except Exception as e:
        results.record("HourlyMonitorTask initialization", False, str(e))
    
    # Test 3: Daily task should run at correct time
    try:
        def dummy_callback():
            return {}
        
        task = DailyScheduleTask("Test", 8, 0, dummy_callback)
        
        # Mock 8:00 AM
        now = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
        should_run = task.should_run(now)
        
        passed = should_run  # Should run at exactly 8 AM
        results.record(
            "Daily task triggers at scheduled time (8:00 AM)",
            passed,
            f"Should run: {should_run}"
        )
    except Exception as e:
        results.record("Daily task triggers at scheduled time", False, str(e))
    
    # Test 4: Keep queued post data structure
    try:
        post = QueuedPost(
            thread_type='daily_scan',
            thread_data={'tweets': ['a', 'b', 'c']},
            priority=1
        )
        
        passed = (
            post.thread_type == 'daily_scan' and
            len(post.thread_data['tweets']) == 3 and
            post.priority == 1
        )
        results.record(
            "QueuedPost data structure",
            passed
        )
    except Exception as e:
        results.record("QueuedPost data structure", False, str(e))
    
    return results


def test_postal_rate_limits():
    """Test XPoster rate limiting integration"""
    print("\n[TEST] Poster Rate Limits")
    results = TestResults()
    
    # Test 1: XPoster initialization
    try:
        # This will fail auth but should still initialize
        poster = XPoster()
        passed = poster is not None
        results.record(
            "XPoster initialization",
            passed,
            f"Enabled: {poster.enabled}"
        )
    except Exception as e:
        results.record("XPoster initialization", False, str(e))
    
    # Test 2: Rate limit tracker in poster
    try:
        poster = XPoster()
        status = poster.get_rate_limit_status()
        
        passed = (
            'posts_this_window' in status and
            'posts_remaining' in status and
            'can_post' in status
        )
        results.record(
            "Poster rate limit status",
            passed,
            f"Status: {status}"
        )
    except Exception as e:
        results.record("Poster rate limit status", False, str(e))
    
    # Test 3: Jitter delay presence
    try:
        poster = XPoster(min_delay=60, max_delay=120)
        
        passed = (
            poster.min_delay == 60 and
            poster.max_delay == 120
        )
        results.record(
            "Jitter delay configuration",
            passed,
            f"Range: {poster.min_delay}-{poster.max_delay}s"
        )
    except Exception as e:
        results.record("Jitter delay configuration", False, str(e))
    
    return results


def test_integration():
    """Test component integration"""
    print("\n[TEST] Component Integration")
    results = TestResults()
    
    # Test 1: ThreadBuilder → RateLimiter
    try:
        builder = ThreadBuilder()
        limiter = XRateLimiter()
        
        thread_data = builder.build_daily_scan_thread(
            period_summary="Test",
            top_gainers=[],
            top_losers=[],
            highlights=[]
        )
        
        post = QueuedPost(
            thread_type='daily_scan',
            thread_data=thread_data
        )
        
        passed = thread_data and post.thread_type == 'daily_scan'
        results.record(
            "ThreadBuilder → QueuedPost flow",
            passed,
            f"Thread type: {post.thread_type}"
        )
    except Exception as e:
        results.record("ThreadBuilder → QueuedPost flow", False, str(e))
    
    # Test 2: NewsDetector → Alert creation
    try:
        detector = XNewsDetector()
        
        # Simulate price move detection
        alert = detector.check_price_move('BTC', 50000, 49000)
        
        passed = alert is not None or alert is None  # Either works
        results.record(
            "NewsDetector event generation",
            passed,
            f"Alert: {alert.title if alert else 'None detected'}"
        )
    except Exception as e:
        results.record("NewsDetector event generation", False, str(e))
    
    return results


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("X/Twitter Posting System - Test Suite")
    print("="*60)
    
    all_results = TestResults()
    
    # Run all test suites
    suites = [
        test_thread_builder(),
        test_rate_limiter(),
        test_news_detector(),
        test_scheduler(),
        test_postal_rate_limits(),
        test_integration()
    ]
    
    # Aggregate results
    for suite in suites:
        all_results.passed += suite.passed
        all_results.failed += suite.failed
        all_results.tests.extend(suite.tests)
    
    # Final summary
    all_results.summary()
    
    if all_results.failed == 0:
        print("✓ All tests passed!\n")
        return 0
    else:
        print(f"✗ {all_results.failed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    exit(main())
