"""
Data Models - Consistent data structures across all providers

These dataclasses ensure consistent data format regardless of source.
Each provider transforms raw API data into these standard structures.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import time


@dataclass
class PriceSnapshot:
    """Price data snapshot for any asset"""
    ticker: str
    price_usd: float
    price_change_24h: float = 0.0  # Percentage
    price_change_1h: float = 0.0   # Percentage
    price_change_7d: float = 0.0   # Percentage
    high_24h: float = 0.0
    low_24h: float = 0.0
    volume_24h: float = 0.0
    volume_change_24h: float = 0.0  # Percentage
    market_cap: float = 0.0
    market_cap_rank: int = 0
    circulating_supply: float = 0.0
    total_supply: float = 0.0
    ath: float = 0.0
    ath_change_percentage: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'price_usd': self.price_usd,
            'price_change_24h': self.price_change_24h,
            'price_change_1h': self.price_change_1h,
            'price_change_7d': self.price_change_7d,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h,
            'volume_24h': self.volume_24h,
            'volume_change_24h': self.volume_change_24h,
            'market_cap': self.market_cap,
            'market_cap_rank': self.market_cap_rank,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply,
            'ath': self.ath,
            'ath_change_percentage': self.ath_change_percentage,
            'timestamp': self.timestamp,
            'source': self.source
        }


@dataclass
class DerivativesData:
    """Derivatives market data (funding, OI, liquidations)"""
    ticker: str
    # Funding rates
    funding_rate: float = 0.0  # Current funding rate
    funding_rate_24h_ago: float = 0.0  # For calculating change
    funding_rate_change_24h: float = 0.0
    next_funding_time: int = 0
    # Open Interest
    open_interest_usd: float = 0.0
    open_interest_base: float = 0.0  # In base currency (BTC, ETH)
    open_interest_change_24h: float = 0.0  # Percentage
    # Liquidations
    liquidations_24h_long: float = 0.0  # USD value
    liquidations_24h_short: float = 0.0  # USD value
    liquidations_24h_total: float = 0.0
    # Long/Short Ratio
    long_short_ratio: float = 1.0  # >1 = more longs, <1 = more shorts
    # Mark vs Index price
    mark_price: float = 0.0
    index_price: float = 0.0
    mark_index_spread: float = 0.0  # Percentage difference
    timestamp: int = field(default_factory=lambda: int(time.time()))
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'funding_rate': self.funding_rate,
            'funding_rate_24h_ago': self.funding_rate_24h_ago,
            'funding_rate_change_24h': self.funding_rate_change_24h,
            'next_funding_time': self.next_funding_time,
            'open_interest_usd': self.open_interest_usd,
            'open_interest_base': self.open_interest_base,
            'open_interest_change_24h': self.open_interest_change_24h,
            'liquidations_24h_long': self.liquidations_24h_long,
            'liquidations_24h_short': self.liquidations_24h_short,
            'liquidations_24h_total': self.liquidations_24h_total,
            'long_short_ratio': self.long_short_ratio,
            'mark_price': self.mark_price,
            'index_price': self.index_price,
            'mark_index_spread': self.mark_index_spread,
            'timestamp': self.timestamp,
            'source': self.source
        }


@dataclass
class MarketMetrics:
    """Global crypto market metrics"""
    total_market_cap: float = 0.0
    total_volume_24h: float = 0.0
    market_cap_change_24h: float = 0.0  # Percentage
    btc_dominance: float = 0.0
    eth_dominance: float = 0.0
    active_cryptocurrencies: int = 0
    # Fear & Greed
    fear_greed_index: int = 50
    fear_greed_classification: str = "Neutral"
    # Alt Season
    alt_season_index: int = 0  # 0 = BTC season, 100 = Alt season
    # Global derivatives
    total_open_interest: float = 0.0
    total_liquidations_24h: float = 0.0
    liquidations_24h_long: float = 0.0  # Long liquidations
    liquidations_24h_short: float = 0.0  # Short liquidations
    # BTC specific (always included as reference)
    btc_price: float = 0.0
    btc_change_24h: float = 0.0
    btc_funding_rate: float = 0.0
    btc_open_interest: float = 0.0
    # ETH specific
    eth_price: float = 0.0
    eth_change_24h: float = 0.0
    eth_funding_rate: float = 0.0
    eth_open_interest: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_market_cap': self.total_market_cap,
            'total_volume_24h': self.total_volume_24h,
            'market_cap_change_24h': self.market_cap_change_24h,
            'btc_dominance': self.btc_dominance,
            'eth_dominance': self.eth_dominance,
            'active_cryptocurrencies': self.active_cryptocurrencies,
            'fear_greed_index': self.fear_greed_index,
            'fear_greed_classification': self.fear_greed_classification,
            'alt_season_index': self.alt_season_index,
            'total_open_interest': self.total_open_interest,
            'total_liquidations_24h': self.total_liquidations_24h,
            'liquidations_24h_long': self.liquidations_24h_long,
            'liquidations_24h_short': self.liquidations_24h_short,
            'btc_price': self.btc_price,
            'btc_change_24h': self.btc_change_24h,
            'btc_funding_rate': self.btc_funding_rate,
            'btc_open_interest': self.btc_open_interest,
            'eth_price': self.eth_price,
            'eth_change_24h': self.eth_change_24h,
            'eth_funding_rate': self.eth_funding_rate,
            'eth_open_interest': self.eth_open_interest,
            'timestamp': self.timestamp,
            'sources': self.sources
        }


@dataclass
class OnChainMetrics:
    """On-chain data for an asset"""
    ticker: str
    # Exchange flows
    exchange_inflow_24h: float = 0.0  # USD value
    exchange_outflow_24h: float = 0.0
    exchange_netflow_24h: float = 0.0  # Positive = inflow, Negative = outflow
    # Active addresses
    active_addresses_24h: int = 0
    active_addresses_change_7d: float = 0.0  # Percentage
    # Transaction count
    transaction_count_24h: int = 0
    # Holder metrics
    whale_count: int = 0  # Addresses holding >1000 BTC or equivalent
    whale_holdings_change_7d: float = 0.0  # Percentage
    # Network hashrate (for PoW)
    hashrate: float = 0.0
    difficulty: float = 0.0
    # Staking (for PoS)
    staked_amount: float = 0.0
    staking_ratio: float = 0.0  # Percentage of supply staked
    # Velocity
    velocity: float = 0.0  # Volume / Market Cap
    # Supply metrics
    total_supply: float = 0.0
    max_supply: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    source: str = "unknown"
    note: str = ""  # For indicating data limitations

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'exchange_inflow_24h': self.exchange_inflow_24h,
            'exchange_outflow_24h': self.exchange_outflow_24h,
            'exchange_netflow_24h': self.exchange_netflow_24h,
            'active_addresses_24h': self.active_addresses_24h,
            'active_addresses_change_7d': self.active_addresses_change_7d,
            'transaction_count_24h': self.transaction_count_24h,
            'whale_count': self.whale_count,
            'whale_holdings_change_7d': self.whale_holdings_change_7d,
            'hashrate': self.hashrate,
            'difficulty': self.difficulty,
            'staked_amount': self.staked_amount,
            'staking_ratio': self.staking_ratio,
            'velocity': self.velocity,
            'total_supply': self.total_supply,
            'max_supply': self.max_supply,
            'timestamp': self.timestamp,
            'source': self.source,
            'note': self.note
        }


@dataclass
class DeFiMetrics:
    """DeFi-specific metrics"""
    protocol: str
    ticker: str
    # TVL
    tvl_usd: float = 0.0
    tvl_change_24h: float = 0.0  # Percentage
    tvl_change_7d: float = 0.0
    # Chain breakdown
    tvl_by_chain: Dict[str, float] = field(default_factory=dict)
    # Yield
    apy: float = 0.0
    apy_7d_avg: float = 0.0
    # Fees & Revenue
    fees_24h: float = 0.0
    fees_7d: float = 0.0
    revenue_24h: float = 0.0
    # Users
    active_users_24h: int = 0
    # Mcap / TVL ratio
    mcap_tvl_ratio: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'protocol': self.protocol,
            'ticker': self.ticker,
            'tvl_usd': self.tvl_usd,
            'tvl_change_24h': self.tvl_change_24h,
            'tvl_change_7d': self.tvl_change_7d,
            'tvl_by_chain': self.tvl_by_chain,
            'apy': self.apy,
            'apy_7d_avg': self.apy_7d_avg,
            'fees_24h': self.fees_24h,
            'fees_7d': self.fees_7d,
            'revenue_24h': self.revenue_24h,
            'active_users_24h': self.active_users_24h,
            'mcap_tvl_ratio': self.mcap_tvl_ratio,
            'timestamp': self.timestamp,
            'source': self.source
        }


@dataclass
class AssetData:
    """Complete aggregated data for an asset from all sources"""
    ticker: str
    asset_type: str  # MAJORS, MEMECOIN, PRIVACY, DEFI, OTHER
    price: Optional[PriceSnapshot] = None
    derivatives: Optional[DerivativesData] = None
    onchain: Optional[OnChainMetrics] = None
    defi: Optional[DeFiMetrics] = None
    timestamp: int = field(default_factory=lambda: int(time.time()))
    data_quality: Dict[str, str] = field(default_factory=dict)  # Source reliability per metric

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'asset_type': self.asset_type,
            'price': self.price.to_dict() if self.price else None,
            'derivatives': self.derivatives.to_dict() if self.derivatives else None,
            'onchain': self.onchain.to_dict() if self.onchain else None,
            'defi': self.defi.to_dict() if self.defi else None,
            'timestamp': self.timestamp,
            'data_quality': self.data_quality
        }
