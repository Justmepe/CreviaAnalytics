"""
Data Providers - Individual API integrations

Each provider handles its own:
- Rate limiting
- Error handling
- Data transformation to standard models
- Caching (optional)

Priority Order:
1. BinanceProvider - Primary for prices & derivatives (reliable, generous limits)
2. CoinGeckoProvider - Secondary for market data
3. CoinMarketCapProvider - Tertiary for global metrics
4. GlassnodeProvider - On-chain metrics (optional, paid)
5. DeFiLlamaProvider - TVL data (free)
6. AlternativeMeProvider - Fear & Greed (free)
"""

from .binance_provider import BinanceProvider
from .coingecko_provider import CoinGeckoProvider
from .coinmarketcap_provider import CoinMarketCapProvider
from .glassnode_provider import GlassnodeProvider
from .defillama_provider import DeFiLlamaProvider
from .alternativeme_provider import AlternativeMeProvider

__all__ = [
    'BinanceProvider',
    'CoinGeckoProvider',
    'CoinMarketCapProvider',
    'GlassnodeProvider',
    'DeFiLlamaProvider',
    'AlternativeMeProvider'
]
