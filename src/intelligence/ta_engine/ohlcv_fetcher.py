"""
OHLCV Fetcher
=============
Fetches candlestick data from Binance and Bybit REST APIs (no auth required for historical klines).
Supports exchange detection from user's connected exchange keys.

Exchange → symbol convention:
  Binance: BTCUSDT  (quotes in USDT)
  Bybit:   BTCUSDT  (USDC/USDT unified)
"""

import asyncio
from typing import Optional
import pandas as pd
import httpx

# ---------------------------------------------------------------------------
# Timeframe maps
# ---------------------------------------------------------------------------

# Ticker → USDT pair symbol
SYMBOL_MAP: dict[str, str] = {
    # Majors
    'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT',
    'SOL': 'SOLUSDT', 'ADA': 'ADAUSDT', 'XRP': 'XRPUSDT',
    'AVAX': 'AVAXUSDT', 'DOT': 'DOTUSDT', 'MATIC': 'MATICUSDT',
    'LINK': 'LINKUSDT', 'UNI': 'UNIUSDT', 'AAVE': 'AAVEUSDT',
    # Memecoins
    'DOGE': 'DOGEUSDT', 'SHIB': 'SHIBUSDT', 'PEPE': 'PEPEUSDT',
    'FLOKI': 'FLOKIUSDT', 'BONK': 'BONKUSDT', 'WIF': 'WIFUSDT',
    # DeFi
    'CRV': 'CRVUSDT', 'GMX': 'GMXUSDT', 'JUP': 'JUPUSDT',
    'LDO': 'LDOUSDT', 'PENDLE': 'PENDLEUSDT', 'RUNE': 'RUNEUSDT',
    # Privacy
    'XMR': 'XMRUSDT', 'ZEC': 'ZECUSDT', 'SCRT': 'SCRTUSDT',
}

# Binance interval identifiers
BINANCE_INTERVALS = {'1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w'}

# Bybit interval → numeric map (v5 API uses minutes or 'D'/'W')
BYBIT_INTERVAL_MAP = {
    '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
    '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
    '1d': 'D', '1w': 'W',
}

# HTF → recommended LTF for entry confirmation
LTF_MAP = {
    '1d': '4h',
    '4h': '1h',
    '1h': '15m',
    '30m': '5m',
    '15m': '5m',
}

# Timeframe → StructureEngine lookback label
STRUCTURE_LABEL_MAP = {
    '1m': 'M1', '5m': 'M5', '15m': 'M15', '30m': 'M30',
    '1h': 'H1', '4h': 'H4', '1d': 'D1',
}

BINANCE_BASE = 'https://api.binance.com'
BYBIT_BASE = 'https://api.bybit.com'


def to_symbol(ticker: str, exchange: str = 'binance') -> str:
    """Convert short ticker (BTC) to exchange symbol (BTCUSDT)."""
    upper = ticker.upper()
    # Already has a quote currency
    if upper.endswith('USDT') or upper.endswith('USDC'):
        return upper
    mapped = SYMBOL_MAP.get(upper)
    if mapped:
        return mapped
    # Fallback: append USDT
    return upper + 'USDT'


def get_ltf(htf: str) -> str:
    """Return recommended lower timeframe for entry confirmation."""
    return LTF_MAP.get(htf, '15m')


def get_structure_label(interval: str) -> str:
    """Return the StructureEngine lookback label for an interval."""
    return STRUCTURE_LABEL_MAP.get(interval, interval)


async def fetch_binance_ohlcv(
    ticker: str,
    interval: str = '1h',
    limit: int = 300,
) -> pd.DataFrame:
    """
    Fetch OHLCV from Binance public klines endpoint (no auth required).
    Returns DataFrame with columns: open, high, low, close, volume (DatetimeIndex).
    """
    symbol = to_symbol(ticker, 'binance')
    url = f'{BINANCE_BASE}/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

    if not raw:
        raise ValueError(f'Binance returned empty klines for {symbol} {interval}')

    df = pd.DataFrame(raw, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    df.set_index('open_time', inplace=True)
    for col in ('open', 'high', 'low', 'close', 'volume'):
        df[col] = df[col].astype(float)
    return df[['open', 'high', 'low', 'close', 'volume']]


async def fetch_bybit_ohlcv(
    ticker: str,
    interval: str = '1h',
    limit: int = 300,
) -> pd.DataFrame:
    """
    Fetch OHLCV from Bybit v5 public klines endpoint (no auth required).
    Returns DataFrame with columns: open, high, low, close, volume (DatetimeIndex).
    """
    symbol = to_symbol(ticker, 'bybit')
    bybit_interval = BYBIT_INTERVAL_MAP.get(interval)
    if not bybit_interval:
        raise ValueError(f'Unsupported Bybit interval: {interval}. Use: {list(BYBIT_INTERVAL_MAP.keys())}')

    url = f'{BYBIT_BASE}/v5/market/kline'
    params = {
        'category': 'spot',
        'symbol': symbol,
        'interval': bybit_interval,
        'limit': min(limit, 1000),
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get('result', {}).get('list', [])
    if not rows:
        raise ValueError(f'Bybit returned empty klines for {symbol} {interval}')

    # Bybit returns newest first — reverse to oldest first
    rows = list(reversed(rows))

    df = pd.DataFrame(rows, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df['open_time'] = pd.to_datetime(df['open_time'].astype(float), unit='ms', utc=True)
    df.set_index('open_time', inplace=True)
    for col in ('open', 'high', 'low', 'close', 'volume'):
        df[col] = df[col].astype(float)
    return df[['open', 'high', 'low', 'close', 'volume']]


async def fetch_ohlcv(
    ticker: str,
    interval: str = '1h',
    exchange: str = 'binance',
    limit: int = 300,
) -> pd.DataFrame:
    """
    Universal OHLCV fetcher. Uses Binance public API by default.
    Falls back to Binance if exchange is unknown.
    """
    if exchange == 'bybit':
        try:
            return await fetch_bybit_ohlcv(ticker, interval, limit)
        except Exception:
            # Fallback to Binance public API if Bybit fails
            return await fetch_binance_ohlcv(ticker, interval, limit)
    else:
        return await fetch_binance_ohlcv(ticker, interval, limit)


def detect_user_exchange(user_id: int, db) -> str:
    """
    Detect which exchange the user has connected.
    Returns exchange name ('binance', 'bybit', 'okx') or 'binance' as default.
    Falls back to Binance public API if no exchange connected.
    """
    try:
        from api.models.user import ExchangeApiKey
        key = db.query(ExchangeApiKey).filter(
            ExchangeApiKey.user_id == user_id,
            ExchangeApiKey.is_active == True,
        ).first()
        if key:
            return key.exchange
    except Exception:
        pass
    return 'binance'
