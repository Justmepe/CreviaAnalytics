"""
CoinGecko Data Provider - SECONDARY DATA SOURCE

CoinGecko provides:
- Market cap and rank data
- Circulating/total supply
- All-time high data
- Historical data
- Comprehensive coin info

Rate Limits:
- Free tier: 10-30 requests/minute
- Demo API key: 30 requests/minute
- Pro API key: 500 requests/minute

Endpoints:
- /coins/markets - Market data for multiple coins
- /coins/{id} - Detailed coin info
- /global - Global market metrics
- /simple/price - Simple price lookup
"""

import requests
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import PriceSnapshot, MarketMetrics, OnChainMetrics


class CoinGeckoProvider:
    """
    CoinGecko API Provider - Secondary data source

    Features:
    - Market cap data
    - Supply metrics
    - ATH tracking
    - Historical data
    """

    BASE_URL = "https://api.coingecko.com/api/v3"
    PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"

    # Rate limiting
    MIN_REQUEST_INTERVAL = 2.0  # Conservative for free tier

    # Ticker to CoinGecko ID mapping
    ID_MAP = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'XRP': 'ripple',
        'SOL': 'solana',
        'BNB': 'binancecoin',
        'AVAX': 'avalanche-2',
        'SUI': 'sui',
        'LINK': 'chainlink',
        'DOGE': 'dogecoin',
        'SHIB': 'shiba-inu',
        'PEPE': 'pepe',
        'FLOKI': 'floki',
        'XMR': 'monero',
        'ZEC': 'zcash',
        'DASH': 'dash',
        'SCRT': 'secret',
        'AAVE': 'aave',
        'UNI': 'uniswap',
        'CRV': 'curve-dao-token',
        'LDO': 'lido-dao',
        # Legacy / extras
        'LTC': 'litecoin',
        'COMP': 'compound-governance-token',
        'MKR': 'maker',
        'MATIC': 'matic-network',
        'ADA': 'cardano',
        'DOT': 'polkadot',
        'ATOM': 'cosmos',
        # XAU (Gold) and TSLA are Binance Futures only — not available on CoinGecko
    }

    def __init__(self, api_key: str = None):
        """
        Initialize CoinGecko provider

        Args:
            api_key: Optional API key for higher rate limits
                     - Demo keys start with 'CG-' (use free endpoint with param)
                     - Pro keys are longer (use pro endpoint with header)
        """
        self.api_key = api_key
        self.last_request_time = 0
        self.session = requests.Session()
        self.is_demo_key = False
        self.is_pro_key = False

        # Determine key type and endpoint
        if api_key:
            if api_key.startswith('CG-'):
                # Demo API key - use FREE endpoint with x_cg_demo_api_key param
                self.base_url = self.BASE_URL
                self.is_demo_key = True
                self.MIN_REQUEST_INTERVAL = 1.5  # 30 req/min demo tier
                print(f"CoinGecko: Using demo API key with free endpoint")
            else:
                # Pro API key - use PRO endpoint with header
                self.base_url = self.PRO_BASE_URL
                self.is_pro_key = True
                self.session.headers.update({'x-cg-pro-api-key': api_key})
                self.MIN_REQUEST_INTERVAL = 0.2  # 500 req/min pro tier
                print(f"CoinGecko: Using pro API key")
        else:
            # No key - use free endpoint
            self.base_url = self.BASE_URL
            self.MIN_REQUEST_INTERVAL = 3.0  # Conservative 10 req/min free tier

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get_id(self, ticker: str) -> str:
        """Convert ticker to CoinGecko ID"""
        ticker = ticker.upper()
        return self.ID_MAP.get(ticker, ticker.lower())

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()

        url = f"{self.base_url}{endpoint}"
        params = params or {}

        # Add demo API key as parameter (not header)
        if self.is_demo_key and self.api_key:
            params['x_cg_demo_api_key'] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("CoinGecko rate limited - waiting 60s...")
                time.sleep(60)
                return self._request(endpoint, params)  # Retry once
            elif e.response.status_code == 400 and self.is_demo_key:
                # Demo key might not work - fall back to no key
                print("CoinGecko demo key failed - trying without key...")
                params.pop('x_cg_demo_api_key', None)
                try:
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except:
                    pass
            print(f"CoinGecko API error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"CoinGecko request error: {e}")
            return None

    # =========================================================================
    # PRICE DATA
    # =========================================================================

    def get_price(self, ticker: str) -> Optional[PriceSnapshot]:
        """
        Get comprehensive price data for a single coin

        Args:
            ticker: Asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            PriceSnapshot with market data
        """
        coin_id = self._get_id(ticker)

        data = self._request(
            "/coins/markets",
            params={
                'vs_currency': 'usd',
                'ids': coin_id,
                'sparkline': 'false',
                'price_change_percentage': '1h,24h,7d'
            }
        )

        if not data or len(data) == 0:
            return None

        coin = data[0]

        return PriceSnapshot(
            ticker=ticker.upper(),
            price_usd=float(coin.get('current_price', 0) or 0),
            price_change_24h=float(coin.get('price_change_percentage_24h', 0) or 0),
            price_change_1h=float(coin.get('price_change_percentage_1h_in_currency', 0) or 0),
            price_change_7d=float(coin.get('price_change_percentage_7d_in_currency', 0) or 0),
            high_24h=float(coin.get('high_24h', 0) or 0),
            low_24h=float(coin.get('low_24h', 0) or 0),
            volume_24h=float(coin.get('total_volume', 0) or 0),
            market_cap=float(coin.get('market_cap', 0) or 0),
            market_cap_rank=int(coin.get('market_cap_rank', 0) or 0),
            circulating_supply=float(coin.get('circulating_supply', 0) or 0),
            total_supply=float(coin.get('total_supply', 0) or 0),
            ath=float(coin.get('ath', 0) or 0),
            ath_change_percentage=float(coin.get('ath_change_percentage', 0) or 0),
            timestamp=int(time.time()),
            source='coingecko'
        )

    def get_prices_batch(self, tickers: List[str]) -> Dict[str, PriceSnapshot]:
        """
        Get prices for multiple tickers efficiently

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to PriceSnapshot
        """
        # Convert tickers to CoinGecko IDs
        ids = [self._get_id(t) for t in tickers]
        id_to_ticker = {self._get_id(t): t.upper() for t in tickers}

        data = self._request(
            "/coins/markets",
            params={
                'vs_currency': 'usd',
                'ids': ','.join(ids),
                'sparkline': 'false',
                'price_change_percentage': '1h,24h,7d'
            }
        )

        if not data:
            return {}

        results = {}
        for coin in data:
            coin_id = coin.get('id')
            ticker = id_to_ticker.get(coin_id, coin.get('symbol', '').upper())

            results[ticker] = PriceSnapshot(
                ticker=ticker,
                price_usd=float(coin.get('current_price', 0) or 0),
                price_change_24h=float(coin.get('price_change_percentage_24h', 0) or 0),
                price_change_1h=float(coin.get('price_change_percentage_1h_in_currency', 0) or 0),
                price_change_7d=float(coin.get('price_change_percentage_7d_in_currency', 0) or 0),
                high_24h=float(coin.get('high_24h', 0) or 0),
                low_24h=float(coin.get('low_24h', 0) or 0),
                volume_24h=float(coin.get('total_volume', 0) or 0),
                market_cap=float(coin.get('market_cap', 0) or 0),
                market_cap_rank=int(coin.get('market_cap_rank', 0) or 0),
                circulating_supply=float(coin.get('circulating_supply', 0) or 0),
                total_supply=float(coin.get('total_supply', 0) or 0),
                ath=float(coin.get('ath', 0) or 0),
                ath_change_percentage=float(coin.get('ath_change_percentage', 0) or 0),
                timestamp=int(time.time()),
                source='coingecko'
            )

        return results

    # =========================================================================
    # GLOBAL MARKET DATA
    # =========================================================================

    def get_global_metrics(self) -> Optional[MarketMetrics]:
        """
        Get global crypto market metrics

        Returns:
            MarketMetrics with global data
        """
        data = self._request("/global")

        if not data or 'data' not in data:
            return None

        global_data = data['data']

        return MarketMetrics(
            total_market_cap=float(global_data.get('total_market_cap', {}).get('usd', 0)),
            total_volume_24h=float(global_data.get('total_volume', {}).get('usd', 0)),
            market_cap_change_24h=float(global_data.get('market_cap_change_percentage_24h_usd', 0)),
            btc_dominance=float(global_data.get('market_cap_percentage', {}).get('btc', 0)),
            eth_dominance=float(global_data.get('market_cap_percentage', {}).get('eth', 0)),
            active_cryptocurrencies=int(global_data.get('active_cryptocurrencies', 0)),
            timestamp=int(time.time()),
            sources=['coingecko']
        )

    # =========================================================================
    # SIMPLE PRICE (Fast)
    # =========================================================================

    def get_simple_price(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get just prices for multiple coins (fastest endpoint)

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to USD price
        """
        ids = [self._get_id(t) for t in tickers]
        id_to_ticker = {self._get_id(t): t.upper() for t in tickers}

        data = self._request(
            "/simple/price",
            params={
                'ids': ','.join(ids),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
        )

        if not data:
            return {}

        results = {}
        for coin_id, prices in data.items():
            ticker = id_to_ticker.get(coin_id, coin_id.upper())
            results[ticker] = float(prices.get('usd', 0))

        return results

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request("/ping")
        return data is not None and 'gecko_says' in data


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("COINGECKO PROVIDER TEST")
    print("=" * 80)

    provider = CoinGeckoProvider()

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to CoinGecko API")
    else:
        print("   ❌ Connection failed")

    # Test 2: Get BTC price
    print("\n2. Testing BTC price fetch...")
    btc = provider.get_price('BTC')
    if btc:
        print(f"   ✅ BTC Price: ${btc.price_usd:,.2f}")
        print(f"   ✅ Market Cap: ${btc.market_cap/1e9:.2f}B")
        print(f"   ✅ Rank: #{btc.market_cap_rank}")
        print(f"   ✅ ATH: ${btc.ath:,.2f} ({btc.ath_change_percentage:.1f}% from ATH)")
    else:
        print("   ❌ Failed to fetch BTC price")

    # Test 3: Global metrics
    print("\n3. Testing global metrics...")
    global_data = provider.get_global_metrics()
    if global_data:
        print(f"   ✅ Total Market Cap: ${global_data.total_market_cap/1e12:.2f}T")
        print(f"   ✅ 24h Volume: ${global_data.total_volume_24h/1e9:.2f}B")
        print(f"   ✅ BTC Dominance: {global_data.btc_dominance:.1f}%")
        print(f"   ✅ ETH Dominance: {global_data.eth_dominance:.1f}%")
    else:
        print("   ❌ Failed to fetch global metrics")

    # Test 4: Batch prices
    print("\n4. Testing batch price fetch...")
    tickers = ['BTC', 'ETH', 'SOL', 'BNB']
    prices = provider.get_prices_batch(tickers)
    for ticker, price in prices.items():
        print(f"   ✅ {ticker}: ${price.price_usd:,.2f} (MCap: ${price.market_cap/1e9:.2f}B)")

    print("\n" + "=" * 80)
    print("✅ COINGECKO PROVIDER TESTS COMPLETE")
    print("=" * 80)
