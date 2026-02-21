"""
X/Twitter News Detector
Monitors market data and news feeds to automatically trigger breaking news threads.

Detection Types:
1. Price Moves: BTC/ETH ±2%, altcoins ±5% (configurable)
2. Trending Alerts: Detect trending keywords/hashtags
3. Market Events: Large volume spikes, exchange flows, liquidations
4. News API: Structured news from multiple sources

Integration: Feeds detected events to X posting queue via NewsOutlet callback
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Thread, Lock, Event


class NewsSource(Enum):
    """Supported news and data sources"""
    COINGECKO = "coingecko"  # Free market data
    CRYPTO_PANIC = "cryptopanic"  # Free news aggregator
    COINMARKET_CAP = "coinmarketcap"  # Market data
    TWITTER_TRENDING = "twitter_trending"  # X trending topics
    REDDIT = "reddit"  # r/cryptocurrency trending posts
    BLOOM_BERG = "bloomberg"  # Bloomberg API (if available)


@dataclass
class NewsAlert:
    """Represents a detected news event"""
    source: NewsSource
    title: str
    description: str
    impact: str  # 'high', 'medium', 'low'
    asset: Optional[str] = None  # BTC, ETH, etc.
    price_change: Optional[float] = None  # % change
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source.value,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'asset': self.asset,
            'price_change': self.price_change,
            'created_at': self.created_at
        }


class PriceMoveDetector:
    """Detect significant price movements"""
    
    def __init__(
        self,
        major_threshold: float = 2.0,  # BTC, ETH
        alt_threshold: float = 5.0,    # Other assets
        min_interval: int = 300        # Min 5 min between alerts for same asset
    ):
        self.major_threshold = major_threshold
        self.alt_threshold = alt_threshold
        self.min_interval = min_interval
        self.last_alert: Dict[str, float] = {}
        self.lock = Lock()
    
    def is_major_asset(self, asset: str) -> bool:
        """Check if asset is in major category (stricter thresholds)"""
        major = ['BTC', 'ETH', 'SOL', 'XRP']
        return asset.upper() in major
    
    def detect(
        self,
        asset: str,
        current_price: float,
        previous_price: float,
        metadata: Dict[str, Any] = None
    ) -> Optional[NewsAlert]:
        """
        Detect if price move warrants alert.
        
        Args:
            asset: Asset symbol (BTC, ETH, etc.)
            current_price: Current price
            previous_price: Previous price
            metadata: Additional data (volume, market_cap, etc.)
        
        Returns:
            NewsAlert if move is significant, None otherwise
        """
        if previous_price <= 0:
            return None
        
        with self.lock:
            # Check rate limit for this asset
            now = time.time()
            last = self.last_alert.get(asset, 0)
            if (now - last) < self.min_interval:
                return None
        
        # Calculate price change
        pct_change = ((current_price - previous_price) / previous_price) * 100
        threshold = self.major_threshold if self.is_major_asset(asset) else self.alt_threshold
        
        if abs(pct_change) < threshold:
            return None
        
        with self.lock:
            self.last_alert[asset] = now
        
        # Determine impact severity
        impact = 'low'
        if abs(pct_change) > threshold * 2:
            impact = 'high'
        elif abs(pct_change) > threshold * 1.5:
            impact = 'medium'
        
        direction = "📈 UP" if pct_change > 0 else "📉 DOWN"
        
        return NewsAlert(
            source=NewsSource.COINGECKO,
            title=f"{asset} Price Alert: {direction} {abs(pct_change):.1f}%",
            description=f"{asset} moved {pct_change:+.2f}% to ${current_price:,.2f}",
            impact=impact,
            asset=asset,
            price_change=pct_change
        )


class TrendingDetector:
    """Detect trending keywords and hashtags"""
    
    def __init__(self, min_frequency: int = 5):
        self.min_frequency = min_frequency
        self.keyword_history: Dict[str, List[float]] = {}
        self.trending_keywords: Dict[str, int] = {}
        self.lock = Lock()
    
    def add_keyword(self, keyword: str):
        """Record a keyword occurrence"""
        with self.lock:
            now = time.time()
            if keyword not in self.keyword_history:
                self.keyword_history[keyword] = []
            
            # Keep only last hour of data
            one_hour_ago = now - 3600
            self.keyword_history[keyword] = [
                t for t in self.keyword_history[keyword] if t > one_hour_ago
            ]
            self.keyword_history[keyword].append(now)
    
    def get_trending(self, lookback_minutes: int = 60) -> Dict[str, int]:
        """Get trending keywords in last N minutes"""
        with self.lock:
            now = time.time()
            cutoff = now - (lookback_minutes * 60)
            
            trending = {}
            for keyword, timestamps in self.keyword_history.items():
                count = len([t for t in timestamps if t > cutoff])
                if count >= self.min_frequency:
                    trending[keyword] = count
            
            return dict(sorted(trending.items(), key=lambda x: x[1], reverse=True))
    
    def detect(self, keywords: List[str]) -> Optional[NewsAlert]:
        """
        Detect if any keywords are trending.
        
        Args:
            keywords: List of keywords/hashtags detected in current data
        
        Returns:
            NewsAlert if trending detected, None otherwise
        """
        for keyword in keywords:
            self.add_keyword(keyword)
        
        trending = self.get_trending(lookback_minutes=30)
        if not trending:
            return None
        
        top_keywords = list(trending.keys())[:3]
        
        return NewsAlert(
            source=NewsSource.TWITTER_TRENDING,
            title=f"Trending in Crypto: {', '.join([f'#{k}' for k in top_keywords])}",
            description=f"Keywords trending: {', '.join([f'{k} ({trending[k]})' for k in top_keywords])}",
            impact='medium'
        )


class VolumeDetector:
    """Detect unusual trading volume spikes"""
    
    def __init__(self, spike_threshold: float = 2.0):
        self.spike_threshold = spike_threshold
        self.volume_history: Dict[str, List[Tuple[float, float]]] = {}  # [(timestamp, volume)]
        self.lock = Lock()
    
    def detect(self, asset: str, current_volume: float) -> Optional[NewsAlert]:
        """
        Detect if volume spike warrants alert.
        
        Args:
            asset: Asset symbol
            current_volume: Current trading volume in USD
        
        Returns:
            NewsAlert if spike detected, None otherwise
        """
        with self.lock:
            if asset not in self.volume_history:
                self.volume_history[asset] = []
            
            now = time.time()
            self.volume_history[asset].append((now, current_volume))
            
            # Keep only last 24 hours
            day_ago = now - 86400
            self.volume_history[asset] = [
                (t, v) for t, v in self.volume_history[asset] if t > day_ago
            ]
            
            if len(self.volume_history[asset]) < 4:
                return None
            
            # Calculate average from last 4 hours
            four_hours_ago = now - (4 * 3600)
            recent_volumes = [v for t, v in self.volume_history[asset] if t > four_hours_ago]
            
            if not recent_volumes:
                return None
            
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            if current_volume < (avg_volume * self.spike_threshold):
                return None
        
        spike_pct = ((current_volume - avg_volume) / avg_volume) * 100
        
        return NewsAlert(
            source=NewsSource.COINGECKO,
            title=f"{asset} Volume Spike: {spike_pct:+.0f}%",
            description=f"{asset} trading volume spiked {spike_pct:+.1f}% to ${current_volume:,.0f}",
            impact='medium',
            asset=asset
        )


class XNewsDetector:
    """
    Main detector coordinating all news sources.
    
    Monitors price moves, trends, volume, and news to trigger breaking news threads.
    """
    
    def __init__(
        self,
        alert_callback: Optional[Callable[[NewsAlert], None]] = None,
        alert_log: str = "data/x_news_alerts.json"
    ):
        self.alert_callback = alert_callback
        self.alert_log = alert_log
        
        # Detectors
        self.price_detector = PriceMoveDetector()
        self.trend_detector = TrendingDetector()
        self.volume_detector = VolumeDetector()
        
        # History
        self.alerts: List[NewsAlert] = []
        self.lock = Lock()
        self.running = False
        self.worker_thread: Optional[Thread] = None
        
        self._load_alerts()
    
    def _load_alerts(self):
        """Load alert history from log"""
        try:
            log_path = Path(self.alert_log)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    data = json.load(f)
                    # Keep only last 24 hours
                    twenty_four_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).timestamp()
                    for alert_dict in data:
                        try:
                            ts = datetime.fromisoformat(alert_dict.get('created_at', '')).timestamp()
                            if ts > twenty_four_hours_ago:
                                # Reconstruct NewsAlert (simplified for now)
                                self.alerts.append(alert_dict)
                        except:
                            pass
        except Exception as e:
            print(f"[WARN] NewsDetector: Failed to load alerts: {e}")
    
    def _save_alert(self, alert: NewsAlert):
        """Save alert to log file"""
        try:
            log_path = Path(self.alert_log)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            alerts_list = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    alerts_list = json.load(f)
            
            alerts_list.append(alert.to_dict())
            
            # Keep only last 7 days
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7))
            alerts_list = [a for a in alerts_list if a.get('created_at', '') != '']
            
            with open(log_path, 'w') as f:
                json.dump(alerts_list, f, indent=2)
        except Exception as e:
            print(f"[WARN] NewsDetector: Failed to save alert: {e}")
    
    def check_price_move(
        self,
        asset: str,
        current_price: float,
        previous_price: float
    ) -> Optional[NewsAlert]:
        """
        Check for price movement alert.
        
        Returns:
            NewsAlert if detected, None otherwise
        """
        alert = self.price_detector.detect(asset, current_price, previous_price)
        
        if alert:
            self._register_alert(alert)
        
        return alert
    
    def check_trending(self, keywords: List[str]) -> Optional[NewsAlert]:
        """
        Check for trending keywords alert.
        
        Returns:
            NewsAlert if detected, None otherwise
        """
        alert = self.trend_detector.detect(keywords)
        
        if alert:
            self._register_alert(alert)
        
        return alert
    
    def check_volume_spike(self, asset: str, volume: float) -> Optional[NewsAlert]:
        """
        Check for volume spike alert.
        
        Returns:
            NewsAlert if detected, None otherwise
        """
        alert = self.volume_detector.detect(asset, volume)
        
        if alert:
            self._register_alert(alert)
        
        return alert
    
    def _register_alert(self, alert: NewsAlert):
        """Register an alert internally and call callback if set"""
        with self.lock:
            self.alerts.append(alert)
            self._save_alert(alert)
        
        print(f"[ALERT] NewsDetector: {alert.title} ({alert.impact.upper()})")
        
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                print(f"[ERR] NewsDetector: Alert callback failed: {e}")
    
    def get_recent_alerts(self, minutes: int = 60, impact: Optional[str] = None) -> List[NewsAlert]:
        """
        Get recent alerts.
        
        Args:
            minutes: Look back N minutes
            impact: Filter by impact level ('high', 'medium', 'low')
        
        Returns:
            List of NewsAlert objects
        """
        with self.lock:
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp()
            alert_dicts = [a for a in self.alerts if isinstance(a, dict)]
            
            filtered = []
            for a in alert_dicts:
                try:
                    ts = datetime.fromisoformat(a.get('created_at', '')).timestamp()
                    if ts > cutoff:
                        if impact is None or a.get('impact') == impact:
                            filtered.append(a)
                except:
                    pass
            
            return filtered
    
    def get_status(self) -> Dict[str, Any]:
        """Get detector status"""
        with self.lock:
            high_impact = [a for a in self.get_recent_alerts(minutes=30) if a.get('impact') == 'high']
            
            return {
                'running': self.running,
                'recent_alerts_30m': len(self.get_recent_alerts(minutes=30)),
                'high_impact_alerts': len(high_impact),
                'trending_keywords': self.trend_detector.get_trending(lookback_minutes=30),
                'total_alerts_24h': len(self.get_recent_alerts(minutes=1440))
            }
    
    def start(self):
        """Start detector (placeholder for continuous monitoring)"""
        self.running = True
        print("[OK] NewsDetector: Started")
    
    def stop(self):
        """Stop detector"""
        self.running = False
        print("[--] NewsDetector: Stopped")
