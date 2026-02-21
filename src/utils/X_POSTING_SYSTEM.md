# X/Twitter Posting System - Architecture & Usage

## System Overview

Complete automated system for posting market analysis threads to X (Twitter) with intelligent rate limiting, news detection, and scheduling.

```
┌─────────────────────────────────────────────────────────────────┐
│                     SCHEDULER (x_scheduler.py)                  │
│  Daily Scan (8 AM UTC) │ Hourly Monitor (every hour)            │
│  Breaking News Triggers (event-based)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  THREAD BUILDER (x_thread_builder.py)           │
│  Format market data into optimized tweet threads                │
│  - Daily Scan (24h summary)                                     │
│  - Hourly Scan (real-time updates)                              │
│  - Breaking News (event analysis)                               │
│  - Analysis (deep-dive topics)                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RATE LIMITER (x_rate_limiter.py)              │
│  Queue Posts │ Track 50-post/30min window │ Async Queue Worker │
│  Daily quota tracking (2,400/24h max)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     POSTER (x_poster.py)                        │
│  Post tweets to X/Twitter API                                  │
│  1-2 minute jitter delays (human-like)                          │
│  Thread chaining with rate limit checks                         │
│  Post history logging                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                      X/Twitter API

┌─────────────────────────────────────────────────────────────────┐
│                NEWS DETECTOR (x_news_detector.py)               │
│  Price Move Detection │ Trending Keywords                       │
│  Volume Spikes │ Feeds alerts to Scheduler                      │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. x_thread_builder.py
**Purpose**: Format analysis data into optimized tweet threads

**Key Methods**:
- `build_daily_scan_thread()` - 24-hour market summary
  - Input: period_summary, top_gainers, top_losers, highlights
  - Output: 10-15 tweets with market analysis
  
- `build_hourly_scan_thread()` - Real-time hourly monitor
  - Input: summary, price_changes (dict), key_events, sentiment
  - Output: 3-5 tweets with asset-level changes
  
- `build_breaking_news_thread()` - Event-triggered news analysis
  - Input: title, key_points, impact_analysis, affected_assets
  - Output: 4-8 tweets with rapid context
  
- `build_analysis_thread()` - Deep-dive topic analysis
  - Input: topic, analysis_points, conclusion
  - Output: Detailed educational thread

**Features**:
- Automatic text wrapping to 280-char limit
- Sequential numbering (1/N, 2/N, etc.)
- Metadata tracking (type, timestamp, tweet count)
- Character count validation

### 2. x_poster.py
**Purpose**: Post tweets to X with rate limiting and delays

**Key Methods**:
- `post_tweet(text, reply_to_id)` - Single tweet
- `post_thread(thread_data)` - Full thread with jitter delays
- `verify_credentials()` - Test OAuth tokens
- `get_rate_limit_status()` - Check 50-post window
- `can_post_now()` - Verify under rate limit

**Rate Limiting**:
- Jitter delay: 1-2 minutes between tweets (configurable)
- Semi-hourly window: 50 posts per 30-minute window
- Automatic rate limit checks before each tweet
- Post history logging to `data/x_posting_log.json`

**Features**:
- Thread-safe with locks
- OAuth 1.0a authentication
- Automatic tweet URL generation
- Comprehensive error handling

### 3. x_rate_limiter.py
**Purpose**: Manage posting queue and semi-hourly rate limits

**Key Classes**:
- `SemiHourlyBucket` - Track posts in 30-minute windows
- `RateLimitTracker` - Track semi-hourly limits (from x_poster)
- `QueuedPost` - Data class for posts awaiting posting

**Key Methods**:
- `enqueue_post(queued_post)` - Add post to async queue
- `record_post(tweet_id)` - Track posted tweet
- `start_worker(callback)` - Async worker to process queue
- `get_status()` - Current rate limit status
- `get_next_available_slot()` - When next post can go
- `get_analytics()` - 24-hour posting patterns

**Features**:
- Async queue (100 item max)
- Semi-hourly bucket tracking (48 buckets = 24h)
- Daily quota counter (2,400 posts/day)
- Post history logging to `data/x_rate_limit_log.json`
- Break-down by thread type

### 4. x_scheduler.py
**Purpose**: Schedule daily scans, hourly monitoring, breaking news

**Key Classes**:
- `DailyScheduleTask` - One-time daily task (8 AM UTC)
- `HourlyMonitorTask` - Recurring hourly task
- `XScheduler` - Main coordinator

**Schedule**:
- **Daily Scan**: 8:00 AM UTC (every day)
- **Hourly Monitor**: Every hour on the hour
- **Breaking News**: Event-triggered when news detected

**Key Methods**:
- `start()` - Run async scheduler loop
- `stop()` - Graceful shutdown
- `trigger_manual_scan(type)` - Manual daily/hourly scan
- `get_schedule()` - Current schedule info
- `get_status()` - Scheduler status with next run times

**Features**:
- Async task runner with proper timing
- Breaking news background monitor
- Action logging to `data/x_scheduler_log.json`
- Support for manual testing/override

### 5. x_news_detector.py
**Purpose**: Monitor markets and news for breaking news triggers

**Key Classes**:
- `PriceMoveDetector` - BTC/ETH ±2%, alts ±5%
- `TrendingDetector` - Keyword frequency tracking
- `VolumeDetector` - Trading volume spike detection
- `XNewsDetector` - Main coordinator

**Detection Types**:
1. **Price Moves**: Configurable thresholds per asset class
2. **Trending**: Keywords reaching min frequency (5+)
3. **Volume Spikes**: 2x+ above 4-hour average
4. **Custom Events**: Extensible for additional sources

**Key Methods**:
- `check_price_move(asset, current, previous)` - Detect price move
- `check_trending(keywords)` - Check trending keywords
- `check_volume_spike(asset, volume)` - Detect volume spike
- `get_recent_alerts(minutes, impact)` - Filter alerts
- `get_status()` - Detection status

**Features**:
- Alert callbacks on detection
- Alert history logging to `data/x_news_alerts.json`
- Rate limiting per asset (5-min minimum)
- Impact classification (high/medium/low)
- Trending frequency counting

### 6. x_integration.py
**Purpose**: Main entry point coordinating all components

**Key Class**:
- `XpostingSystem` - Complete integrated system

**Main Methods**:
- `verify_credentials()` - Test X authentication
- `trigger_daily_scan()` - Manual daily scan
- `trigger_hourly_scan()` - Manual hourly scan
- `get_status()` - Full system status
- `start()` - Run full system with all schedulers

**Features**:
- Single entry point for complete system
- Automatic credential verification
- Status monitoring across all components
- Easy manual testing

## Installation & Configuration

### Prerequisites
```bash
pip install tweepy  # X API v2 client (already in requirements.txt)
pip install schedule  # Optional: for cron-like scheduling
```

### Environment Variables
Set in `.env`:
```
X_CONSUMER_KEY=your_consumer_key
X_CONSUMER_SECRET=your_consumer_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret

# Or legacy names (also supported):
TWITTER_CONSUMER_KEY=...
TWITTER_CONSUMER_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
```

### X API Setup
1. Create app at https://developer.twitter.com/en/portal/dashboard
2. Set permissions: Read + Write + Direct Messages
3. Generate OAuth 1.0a User Context tokens
4. Add to `.env`

## Usage Examples

### Minimal Setup
```python
from src.utils.x_integration import XpostingSystem
import asyncio

async def main():
    system = XpostingSystem()
    
    # Verify credentials work
    if not system.verify_credentials():
        print("Failed to auth")
        return
    
    # Start full system (runs indefinitely)
    await system.start()

asyncio.run(main())
```

### Manual Testing
```python
system = XpostingSystem()
system.verify_credentials()

# Manual triggers
daily_data = system.trigger_daily_scan()
print(f"Built {len(daily_data['tweets'])} tweets for daily scan")

hourly_data = system.trigger_hourly_scan()
print(f"Built {len(hourly_data['tweets'])} tweets for hourly scan")

# Check system status
status = system.get_status()
print(f"Rate limit: {status['poster']['posts_this_window']}/50")
print(f"Daily total: {status['rate_limiter']['daily_total']}/2400")
```

### Component Testing
```python
from src.utils.x_thread_builder import ThreadBuilder
from src.utils.x_poster import XPoster

# Build a thread
builder = ThreadBuilder()
thread = builder.build_daily_scan_thread(
    period_summary="Market up 2.5%",
    top_gainers=["BTC +2.5%"],
    top_losers=["SHIB -1.1%"],
    highlights=["SEC approves spot BTC ETF"]
)

# Post it
poster = XPoster()
result = poster.post_thread(thread)
print(f"Posted {result['posted_count']} tweets")
print(f"Thread URL: {result['thread_url']}")
```

### Rate Limit Monitoring
```python
system = XpostingSystem()

# Check current window
status = system.rate_limiter.get_status()
print(f"Posts in current 30-min window: {status['posts_this_window']}/50")
print(f"Posts today: {status['daily_total']}/2,400")
print(f"Can post: {status['can_post']}")

# Get analytics
analytics = system.rate_limiter.get_analytics()
print(f"Average posts per window: {analytics['avg_posts_per_window']:.1f}")
print(f"24-hour capacity used: {analytics['daily_capacity_used']}")
```

### News Monitoring
```python
system = XpostingSystem()

# Check recent alerts
alerts = system.news_detector.get_recent_alerts(minutes=60, impact='high')
for alert in alerts:
    print(f"[{alert['impact']}] {alert['title']}")
    print(f"  {alert['description']}")

# Check detection status
status = system.news_detector.get_status()
print(f"Recent alerts (30m): {status['recent_alerts_30m']}")
print(f"High impact alerts: {status['high_impact_alerts']}")
```

### Custom Thread Building
```python
builder = ThreadBuilder()

# Custom thread with your own content
thread = builder.build_custom_thread(
    title="My Custom Analysis",
    segments=[
        "First part of analysis",
        "Second part with data",
        "Conclusion and outlook"
    ],
    tags=['crypto', 'analysis']
)

# Post it
poster = XPoster()
result = poster.post_thread(thread)
```

## Rate Limits in Detail

### X API Limits
- **Hard ceiling**: 2,400 posts per 24 hours
- **Semi-hourly limit**: ~50 posts per 30-minute window (strict)
- **Recommended spacing**: 1-2 minutes between posts (human-like)

### System Implementation
- Posts are automatically batched into 30-min windows
- Jitter delays (1-2 min) applied between tweets for natural feel
- Queue holds up to 100 posts
- Breaks/waits automatically when window fills
- Daily counter prevents exceeding 2,400/day

### Example Capacity
- With 1-2 min spacing: ~30-60 posts per day (safe)
- Maximum if pressed: 2,400 per day (not recommended)
- Current system targets: ~10-20 posts per day (sustainable)

## Logging

### Post History
Log: `data/x_posting_log.json`
```json
{
  "timestamp": "2025-02-05T08:15:30.123456+00:00",
  "tweet_id": "1234567890",
  "thread_type": "daily_scan",
  "tweet_count": 12,
  "content_preview": "Market Summary: Bitcoin up 2.5% overnight..."
}
```

### Rate Limit History
Log: `data/x_rate_limit_log.json`
```json
{
  "timestamp": "2025-02-05T08:15:30.123456+00:00",
  "thread_type": "daily_scan",
  "tweet_count": 12
}
```

### News Alerts
Log: `data/x_news_alerts.json`
```json
{
  "timestamp": "2025-02-05T08:15:30.123456+00:00",
  "source": "coingecko",
  "title": "BTC Price Alert: UP 2.5%",
  "impact": "medium",
  "asset": "BTC",
  "price_change": 2.5
}
```

### Scheduler Log
Log: `data/x_scheduler_log.json`
```json
{
  "timestamp": "2025-02-05T08:00:00.000000+00:00",
  "action": "daily_scan_queued",
  "data": {
    "tweet_count": 12,
    "type": "daily_scan"
  }
}
```

## Troubleshooting

### Authentication Issues
```python
system = XpostingSystem()
if not system.verify_credentials():
    # Check:
    # 1. Credentials in .env file
    # 2. Correct Consumer Key/Secret (app keys)
    # 3. Correct Access Token/Secret (user keys)
    # 4. App permissions include Read + Write
```

### Rate Limit Exceeded
```python
# Check current status
status = system.rate_limiter.get_status()
if not status['can_post']:
    print(f"Rate limited: {status['posts_this_window']}/50 in window")
    # System waits automatically
```

### Queue Backing Up
```python
# Check queue size
queue_status = system.rate_limiter.get_queue_summary()
if queue_status['total_queued'] > 80:  # 80% full
    # Reduce submission rate or increase jitter delays
```

### Posts Not Going Out
```python
# Check scheduler
sched_status = system.scheduler.get_status()
print(f"Scheduler running: {sched_status['running']}")
print(f"Next daily: {sched_status['next_daily_scan']}")
print(f"Next hourly: {sched_status['next_hourly_scan']}")

# Check rate limiter
rate_status = system.rate_limiter.get_status()
print(f"Queue size: {rate_status['queue_size']}")

# Check poster
poster_status = system.poster.get_rate_limit_status()
print(f"Poster enabled: {system.poster.enabled}")
```

## Next Steps

1. **Integrate Real Data Sources**
   - Connect to CoinGecko API for price data
   - Add Reddit/Twitter trend tracking
   - Integrate news APIs (Bloomberg, CoinTelegraph)

2. **Customize Thread Building**
   - Add custom analysis functions
   - Integrate with your analytics engine
   - Auto-generate charts/images

3. **Production Deployment**
   - Set up monitoring/alerting
   - Add error recovery
   - Schedule with systemd or cron
   - Monitor logs and metrics

4. **Extended Features**
   - Vote/poll threads
   - Media/image attachment
   - Reply monitoring
   - Engagement tracking

## Related Files
- ThreadBuilder: [x_thread_builder.py](x_thread_builder.py) (515 lines)
- Poster: [x_poster.py](x_poster.py) (339 lines)
- RateLimiter: [x_rate_limiter.py](x_rate_limiter.py) (330 lines)
- NewsDetector: [x_news_detector.py](x_news_detector.py) (380 lines)
- Scheduler: [x_scheduler.py](x_scheduler.py) (310 lines)
- Integration: [x_integration.py](x_integration.py) (280 lines)

**Total X System**: ~1,950 lines of production-ready code
