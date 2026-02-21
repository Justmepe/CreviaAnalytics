"""
Glassnode Data Provider - ON-CHAIN METRICS

Glassnode provides professional-grade on-chain analytics:
- Exchange flows (inflows/outflows)
- Active addresses
- Holder distribution
- Network metrics

Pricing:
- Free tier: Limited metrics, 24h resolution
- Standard ($29/mo): More metrics, hourly resolution
- Professional ($799/mo): All metrics, 10-min resolution

Free Endpoints (no API key needed):
- Limited historical data
- 24h resolution only
- Basic metrics

Alternative Free Sources Used:
- Blockchain.info for BTC on-chain data
- Etherscan for ETH data (with free API key)
"""

import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..models import OnChainMetrics


class GlassnodeProvider:
    """
    On-chain data provider

    Primary: Glassnode API (if key available)
    Fallback: Free public APIs (Blockchain.info, Etherscan)
    """

    GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"
    BLOCKCHAIN_INFO_BASE = "https://api.blockchain.info"
    ETHERSCAN_BASE = "https://api.etherscan.io/api"

    # Rate limiting
    MIN_REQUEST_INTERVAL = 1.0

    def __init__(self, api_key: str = None, etherscan_key: str = None):
        """
        Initialize Glassnode provider

        Args:
            api_key: Glassnode API key (optional)
            etherscan_key: Etherscan API key for ETH data (optional)
        """
        self.api_key = api_key
        self.etherscan_key = etherscan_key
        self.last_request_time = 0
        self.session = requests.Session()

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API error: {e}")
            return None

    # =========================================================================
    # BITCOIN ON-CHAIN (Free via Blockchain.info)
    # =========================================================================

    def get_btc_onchain(self) -> Optional[OnChainMetrics]:
        """
        Get BTC on-chain metrics from free sources

        Returns:
            OnChainMetrics for Bitcoin
        """
        # Blockchain.info stats endpoint
        data = self._request(f"{self.BLOCKCHAIN_INFO_BASE}/stats")

        if not data:
            return None

        # Calculate velocity from trade volume vs market cap
        market_cap = float(data.get('market_price_usd', 0)) * float(data.get('n_btc_mined', 0)) / 100000000
        trade_volume = float(data.get('trade_volume_usd', 0))
        velocity = trade_volume / market_cap if market_cap > 0 else 0

        return OnChainMetrics(
            ticker='BTC',
            # Transaction metrics
            transaction_count_24h=int(data.get('n_tx', 0)),
            # Difficulty and hashrate
            hashrate=float(data.get('hash_rate', 0)),
            difficulty=float(data.get('difficulty', 0)),
            # Supply
            total_supply=float(data.get('n_btc_mined', 0)) / 100000000,  # Convert from satoshis
            max_supply=21000000,
            # Calculated velocity
            velocity=velocity,
            timestamp=int(time.time()),
            source='blockchain.info',
            note='Free API - limited metrics available'
        )

    # =========================================================================
    # ETHEREUM ON-CHAIN (Free via Etherscan)
    # =========================================================================

    def get_eth_onchain(self) -> Optional[OnChainMetrics]:
        """
        Get ETH on-chain metrics from Etherscan

        Returns:
            OnChainMetrics for Ethereum
        """
        if not self.etherscan_key:
            return OnChainMetrics(
                ticker='ETH',
                timestamp=int(time.time()),
                source='none',
                note='Etherscan API key required for ETH on-chain data'
            )

        # Get ETH supply
        supply_data = self._request(
            self.ETHERSCAN_BASE,
            params={
                'module': 'stats',
                'action': 'ethsupply',
                'apikey': self.etherscan_key
            }
        )

        # Get ETH2 staking stats
        staking_data = self._request(
            self.ETHERSCAN_BASE,
            params={
                'module': 'stats',
                'action': 'ethsupply2',
                'apikey': self.etherscan_key
            }
        )

        total_supply = 0
        staked_amount = 0

        if supply_data and supply_data.get('status') == '1':
            total_supply = float(supply_data.get('result', 0)) / 1e18

        if staking_data and staking_data.get('status') == '1':
            staking_result = staking_data.get('result', {})
            if isinstance(staking_result, dict):
                staked_amount = float(staking_result.get('EthStaking', 0)) / 1e18

        staking_ratio = (staked_amount / total_supply * 100) if total_supply > 0 else 0

        return OnChainMetrics(
            ticker='ETH',
            total_supply=total_supply,
            staked_amount=staked_amount,
            staking_ratio=staking_ratio,
            timestamp=int(time.time()),
            source='etherscan',
            note='Free Etherscan API - limited metrics'
        )

    # =========================================================================
    # GLASSNODE (If API key available)
    # =========================================================================

    def get_glassnode_metric(self, asset: str, metric: str, resolution: str = '24h') -> Optional[float]:
        """
        Get specific metric from Glassnode API

        Args:
            asset: Asset symbol (btc, eth)
            metric: Metric path (e.g., 'addresses/active_count')
            resolution: Data resolution

        Returns:
            Latest metric value or None
        """
        if not self.api_key:
            return None

        url = f"{self.GLASSNODE_BASE}/{metric}"
        params = {
            'a': asset.lower(),
            'api_key': self.api_key,
            'i': resolution
        }

        data = self._request(url, params)

        if data and isinstance(data, list) and len(data) > 0:
            return data[-1].get('v')

        return None

    def get_exchange_netflow(self, asset: str) -> Optional[Dict[str, float]]:
        """
        Get exchange netflow data from Glassnode

        Args:
            asset: Asset symbol

        Returns:
            Dict with inflow, outflow, netflow
        """
        if not self.api_key:
            return None

        inflow = self.get_glassnode_metric(asset, 'transactions/transfers_volume_to_exchanges_sum')
        outflow = self.get_glassnode_metric(asset, 'transactions/transfers_volume_from_exchanges_sum')

        if inflow is not None and outflow is not None:
            return {
                'inflow': inflow,
                'outflow': outflow,
                'netflow': inflow - outflow
            }

        return None

    # =========================================================================
    # UNIFIED INTERFACE
    # =========================================================================

    def get_onchain(self, ticker: str) -> Optional[OnChainMetrics]:
        """
        Get on-chain metrics for any supported asset

        Args:
            ticker: Asset symbol

        Returns:
            OnChainMetrics
        """
        ticker = ticker.upper()

        if ticker == 'BTC':
            return self.get_btc_onchain()
        elif ticker == 'ETH':
            return self.get_eth_onchain()
        else:
            # Return basic metrics with note
            return OnChainMetrics(
                ticker=ticker,
                timestamp=int(time.time()),
                source='none',
                note=f'On-chain data for {ticker} requires Glassnode API key'
            )

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request(f"{self.BLOCKCHAIN_INFO_BASE}/stats")
        return data is not None


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("GLASSNODE/ON-CHAIN PROVIDER TEST")
    print("=" * 80)

    provider = GlassnodeProvider()

    # Test 1: Connection
    print("\n1. Testing connection to Blockchain.info...")
    if provider.test_connection():
        print("   ✅ Connected to Blockchain.info")
    else:
        print("   ❌ Connection failed")

    # Test 2: BTC on-chain
    print("\n2. Testing BTC on-chain metrics...")
    btc = provider.get_btc_onchain()
    if btc:
        print(f"   ✅ Transaction Count (24h): {btc.transaction_count_24h:,}")
        print(f"   ✅ Hashrate: {btc.hashrate/1e18:.2f} EH/s")
        print(f"   ✅ Difficulty: {btc.difficulty/1e12:.2f}T")
        print(f"   ✅ Total Supply: {btc.total_supply:,.0f} BTC")
        print(f"   ✅ Velocity: {btc.velocity:.4f}")
        print(f"   Source: {btc.source}")
    else:
        print("   ❌ Failed to fetch BTC on-chain")

    # Test 3: ETH on-chain (requires API key)
    print("\n3. Testing ETH on-chain metrics...")
    eth = provider.get_eth_onchain()
    if eth:
        print(f"   ⚠️  {eth.note}")
    else:
        print("   ❌ Failed to fetch ETH on-chain")

    print("\n" + "=" * 80)
    print("✅ ON-CHAIN PROVIDER TESTS COMPLETE")
    print("=" * 80)
