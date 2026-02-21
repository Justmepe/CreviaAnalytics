"""
Discord Notification Module
Sends X threads and news reports to Discord via webhooks

Features:
- Thread notifications with emoji formatting
- News report summaries
- Price updates and market alerts
- Error handling and retry logic
- Markdown formatting for readability
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


class DiscordNotifier:
    """Send crypto analysis updates to Discord"""
    
    def __init__(self, webhook_url: Optional[str] = None, thread_webhook_url: Optional[str] = None,
                 news_webhook_url: Optional[str] = None):
        """
        Initialize Discord notifier

        Args:
            webhook_url: Default Discord webhook URL (or from env: DISCORD_WEBHOOK_URL)
            thread_webhook_url: Separate webhook for X threads (or from env: DISCORD_THREAD_WEBHOOK_URL)
            news_webhook_url: Separate webhook for news memos (or from env: DISCORD_NEWS_WEBHOOK_URL)
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL', '')
        self.thread_webhook_url = thread_webhook_url or os.getenv('DISCORD_THREAD_WEBHOOK_URL', '') or self.webhook_url
        self.news_webhook_url = news_webhook_url or os.getenv('DISCORD_NEWS_WEBHOOK_URL', '') or self.webhook_url
        self.enabled = bool(self.webhook_url)
        self.session = requests.Session()
    
    def send_x_thread(self, thread_data: Dict[str, Any]) -> bool:
        """
        Send X thread to Discord, one tweet per message.

        Strategy:
        1. Header embed announcing the thread
        2. Each tweet sent as its own Discord message (like a real thread)

        Args:
            thread_data: Dict with 'tweets', 'tweet_count', 'copy_paste_ready'

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        try:
            tweets = thread_data.get('tweets', [])
            tweet_count = thread_data.get('tweet_count', 0)

            # --- 1. Header embed ---
            embed = {
                "title": f"📊 X Thread ({tweet_count} tweets)",
                "description": "Complete crypto market analysis thread - READY TO POST",
                "color": 0x2E3338,
                "timestamp": datetime.utcnow().isoformat(),
            }

            payload = {
                "username": "Crypto Analysis Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055270.png",
                "embeds": [embed]
            }
            url = self.thread_webhook_url
            response = self.session.post(url, json=payload, timeout=10)

            if response.status_code != 204:
                print(f"⚠️  Discord: Failed to send thread header (HTTP {response.status_code})")
                try:
                    print(f"   Response: {response.text}")
                except Exception:
                    pass
                return False

            # --- 2. Send each tweet as its own message ---
            for tweet in tweets:
                tweet_text = tweet.strip()
                if not tweet_text:
                    continue
                # Truncate to Discord's 2000-char message limit
                msg_payload = {
                    "username": "Crypto Analysis Bot",
                    "content": tweet_text[:2000]
                }
                self.session.post(url, json=msg_payload, timeout=10)

            print(f"✅ Discord: X thread sent ({tweet_count} tweets)")
            return True
                
        except Exception as e:
            print(f"❌ Discord: Error sending thread: {e}")
            return False
    
    def send_news_report(self, ticker: str, memo: str, current_price: Optional[float] = None,
                         image_url: Optional[str] = None) -> bool:
        """
        Send news report to Discord

        Args:
            ticker: Asset ticker (BTC, ETH, etc)
            memo: News memo content
            current_price: Current price (optional)
            image_url: Image URL for embed thumbnail (optional)

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        try:
            # Extract first 500 chars of memo for preview
            preview = memo[:500] if memo else "No content"
            if len(memo) > 500:
                preview += "\n...[truncated]"

            # Determine color based on ticker
            color_map = {
                'BTC': 0xF7931A,  # Orange
                'ETH': 0x627EEA,  # Blue
            }
            color = color_map.get(ticker, 0x2E3338)

            embed = {
                "title": f"📰 News Report - {ticker}",
                "description": "Fact-checked market analysis from RSS feeds",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "📋 Summary",
                        "value": preview,
                        "inline": False
                    }
                ]
            }

            # Add image as embed thumbnail if available
            if image_url:
                embed["thumbnail"] = {"url": image_url}

            if current_price:
                embed["fields"].append({
                    "name": f"💰 Current Price",
                    "value": f"${current_price:,.2f}",
                    "inline": True
                })

            embed["fields"].append({
                "name": "🔗 Source",
                "value": "RSS Feeds + Claude AI",
                "inline": True
            })

            payload = {
                "username": "Crypto Analysis Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055270.png",
                "embeds": [embed]
            }

            response = self.session.post(self.news_webhook_url, json=payload, timeout=10)

            if response.status_code == 204:
                print(f"✅ Discord: News report sent for {ticker}")
                return True
            else:
                print(f"⚠️  Discord: Failed to send news (HTTP {response.status_code})")
                try:
                    print(f"   Response: {response.text}")
                except Exception:
                    pass
                return False

        except Exception as e:
            print(f"❌ Discord: Error sending news: {e}")
            return False

    def send_news_memo(self, ticker: str, memo: str, current_price: Optional[float] = None,
                       image_url: Optional[str] = None) -> bool:
        """
        Send a Claude-generated news memo to Discord with full content.

        For longer memos, splits into embed + follow-up message to stay
        within Discord's character limits.

        Args:
            ticker: Asset ticker (BTC, ETH, etc)
            memo: Full news memo content from NewsNarrator
            current_price: Current price (optional)
            image_url: Lead image URL for the embed (optional)

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        try:
            color_map = {
                'BTC': 0xF7931A,
                'ETH': 0x627EEA,
                'SOL': 0x9945FF,
                'BNB': 0xF3BA2F,
            }
            color = color_map.get(ticker, 0x2E3338)

            # Build description: full memo up to Discord's 4096 char embed description limit
            description = memo[:4000] if memo else "No content"
            if len(memo) > 4000:
                description += "\n\n*...continued below*"

            embed = {
                "title": f"📝 Market Memo - {ticker}",
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "RSS Feeds + Claude AI"},
                "fields": []
            }

            # Add lead image
            if image_url:
                embed["image"] = {"url": image_url}

            if current_price:
                embed["fields"].append({
                    "name": "💰 Price at Generation",
                    "value": f"${current_price:,.2f}",
                    "inline": True
                })

            payload = {
                "username": "Crypto Analysis Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055270.png",
                "embeds": [embed]
            }

            url = self.news_webhook_url
            response = self.session.post(url, json=payload, timeout=10)

            if response.status_code != 204:
                print(f"⚠️  Discord: Failed to send memo (HTTP {response.status_code})")
                try:
                    print(f"   Response: {response.text}")
                except Exception:
                    pass
                return False

            # Send overflow as a follow-up plain message if memo exceeds embed limit
            if len(memo) > 4000:
                overflow = memo[4000:6000]
                overflow_payload = {
                    "username": "Crypto Analysis Bot",
                    "content": f"**{ticker} Memo (continued):**\n{overflow}"
                }
                self.session.post(url, json=overflow_payload, timeout=10)

            print(f"✅ Discord: News memo sent for {ticker}")
            return True

        except Exception as e:
            print(f"❌ Discord: Error sending memo: {e}")
            return False
    
    def send_market_update(self, market_data: Dict[str, Any]) -> bool:
        """
        Send market update snapshot
        
        Args:
            market_data: Global market metrics
        
        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False
        
        try:
            total_mcap = market_data.get('total_market_cap', 0)
            btc_dom = market_data.get('btc_dominance', 0)
            fear_greed = market_data.get('fear_greed_equivalent', 50)
            
            # Determine sentiment color
            if fear_greed < 25:
                sentiment = "😱 Extreme Fear"
                color = 0xFF0000  # Red
            elif fear_greed < 45:
                sentiment = "😨 Fear"
                color = 0xFF6600  # Orange
            elif fear_greed < 55:
                sentiment = "😐 Neutral"
                color = 0xFFFF00  # Yellow
            elif fear_greed < 75:
                sentiment = "😊 Greed"
                color = 0x00FF00  # Green
            else:
                sentiment = "🤑 Extreme Greed"
                color = 0x00AA00  # Dark Green
            
            embed = {
                "title": "🌍 Global Market Update",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "📊 Total Market Cap",
                        "value": f"${total_mcap:,.0f}",
                        "inline": True
                    },
                    {
                        "name": "₿ BTC Dominance",
                        "value": f"{btc_dom:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "😊 Sentiment",
                        "value": sentiment,
                        "inline": False
                    }
                ]
            }
            
            payload = {
                "username": "Crypto Analysis Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055270.png",
                "embeds": [embed]
            }
            
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ Discord: Market update sent")
                return True
            else:
                print(f"⚠️  Discord: Failed to send update (HTTP {response.status_code})")
                try:
                    print(f"   Response: {response.text}")
                except Exception:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ Discord: Error sending update: {e}")
            return False
    
    def send_validation_test(self) -> bool:
        """
        Send validation test message to verify webhook
        
        Returns:
            bool: Success status
        """
        if not self.enabled:
            print("❌ Discord: Webhook URL not configured")
            return False
        
        try:
            embed = {
                "title": "✅ Webhook Connection Successful",
                "description": "Discord integration is working! Ready to receive crypto analysis updates.",
                "color": 0x00FF00,  # Green
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "📊 What you'll receive:",
                        "value": "• X threads (copy-paste ready)\n• News reports (fact-checked)\n• Market updates (daily)\n• Price alerts (threshold-based)",
                        "inline": False
                    },
                    {
                        "name": "🚀 Status",
                        "value": "Active and monitoring",
                        "inline": True
                    },
                    {
                        "name": "⏰ Frequency",
                        "value": "Real-time updates",
                        "inline": True
                    }
                ]
            }
            
            payload = {
                "username": "Crypto Analysis Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055270.png",
                "embeds": [embed]
            }
            
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Discord: Validation test successful - webhook is working!")
                return True
            else:
                print(f"❌ Discord: Webhook test failed (HTTP {response.status_code})")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Discord: Error testing webhook: {e}")
            return False
    
    def close(self):
        """Close session"""
        self.session.close()
