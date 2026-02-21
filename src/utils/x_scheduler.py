"""
X/Twitter Scheduler
Coordinates daily scans, hourly monitoring, and async posting queue.

Schedule:
- Daily Scan: 8 AM UTC (summary of last 24 hours)
- Hourly Scan: Every hour on the hour (real-time market updates)
- Breaking News: Event-triggered (from news detector)
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Dict, Any, Optional, Callable
from threading import Thread, Lock, Event
import json
from pathlib import Path

try:
    import schedule
except ImportError:
    schedule = None


class DailyScheduleTask:
    """Represents a daily scheduled task"""
    
    def __init__(
        self,
        name: str,
        hour: int,
        minute: int,
        callback: Callable
    ):
        self.name = name
        self.hour = hour
        self.minute = minute
        self.callback = callback
        self.last_run: Optional[datetime] = None
    
    def should_run(self, now: datetime) -> bool:
        """Check if task should run now"""
        task_time = dtime(self.hour, self.minute)
        current_time = now.time()
        
        # Run if we've reached the scheduled time and haven't run today
        if current_time >= task_time:
            if self.last_run is None or self.last_run.date() < now.date():
                return True
        
        return False
    
    async def execute(self):
        """Execute the scheduled task"""
        print(f"[...] Scheduler: Running {self.name}...")
        try:
            result = self.callback()
            if asyncio.iscoroutine(result):
                await result
            self.last_run = datetime.now(timezone.utc)
            print(f"[OK] Scheduler: {self.name} completed")
            return True
        except Exception as e:
            print(f"[ERR] Scheduler: {self.name} failed: {e}")
            return False


class HourlyMonitorTask:
    """Monitor for hourly changes"""
    
    def __init__(
        self,
        name: str,
        callback: Callable,
        every_n_hours: int = 1
    ):
        self.name = name
        self.callback = callback
        self.every_n_hours = every_n_hours
        self.last_run: Optional[datetime] = None
    
    def should_run(self, now: datetime) -> bool:
        """Check if task should run now"""
        if self.last_run is None:
            return True
        
        time_since_last = (now - self.last_run).total_seconds()
        min_interval = self.every_n_hours * 3600
        
        return time_since_last >= min_interval
    
    async def execute(self):
        """Execute the monitor task"""
        print(f"[...] Scheduler: Running {self.name}...")
        try:
            result = self.callback()
            if asyncio.iscoroutine(result):
                await result
            self.last_run = datetime.now(timezone.utc)
            print(f"[OK] Scheduler: {self.name} completed")
            return True
        except Exception as e:
            print(f"[ERR] Scheduler: {self.name} failed: {e}")
            return False


class XScheduler:
    """
    Coordinate X posting schedule and news monitoring.
    
    Manages:
    - Daily scan thread (8 AM UTC)
    - Hourly monitoring (every hour)
    - Breaking news triggers (event-based)
    - Async posting queue
    """
    
    def __init__(
        self,
        thread_builder_callback: Callable,  # Returns thread_data dict
        queue_callback: Callable,           # Takes thread_data, returns awaitable
        news_detector_callback: Callable,   # Monitors for news
        log_file: str = "data/x_scheduler_log.json"
    ):
        """
        Initialize scheduler.
        
        Args:
            thread_builder_callback: Function to build daily/hourly thread data
                                    Signature: daily_scan() or hourly_scan(data)
            queue_callback: Function to queue a post for async posting
                           Signature: async queue_post(thread_data)
            news_detector_callback: Function to check for news alerts
                                   Signature: async check_news() -> NewsAlert or None
            log_file: Path to scheduler log
        """
        self.thread_builder = thread_builder_callback
        self.queue_post = queue_callback
        self.check_news = news_detector_callback
        self.log_file = log_file
        
        # Schedule tasks
        self.daily_task: Optional[DailyScheduleTask] = None
        self.hourly_task: Optional[HourlyMonitorTask] = None
        self.breaking_news_monitor: Optional[Thread] = None
        
        # State
        self.running = False
        self.lock = Lock()
        self.stop_event = Event()
        
        self._setup_tasks()
    
    def _setup_tasks(self):
        """Initialize scheduled tasks"""
        # Daily scan at 8 AM UTC
        self.daily_task = DailyScheduleTask(
            name="Daily Market Scan",
            hour=8,
            minute=0,
            callback=self._run_daily_scan
        )
        
        # Hourly monitor every hour
        self.hourly_task = HourlyMonitorTask(
            name="Hourly Market Monitor",
            callback=self._run_hourly_monitor,
            every_n_hours=1
        )
    
    def _run_daily_scan(self) -> Dict[str, Any]:
        """Build and queue daily scan thread"""
        print("[...] Scheduler: Building daily scan thread...")
        
        try:
            # Get daily market summary data (integrate with your data source)
            # This is a placeholder - replace with actual data retrieval
            market_data = {
                'period': '24h',
                'top_movers': {
                    'gainers': ['BTC (+2.5%)', 'ETH (+1.8%)'],
                    'losers': ['SHIB (-3.2%)']
                },
                'market_cap_change': '+1.2%',
                'total_volume': '$850B',
                'dominant_asset': 'Bitcoin'
            }
            
            # Build thread
            thread_data = self.thread_builder(market_data)
            
            if thread_data and thread_data.get('tweets'):
                self._log_action('daily_scan_queued', {
                    'tweet_count': len(thread_data.get('tweets', [])),
                    'type': 'daily_scan'
                })
                print(f"[OK] Scheduler: Daily scan thread ready ({len(thread_data.get('tweets', []))} tweets)")
                return thread_data
            else:
                print("[WARN] Scheduler: Failed to build daily scan thread")
                return None
        except Exception as e:
            print(f"[ERR] Scheduler: Daily scan error: {e}")
            return None
    
    def _run_hourly_monitor(self) -> Dict[str, Any]:
        """Build and queue hourly market monitor thread"""
        print("[...] Scheduler: Building hourly market thread...")
        
        try:
            # Get current market snapshot (integrate with your data source)
            market_data = {
                'period': '1h',
                'price_changes': {
                    'BTC': 0.5,
                    'ETH': -0.3,
                    'SOL': 1.2
                },
                'key_events': ['Altcoin trading volume up 15%'],
                'market_sentiment': 'bullish'
            }
            
            # Build thread
            thread_data = self.thread_builder(market_data)
            
            if thread_data and thread_data.get('tweets'):
                self._log_action('hourly_scan_queued', {
                    'tweet_count': len(thread_data.get('tweets', [])),
                    'type': 'hourly_scan'
                })
                print(f"[OK] Scheduler: Hourly thread ready ({len(thread_data.get('tweets', []))} tweets)")
                return thread_data
            else:
                print("[WARN] Scheduler: Failed to build hourly thread")
                return None
        except Exception as e:
            print(f"[ERR] Scheduler: Hourly monitor error: {e}")
            return None
    
    async def _breaking_news_monitor(self):
        """Continuously monitor for breaking news (runs in background)"""
        print("[OK] Scheduler: Breaking news monitor started")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Check for news alerts
                alert = self.check_news()
                
                if alert and hasattr(alert, 'impact') and alert.impact == 'high':
                    print(f"[ALERT] Scheduler: High-impact news detected: {alert.title}")
                    
                    # Build breaking news thread
                    breaking_data = {
                        'type': 'breaking_news',
                        'alert': alert.to_dict() if hasattr(alert, 'to_dict') else alert,
                        'context': f"Alert: {alert.title}"
                    }
                    
                    # Queue for posting
                    if self.queue_post:
                        try:
                            await self.queue_post(breaking_data)
                            self._log_action('breaking_news_queued', {
                                'title': alert.title,
                                'impact': alert.impact
                            })
                        except Exception as e:
                            print(f"[ERR] Scheduler: Failed to queue breaking news: {e}")
                
                # Check every 30 seconds
                await asyncio.sleep(30)
            
            except Exception as e:
                print(f"[ERR] Scheduler: Breaking news monitor error: {e}")
                await asyncio.sleep(60)
        
        print("[--] Scheduler: Breaking news monitor stopped")
    
    def _log_action(self, action: str, data: Dict[str, Any]):
        """Log scheduler actions"""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': action,
                'data': data
            }
            
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            
            logs.append(log_entry)
            
            # Keep only last 7 days
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7))
            
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[WARN] Scheduler: Failed to log action: {e}")
    
    async def start(self):
        """Start the scheduler (runs async tasks)"""
        self.running = True
        self.stop_event.clear()
        print("[OK] Scheduler: Started")
        
        # Start breaking news monitor in background
        monitor_task = asyncio.create_task(self._breaking_news_monitor())
        
        # Main scheduling loop
        try:
            while self.running and not self.stop_event.is_set():
                now = datetime.now(timezone.utc)
                
                # Check daily task
                if self.daily_task and self.daily_task.should_run(now):
                    await self.daily_task.execute()
                
                # Check hourly task
                if self.hourly_task and self.hourly_task.should_run(now):
                    await self.hourly_task.execute()
                
                # Sleep before next check (every 1 minute)
                await asyncio.sleep(60)
        
        except asyncio.CancelledError:
            print("[--] Scheduler: Cancelled")
        except Exception as e:
            print(f"[ERR] Scheduler: Fatal error: {e}")
        finally:
            self.running = False
            self.stop_event.set()
            print("[--] Scheduler: Stopped")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.stop_event.set()
        print("[--] Scheduler: Stopping...")
    
    def get_schedule(self) -> Dict[str, Any]:
        """Get current schedule info"""
        with self.lock:
            return {
                'running': self.running,
                'daily_scan': {
                    'scheduled_time': '08:00 UTC',
                    'last_run': self.daily_task.last_run.isoformat() if self.daily_task and self.daily_task.last_run else None
                },
                'hourly_monitor': {
                    'frequency': 'Every hour',
                    'last_run': self.hourly_task.last_run.isoformat() if self.hourly_task and self.hourly_task.last_run else None
                }
            }
    
    def trigger_manual_scan(self, scan_type: str = 'daily') -> Optional[Dict[str, Any]]:
        """
        Manually trigger a scan (for testing or immediate posting).
        
        Args:
            scan_type: 'daily' or 'hourly'
        
        Returns:
            Thread data if successful, None otherwise
        """
        if scan_type == 'daily':
            return self._run_daily_scan()
        elif scan_type == 'hourly':
            return self._run_hourly_monitor()
        else:
            print(f"[ERR] Scheduler: Unknown scan type: {scan_type}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed scheduler status"""
        return {
            'running': self.running,
            'schedule': self.get_schedule(),
            'next_daily_scan': self._get_next_daily_time(),
            'next_hourly_scan': self._get_next_hourly_time()
        }
    
    def _get_next_daily_time(self) -> str:
        """Calculate next daily scan time"""
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run.isoformat()
    
    def _get_next_hourly_time(self) -> str:
        """Calculate next hourly scan time"""
        now = datetime.now(timezone.utc)
        next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        return next_run.isoformat()
