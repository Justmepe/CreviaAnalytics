"""
CoinMarketCap Data Provider - TERTIARY DATA SOURCE

CoinMarketCap provides:
- Global market metrics (free public API)
- Market cap data
- Volume data
- Dominance metrics

Note: Uses free public API endpoints (no API key required for basic data)
"""

import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime

from ..models import MarketMetrics


class CoinMarketCapProvider:
    """
    CoinMarketCap API Provider - Global metrics

    Uses free public API endpoints for:
    - Total market cap
    - Total volume
    - BTC/ETH dominance
    - Market cap changes
    """

    # Free public API endpoint
    BASE_URL = "https://api.coinmarketcap.com/data-api/v3"

    # Rate limiting (be conservative)
    MIN_REQUEST_INTERVAL = 5.0

    def __init__(self, api_key: str = None):
        """
        Initialize CoinMarketCap provider

        Args:
            api_key: Optional API key (for pro features)
        """
        self.api_key = api_key
        self.last_request_time = 0
        self.session = requests.Session()

        # Set headers
        self.session.headers.update({
            'User-Agent': 'CreviaAnalytics/1.0',
            'Accept': 'application/json'
        })

        if api_key:
            self.session.headers.update({'X-CMC_PRO_API_KEY': api_key})

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"CoinMarketCap API error: {e}")
            return None

    # =========================================================================
    # GLOBAL METRICS
    # =========================================================================

    def get_global_metrics(self) -> Optional[MarketMetrics]:
        """
        Get global crypto market metrics

        Returns:
            MarketMetrics with global data
        """
        data = self._request("/global-metrics/quotes/latest")

        if not data or 'data' not in data:
            return None

        d = data['data']

        # Get quotes for total market cap and volume
        quotes = d.get('quotes', [])
        usd_quote = {}
        for q in quotes:
            if q.get('name') == 'USD':
                usd_quote = q
                break

        # Calculate alt season index from BTC dominance
        btc_dom = float(d.get('btcDominance', 0))
        alt_season_index = max(0, min(100, int((70 - btc_dom) * 3.33)))

        # Get market cap change from today change percent
        mcap_change = float(d.get('todayChangePercent', 0))

        return MarketMetrics(
            total_market_cap=float(usd_quote.get('totalMarketCap', 0)),
            total_volume_24h=float(usd_quote.get('totalVolume24h', 0)),
            market_cap_change_24h=mcap_change,
            btc_dominance=btc_dom,
            eth_dominance=float(d.get('ethDominance', 0)),
            active_cryptocurrencies=int(d.get('activeCryptoCurrencies', 0)),
            alt_season_index=alt_season_index,
            timestamp=int(time.time()),
            sources=['coinmarketcap']
        )

    def get_fear_greed_equivalent(self) -> int:
        """
        Calculate fear/greed index from market metrics

        Returns:
            int: 0-100 (0 = extreme fear, 100 = extreme greed)
        """
        metrics = self.get_global_metrics()

        if not metrics:
            return 50  # Neutral fallback

        score = 50

        # Market cap change impact
        if metrics.market_cap_change_24h < -5:
            score -= 20
        elif metrics.market_cap_change_24h < -2:
            score -= 10
        elif metrics.market_cap_change_24h > 5:
            score += 20
        elif metrics.market_cap_change_24h > 2:
            score += 10

        # BTC dominance impact
        if metrics.btc_dominance > 60:
            score -= 10  # Fear (flight to BTC)
        elif metrics.btc_dominance < 45:
            score += 10  # Greed (alt season)

        return max(0, min(100, score))

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request("/global-metrics/quotes/latest")
        return data is not None and 'data' in data


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("COINMARKETCAP PROVIDER TEST")
    print("=" * 80)

    provider = CoinMarketCapProvider()

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to CoinMarketCap API")
    else:
        print("   ❌ Connection failed")

    # Test 2: Global metrics
    print("\n2. Testing global metrics...")
    metrics = provider.get_global_metrics()
    if metrics:
        print(f"   ✅ Total Market Cap: ${metrics.total_market_cap/1e12:.2f}T")
        print(f"   ✅ 24h Volume: ${metrics.total_volume_24h/1e9:.2f}B")
        print(f"   ✅ 24h Change: {metrics.market_cap_change_24h:+.2f}%")
        print(f"   ✅ BTC Dominance: {metrics.btc_dominance:.1f}%")
        print(f"   ✅ ETH Dominance: {metrics.eth_dominance:.1f}%")
        print(f"   ✅ Active Cryptos: {metrics.active_cryptocurrencies:,}")
        print(f"   ✅ Alt Season Index: {metrics.alt_season_index}")
    else:
        print("   ❌ Failed to fetch global metrics")

    # Test 3: Fear/Greed equivalent
    print("\n3. Testing fear/greed equivalent...")
    fg = provider.get_fear_greed_equivalent()
    print(f"   ✅ Fear/Greed Equivalent: {fg}")

    print("\n" + "=" * 80)
    print("✅ COINMARKETCAP PROVIDER TESTS COMPLETE")
    print("=" * 80)
