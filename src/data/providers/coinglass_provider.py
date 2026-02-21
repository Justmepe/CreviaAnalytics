"""
Coinglass Data Provider - Liquidation Data

Coinglass is the primary source for liquidation data after Binance
removed the /fapi/v1/forceOrders endpoint.

API Documentation: https://coinglass.github.io/API-Reference/

Endpoints used:
- /api/futures/liquidation/info - Get liquidation data
- /api/futures/liquidation/chart - Historical liquidation charts
"""

import requests
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class CoinglassProvider:
    """
    Coinglass API Provider - Liquidation Data

    Features:
    - Real-time liquidation data
    - Long/Short liquidation breakdown
    - Multi-exchange aggregation
    - Historical liquidation charts
    """

    BASE_URL = "https://open-api-v4.coinglass.com/api"

    # Rate limiting
    MIN_REQUEST_INTERVAL = 0.2  # 200ms between requests (5 req/sec max)

    # Symbol mappings (ticker -> Coinglass symbol)
    SYMBOL_MAP = {
        'BTC': 'BTC',
        'ETH': 'ETH',
        'SOL': 'SOL',
        'BNB': 'BNB',
        'XRP': 'XRP',
        'DOGE': 'DOGE',
        'SHIB': 'SHIB',
        'PEPE': 'PEPE',
        'FLOKI': 'FLOKI',
        'XMR': 'XMR',
        'LTC': 'LTC',
        'AAVE': 'AAVE',
        'UNI': 'UNI',
        'LINK': 'LINK',
        'AVAX': 'AVAX',
        'MATIC': 'MATIC',
        'ADA': 'ADA',
        'DOT': 'DOT',
        'ATOM': 'ATOM',
    }

    def __init__(self, api_key: str = None):
        """
        Initialize Coinglass provider

        Args:
            api_key: Coinglass API key (required for most endpoints)
        """
        self.api_key = api_key
        self.last_request_time = 0
        self.session = requests.Session()

        # Set API key in headers if provided
        if api_key:
            self.session.headers.update({'CG-API-KEY': api_key})

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get_symbol(self, ticker: str) -> str:
        """Convert ticker to Coinglass symbol"""
        ticker = ticker.upper()
        return self.SYMBOL_MAP.get(ticker, ticker)

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Coinglass API returns {success: true/false, code: ..., data: ...}
            if data.get('success') or data.get('code') == '0':
                return data.get('data')
            else:
                msg = data.get('msg', 'Unknown error')
                # Check if it's a plan limit error
                if 'upgrade' in msg.lower() or 'plan' in msg.lower():
                    # Don't spam logs with upgrade messages
                    pass
                else:
                    print(f"Coinglass API error: {msg}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Coinglass API request error: {e}")
            return None

    def get_liquidations(self, ticker: str, hours: int = 24, exchange: str = 'Binance') -> Dict[str, float]:
        """
        Get liquidation data for an asset

        Args:
            ticker: Asset symbol (e.g., 'BTC', 'ETH')
            hours: Time window (1, 4, 12, 24)
            exchange: Exchange name (default: 'Binance')

        Returns:
            Dict with long/short/total liquidations in USD
        """
        symbol = self._get_symbol(ticker)

        # Validate hours
        if hours not in [1, 4, 12, 24]:
            hours = 24

        # Get liquidation data from coin-list endpoint
        data = self._request(
            "/futures/liquidation/coin-list",
            params={'exchange': exchange}
        )

        if not data or not isinstance(data, list):
            return {
                'long': 0.0,
                'short': 0.0,
                'total': 0.0,
                'note': 'Coinglass API returned no data'
            }

        # Find the coin in the list
        coin_data = None
        for item in data:
            if item.get('symbol', '').upper() == symbol.upper():
                coin_data = item
                break

        if not coin_data:
            return {
                'long': 0.0,
                'short': 0.0,
                'total': 0.0,
                'note': f'{symbol} not found in {exchange} liquidation data'
            }

        # Extract liquidation values based on time window
        time_suffix = f'_{hours}h'
        long_liq = float(coin_data.get(f'long_liquidation_usd{time_suffix}', 0))
        short_liq = float(coin_data.get(f'short_liquidation_usd{time_suffix}', 0))
        total_liq = float(coin_data.get(f'liquidation_usd{time_suffix}', 0))

        # If total is not provided, calculate it
        if total_liq == 0 and (long_liq > 0 or short_liq > 0):
            total_liq = long_liq + short_liq

        return {
            'long': long_liq,
            'short': short_liq,
            'total': total_liq,
            'note': f'Coinglass {exchange} data ({hours}h window)',
            'timestamp': int(time.time())
        }

    def get_liquidation_history(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Get historical liquidation chart data

        Args:
            ticker: Asset symbol
            days: Number of days (1-30)

        Returns:
            List of liquidation data points
        """
        symbol = self._get_symbol(ticker)

        data = self._request(
            "/indicator/liquidation_history",
            params={
                'symbol': symbol,
                'interval': '1d'  # Daily data
            }
        )

        if not data:
            return []

        # Parse liquidation history
        history = []
        for point in data.get('data', [])[:days]:
            history.append({
                'timestamp': point.get('t', 0) // 1000,  # Convert ms to seconds
                'date': datetime.fromtimestamp(point.get('t', 0) // 1000).strftime('%Y-%m-%d'),
                'long_liquidation': float(point.get('longLiquidationUsd', 0)) * 1_000_000,
                'short_liquidation': float(point.get('shortLiquidationUsd', 0)) * 1_000_000,
                'total_liquidation': float(point.get('totalLiquidationUsd', 0)) * 1_000_000
            })

        return history

    def get_total_liquidations(self, hours: int = 24) -> Dict[str, float]:
        """
        Get total market-wide liquidations across all coins

        Args:
            hours: Time window (1, 4, 12, 24)

        Returns:
            Dict with aggregated liquidation data
        """
        # Map hours to time type
        time_type_map = {
            1: 'h1',
            4: 'h4',
            12: 'h12',
            24: 'h24'
        }
        time_type = time_type_map.get(hours, 'h24')

        data = self._request(
            "/indicator/liquidation_total",
            params={'timeType': time_type}
        )

        if not data:
            return {
                'total': 0.0,
                'note': 'Coinglass API returned no data'
            }

        # Extract total liquidations (in millions)
        total = float(data.get('totalLiquidationUsd', 0)) * 1_000_000

        return {
            'total': total,
            'long': float(data.get('longLiquidationUsd', 0)) * 1_000_000,
            'short': float(data.get('shortLiquidationUsd', 0)) * 1_000_000,
            'note': f'Market-wide liquidations ({hours}h)',
            'timestamp': int(time.time())
        }

    def test_connection(self) -> bool:
        """Test API connectivity"""
        try:
            # Try to get BTC liquidations as a test
            result = self.get_liquidations('BTC', hours=1)
            return result is not None and 'total' in result
        except Exception:
            return False


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    import os
    import sys
    from dotenv import load_dotenv

    # Fix Windows encoding
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    load_dotenv()

    print("=" * 80)
    print("COINGLASS PROVIDER TEST")
    print("=" * 80)

    api_key = os.getenv('COINGLASS_API_KEY', '')

    if not api_key:
        print("\n⚠️  Warning: No COINGLASS_API_KEY in .env")
        print("   Some endpoints may not work without authentication")
        print()

    provider = CoinglassProvider(api_key)

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to Coinglass API")
    else:
        print("   ❌ Connection failed")

    # Test 2: BTC liquidations (24h)
    print("\n2. Testing BTC liquidations (24h)...")
    liq = provider.get_liquidations('BTC', hours=24)
    print(f"   Long Liquidations: ${liq['long']:,.2f}")
    print(f"   Short Liquidations: ${liq['short']:,.2f}")
    print(f"   Total Liquidations: ${liq['total']:,.2f}")
    print(f"   Note: {liq['note']}")

    if liq['total'] > 0:
        pct_long = (liq['long'] / liq['total'] * 100)
        pct_short = (liq['short'] / liq['total'] * 100)
        print(f"   Breakdown: {pct_long:.1f}% Long / {pct_short:.1f}% Short")

    # Test 3: ETH liquidations (4h)
    print("\n3. Testing ETH liquidations (4h)...")
    liq = provider.get_liquidations('ETH', hours=4)
    print(f"   Total: ${liq['total']:,.2f}")

    # Test 4: Total market liquidations
    print("\n4. Testing total market liquidations (24h)...")
    total = provider.get_total_liquidations(hours=24)
    print(f"   Market-wide Total: ${total['total']:,.2f}")

    # Test 5: Liquidation history
    print("\n5. Testing BTC liquidation history (7 days)...")
    history = provider.get_liquidation_history('BTC', days=7)
    if history:
        print(f"   ✅ Retrieved {len(history)} days of data")
        for day in history[:3]:  # Show first 3 days
            print(f"   - {day['date']}: ${day['total_liquidation']:,.2f}")
    else:
        print("   ❌ No history data")

    print("\n" + "=" * 80)
    print("✅ COINGLASS PROVIDER TESTS COMPLETE")
    print("=" * 80)
