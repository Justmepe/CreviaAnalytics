"""
Crypto Technical Analysis Engine
---------------------------------
Pure pandas-based structure/zone analysis adapted from the MT5 TA system.
Supports Binance and Bybit via REST OHLCV. No broker connection required.
"""

from .crypto_ta_engine import CryptoTAEngine, analyze_asset

__all__ = ['CryptoTAEngine', 'analyze_asset']
