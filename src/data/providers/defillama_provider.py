"""
DeFiLlama Data Provider - DEFI TVL DATA

DeFiLlama is FREE and provides:
- Total Value Locked (TVL) for all DeFi protocols
- TVL by chain
- Protocol-specific metrics
- Historical data
- Fees and revenue

No API key required!

Endpoints:
- /tvl - Total TVL
- /protocols - All protocols
- /protocol/{name} - Single protocol details
- /chains - TVL by chain
"""

import requests
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import DeFiMetrics, MarketMetrics


class DeFiLlamaProvider:
    """
    DeFiLlama API Provider - Free DeFi data

    Features:
    - TVL for all protocols
    - Chain breakdown
    - Historical data
    - Fees and revenue
    """

    BASE_URL = "https://api.llama.fi"
    COINS_BASE = "https://coins.llama.fi"

    # Rate limiting (generous - no official limits)
    MIN_REQUEST_INTERVAL = 0.5

    # Protocol name mappings
    PROTOCOL_MAP = {
        'AAVE': 'aave',
        'UNI': 'uniswap',
        'CRV': 'curve-dex',
        'COMP': 'compound',
        'MKR': 'makerdao',
        'SUSHI': 'sushiswap',
        'LDO': 'lido',
        'GMX': 'gmx',
        'DYDX': 'dydx',
        'SNX': 'synthetix',
        'BAL': 'balancer',
        '1INCH': '1inch-network',
        'YFI': 'yearn-finance',
    }

    def __init__(self):
        """Initialize DeFiLlama provider"""
        self.last_request_time = 0
        self.session = requests.Session()

    def _rate_limit(self):
        """Respect rate limits between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get_protocol_slug(self, ticker: str) -> str:
        """Convert ticker to DeFiLlama protocol slug"""
        return self.PROTOCOL_MAP.get(ticker.upper(), ticker.lower())

    def _request(self, endpoint: str) -> Optional[Any]:
        """Make API request with error handling"""
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"DeFiLlama API error: {e}")
            return None

    # =========================================================================
    # TOTAL TVL
    # =========================================================================

    def get_total_tvl(self) -> Optional[Dict[str, float]]:
        """
        Get total DeFi TVL

        Returns:
            Dict with total TVL and chain breakdown
        """
        # Use v2/chains endpoint and sum all chain TVLs
        chains = self.get_tvl_by_chain()

        if chains is None:
            return None

        total = sum(chains.values())
        return {'total_tvl': total}

    def get_tvl_by_chain(self) -> Optional[Dict[str, float]]:
        """
        Get TVL breakdown by chain

        Returns:
            Dict mapping chain name to TVL
        """
        data = self._request("/v2/chains")

        if not data:
            return None

        return {
            chain['name']: float(chain.get('tvl', 0))
            for chain in data
            if 'tvl' in chain
        }

    # =========================================================================
    # PROTOCOL DATA
    # =========================================================================

    def get_protocol(self, ticker: str) -> Optional[DeFiMetrics]:
        """
        Get detailed data for a specific protocol

        Args:
            ticker: Protocol ticker (e.g., 'AAVE', 'UNI')

        Returns:
            DeFiMetrics with protocol data
        """
        slug = self._get_protocol_slug(ticker)
        data = self._request(f"/protocol/{slug}")

        if not data:
            return None

        # Get current TVL - handle both number and list formats
        tvl_data = data.get('tvl', 0)
        tvl_change_24h = 0
        tvl_change_7d = 0

        if isinstance(tvl_data, list) and len(tvl_data) > 0:
            # TVL is historical data - get latest value
            current_tvl = float(tvl_data[-1].get('totalLiquidityUSD', 0) or 0)

            # Calculate 24h change
            if len(tvl_data) >= 2:
                yesterday_tvl = float(tvl_data[-2].get('totalLiquidityUSD', 0) or 0)
                if yesterday_tvl > 0:
                    tvl_change_24h = ((current_tvl - yesterday_tvl) / yesterday_tvl) * 100

            # Calculate 7d change
            if len(tvl_data) >= 8:
                week_ago_tvl = float(tvl_data[-8].get('totalLiquidityUSD', 0) or 0)
                if week_ago_tvl > 0:
                    tvl_change_7d = ((current_tvl - week_ago_tvl) / week_ago_tvl) * 100
        elif isinstance(tvl_data, (int, float)):
            current_tvl = float(tvl_data or 0)
        else:
            current_tvl = 0

        # Get chain breakdown
        chain_tvls = data.get('chainTvls', {})
        tvl_by_chain = {}
        for chain, chain_data in chain_tvls.items():
            if isinstance(chain_data, dict) and 'tvl' in chain_data:
                chain_tvl = chain_data['tvl']
                if isinstance(chain_tvl, list) and len(chain_tvl) > 0:
                    tvl_by_chain[chain] = float(chain_tvl[-1].get('totalLiquidityUSD', 0) or 0)
                elif isinstance(chain_tvl, (int, float)):
                    tvl_by_chain[chain] = float(chain_tvl)
            elif isinstance(chain_data, (int, float)):
                tvl_by_chain[chain] = float(chain_data)

        return DeFiMetrics(
            protocol=data.get('name', slug),
            ticker=ticker.upper(),
            tvl_usd=current_tvl,
            tvl_change_24h=tvl_change_24h,
            tvl_change_7d=tvl_change_7d,
            tvl_by_chain=tvl_by_chain,
            mcap_tvl_ratio=float(data.get('mcap', 0) or 0) / current_tvl if current_tvl > 0 else 0,
            timestamp=int(time.time()),
            source='defillama'
        )

    def get_top_protocols(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get top protocols by TVL

        Args:
            limit: Number of protocols to return

        Returns:
            List of protocol summaries
        """
        data = self._request("/protocols")

        if not data:
            return []

        # Sort by TVL and return top N
        sorted_protocols = sorted(data, key=lambda x: float(x.get('tvl', 0) or 0), reverse=True)

        return [
            {
                'name': p.get('name'),
                'symbol': p.get('symbol', '').upper(),
                'tvl': float(p.get('tvl', 0) or 0),
                'change_1d': float(p.get('change_1d', 0) or 0),
                'change_7d': float(p.get('change_7d', 0) or 0),
                'category': p.get('category'),
                'chains': p.get('chains', [])
            }
            for p in sorted_protocols[:limit]
        ]

    # =========================================================================
    # FEES AND REVENUE
    # =========================================================================

    def get_protocol_fees(self, ticker: str) -> Optional[Dict[str, float]]:
        """
        Get fees and revenue for a protocol

        Args:
            ticker: Protocol ticker

        Returns:
            Dict with fees data
        """
        slug = self._get_protocol_slug(ticker)

        # Fees endpoint
        data = self._request(f"/summary/fees/{slug}")

        if not data:
            return None

        return {
            'fees_24h': float(data.get('total24h', 0) or 0),
            'fees_7d': float(data.get('total7d', 0) or 0),
            'fees_30d': float(data.get('total30d', 0) or 0),
        }

    # =========================================================================
    # GLOBAL DEFI METRICS
    # =========================================================================

    def get_global_defi_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get global DeFi metrics

        Returns:
            Dict with global DeFi stats
        """
        total_tvl = self.get_total_tvl()
        chain_tvl = self.get_tvl_by_chain()
        top_protocols = self.get_top_protocols(10)

        if not total_tvl:
            return None

        return {
            'total_tvl': total_tvl.get('total_tvl', 0),
            'tvl_by_chain': chain_tvl or {},
            'top_protocols': top_protocols,
            'timestamp': int(time.time())
        }

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request("/v2/chains")
        return data is not None and len(data) > 0


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("DEFILLAMA PROVIDER TEST")
    print("=" * 80)

    provider = DeFiLlamaProvider()

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to DeFiLlama API")
    else:
        print("   ❌ Connection failed")

    # Test 2: Total TVL
    print("\n2. Testing total TVL...")
    tvl = provider.get_total_tvl()
    if tvl:
        print(f"   ✅ Total DeFi TVL: ${tvl['total_tvl']/1e9:.2f}B")
    else:
        print("   ❌ Failed to fetch TVL")

    # Test 3: TVL by chain
    print("\n3. Testing TVL by chain (Top 5)...")
    chain_tvl = provider.get_tvl_by_chain()
    if chain_tvl:
        sorted_chains = sorted(chain_tvl.items(), key=lambda x: x[1], reverse=True)[:5]
        for chain, tvl in sorted_chains:
            print(f"   ✅ {chain}: ${tvl/1e9:.2f}B")
    else:
        print("   ❌ Failed to fetch chain TVL")

    # Test 4: Protocol data (AAVE)
    print("\n4. Testing AAVE protocol data...")
    aave = provider.get_protocol('AAVE')
    if aave:
        print(f"   ✅ AAVE TVL: ${aave.tvl_usd/1e9:.2f}B")
        print(f"   ✅ 24h Change: {aave.tvl_change_24h:+.2f}%")
        if aave.tvl_by_chain:
            print(f"   ✅ Chains: {', '.join(list(aave.tvl_by_chain.keys())[:5])}")
    else:
        print("   ❌ Failed to fetch AAVE data")

    # Test 5: Top protocols
    print("\n5. Testing top protocols...")
    top = provider.get_top_protocols(5)
    if top:
        for p in top:
            print(f"   ✅ {p['name']}: ${p['tvl']/1e9:.2f}B ({p['change_1d']:+.1f}% 24h)")
    else:
        print("   ❌ Failed to fetch top protocols")

    print("\n" + "=" * 80)
    print("✅ DEFILLAMA PROVIDER TESTS COMPLETE")
    print("=" * 80)
