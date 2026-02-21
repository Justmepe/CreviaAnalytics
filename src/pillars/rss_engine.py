"""
File: rss_engine.py
Purpose: Replace CryptoPanic API with local RSS aggregation and search
Dependencies: feedparser, dateparser, beautifulsoup4
"""

import os
import feedparser
import dateparser
import re
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json
from typing import List, Dict, Optional

# 1. Configuration: Curated RSS Feeds for Balanced Crypto News
# Based on industry reputation and reliability

# Core Crypto News (High Velocity Layer) - Poll every 1-2 minutes
HIGH_VELOCITY_FEEDS = [
    {
        'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'name': 'CoinDesk',
        'category': 'crypto_core',
        'description': 'Institutional-grade reporting, breaking news, policy scoops'
    },
    {
        'url': 'https://cointelegraph.com/rss',
        'name': 'Cointelegraph',
        'category': 'crypto_core',
        'description': 'High volume updates, broad market coverage'
    },
    {
        'url': 'https://www.theblock.co/rss.xml',
        'name': 'The Block',
        'category': 'crypto_core',
        'description': 'Research-driven, institutional insights, DeFi deep dives'
    },
    {
        'url': 'https://decrypt.co/feed',
        'name': 'Decrypt',
        'category': 'crypto_core',
        'description': 'Clarity-focused, Web3 culture and tech'
    },
    {
        'url': 'https://bitcoinmagazine.com/.rss/full/',
        'name': 'Bitcoin Magazine',
        'category': 'crypto_core',
        'description': 'Bitcoin ecosystem, maximalist infrastructure news'
    }
]

# Fed & Macro Layer (Market Movers) - Poll every 5 minutes
MACRO_FEEDS = [
    {
        'url': 'https://www.federalreserve.gov/feeds/press_all.xml',
        'name': 'Federal Reserve',
        'category': 'macro',
        'description': 'FOMC decisions, rate hikes, monetary policy'
    },
    {
        'url': 'https://www.treasury.gov/rss/press-releases.xml',
        'name': 'US Treasury',
        'category': 'macro',
        'description': 'OFAC sanctions, stablecoin regulation, AML policy'
    },
    {
        'url': 'https://www.sec.gov/rss/news/press.xml',
        'name': 'SEC',
        'category': 'macro',
        'description': 'Securities regulation, ETF approvals, lawsuits'
    },
    {
        'url': 'https://www.whitehouse.gov/briefing-room/feed/',
        'name': 'The White House',
        'category': 'macro',
        'description': 'Executive orders, official statements on digital assets'
    }
]

# Global Finance & Broad Market Context - Poll every 5 minutes
GLOBAL_FINANCE_FEEDS = [
    {
        'url': 'https://www.cnbc.com/id/10000664/device/rss/rss.html',
        'name': 'CNBC Finance',
        'category': 'global_finance',
        'description': 'Stock market correlation, investor sentiment'
    },
    {
        'url': 'https://finance.yahoo.com/news/rssindex',
        'name': 'Yahoo Finance',
        'category': 'global_finance',
        'description': 'Broad market overview, earnings reports, economic data'
    },
    {
        'url': 'https://www.stlouisfed.org/newsroom/news-releases?format=rss',
        'name': 'St. Louis Fed (FRED)',
        'category': 'global_finance',
        'description': 'Economic data releases, inflation, employment metrics'
    },
    # Reuters / major wire services
    {
        'url': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
        'name': 'Reuters',
        'category': 'global_finance',
        'description': 'Global financial wire, breaking macro news'
    },
    # MarketWatch
    {
        'url': 'https://feeds.marketwatch.com/marketwatch/topstories/',
        'name': 'MarketWatch',
        'category': 'global_finance',
        'description': 'US market coverage, Fed, earnings, economy'
    },
    # Forex & commodities
    {
        'url': 'https://www.forexlive.com/feed/',
        'name': 'ForexLive',
        'category': 'global_finance',
        'description': 'Forex, central bank decisions, rate expectations'
    },
    # Bloomberg via Google News (Bloomberg blocks direct RSS)
    {
        'url': 'https://news.google.com/rss/search?q=site:bloomberg.com+economy+OR+fed+OR+markets&hl=en-US&gl=US&ceid=US:en',
        'name': 'Bloomberg (via Google)',
        'category': 'global_finance',
        'description': 'Bloomberg economy and market coverage'
    },
    # Financial Times via Google News
    {
        'url': 'https://news.google.com/rss/search?q=site:ft.com+markets+OR+central+bank+OR+economy&hl=en-US&gl=US&ceid=US:en',
        'name': 'FT (via Google)',
        'category': 'global_finance',
        'description': 'FT global markets and central bank coverage'
    },
]

# Technical & On-Chain Updates (Bleeding Edge) - Poll every 5 minutes
TECHNICAL_FEEDS = [
    {
        'url': 'https://github.com/bitcoin/bitcoin/releases.atom',
        'name': 'Bitcoin (Github)',
        'category': 'technical',
        'description': 'Bitcoin core releases, version updates, protocol changes'
    },
    {
        'url': 'https://github.com/ethereum/go-ethereum/releases.atom',
        'name': 'Ethereum (Github)',
        'category': 'technical',
        'description': 'Geth releases, Ethereum protocol updates'
    },
    {
        'url': 'https://github.com/ethereum/consensus-specs/releases.atom',
        'name': 'Ethereum Consensus (Github)',
        'category': 'technical',
        'description': 'Ethereum consensus layer (Beacon chain) updates'
    },
]

# Project-Specific Updates (Direct from the Source) - Poll every 5 minutes
PROJECT_FEEDS = [
    {
        'url': 'https://bitcoincore.org/en/rss.xml',
        'name': 'Bitcoin Core',
        'category': 'project',
        'description': 'Bitcoin Core releases, technical updates, protocol milestones'
    },
    {
        'url': 'https://blog.ethereum.org/feed.xml',
        'name': 'Ethereum Foundation',
        'category': 'project',
        'description': 'Official Ethereum hard forks, upgrades, research'
    },
    {
        'url': 'https://solana.com/news/rss',
        'name': 'Solana Foundation',
        'category': 'project',
        'description': 'Solana ecosystem updates, network health, validator news'
    },
    {
        'url': 'https://www.bnbchain.org/en/blog/rss.xml',
        'name': 'BNB Chain',
        'category': 'project',
        'description': 'BNB ecosystem growth, token burns, validator updates'
    },
]

# Privacy Coins & Regulatory Tracks - Poll every 5 minutes
PRIVACY_COIN_FEEDS = [
    {
        'url': 'https://www.getmonero.org/feed.xml',
        'name': 'Monero (XMR)',
        'category': 'privacy_coins',
        'description': 'Official Monero releases, privacy updates, regulatory news'
    },
    {
        'url': 'https://zfnd.org/feed/',
        'name': 'Zcash Foundation',
        'category': 'privacy_coins',
        'description': 'Zcash protocol updates, research, ecosystem grants'
    },
]

# Community & Meme Coin Sentiment - Poll every 3 minutes (High Velocity)
MEME_COIN_FEEDS = [
    {
        'url': 'https://www.reddit.com/r/CryptoCurrency/.rss',
        'name': 'Reddit: CryptoCurrency',
        'category': 'sentiment',
        'description': 'Community sentiment, retail trading discussion, meme coin trends'
    },
    {
        'url': 'https://cryptoslate.com/cryptos/meme-coins/feed/',
        'name': 'CryptoSlate (Meme Coins)',
        'category': 'sentiment',
        'description': 'Meme coin data, on-chain analytics, social volume tracking'
    },
]

# Alternative & Advanced Macro Perspectives - Poll every 5 minutes
ALTERNATIVE_MACRO_FEEDS = [
    {
        'url': 'https://www.theblock.co/category/policy/rss.xml',
        'name': 'The Block (Policy)',
        'category': 'macro',
        'description': 'Deep policy analysis, regulatory frameworks, government crypto stance'
    },
    {
        'url': 'http://feeds.feedburner.com/zerohedge/feed',
        'name': 'ZeroHedge',
        'category': 'macro',
        'description': 'Contrarian macro analysis, global financial chaos early warnings'
    },
    {
        'url': 'https://www.ft.com/currencies?format=rss',
        'name': 'FT: Digital Currencies',
        'category': 'macro',
        'description': 'Financial Times perspective on CBDCs, digital assets, currency wars'
    },
]

# Google News Custom RSS Feeds (Secret Weapon) - Poll every 3 minutes
GOOGLE_NEWS_QUERIES = [
    # Crypto-specific
    'stablecoin regulation',
    'crypto ETF approval',
    'bitcoin SEC lawsuit',
    'binance listing',
    'ethereum upgrade',
    'solana ecosystem news',
    'crypto sanctions',
    'central bank digital currency',
    # Memecoins
    'memecoin dogecoin shiba inu',
    'pepe floki crypto meme token',
    # Privacy coins
    'monero privacy coin regulation',
    'zcash dash privacy crypto',
    # DeFi sector
    'defi regulation TVL',
    'aave uniswap curve lending',
    'lido staking liquid ethereum',
    'decentralized finance yield',
    # Fed & US monetary policy
    'federal reserve interest rate decision',
    'fed rate cut OR rate hike',
    'US inflation CPI data',
    'US treasury yields',
    'US jobs report nonfarm payrolls',
    # Global macro & geopolitics that move markets
    'China economy trade tariffs',
    'Russia sanctions oil price',
    'BRICS currency dollar',
    'Japan yen intervention central bank',
    'European Central Bank rate decision',
    'oil price OPEC production',
    'gold price safe haven',
    'US dollar index DXY forex',
    'trade war tariffs global markets',
    'bank failure financial crisis',
]

def generate_google_news_feeds():
    """Generate Google News RSS feeds for specific crypto queries"""
    base_url = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en"
    feeds = []

    for query in GOOGLE_NEWS_QUERIES:
        # URL encode the query
        encoded_query = query.replace(' ', '+')
        feeds.append({
            'url': base_url.format(encoded_query),
            'name': f'Google News: {query.title()}',
            'category': 'google_news',
            'description': f'Custom Google News feed for "{query}"'
        })

    return feeds

# Combine all feeds
RSS_FEEDS = (
    HIGH_VELOCITY_FEEDS + 
    MACRO_FEEDS + 
    GLOBAL_FINANCE_FEEDS + 
    TECHNICAL_FEEDS + 
    PROJECT_FEEDS + 
    PRIVACY_COIN_FEEDS + 
    MEME_COIN_FEEDS + 
    ALTERNATIVE_MACRO_FEEDS + 
    generate_google_news_feeds()
)

RSS_SEEN_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'rss_seen_state.json')


class CryptoNewsAggregator:
    # Ticker → list of search terms (lowercase) so "BTC" matches "bitcoin", etc.
    TICKER_ALIASES = {
        # Majors
        'BTC': ['btc', 'bitcoin', 'satoshi'],
        'ETH': ['eth', 'ethereum', 'ether', 'vitalik'],
        'SOL': ['sol', 'solana'],
        'BNB': ['bnb', 'binance'],
        # Memecoins
        'DOGE': ['doge', 'dogecoin'],
        'SHIB': ['shib', 'shiba'],
        'PEPE': ['pepe'],
        'FLOKI': ['floki'],
        # Privacy
        'XMR': ['xmr', 'monero'],
        'ZEC': ['zec', 'zcash'],
        'DASH': ['dash'],
        'SCRT': ['scrt', 'secret network'],
        # DeFi
        'AAVE': ['aave'],
        'UNI': ['uniswap'],
        'CRV': ['crv', 'curve'],
        'LDO': ['ldo', 'lido'],
        # Sector-level aliases (used by sector memo generation)
        'MEMECOINS': ['memecoin', 'meme coin', 'meme token', 'doge', 'dogecoin',
                      'shib', 'shiba', 'pepe', 'floki', 'bonk', 'wif'],
        'PRIVACY': ['privacy coin', 'monero', 'xmr', 'zcash', 'zec', 'dash',
                    'secret network', 'tornado cash', 'coin mixing'],
        'DEFI': ['defi', 'decentralized finance', 'aave', 'uniswap', 'curve',
                 'lido', 'tvl', 'yield farming', 'liquidity pool', 'lending protocol',
                 'dex', 'liquid staking'],
    }

    def __init__(self):
        self.articles = []
        self.last_update = None
        self.last_fetch_times = {}
        self.seen_urls = set()  # For deduplication by URL
        self.seen_titles = set()  # For fuzzy title deduplication

        # Polling intervals (in seconds) based on feed categories
        self.polling_intervals = {
            'crypto_core': 120,    # 2 minutes for high velocity crypto news
            'macro': 300,          # 5 minutes for fed/macro updates
            'global_finance': 300, # 5 minutes for global finance
            'technical': 300,      # 5 minutes for GitHub technical updates
            'project': 300,        # 5 minutes for direct project updates
            'privacy_coins': 300,  # 5 minutes for privacy coin feeds
            'sentiment': 180,      # 3 minutes for Reddit/social sentiment (high velocity)
            'google_news': 180     # 3 minutes for google news queries
        }

        # Initialize last fetch times for all feeds
        for feed in RSS_FEEDS:
            self.last_fetch_times[feed['url']] = 0

        # Load previously seen state from disk (survives restarts)
        self.load_seen_state()

    def fetch_all_feeds(self):
        """Polls RSS feeds based on tiered polling strategy with deduplication"""
        current_time = time.time()
        new_articles = []
        successful_feeds = 0
        feeds_polled = 0
        
        print(f"[...] Tiered polling strategy: Checking {len(RSS_FEEDS)} RSS feeds...")
        
        for feed in RSS_FEEDS:
            url = feed['url']
            category = feed['category']
            name = feed['name']
            
            # Check if this feed is due for polling
            time_since_last_fetch = current_time - self.last_fetch_times[url]
            polling_interval = self.polling_intervals.get(category, 300)  # Default 5 minutes
            
            if time_since_last_fetch < polling_interval:
                # Skip this feed, not due yet
                continue
                
            feeds_polled += 1
            try:
                print(f"  >> Fetching {category}: {name}...")
                # Add timeout and better error handling
                import requests
                # Use a realistic browser User-Agent to avoid blocks (e.g., TradingEconomics)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
                }
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                
                feed_data = feedparser.parse(response.content)
                source_name = feed_data.feed.get('title', name)
                
                feed_articles = 0
                for entry in feed_data.entries:
                    # Clean the summary (remove HTML tags)
                    raw_summary = entry.get('summary', '')
                    summary_text = self._clean_html(raw_summary)

                    # Extract image URL from entry
                    image_url = self._extract_image_url(entry, raw_summary)

                    # Create article with enhanced metadata
                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'published_at': self._parse_date(entry.get('published', '')),
                        'source': source_name,
                        'summary': summary_text,
                        'category': category,
                        'id': entry.get('id', entry.link),  # Unique ID for de-duplication
                        'image_url': image_url
                    }

                    # Check for duplicates
                    if self._is_duplicate(article):
                        continue

                    new_articles.append(article)
                    feed_articles += 1

                # Update last fetch time
                self.last_fetch_times[url] = current_time
                successful_feeds += 1
                print(f"    [OK] {feed_articles} new articles from {source_name}")

            except requests.exceptions.Timeout:
                print(f"    [TIMEOUT] Timeout: {name}")
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors gracefully
                if e.response.status_code == 403:
                    # Silently skip feeds that block us
                    pass
                elif e.response.status_code == 410:
                    # Feed permanently removed
                    pass
                else:
                    print(f"    [ERR] HTTP {e.response.status_code}: {name}")
            except requests.exceptions.RequestException as e:
                print(f"    [ERR] Network error: {name} - {str(e)[:50]}")
            except Exception as e:
                print(f"    [ERR] Error fetching {name}: {str(e)[:50]}")

        # De-duplicate and sort
        self._merge_articles(new_articles)
        print(f"[OK] Tiered polling complete. {feeds_polled} feeds checked, {successful_feeds} successful. Total indexed articles: {len(self.articles)}")

    def search_news(self, query: str = None, ticker: str = None, limit: int = 10,
                     include_broad_market: bool = False) -> List[Dict]:
        """
        Search your local database for specific news

        Args:
            query: Keywords like "regulation", "ETF"
            ticker: Asset symbol like "BTC", "ETH"
            include_broad_market: When True, pad results with general crypto/finance
                                 news so memos aren't starved for content.
        """
        results = self.articles

        # Filter by Ticker using aliases for much broader matching
        if ticker:
            aliases = self.TICKER_ALIASES.get(ticker.upper(), [ticker.lower()])
            results = [
                a for a in results
                if any(alias in a['title'].lower() or alias in a['summary'].lower()
                       for alias in aliases)
            ]

        # Filter by Search Query
        if query:
            query_lower = query.lower()
            results = [
                a for a in results
                if query_lower in a['title'].lower() or query_lower in a['summary'].lower()
            ]

        # If we don't have enough ticker-specific results, pad with broad market news
        if include_broad_market and len(results) < limit:
            broad_keywords = [
                # Crypto-specific
                'crypto', 'blockchain', 'defi', 'regulation', 'sec', 'etf', 'stablecoin',
                # Macro / central banks
                'fed', 'federal reserve', 'interest rate', 'rate cut', 'rate hike',
                'inflation', 'cpi', 'pce', 'treasury', 'yield', 'jobs report', 'nonfarm',
                'gdp', 'recession', 'monetary policy', 'quantitative',
                # Geopolitical / global
                'china', 'russia', 'sanctions', 'tariff', 'trade war', 'brics',
                'opec', 'oil price', 'gold price', 'dollar index', 'dxy', 'forex',
                'ecb', 'bank of japan', 'yen',
                # Broader finance
                'wall street', 'nasdaq', 's&p', 'stock market', 'bond market',
                'bank failure', 'liquidity', 'debt ceiling',
            ]
            existing_ids = {a['id'] for a in results}
            for a in self.articles:
                if a['id'] in existing_ids:
                    continue
                text = (a['title'] + ' ' + a['summary']).lower()
                if any(kw in text for kw in broad_keywords):
                    results.append(a)
                    existing_ids.add(a['id'])
                if len(results) >= limit:
                    break

        return results[:limit]

    def _is_duplicate(self, article):
        """Check if article is duplicate using URL and fuzzy title matching"""
        # Check URL duplication
        if article['link'] in self.seen_urls:
            return True
            
        # Check title duplication (simple fuzzy match)
        title_lower = article['title'].lower().strip()
        for seen_title in self.seen_titles:
            # Simple similarity check - if titles are very similar
            if self._titles_similar(title_lower, seen_title):
                return True
                
        # Not a duplicate, add to seen sets
        self.seen_urls.add(article['link'])
        self.seen_titles.add(title_lower)
        return False
    
    def _titles_similar(self, title1, title2, threshold=0.85):
        """Simple fuzzy title matching using word overlap"""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return False
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
            
        similarity = intersection / union
        return similarity >= threshold

    def _merge_articles(self, new_items):
        """Merges new items while avoiding duplicates"""
        existing_ids = {a['id'] for a in self.articles}
        for item in new_items:
            if item['id'] not in existing_ids:
                self.articles.append(item)
        
        # Sort by date (newest first)
        self.articles.sort(key=lambda x: x['published_at'] or datetime.min, reverse=True)

    def force_fetch_all_feeds(self):
        """Force fetch all feeds ignoring polling intervals (for initial setup)"""
        print("[...] Force fetching all RSS feeds for initial setup...")
        current_time = time.time()
        new_articles = []
        successful_feeds = 0
        
        for feed in RSS_FEEDS:
            url = feed['url']
            category = feed['category']
            name = feed['name']
            
            try:
                print(f"  >> Force fetching {category}: {name}...")
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
                }
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                
                feed_data = feedparser.parse(response.content)
                source_name = feed_data.feed.get('title', name)
                
                feed_articles = 0
                for entry in feed_data.entries:
                    raw_summary = entry.get('summary', '')
                    summary_text = self._clean_html(raw_summary)

                    # Extract image URL from entry
                    image_url = self._extract_image_url(entry, raw_summary)

                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'published_at': self._parse_date(entry.get('published', '')),
                        'source': source_name,
                        'summary': summary_text,
                        'category': category,
                        'id': entry.get('id', entry.link),
                        'image_url': image_url
                    }

                    if self._is_duplicate(article):
                        continue

                    new_articles.append(article)
                    feed_articles += 1
                
                # Update last fetch time
                self.last_fetch_times[url] = current_time
                successful_feeds += 1
                print(f"    [OK] {feed_articles} new articles from {source_name}")
                
            except Exception as e:
                print(f"    [ERR] Error fetching {name}: {str(e)[:50]}")

        self._merge_articles(new_articles)
        print(f"[OK] Force fetch complete. {successful_feeds}/{len(RSS_FEEDS)} feeds successful. Total indexed articles: {len(self.articles)}")

    def start_background_polling(self, interval_minutes=1):
        """Start background polling with tiered intervals"""
        import threading
        
        def poll_worker():
            while True:
                try:
                    self.fetch_all_feeds()
                except Exception as e:
                    print(f"[ERR] Background polling error: {e}")
                
                # Sleep for the specified interval
                time.sleep(interval_minutes * 60)
        
        polling_thread = threading.Thread(target=poll_worker, daemon=True)
        polling_thread.start()
        print(f"🟢 Background polling started (checking every {interval_minutes} minute{'s' if interval_minutes != 1 else ''})")
        return polling_thread

    def _extract_image_url(self, entry, raw_summary: str) -> Optional[str]:
        """
        Extract image URL from an RSS feed entry.

        Checks (in priority order):
        1. media:content or media:thumbnail (feedparser exposes as media_content/media_thumbnail)
        2. Enclosures with image MIME type
        3. <img> tags in the raw HTML summary
        """
        # 1. media:content (e.g. <media:content url="..." medium="image"/>)
        media_content = entry.get('media_content', [])
        for media in media_content:
            url = media.get('url', '')
            medium = media.get('medium', '')
            mtype = media.get('type', '')
            if url and (medium == 'image' or mtype.startswith('image/')):
                return url
        # Also check first media_content even without explicit medium attribute
        if media_content and media_content[0].get('url'):
            return media_content[0]['url']

        # media:thumbnail
        media_thumb = entry.get('media_thumbnail', [])
        if media_thumb and media_thumb[0].get('url'):
            return media_thumb[0]['url']

        # 2. Enclosures (e.g. <enclosure url="..." type="image/jpeg"/>)
        enclosures = entry.get('enclosures', [])
        for enc in enclosures:
            enc_type = enc.get('type', '')
            if enc.get('url') and enc_type.startswith('image/'):
                return enc['url']

        # 3. <img> tags in summary HTML
        if raw_summary:
            soup = BeautifulSoup(raw_summary, 'html.parser')
            img = soup.find('img', src=True)
            if img:
                return img['src']

        return None

    # Sources that use real photographs (Reuters, MarketWatch, Bloomberg, FT, etc.)
    # vs crypto-native sites that use cartoon/illustration art (Cointelegraph, CoinDesk)
    PHOTOGRAPHIC_SOURCES = [
        'reuters', 'marketwatch', 'bloomberg', 'financial times', 'ft.com',
        'cnbc', 'wsj', 'wall street journal', 'forexlive', 'trading economics',
        'yahoo finance', 'associated press', 'ap news', 'bbc', 'nytimes',
    ]
    ILLUSTRATION_SOURCES = [
        'cointelegraph', 'coindesk', 'decrypt', 'theblock', 'the block',
        'bitcoinist', 'newsbtc', 'u.today', 'beincrypto',
    ]

    def fetch_og_image(self, article_url: str) -> Optional[str]:
        """
        Fetch the Open Graph (og:image) meta tag from an article page.
        This gives the article-specific hero image, not a generic RSS thumbnail.

        Returns the og:image URL or None on failure.
        """
        if not article_url:
            return None
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
            }
            resp = requests.get(article_url, timeout=8, headers=headers)
            resp.raise_for_status()
            # Only parse the first 50KB to avoid downloading huge pages
            html_chunk = resp.text[:50000]
            soup = BeautifulSoup(html_chunk, 'html.parser')

            # Try og:image first (most reliable)
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                return og['content']

            # Try twitter:image as fallback
            tw = soup.find('meta', attrs={'name': 'twitter:image'})
            if tw and tw.get('content'):
                return tw['content']

            return None
        except Exception:
            return None

    def select_best_image(self, events: list, ticker: str = '') -> Optional[str]:
        """
        Pick the best contextual image for a set of news events.

        Strategy:
        1. Prefer images from photographic sources (Reuters, Bloomberg, etc.)
        2. If none, try fetching OG image from the top article's URL
        3. Fall back to any available RSS image
        4. Skip known-generic illustration sources if better options exist
        """
        photo_images = []
        illustration_images = []
        any_images = []

        for event in events:
            img = event.get('image_url')
            if not img:
                continue

            source_lower = (event.get('source') or '').lower()
            url_lower = (event.get('url') or '').lower()

            # Classify by source quality
            is_photo_source = any(ps in source_lower or ps in url_lower
                                  for ps in self.PHOTOGRAPHIC_SOURCES)
            is_illustration = any(il in source_lower or il in url_lower
                                  for il in self.ILLUSTRATION_SOURCES)

            if is_photo_source:
                photo_images.append(img)
            elif is_illustration:
                illustration_images.append(img)
            else:
                any_images.append(img)

        # 1. Best: photographic source image
        if photo_images:
            return photo_images[0]

        # 2. Try OG image from the top article URL (most relevant article first)
        for event in events[:3]:  # Only try top 3 to avoid too many HTTP requests
            url = event.get('url')
            if url:
                og_img = self.fetch_og_image(url)
                if og_img:
                    # Check it's not a generic site logo (skip tiny images or known logos)
                    if not self._is_generic_logo(og_img):
                        return og_img

        # 3. Unknown source images (might be decent)
        if any_images:
            return any_images[0]

        # 4. Last resort: illustration (better than nothing)
        if illustration_images:
            return illustration_images[0]

        return None

    def _is_generic_logo(self, img_url: str) -> bool:
        """Detect obviously generic logos/icons that shouldn't be used as article images."""
        if not img_url:
            return True
        lower = img_url.lower()
        # Skip tiny icons, favicons, logos
        generic_patterns = [
            'favicon', 'logo', 'icon', 'avatar', 'badge',
            '1x1', 'pixel', 'spacer', 'blank',
            'default-thumb', 'placeholder',
        ]
        return any(p in lower for p in generic_patterns)

    def save_seen_state(self):
        """Persist seen_urls and seen_titles to disk so they survive restarts."""
        try:
            os.makedirs(os.path.dirname(RSS_SEEN_STATE_FILE), exist_ok=True)
            state = {
                'seen_urls': list(self.seen_urls),
                'seen_titles': list(self.seen_titles),
                'saved_at': datetime.now().isoformat(),
            }
            with open(RSS_SEEN_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f)
            print(f"[RSS] Saved seen state: {len(self.seen_urls)} URLs, {len(self.seen_titles)} titles")
        except Exception as e:
            print(f"[RSS] Failed to save seen state: {e}")

    def load_seen_state(self):
        """Load previously saved seen_urls and seen_titles from disk."""
        try:
            if os.path.exists(RSS_SEEN_STATE_FILE):
                with open(RSS_SEEN_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.seen_urls = set(state.get('seen_urls', []))
                self.seen_titles = set(state.get('seen_titles', []))
                print(f"[RSS] Loaded seen state: {len(self.seen_urls)} URLs, {len(self.seen_titles)} titles")
            else:
                print("[RSS] No previous seen state found, starting fresh")
        except Exception as e:
            print(f"[RSS] Failed to load seen state: {e}")

    def _clean_html(self, raw_html):
        """Removes HTML tags from RSS summaries"""
        return BeautifulSoup(raw_html, "html.parser").get_text()

    def _parse_date(self, date_str):
        """Standardizes varied RSS date formats"""
        if not date_str:
            return datetime.now()
        return dateparser.parse(date_str)

# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================
if __name__ == "__main__":
    # Initialize Engine
    engine = CryptoNewsAggregator()
    
    # 1. Fetch Data
    engine.fetch_all_feeds()
    
    # 2. Simulate "Search" used by your Analyzer
    print("\n🔍 SEARCH TEST: 'Bitcoin'")
    results = engine.search_news(ticker="Bitcoin", limit=3)
    
    for news in results:
        print(f"- [{news['source']}] {news['title']}")
        print(f"  Link: {news['link']}\n")
    
    # 3. Simulate "Regulation" Search
    print("\n🔍 SEARCH TEST: 'Regulation'")
    reg_news = engine.search_news(query="SEC", limit=3)
    for news in reg_news:
        print(f"- {news['title']}")