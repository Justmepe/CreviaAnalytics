"""
Data Layer - Unified Data Aggregation

This module provides a clean separation between data fetching and analysis.
Claude is used ONLY for content writing, NOT for data research.

Architecture:
- providers/: Individual data source providers (Binance, CoinGecko, etc.)
- aggregator.py: Combines data from multiple sources
- models.py: Data structures for consistent data handling

Data Sources (Priority Order):
1. Binance - Primary (reliable, no rate limits with API key)
2. CoinGecko - Secondary (market data, coin info)
3. CoinMarketCap - Tertiary (global metrics)
4. Glassnode - On-chain metrics (optional, paid)
5. DeFiLlama - DeFi TVL data (free)
6. Alternative.me - Fear & Greed Index (free)
"""

# Import models first (always available)
from .models import (
    PriceSnapshot,
    DerivativesData,
    MarketMetrics,
    OnChainMetrics,
    DeFiMetrics,
    AssetData
)

# Try to import aggregator (may not exist yet during development)
try:
    from .aggregator import DataAggregator
    __all__ = [
        'DataAggregator',
        'PriceSnapshot',
        'DerivativesData',
        'MarketMetrics',
        'OnChainMetrics',
        'DeFiMetrics',
        'AssetData'
    ]
except ImportError:
    __all__ = [
        'PriceSnapshot',
        'DerivativesData',
        'MarketMetrics',
        'OnChainMetrics',
        'DeFiMetrics',
        'AssetData'
    ]
