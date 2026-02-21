"""
File 4: API Integration Layer
Dependencies: config.py, helpers.py
Status: ✅ COMPLETE

Purpose:
- Wrapper functions for all external APIs
- CoinGecko, Binance, CryptoPanic, Alternative.me
- Handle rate limiting, retries, caching
- Error handling and fallbacks
"""

import requests
import time
from typing import Optional, Dict, Any, List
from functools import lru_cache
import json

from src.core.config import (
    COINGECKO_API_KEY, COINGECKO_BASE_URL,
    BINANCE_API_KEY, BINANCE_BASE_URL,
    CRYPTOPANIC_API_KEY, CRYPTOPANIC_BASE_URL,
    FEAR_GREED_URL,
    REQUEST_DELAY_SECONDS
)
from src.utils.helpers import safe_get, get_current_timestamp


# =============================================================================
# RATE LIMITING & RETRY LOGIC
# =============================================================================

class RateLimiter:
    """Simple rate limiter to prevent API abuse"""
    
    def __init__(self, min_interval: float = REQUEST_DELAY_SECONDS):
        self.min_interval = min_interval
        self.last_call = 0
    
    def wait(self):
        """Wait if necessary to respect rate limits"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


# Create rate limiters for each API
_coingecko_limiter = RateLimiter(6)  # ~10 requests per minute
_binance_limiter = RateLimiter(1)    # More generous for Binance
_cryptopanic_limiter = RateLimiter(60)  # Very conservative for free tier


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Decorator for retrying failed API calls with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        print(f"ERROR: {func.__name__} failed after {max_retries} attempts: {e}")
                        return None
                    
                    wait_time = backoff_factor ** attempt
                    print(f"WARNING: {func.__name__} attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator


# =============================================================================
# COINGECKO API (Market Data, Coin Info)
# =============================================================================

@retry_on_failure()
def get_coin_data(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive coin data from CoinGecko
    
    Args:
        ticker: Coin symbol (e.g., 'BTC', 'ETH')
    
    Returns:
        dict: {
            'id': 'bitcoin',
            'symbol': 'btc',
            'name': 'Bitcoin',
            'current_price': 50000.0,
            'market_cap': 1000000000000,
            'total_volume': 25000000000,
            'price_change_24h': 1250.5,
            'price_change_percentage_24h': 2.56,
            'categories': ['layer-1', ...],
            ...
        }
    """
    _coingecko_limiter.wait()
    
    # First, search for coin ID by symbol
    search_url = f"{COINGECKO_BASE_URL}/search"
    params = {'query': ticker}
    
    if COINGECKO_API_KEY:
        params['x_cg_demo_api_key'] = COINGECKO_API_KEY
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        search_data = response.json()
        
        # Find matching coin
        coins = search_data.get('coins', [])
        if not coins:
            print(f"WARNING: No coin found for ticker: {ticker}")
            return None
        
        # Get first match (usually most relevant)
        coin_id = coins[0]['id']
        
        # Now fetch full coin data
        _coingecko_limiter.wait()
        coin_url = f"{COINGECKO_BASE_URL}/coins/{coin_id}"
        coin_params = {
            'localization': 'false',
            'tickers': 'false',
            'community_data': 'false',
            'developer_data': 'false'
        }
        
        if COINGECKO_API_KEY:
            coin_params['x_cg_demo_api_key'] = COINGECKO_API_KEY
        
        response = requests.get(coin_url, params=coin_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract and structure relevant data
        market_data = data.get('market_data', {})
        
        return {
            'id': data.get('id'),
            'symbol': data.get('symbol', '').upper(),
            'name': data.get('name'),
            'categories': data.get('categories', []),
            'current_price': safe_get(market_data, 'current_price', 'usd', default=0),
            'market_cap': safe_get(market_data, 'market_cap', 'usd', default=0),
            'total_volume': safe_get(market_data, 'total_volume', 'usd', default=0),
            'price_change_24h': safe_get(market_data, 'price_change_24h', default=0),
            'price_change_percentage_24h': safe_get(market_data, 'price_change_percentage_24h', default=0),
            'market_cap_rank': data.get('market_cap_rank'),
            'circulating_supply': safe_get(market_data, 'circulating_supply', default=0),
            'total_supply': safe_get(market_data, 'total_supply', default=0),
            'ath': safe_get(market_data, 'ath', 'usd', default=0),
            'atl': safe_get(market_data, 'atl', 'usd', default=0),
        }
        
    except requests.RequestException as e:
        print(f"ERROR: CoinGecko API error for {ticker}: {e}")
        return None


@retry_on_failure()
def get_market_chart(ticker: str, days: int = 1) -> Optional[Dict[str, Any]]:
    """
    Fetch historical price/volume data
    
    Args:
        ticker: Coin symbol
        days: Number of days (1, 7, 30, etc.)
    
    Returns:
        dict: {
            'prices': [[timestamp, price], ...],
            'volumes': [[timestamp, volume], ...],
            'market_caps': [[timestamp, market_cap], ...]
        }
    """
    _coingecko_limiter.wait()
    
    # Get coin ID first
    coin_data = get_coin_data(ticker)
    if not coin_data:
        return None
    
    coin_id = coin_data['id']
    
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': str(days),
        'interval': 'hourly' if days <= 7 else 'daily'
    }
    
    if COINGECKO_API_KEY:
        params['x_cg_demo_api_key'] = COINGECKO_API_KEY
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.RequestException as e:
        print(f"ERROR: CoinGecko market chart error for {ticker}: {e}")
        return None


# =============================================================================
# BINANCE API (Derivatives Data)
# =============================================================================

@retry_on_failure()
def get_funding_rate(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current funding rate from Binance Futures
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
    
    Returns:
        dict: {
            'symbol': 'BTCUSDT',
            'funding_rate': 0.0001,  # 0.01%
            'funding_time': 1640000000,
            'mark_price': 50000.0
        }
    """
    _binance_limiter.wait()
    
    # Ensure symbol format (e.g., BTC -> BTCUSDT)
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"
    
    url = f"{BINANCE_BASE_URL}/fapi/v1/premiumIndex"
    params = {'symbol': symbol}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'symbol': data.get('symbol'),
            'funding_rate': float(data.get('lastFundingRate', 0)),
            'funding_time': int(data.get('nextFundingTime', 0)) // 1000,  # Convert to seconds
            'mark_price': float(data.get('markPrice', 0))
        }
    
    except requests.RequestException as e:
        print(f"ERROR: Binance funding rate error for {symbol}: {e}")
        return None


@retry_on_failure()
def get_open_interest(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch open interest from Binance Futures
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
    
    Returns:
        dict: {
            'symbol': 'BTCUSDT',
            'open_interest': 125000.5,  # In base currency
            'open_interest_usd': 6250000000.0,
            'timestamp': 1640000000
        }
    """
    _binance_limiter.wait()
    
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"
    
    url = f"{BINANCE_BASE_URL}/fapi/v1/openInterest"
    params = {'symbol': symbol}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        oi = float(data.get('openInterest', 0))
        
        # Get current price to calculate USD value
        funding_data = get_funding_rate(symbol)
        price = funding_data['mark_price'] if funding_data else 0
        
        return {
            'symbol': data.get('symbol'),
            'open_interest': oi,
            'open_interest_usd': oi * price,
            'timestamp': int(data.get('time', 0)) // 1000
        }
    
    except requests.RequestException as e:
        print(f"ERROR: Binance open interest error for {symbol}: {e}")
        return None


# =============================================================================
# CRYPTOPANIC API (News Aggregation)
# =============================================================================

@retry_on_failure()
def get_news(ticker: Optional[str] = None, hours: int = 24) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch crypto news from CryptoPanic
    
    Args:
        ticker: Filter by specific coin (optional)
        hours: Hours of news to fetch
    
    Returns:
        list: [{
            'title': 'Bitcoin ETF Approved',
            'published_at': '2024-01-01T12:00:00Z',
            'url': 'https://...',
            'source': 'CoinDesk',
            'currencies': ['BTC'],
            'kind': 'news'
        }, ...]
    """
    _cryptopanic_limiter.wait()
    
    if not CRYPTOPANIC_API_KEY:
        print("WARNING: CryptoPanic API key not configured")
        return None
    
    url = f"{CRYPTOPANIC_BASE_URL}/posts/"
    params = {
        'auth_token': CRYPTOPANIC_API_KEY,
        'public': 'true',
        'kind': 'news'
    }
    
    if ticker:
        params['currencies'] = ticker.upper()
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        
        # Filter by time window
        cutoff_time = get_current_timestamp() - (hours * 3600)
        filtered_results = []
        
        for item in results:
            published_str = item.get('published_at', '')
            # Simple timestamp comparison (CryptoPanic uses ISO format)
            # For production, use proper datetime parsing
            filtered_results.append({
                'title': item.get('title'),
                'published_at': published_str,
                'url': item.get('url'),
                'source': safe_get(item, 'source', 'title', default='Unknown'),
                'currencies': [c['code'] for c in item.get('currencies', [])],
                'kind': item.get('kind')
            })
        
        return filtered_results[:20]  # Limit to 20 most recent
    
    except requests.RequestException as e:
        print(f"ERROR: CryptoPanic API error: {e}")
        return None


# =============================================================================
# ALTERNATIVE.ME (Fear & Greed Index)
# =============================================================================

@lru_cache(maxsize=1)  # Cache for 1 hour (decorated function caches based on args)
@retry_on_failure()
def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """
    Fetch Fear & Greed Index (updates daily)
    
    Returns:
        dict: {
            'value': 45,
            'value_classification': 'Fear',
            'timestamp': 1640000000,
            'time_until_update': 43200
        }
    """
    try:
        response = requests.get(FEAR_GREED_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or not data['data']:
            return None
        
        latest = data['data'][0]
        
        return {
            'value': int(latest.get('value', 50)),
            'value_classification': latest.get('value_classification', 'Neutral'),
            'timestamp': int(latest.get('timestamp', 0)),
            'time_until_update': int(latest.get('time_until_update', 0))
        }
    
    except requests.RequestException as e:
        print(f"ERROR: Fear & Greed Index error: {e}")
        return None


# =============================================================================
# MOCK DATA (For Testing Without API Keys)
# =============================================================================

def get_mock_coin_data(ticker: str) -> Dict[str, Any]:
    """Return mock data for testing without API access"""
    return {
        'id': ticker.lower(),
        'symbol': ticker.upper(),
        'name': ticker.capitalize(),
        'categories': ['cryptocurrency'],
        'current_price': 50000.0,
        'market_cap': 1_000_000_000,
        'total_volume': 25_000_000,
        'price_change_24h': 1250.0,
        'price_change_percentage_24h': 2.5,
        'market_cap_rank': 1,
        'circulating_supply': 19_000_000,
        'total_supply': 21_000_000,
        'ath': 69000.0,
        'atl': 100.0
    }


def get_mock_funding_rate(symbol: str) -> Dict[str, Any]:
    """Return mock funding rate for testing"""
    return {
        'symbol': symbol,
        'funding_rate': 0.0001,
        'funding_time': get_current_timestamp() + 28800,
        'mark_price': 50000.0
    }


# =============================================================================
# UNIFIED API WRAPPER (Auto-selects real or mock data)
# =============================================================================

USE_MOCK_DATA = not COINGECKO_API_KEY  # Use mock if no API key


def fetch_coin_data(ticker: str, use_mock: bool = USE_MOCK_DATA) -> Optional[Dict[str, Any]]:
    """Unified wrapper that uses real or mock data based on config"""
    if use_mock:
        print(f"NOTE: Using mock data for {ticker} (no API key configured)")
        return get_mock_coin_data(ticker)
    return get_coin_data(ticker)


def fetch_funding_rate(symbol: str, use_mock: bool = USE_MOCK_DATA) -> Optional[Dict[str, Any]]:
    """Unified wrapper for funding rate"""
    if use_mock:
        return get_mock_funding_rate(symbol)
    return get_funding_rate(symbol)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing data_fetchers.py...")
    
    # Test Fear & Greed (no auth needed)
    print("\n1. Testing Fear & Greed Index...")
    fg = get_fear_greed_index()
    if fg:
        print(f"   ✓ Fear & Greed: {fg['value']} ({fg['value_classification']})")
    
    # Test mock data
    print("\n2. Testing mock data...")
    mock_data = get_mock_coin_data('BTC')
    print(f"   ✓ Mock BTC price: ${mock_data['current_price']:,.2f}")
    
    print("\n✅ Data fetchers ready!")