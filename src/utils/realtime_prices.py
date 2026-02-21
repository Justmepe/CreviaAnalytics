"""
Real-Time Price Fetcher from Binance
Fetches live prices immediately before thread generation to ensure accuracy
"""

import requests
import json
import os
from typing import Dict, Any, List
from datetime import datetime

# Binance API endpoints
BINANCE_API = "https://api.binance.com/api/v3"
BINANCE_FUTURES = "https://fapi.binance.com/fapi/v1"


def fetch_binance_spot_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch real-time spot prices from Binance for multiple symbols
    
    Args:
        symbols: List of symbols like ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    Returns:
        dict: {'BTCUSDT': 89500.00, 'ETHUSDT': 3250.00, ...}
    """
    try:
        prices = {}
        for symbol in symbols:
            try:
                url = f"{BINANCE_API}/ticker/price"
                params = {'symbol': symbol}
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                prices[symbol] = float(data['price'])
                print(f"   ✅ {symbol}: ${prices[symbol]:,.2f}")
            except Exception as e:
                print(f"   ❌ Error fetching {symbol}: {e}")
                continue
        
        return prices
    except Exception as e:
        print(f"Error in fetch_binance_spot_prices: {e}")
        return {}


def fetch_binance_futures_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch real-time futures prices from Binance for multiple symbols
    
    Args:
        symbols: List of symbols like ['BTCUSDT', 'ETHUSDT']
    
    Returns:
        dict: {'BTCUSDT': 89500.00, 'ETHUSDT': 3250.00, ...}
    """
    try:
        prices = {}
        for symbol in symbols:
            try:
                url = f"{BINANCE_FUTURES}/ticker/price"
                params = {'symbol': symbol}
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                prices[symbol] = float(data['price'])
                print(f"   ✅ {symbol} (Futures): ${prices[symbol]:,.2f}")
            except Exception as e:
                print(f"   ❌ Error fetching {symbol} (Futures): {e}")
                continue
        
        return prices
    except Exception as e:
        print(f"Error in fetch_binance_futures_prices: {e}")
        return {}


def get_crypto_prices_before_thread(assets: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch REAL-TIME prices from Binance for all assets before thread generation
    
    This is the FINAL price check to ensure accuracy in tweets
    
    Args:
        assets: List of symbols like ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'SHIB', ...]
    
    Returns:
        dict: {
            'BTC': {'spot': 89500.00, 'timestamp': '2026-02-01 14:30:00'},
            'ETH': {'spot': 3250.00, 'timestamp': '2026-02-01 14:30:00'},
            ...
        }
    """
    print("\n🔄 FETCHING REAL-TIME PRICES FROM BINANCE...")
    print("-" * 60)
    
    result = {}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Symbol mapping for assets with different Binance names
    symbol_mapping = {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT',
        'SOL': 'SOLUSDT',
        'BNB': 'BNBUSDT',
        'AAVE': 'AAVEUSDT',
        'UNI': 'UNIUSDT',
        'CRV': 'CRVUSDT',
        'LIDO': 'LDOUSDT',  # Lido token on Binance
        'DOGE': 'DOGEUSDT',
        'SHIB': 'SHIBUSDT',
        'PEPE': 'PEPEUSDT',
        'FLOKI': 'FLOKIUSDT',
        'XMR': 'XMRUSDT',
        'ZEC': 'ZECUSDT',
        'DASH': 'DASHUSDT',
        'MONERO': 'XMRUSDT'  # Monero is XMR on Binance
    }
    
    # Fetch spot prices
    spot_prices = {}
    for asset in assets:
        symbol = symbol_mapping.get(asset, f"{asset}USDT")
        try:
            url = f"{BINANCE_API}/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            spot_prices[asset] = float(data['price'])
            print(f"   ✅ {asset:8} ({symbol}): ${float(data['price']):>12,.2f}")
        except Exception as e:
            print(f"   ❌ Error fetching {asset} ({symbol}): {e}")
            spot_prices[asset] = 0.0
    
    # Build result
    for asset in assets:
        result[asset] = {
            'spot': spot_prices.get(asset, 0.0),
            'timestamp': timestamp,
            'source': 'Binance Spot'
        }
    
    print("-" * 60)
    successful = len([p for p in result.values() if p['spot'] > 0])
    print(f"✅ Real-time price fetch complete ({successful}/{len(assets)} successful)")
    print()
    
    return result


def inject_real_prices_into_analysis(
    analyses: Dict[str, Any],
    real_prices: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    """
    Update analysis data with real-time Binance prices before thread generation
    
    Args:
        analyses: Current analyses from orchestrator
        real_prices: Fresh prices from Binance
    
    Returns:
        dict: Updated analyses with latest prices
    """
    updated = analyses.copy()
    
    for asset, price_data in real_prices.items():
        if asset in updated and price_data['spot'] > 0:
            # Update the snapshot with real-time price
            if 'snapshot' not in updated[asset]:
                updated[asset]['snapshot'] = {}
            if 'price' not in updated[asset]['snapshot']:
                updated[asset]['snapshot']['price'] = {}
            
            updated[asset]['snapshot']['price']['mark_price'] = price_data['spot']
            updated[asset]['snapshot']['price']['binance_timestamp'] = price_data['timestamp']
            updated[asset]['snapshot']['price']['source'] = 'Binance Real-Time'
    
    return updated


def validate_prices_for_thread(prices: Dict[str, Dict[str, float]]) -> bool:
    """
    Validate that we have real prices for critical assets before sending thread
    
    Critical assets: BTC, ETH, SOL, BNB
    
    Returns:
        bool: True if all critical prices available, False otherwise
    """
    critical_assets = ['BTC', 'ETH', 'SOL', 'BNB']
    
    for asset in critical_assets:
        if asset not in prices or prices[asset].get('spot', 0) == 0:
            print(f"⚠️  WARNING: No real-time price for {asset}, thread may have stale data")
            return False
    
    print("✅ All critical asset prices validated from Binance")
    return True


# Testing
if __name__ == '__main__':
    # Test fetching prices for all 16 assets
    assets = ['BTC', 'ETH', 'SOL', 'BNB', 'AAVE', 'UNI', 'CRV', 'LIDO', 'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'XMR', 'ZEC', 'DASH', 'MONERO']
    
    prices = get_crypto_prices_before_thread(assets)
    
    print("\n📊 REAL-TIME PRICE SNAPSHOT:")
    print("=" * 60)
    for asset, data in prices.items():
        if data['spot'] > 0:
            print(f"{asset:8} → ${data['spot']:>12,.2f} ({data['source']})")
    print("=" * 60)
    
    # Validate critical assets
    validate_prices_for_thread(prices)
