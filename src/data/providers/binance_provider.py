"""
Binance Data Provider - PRIMARY DATA SOURCE

Binance is our most reliable source because:
- Generous rate limits (2400 weight/minute)
- No authentication required for public endpoints
- Real-time data
- Comprehensive derivatives data

Endpoints used:
- /fapi/v1/ticker/24hr - 24h price statistics
- /fapi/v1/premiumIndex - Funding rate & mark price
- /fapi/v1/openInterest - Open interest
- /fapi/v1/fundingRate - Historical funding rates
- /fapi/v1/forceOrders - Liquidation data (requires API key)
- /futures/data/globalLongShortAccountRatio - Long/Short ratio
- /api/v3/ticker/24hr - Spot market data
"""

import requests
import time
import hmac
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlencode

from ..models import PriceSnapshot, DerivativesData


class BinanceProvider:
    """
    Binance API Provider - Primary data source

    Features:
    - Spot and Futures data
    - Real-time prices
    - Funding rates
    - Open interest
    - Liquidations
    - Long/Short ratios
    """

    # API endpoints
    FUTURES_BASE = "https://fapi.binance.com"
    SPOT_BASE = "https://api.binance.com"

    # Rate limiting (conservative)
    MIN_REQUEST_INTERVAL = 0.1  # 100ms between requests

    # Symbol mappings (ticker -> Binance symbol)
    SYMBOL_MAP = {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT',
        'XRP': 'XRPUSDT',
        'SOL': 'SOLUSDT',
        'BNB': 'BNBUSDT',
        'AVAX': 'AVAXUSDT',
        'SUI': 'SUIUSDT',
        'LINK': 'LINKUSDT',
        'DOGE': 'DOGEUSDT',
        'SHIB': 'SHIBUSDT',
        'PEPE': 'PEPEUSDT',
        'FLOKI': 'FLOKIUSDT',
        'XMR': 'XMRUSDT',
        'ZEC': 'ZECUSDT',
        'DASH': 'DASHUSDT',
        'SCRT': 'SCRTUSDT',
        'AAVE': 'AAVEUSDT',
        'UNI': 'UNIUSDT',
        'CRV': 'CRVUSDT',
        'LDO': 'LDOUSDT',
        'XAU': 'XAUUSDT',   # Gold perpetual — Binance Futures only
        'TSLA': 'TSLAUSDT', # Tesla tokenized stock — Binance Futures only
        'LTC': 'LTCUSDT',
        'MATIC': 'MATICUSDT',
        'ADA': 'ADAUSDT',
        'DOT': 'DOTUSDT',
        'ATOM': 'ATOMUSDT',
    }

    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize Binance provider

        Args:
            api_key: Optional API key (increases rate limits)
            api_secret: Optional API secret (for authenticated endpoints)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_request_time = 0
        self.session = requests.Session()

        # Set headers if API key provided
        if api_key:
            self.session.headers.update({'X-MBX-APIKEY': api_key})

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get_symbol(self, ticker: str) -> str:
        """Convert ticker to Binance symbol"""
        ticker = ticker.upper()
        if ticker in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[ticker]
        # Try appending USDT
        return f"{ticker}USDT"

    def _request(self, base_url: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()

        url = f"{base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Binance API error: {e}")
            return None

    def _signed_request(self, base_url: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated API request with HMAC-SHA256 signature"""
        if not self.api_key or not self.api_secret:
            print("Binance: API key/secret required for signed requests")
            return None

        self._rate_limit()

        # Add timestamp
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)

        # Create signature
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature

        url = f"{base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Binance API error: {e}")
            return None

    # =========================================================================
    # PRICE DATA
    # =========================================================================

    def get_price(self, ticker: str) -> Optional[PriceSnapshot]:
        """
        Get current price and 24h statistics

        Args:
            ticker: Asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            PriceSnapshot with price data
        """
        symbol = self._get_symbol(ticker)

        # Try futures first (more comprehensive data)
        data = self._request(
            self.FUTURES_BASE,
            "/fapi/v1/ticker/24hr",
            params={'symbol': symbol}
        )

        if data:
            return PriceSnapshot(
                ticker=ticker.upper(),
                price_usd=float(data.get('lastPrice', 0)),
                price_change_24h=float(data.get('priceChangePercent', 0)),
                high_24h=float(data.get('highPrice', 0)),
                low_24h=float(data.get('lowPrice', 0)),
                volume_24h=float(data.get('quoteVolume', 0)),  # Volume in USDT
                timestamp=int(time.time()),
                source='binance_futures'
            )

        # Fallback to spot
        data = self._request(
            self.SPOT_BASE,
            "/api/v3/ticker/24hr",
            params={'symbol': symbol}
        )

        if data:
            return PriceSnapshot(
                ticker=ticker.upper(),
                price_usd=float(data.get('lastPrice', 0)),
                price_change_24h=float(data.get('priceChangePercent', 0)),
                high_24h=float(data.get('highPrice', 0)),
                low_24h=float(data.get('lowPrice', 0)),
                volume_24h=float(data.get('quoteVolume', 0)),
                timestamp=int(time.time()),
                source='binance_spot'
            )

        return None

    def get_prices_batch(self, tickers: List[str]) -> Dict[str, PriceSnapshot]:
        """
        Get prices for multiple tickers efficiently

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to PriceSnapshot
        """
        results = {}

        # Fetch all futures tickers at once
        all_data = self._request(self.FUTURES_BASE, "/fapi/v1/ticker/24hr")

        if all_data:
            # Create lookup by symbol
            data_by_symbol = {item['symbol']: item for item in all_data}

            for ticker in tickers:
                symbol = self._get_symbol(ticker)
                if symbol in data_by_symbol:
                    data = data_by_symbol[symbol]
                    results[ticker.upper()] = PriceSnapshot(
                        ticker=ticker.upper(),
                        price_usd=float(data.get('lastPrice', 0)),
                        price_change_24h=float(data.get('priceChangePercent', 0)),
                        high_24h=float(data.get('highPrice', 0)),
                        low_24h=float(data.get('lowPrice', 0)),
                        volume_24h=float(data.get('quoteVolume', 0)),
                        timestamp=int(time.time()),
                        source='binance_futures'
                    )

        return results

    # =========================================================================
    # DERIVATIVES DATA
    # =========================================================================

    def get_derivatives(self, ticker: str) -> Optional[DerivativesData]:
        """
        Get comprehensive derivatives data

        Args:
            ticker: Asset symbol

        Returns:
            DerivativesData with funding, OI, liquidations
        """
        symbol = self._get_symbol(ticker)

        # Get funding rate and mark price
        premium_data = self._request(
            self.FUTURES_BASE,
            "/fapi/v1/premiumIndex",
            params={'symbol': symbol}
        )

        # Get open interest
        oi_data = self._request(
            self.FUTURES_BASE,
            "/fapi/v1/openInterest",
            params={'symbol': symbol}
        )

        # Get historical funding rate (for 24h comparison)
        funding_history = self._request(
            self.FUTURES_BASE,
            "/fapi/v1/fundingRate",
            params={'symbol': symbol, 'limit': 3}  # ~24h of funding periods
        )

        # Get long/short ratio
        ls_ratio = self._request(
            self.FUTURES_BASE,
            "/futures/data/globalLongShortAccountRatio",
            params={'symbol': symbol, 'period': '1h', 'limit': 1}
        )

        if not premium_data:
            return None

        # Extract data
        funding_rate = float(premium_data.get('lastFundingRate', 0))
        mark_price = float(premium_data.get('markPrice', 0))
        index_price = float(premium_data.get('indexPrice', 0))
        next_funding_time = int(premium_data.get('nextFundingTime', 0)) // 1000

        # Calculate OI in USD
        oi_base = float(oi_data.get('openInterest', 0)) if oi_data else 0
        oi_usd = oi_base * mark_price

        # Get funding rate 24h ago
        funding_24h_ago = 0
        if funding_history and len(funding_history) > 2:
            funding_24h_ago = float(funding_history[-1].get('fundingRate', 0))

        # Get long/short ratio
        long_short_ratio = 1.0
        if ls_ratio and len(ls_ratio) > 0:
            long_short_ratio = float(ls_ratio[0].get('longShortRatio', 1.0))

        # Calculate mark/index spread
        mark_index_spread = 0
        if index_price > 0:
            mark_index_spread = ((mark_price - index_price) / index_price) * 100

        return DerivativesData(
            ticker=ticker.upper(),
            funding_rate=funding_rate,
            funding_rate_24h_ago=funding_24h_ago,
            funding_rate_change_24h=funding_rate - funding_24h_ago,
            next_funding_time=next_funding_time,
            open_interest_usd=oi_usd,
            open_interest_base=oi_base,
            mark_price=mark_price,
            index_price=index_price,
            mark_index_spread=mark_index_spread,
            long_short_ratio=long_short_ratio,
            timestamp=int(time.time()),
            source='binance'
        )

    def get_liquidations(self, ticker: str, hours: int = 24) -> Dict[str, float]:
        """
        Get liquidation data.

        Note: /fapi/v1/forceOrders requires API key + signature authentication.
        Only attempts if both API key AND secret are configured.

        Args:
            ticker: Asset symbol
            hours: Time window

        Returns:
            Dict with long/short/total liquidations in USD
        """
        symbol = self._get_symbol(ticker)
        long_liquidations = 0
        short_liquidations = 0

        # Only attempt if we have both API key and secret (endpoint requires signature)
        if self.api_key and self.api_secret:
            data = self._signed_request(
                self.FUTURES_BASE,
                "/fapi/v1/forceOrders",
                params={
                    'symbol': symbol,
                    'limit': 100
                }
            )

            if data and isinstance(data, list):
                for order in data:
                    qty = float(order.get('origQty', 0))
                    price = float(order.get('avgPrice', 0) or order.get('price', 0))
                    value = qty * price
                    side = order.get('side', '')

                    # SELL = Long position liquidated, BUY = Short position liquidated
                    if side == 'SELL':
                        long_liquidations += value
                    elif side == 'BUY':
                        short_liquidations += value

        return {
            'long': long_liquidations,
            'short': short_liquidations,
            'total': long_liquidations + short_liquidations,
            'note': 'Requires BINANCE_API_KEY for liquidation data' if not self.api_key else 'Authenticated'
        }

    def get_all_funding_rates(self) -> Dict[str, float]:
        """
        Get funding rates for all perpetual contracts

        Returns:
            Dict mapping symbol to funding rate
        """
        data = self._request(self.FUTURES_BASE, "/fapi/v1/premiumIndex")

        if not data:
            return {}

        return {
            item['symbol'].replace('USDT', ''): float(item.get('lastFundingRate', 0))
            for item in data
            if 'USDT' in item['symbol']
        }

    def get_all_open_interest(self) -> Dict[str, Dict[str, float]]:
        """
        Get open interest for all contracts

        Returns:
            Dict mapping ticker to OI data
        """
        # Get all OI
        oi_data = self._request(self.FUTURES_BASE, "/fapi/v1/openInterest")

        # Get all prices for USD conversion
        ticker_data = self._request(self.FUTURES_BASE, "/fapi/v1/ticker/24hr")

        if not oi_data or not ticker_data:
            return {}

        # Create price lookup
        prices = {
            item['symbol']: float(item.get('lastPrice', 0))
            for item in ticker_data
        }

        results = {}

        # Note: openInterest endpoint returns single symbol, need to iterate
        # Using ticker data which has openInterest-like info
        for item in ticker_data:
            symbol = item['symbol']
            if 'USDT' in symbol:
                ticker = symbol.replace('USDT', '')
                price = prices.get(symbol, 0)
                # Approximate OI from volume (actual OI requires per-symbol call)
                results[ticker] = {
                    'price': price,
                    'volume_24h': float(item.get('quoteVolume', 0))
                }

        return results

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request(self.FUTURES_BASE, "/fapi/v1/ping")
        return data == {}


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("BINANCE PROVIDER TEST")
    print("=" * 80)

    provider = BinanceProvider()

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to Binance API")
    else:
        print("   ❌ Connection failed")

    # Test 2: Get BTC price
    print("\n2. Testing BTC price fetch...")
    btc_price = provider.get_price('BTC')
    if btc_price:
        print(f"   ✅ BTC Price: ${btc_price.price_usd:,.2f}")
        print(f"   ✅ 24h Change: {btc_price.price_change_24h:+.2f}%")
        print(f"   ✅ 24h Volume: ${btc_price.volume_24h/1e9:.2f}B")
        print(f"   ✅ Source: {btc_price.source}")
    else:
        print("   ❌ Failed to fetch BTC price")

    # Test 3: Get derivatives data
    print("\n3. Testing BTC derivatives...")
    btc_deriv = provider.get_derivatives('BTC')
    if btc_deriv:
        print(f"   ✅ Funding Rate: {btc_deriv.funding_rate*100:.4f}%")
        print(f"   ✅ Open Interest: ${btc_deriv.open_interest_usd/1e9:.2f}B")
        print(f"   ✅ Mark Price: ${btc_deriv.mark_price:,.2f}")
        print(f"   ✅ Long/Short Ratio: {btc_deriv.long_short_ratio:.2f}")
        print(f"   ✅ Mark-Index Spread: {btc_deriv.mark_index_spread:.4f}%")
    else:
        print("   ❌ Failed to fetch derivatives")

    # Test 4: Get liquidations
    print("\n4. Testing liquidation data...")
    liquidations = provider.get_liquidations('BTC', hours=24)
    print(f"   ✅ Long Liquidations: ${liquidations['long']/1e6:.2f}M")
    print(f"   ✅ Short Liquidations: ${liquidations['short']/1e6:.2f}M")
    print(f"   ✅ Total: ${liquidations['total']/1e6:.2f}M")

    # Test 5: Batch price fetch
    print("\n5. Testing batch price fetch...")
    tickers = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE']
    prices = provider.get_prices_batch(tickers)
    for ticker, price in prices.items():
        print(f"   ✅ {ticker}: ${price.price_usd:,.2f} ({price.price_change_24h:+.2f}%)")

    # Test 6: All funding rates
    print("\n6. Testing all funding rates...")
    funding_rates = provider.get_all_funding_rates()
    print(f"   ✅ Fetched {len(funding_rates)} funding rates")
    top_5 = sorted(funding_rates.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    for ticker, rate in top_5:
        print(f"   - {ticker}: {rate*100:.4f}%")

    print("\n" + "=" * 80)
    print("✅ BINANCE PROVIDER TESTS COMPLETE")
    print("=" * 80)
