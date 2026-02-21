"""
Data Aggregator - Unified Data Layer

This is the main interface that the analysis engine uses.
It combines data from all providers with intelligent fallbacks.

Priority Order:
1. Binance (Primary) - Prices & Derivatives (reliable, no limits)
2. CoinGecko (Secondary) - Market cap, supply, ATH data
3. CoinMarketCap (Tertiary) - Global metrics fallback
4. Blockchain.info/Etherscan - On-chain data
5. DeFiLlama - DeFi TVL data
6. Alternative.me - Fear & Greed Index

IMPORTANT: Claude is NOT used for data fetching.
Claude is only used for content generation (threads, reports).
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .models import (
    PriceSnapshot,
    DerivativesData,
    MarketMetrics,
    OnChainMetrics,
    DeFiMetrics,
    AssetData
)
from .providers.binance_provider import BinanceProvider
from .providers.coingecko_provider import CoinGeckoProvider
from .providers.coinmarketcap_provider import CoinMarketCapProvider
from .providers.glassnode_provider import GlassnodeProvider
from .providers.defillama_provider import DeFiLlamaProvider
from .providers.alternativeme_provider import AlternativeMeProvider
from .providers.coinglass_provider import CoinglassProvider
from .providers.binance_liquidation_aggregator import BinanceLiquidationAggregator


class DataAggregator:
    """
    Unified data aggregator that combines multiple sources

    Features:
    - Automatic fallbacks when primary source fails
    - Data quality tracking
    - Caching (optional)
    - Batch operations for efficiency
    """

    def __init__(
        self,
        binance_key: str = None,
        binance_secret: str = None,
        coingecko_key: str = None,
        etherscan_key: str = None,
        glassnode_key: str = None,
        coinglass_key: str = None
    ):
        """
        Initialize data aggregator with all providers

        Args:
            binance_key: Binance API key (optional, increases limits)
            binance_secret: Binance API secret
            coingecko_key: CoinGecko API key (optional, for pro features)
            etherscan_key: Etherscan API key (for ETH on-chain data)
            glassnode_key: Glassnode API key (for advanced on-chain)
            coinglass_key: Coinglass API key (for liquidation data, requires paid plan)
        """
        # Initialize all providers
        self.binance = BinanceProvider(binance_key, binance_secret)
        self.coingecko = CoinGeckoProvider(coingecko_key)
        self.coinmarketcap = CoinMarketCapProvider()
        self.glassnode = GlassnodeProvider(glassnode_key, etherscan_key)
        self.defillama = DeFiLlamaProvider()
        self.alternativeme = AlternativeMeProvider()
        self.coinglass = CoinglassProvider(coinglass_key)

        # Initialize Binance liquidation aggregator (WebSocket, FREE!)
        # Tracks BTC, ETH, SOL, BNB liquidations in real-time
        self.liquidation_aggregator = BinanceLiquidationAggregator(['BTC', 'ETH', 'SOL', 'BNB'])
        self.liquidation_aggregator.start()

        # Cache for reducing API calls
        self._cache = {}
        self._cache_ttl = {
            'price': 60,        # 1 minute
            'derivatives': 60,  # 1 minute
            'global': 300,      # 5 minutes
            'onchain': 1800,    # 30 minutes
            'defi': 600,        # 10 minutes
            'fear_greed': 3600  # 1 hour
        }

    def _get_cached(self, key: str, ttl_type: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl.get(ttl_type, 300):
                return data
        return None

    def _set_cached(self, key: str, data: Any):
        """Cache data with timestamp"""
        self._cache[key] = (data, time.time())

    # =========================================================================
    # PRICE DATA
    # =========================================================================

    def get_price(self, ticker: str, use_cache: bool = True) -> Optional[PriceSnapshot]:
        """
        Get price data for an asset

        Priority: Binance -> CoinGecko

        Args:
            ticker: Asset symbol
            use_cache: Whether to use cached data

        Returns:
            PriceSnapshot with price data
        """
        cache_key = f"price_{ticker}"

        if use_cache:
            cached = self._get_cached(cache_key, 'price')
            if cached:
                return cached

        # Try Binance first (most reliable, real-time)
        price = self.binance.get_price(ticker)

        if price:
            # Enhance with CoinGecko data (market cap, supply, ATH)
            cg_price = self.coingecko.get_price(ticker)
            if cg_price:
                price.market_cap = cg_price.market_cap
                price.market_cap_rank = cg_price.market_cap_rank
                price.circulating_supply = cg_price.circulating_supply
                price.total_supply = cg_price.total_supply
                price.ath = cg_price.ath
                price.ath_change_percentage = cg_price.ath_change_percentage
                price.source = 'binance+coingecko'

            self._set_cached(cache_key, price)
            return price

        # Fallback to CoinGecko only
        price = self.coingecko.get_price(ticker)
        if price:
            self._set_cached(cache_key, price)
            return price

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

        # Get Binance prices (batch)
        binance_prices = self.binance.get_prices_batch(tickers)

        # Get CoinGecko data for additional info
        cg_prices = self.coingecko.get_prices_batch(tickers)

        # Merge data
        for ticker in tickers:
            ticker = ticker.upper()

            if ticker in binance_prices:
                price = binance_prices[ticker]

                # Enhance with CoinGecko data
                if ticker in cg_prices:
                    cg = cg_prices[ticker]
                    price.market_cap = cg.market_cap
                    price.market_cap_rank = cg.market_cap_rank
                    price.circulating_supply = cg.circulating_supply
                    price.total_supply = cg.total_supply
                    price.ath = cg.ath
                    price.ath_change_percentage = cg.ath_change_percentage
                    price.source = 'binance+coingecko'

                results[ticker] = price

            elif ticker in cg_prices:
                results[ticker] = cg_prices[ticker]

        return results

    # =========================================================================
    # DERIVATIVES DATA
    # =========================================================================

    def get_derivatives(self, ticker: str, use_cache: bool = True) -> Optional[DerivativesData]:
        """
        Get derivatives data (funding, OI, liquidations)

        Source: Binance Futures (primary and only reliable source)

        Args:
            ticker: Asset symbol
            use_cache: Whether to use cached data

        Returns:
            DerivativesData with funding rates, OI, etc.
        """
        cache_key = f"deriv_{ticker}"

        if use_cache:
            cached = self._get_cached(cache_key, 'derivatives')
            if cached:
                return cached

        # Get derivatives from Binance
        deriv = self.binance.get_derivatives(ticker)

        if deriv:
            # Get liquidations - Priority order:
            # 1. WebSocket aggregator (FREE, real-time)
            # 2. Coinglass (paid plan)
            # 3. Binance REST (deprecated, will return 0)

            liquidations = None

            # Try WebSocket aggregator first
            if self.liquidation_aggregator and self.liquidation_aggregator.connected:
                ws_liq = self.liquidation_aggregator.get_liquidations(ticker, hours=24)
                if ws_liq and ws_liq['total'] > 0:
                    liquidations = ws_liq

            # Fallback to Coinglass
            if not liquidations or liquidations['total'] == 0:
                if self.coinglass:
                    cg_liq = self.coinglass.get_liquidations(ticker, hours=24)
                    if cg_liq and cg_liq['total'] > 0:
                        liquidations = cg_liq

            # Final fallback to Binance REST (will likely be 0)
            if not liquidations or liquidations['total'] == 0:
                liquidations = self.binance.get_liquidations(ticker, hours=24)

            deriv.liquidations_24h_long = liquidations['long']
            deriv.liquidations_24h_short = liquidations['short']
            deriv.liquidations_24h_total = liquidations['total']

            self._set_cached(cache_key, deriv)

        return deriv

    # =========================================================================
    # GLOBAL MARKET METRICS
    # =========================================================================

    def get_global_metrics(self, use_cache: bool = True) -> Optional[MarketMetrics]:
        """
        Get global crypto market metrics

        Priority: CoinGecko -> CoinMarketCap
        Fear & Greed: Alternative.me
        Derivatives: Binance

        Args:
            use_cache: Whether to use cached data

        Returns:
            MarketMetrics with comprehensive global data
        """
        cache_key = "global_metrics"

        if use_cache:
            cached = self._get_cached(cache_key, 'global')
            if cached:
                return cached

        # Get base metrics from CoinGecko
        metrics = self.coingecko.get_global_metrics()

        if not metrics:
            # Fallback to CoinMarketCap
            metrics = self.coinmarketcap.get_global_metrics()

        if not metrics:
            return None

        # Add Fear & Greed from Alternative.me
        fg_value, fg_class = self.alternativeme.get_fear_greed_for_metrics()
        metrics.fear_greed_index = fg_value
        metrics.fear_greed_classification = fg_class

        # Add BTC/ETH derivatives data from Binance (with liquidations)
        btc_deriv = self.get_derivatives('BTC')  # Use get_derivatives to include liquidations
        eth_deriv = self.get_derivatives('ETH')

        total_liquidations = 0.0
        total_longs_liquidated = 0.0
        total_shorts_liquidated = 0.0

        if btc_deriv:
            metrics.btc_funding_rate = btc_deriv.funding_rate
            metrics.btc_open_interest = btc_deriv.open_interest_usd
            metrics.btc_price = btc_deriv.mark_price
            total_liquidations += btc_deriv.liquidations_24h_total
            total_longs_liquidated += btc_deriv.liquidations_24h_long
            total_shorts_liquidated += btc_deriv.liquidations_24h_short

        if eth_deriv:
            metrics.eth_funding_rate = eth_deriv.funding_rate
            metrics.eth_open_interest = eth_deriv.open_interest_usd
            metrics.eth_price = eth_deriv.mark_price
            total_liquidations += eth_deriv.liquidations_24h_total
            total_longs_liquidated += eth_deriv.liquidations_24h_long
            total_shorts_liquidated += eth_deriv.liquidations_24h_short

        # Add liquidations from other majors (SOL, BNB) for comprehensive total
        for symbol in ['SOL', 'BNB']:
            deriv = self.get_derivatives(symbol)
            if deriv:
                total_liquidations += deriv.liquidations_24h_total
                total_longs_liquidated += deriv.liquidations_24h_long
                total_shorts_liquidated += deriv.liquidations_24h_short

        # Set total liquidations and long/short split
        metrics.total_liquidations_24h = total_liquidations
        metrics.liquidations_24h_long = total_longs_liquidated
        metrics.liquidations_24h_short = total_shorts_liquidated

        # Calculate total OI and alt season
        metrics.total_open_interest = (
            (metrics.btc_open_interest or 0) +
            (metrics.eth_open_interest or 0)
        )
        metrics.alt_season_index = max(0, min(100, int((70 - metrics.btc_dominance) * 3.33)))

        # Track sources
        metrics.sources = ['coingecko', 'alternative.me', 'binance']

        self._set_cached(cache_key, metrics)
        return metrics

    # =========================================================================
    # ON-CHAIN DATA
    # =========================================================================

    def get_onchain(self, ticker: str, use_cache: bool = True) -> Optional[OnChainMetrics]:
        """
        Get on-chain metrics for an asset

        Source: Glassnode provider (uses free APIs as fallback)

        Args:
            ticker: Asset symbol
            use_cache: Whether to use cached data

        Returns:
            OnChainMetrics
        """
        cache_key = f"onchain_{ticker}"

        if use_cache:
            cached = self._get_cached(cache_key, 'onchain')
            if cached:
                return cached

        onchain = self.glassnode.get_onchain(ticker)

        if onchain:
            # Calculate velocity from price data
            price = self.get_price(ticker)
            if price and price.market_cap > 0:
                onchain.velocity = price.volume_24h / price.market_cap

            self._set_cached(cache_key, onchain)

        return onchain

    # =========================================================================
    # DEFI DATA
    # =========================================================================

    def get_defi_metrics(self, ticker: str, use_cache: bool = True) -> Optional[DeFiMetrics]:
        """
        Get DeFi protocol metrics (TVL, etc.)

        Source: DeFiLlama

        Args:
            ticker: Protocol ticker
            use_cache: Whether to use cached data

        Returns:
            DeFiMetrics
        """
        cache_key = f"defi_{ticker}"

        if use_cache:
            cached = self._get_cached(cache_key, 'defi')
            if cached:
                return cached

        defi = self.defillama.get_protocol(ticker)

        if defi:
            # Add price data
            price = self.get_price(ticker)
            if price and defi.tvl_usd > 0:
                defi.mcap_tvl_ratio = price.market_cap / defi.tvl_usd

            self._set_cached(cache_key, defi)

        return defi

    def get_total_tvl(self) -> Optional[float]:
        """Get total DeFi TVL"""
        tvl = self.defillama.get_total_tvl()
        return tvl.get('total_tvl') if tvl else None

    # =========================================================================
    # COMPLETE ASSET DATA
    # =========================================================================

    def get_asset_data(
        self,
        ticker: str,
        asset_type: str = 'OTHER',
        include_derivatives: bool = True,
        include_onchain: bool = True,
        include_defi: bool = False
    ) -> AssetData:
        """
        Get complete data for an asset from all relevant sources

        Args:
            ticker: Asset symbol
            asset_type: Asset category (MAJORS, MEMECOIN, PRIVACY, DEFI, OTHER)
            include_derivatives: Include derivatives data
            include_onchain: Include on-chain data
            include_defi: Include DeFi metrics (for DeFi tokens)

        Returns:
            AssetData with all available metrics
        """
        data = AssetData(
            ticker=ticker.upper(),
            asset_type=asset_type,
            data_quality={}
        )

        # Always get price data
        data.price = self.get_price(ticker)
        data.data_quality['price'] = 'high' if data.price else 'unavailable'

        # Get derivatives for majors
        if include_derivatives and asset_type in ['MAJORS', 'OTHER']:
            data.derivatives = self.get_derivatives(ticker)
            data.data_quality['derivatives'] = 'high' if data.derivatives else 'unavailable'

        # Get on-chain data
        if include_onchain:
            data.onchain = self.get_onchain(ticker)
            data.data_quality['onchain'] = data.onchain.source if data.onchain else 'unavailable'

        # Get DeFi metrics
        if include_defi or asset_type == 'DEFI':
            data.defi = self.get_defi_metrics(ticker)
            data.data_quality['defi'] = 'high' if data.defi else 'unavailable'

        data.timestamp = int(time.time())
        return data

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def get_multiple_assets(
        self,
        tickers: List[str],
        asset_types: Dict[str, str] = None
    ) -> Dict[str, AssetData]:
        """
        Get data for multiple assets efficiently

        Args:
            tickers: List of ticker symbols
            asset_types: Optional mapping of ticker -> asset type

        Returns:
            Dict mapping ticker to AssetData
        """
        asset_types = asset_types or {}
        results = {}

        # Batch fetch prices
        prices = self.get_prices_batch(tickers)

        for ticker in tickers:
            ticker = ticker.upper()
            asset_type = asset_types.get(ticker, 'OTHER')

            data = AssetData(
                ticker=ticker,
                asset_type=asset_type,
                data_quality={}
            )

            # Add price from batch
            if ticker in prices:
                data.price = prices[ticker]
                data.data_quality['price'] = 'high'

            # Get derivatives for majors
            if asset_type == 'MAJORS':
                data.derivatives = self.get_derivatives(ticker)
                data.data_quality['derivatives'] = 'high' if data.derivatives else 'unavailable'

            # Get DeFi metrics
            if asset_type == 'DEFI':
                data.defi = self.get_defi_metrics(ticker)
                data.data_quality['defi'] = 'high' if data.defi else 'unavailable'

            data.timestamp = int(time.time())
            results[ticker] = data

        return results

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self) -> Dict[str, bool]:
        """
        Check connectivity to all data sources

        Returns:
            Dict mapping provider name to status
        """
        return {
            'binance': self.binance.test_connection(),
            'coingecko': self.coingecko.test_connection(),
            'coinmarketcap': self.coinmarketcap.test_connection(),
            'blockchain_info': self.glassnode.test_connection(),
            'defillama': self.defillama.test_connection(),
            'alternativeme': self.alternativeme.test_connection()
        }

    def clear_cache(self):
        """Clear all cached data"""
        self._cache = {}


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("DATA AGGREGATOR TEST")
    print("=" * 80)

    aggregator = DataAggregator()

    # Test 1: Health check
    print("\n1. Health Check - All Providers")
    print("-" * 40)
    health = aggregator.health_check()
    for provider, status in health.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {provider}")

    # Test 2: BTC price
    print("\n2. BTC Price (Binance + CoinGecko)")
    print("-" * 40)
    btc = aggregator.get_price('BTC')
    if btc:
        print(f"   Price: ${btc.price_usd:,.2f}")
        print(f"   24h Change: {btc.price_change_24h:+.2f}%")
        print(f"   Market Cap: ${btc.market_cap/1e9:.2f}B")
        print(f"   ATH: ${btc.ath:,.2f} ({btc.ath_change_percentage:.1f}% from ATH)")
        print(f"   Source: {btc.source}")

    # Test 3: BTC derivatives
    print("\n3. BTC Derivatives (Binance)")
    print("-" * 40)
    deriv = aggregator.get_derivatives('BTC')
    if deriv:
        print(f"   Funding Rate: {deriv.funding_rate*100:.4f}%")
        print(f"   Open Interest: ${deriv.open_interest_usd/1e9:.2f}B")
        print(f"   Long Liquidations: ${deriv.liquidations_24h_long/1e6:.2f}M")
        print(f"   Short Liquidations: ${deriv.liquidations_24h_short/1e6:.2f}M")

    # Test 4: Global metrics
    print("\n4. Global Market Metrics")
    print("-" * 40)
    global_data = aggregator.get_global_metrics()
    if global_data:
        print(f"   Total Market Cap: ${global_data.total_market_cap/1e12:.2f}T")
        print(f"   24h Volume: ${global_data.total_volume_24h/1e9:.2f}B")
        print(f"   BTC Dominance: {global_data.btc_dominance:.1f}%")
        print(f"   Fear & Greed: {global_data.fear_greed_index} ({global_data.fear_greed_classification})")
        print(f"   Alt Season Index: {global_data.alt_season_index}")
        print(f"   Sources: {', '.join(global_data.sources)}")

    # Test 5: Complete asset data
    print("\n5. Complete BTC Data")
    print("-" * 40)
    btc_full = aggregator.get_asset_data('BTC', 'MAJORS')
    print(f"   Price: ${btc_full.price.price_usd:,.2f}" if btc_full.price else "   Price: N/A")
    print(f"   Derivatives: {'Available' if btc_full.derivatives else 'N/A'}")
    print(f"   On-Chain: {btc_full.onchain.source if btc_full.onchain else 'N/A'}")
    print(f"   Data Quality: {btc_full.data_quality}")

    # Test 6: Batch prices
    print("\n6. Batch Price Fetch")
    print("-" * 40)
    tickers = ['BTC', 'ETH', 'SOL', 'DOGE']
    prices = aggregator.get_prices_batch(tickers)
    for ticker, price in prices.items():
        print(f"   {ticker}: ${price.price_usd:,.2f} ({price.price_change_24h:+.2f}%)")

    print("\n" + "=" * 80)
    print("✅ DATA AGGREGATOR TESTS COMPLETE")
    print("=" * 80)
