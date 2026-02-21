"""
Alternative.me Data Provider - FEAR & GREED INDEX

Alternative.me provides the popular Crypto Fear & Greed Index.

Features:
- Fear & Greed Index (0-100)
- Historical data
- Classification (Extreme Fear, Fear, Neutral, Greed, Extreme Greed)

FREE - No API key required!
"""

import requests
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import MarketMetrics


class AlternativeMeProvider:
    """
    Alternative.me API Provider - Fear & Greed Index

    The Fear & Greed Index analyzes:
    - Volatility (25%)
    - Market momentum/volume (25%)
    - Social media (15%)
    - Dominance (10%)
    - Trends (10%)
    - Surveys (15%)
    """

    BASE_URL = "https://api.alternative.me"

    # Rate limiting
    MIN_REQUEST_INTERVAL = 1.0

    def __init__(self):
        """Initialize Alternative.me provider"""
        self.last_request_time = 0
        self.session = requests.Session()

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
            print(f"Alternative.me API error: {e}")
            return None

    # =========================================================================
    # FEAR & GREED INDEX
    # =========================================================================

    def get_fear_greed(self) -> Optional[Dict[str, Any]]:
        """
        Get current Fear & Greed Index

        Returns:
            Dict with index value and classification
        """
        data = self._request("/fng/")

        if not data or 'data' not in data:
            return None

        if len(data['data']) == 0:
            return None

        current = data['data'][0]

        return {
            'value': int(current.get('value', 50)),
            'classification': current.get('value_classification', 'Neutral'),
            'timestamp': int(current.get('timestamp', time.time())),
            'time_until_update': int(current.get('time_until_update', 0))
        }

    def get_fear_greed_historical(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical Fear & Greed data

        Args:
            days: Number of days of history

        Returns:
            List of daily Fear & Greed values
        """
        data = self._request("/fng/", params={'limit': days})

        if not data or 'data' not in data:
            return None

        return [
            {
                'value': int(item.get('value', 50)),
                'classification': item.get('value_classification', 'Neutral'),
                'timestamp': int(item.get('timestamp', 0)),
                'date': datetime.fromtimestamp(int(item.get('timestamp', 0))).strftime('%Y-%m-%d')
            }
            for item in data['data']
        ]

    def get_fear_greed_for_metrics(self) -> tuple:
        """
        Get Fear & Greed index and classification for use in MarketMetrics

        Returns:
            Tuple of (value: int, classification: str)
        """
        fg = self.get_fear_greed()

        if fg:
            return fg['value'], fg['classification']

        return 50, 'Neutral'  # Default fallback

    # =========================================================================
    # ANALYSIS HELPERS
    # =========================================================================

    def interpret_fear_greed(self, value: int) -> Dict[str, Any]:
        """
        Interpret Fear & Greed value

        Args:
            value: Fear & Greed index (0-100)

        Returns:
            Dict with interpretation
        """
        if value <= 24:
            level = 'extreme_fear'
            signal = 'Strong contrarian buy signal'
            risk = 'Low (sentiment oversold)'
        elif value <= 44:
            level = 'fear'
            signal = 'Accumulation zone'
            risk = 'Low-Medium'
        elif value <= 55:
            level = 'neutral'
            signal = 'Wait for direction'
            risk = 'Medium'
        elif value <= 74:
            level = 'greed'
            signal = 'Caution - getting extended'
            risk = 'Medium-High'
        else:
            level = 'extreme_greed'
            signal = 'Strong contrarian sell signal'
            risk = 'High (sentiment overbought)'

        return {
            'value': value,
            'level': level,
            'signal': signal,
            'risk': risk,
            'contrarian_action': 'buy' if value < 40 else 'sell' if value > 60 else 'neutral'
        }

    # =========================================================================
    # TESTING
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API connectivity"""
        data = self._request("/fng/")
        return data is not None and 'data' in data


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("ALTERNATIVE.ME PROVIDER TEST (Fear & Greed Index)")
    print("=" * 80)

    provider = AlternativeMeProvider()

    # Test 1: Connection
    print("\n1. Testing connection...")
    if provider.test_connection():
        print("   ✅ Connected to Alternative.me API")
    else:
        print("   ❌ Connection failed")

    # Test 2: Current Fear & Greed
    print("\n2. Testing current Fear & Greed...")
    fg = provider.get_fear_greed()
    if fg:
        print(f"   ✅ Current Value: {fg['value']}")
        print(f"   ✅ Classification: {fg['classification']}")
        print(f"   ✅ Updates in: {fg['time_until_update']//3600}h {(fg['time_until_update']%3600)//60}m")
    else:
        print("   ❌ Failed to fetch Fear & Greed")

    # Test 3: Interpretation
    print("\n3. Testing interpretation...")
    if fg:
        interp = provider.interpret_fear_greed(fg['value'])
        print(f"   ✅ Level: {interp['level'].replace('_', ' ').title()}")
        print(f"   ✅ Signal: {interp['signal']}")
        print(f"   ✅ Risk: {interp['risk']}")
        print(f"   ✅ Contrarian Action: {interp['contrarian_action'].upper()}")

    # Test 4: Historical data
    print("\n4. Testing 7-day history...")
    history = provider.get_fear_greed_historical(7)
    if history:
        for day in history:
            print(f"   ✅ {day['date']}: {day['value']} ({day['classification']})")
    else:
        print("   ❌ Failed to fetch history")

    print("\n" + "=" * 80)
    print("✅ ALTERNATIVE.ME PROVIDER TESTS COMPLETE")
    print("=" * 80)
