"""
BinanceWSClient
===============
Live Binance kline (candlestick) stream via WebSocket.

- Subscribes to one or more symbols on a single connection
- Updates an in-memory OHLCV cache on each closed bar
- Exposes get_df(symbol, interval) for any consumer (TA engine, chart generator)
- Auto-reconnects on disconnect

Usage:
    from src.intelligence.ta_engine.binance_ws import BinanceWSClient

    client = BinanceWSClient(['BTC', 'ETH', 'SOL'], interval='4h')
    await client.start()                    # background task — non-blocking
    df = client.get_df('BTC', '4h')        # always returns latest cached DataFrame
    await client.stop()

Symbol convention:  ticker 'BTC' → Binance stream 'btcusdt@kline_4h'
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

_WS_BASE   = 'wss://stream.binance.com:9443/stream'
_MAX_BARS  = 500      # bars kept per symbol per interval
_RECONNECT_DELAY = 5  # seconds between reconnect attempts


def _ticker_to_stream(ticker: str, interval: str) -> str:
    symbol = ticker.upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    return f'{symbol.lower()}@kline_{interval}'


def _kline_to_row(k: dict) -> Tuple:
    """Extract OHLCV row from Binance kline payload."""
    return (
        pd.Timestamp(k['t'], unit='ms', tz='UTC'),  # open_time
        float(k['o']),  # open
        float(k['h']),  # high
        float(k['l']),  # low
        float(k['c']),  # close
        float(k['v']),  # volume
    )


class BinanceWSClient:
    """
    Maintains a live OHLCV cache for a list of tickers.
    Starts a background asyncio task that keeps the WebSocket open.
    """

    def __init__(
        self,
        tickers: List[str],
        interval: str = '4h',
        seed_limit: int = 300,
    ):
        self.tickers   = [t.upper() for t in tickers]
        self.interval  = interval
        self.seed_limit = seed_limit

        # Cache: key = (TICKER, interval), value = deque of [ts, o, h, l, c, v] rows
        self._cache: Dict[Tuple[str, str], deque] = {}
        self._running  = False
        self._task: Optional[asyncio.Task] = None
        self._streams  = [_ticker_to_stream(t, interval) for t in tickers]

    # ── Public ────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Seed cache from REST then launch WS background task."""
        await self._seed_all()
        self._running = True
        self._task = asyncio.create_task(self._run_forever(), name='binance-ws')
        logger.info(f"[BinanceWS] Started: {self.tickers} @ {self.interval}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[BinanceWS] Stopped")

    def get_df(self, ticker: str, interval: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Return the cached OHLCV DataFrame for a ticker. None if not yet seeded."""
        key = (ticker.upper(), interval or self.interval)
        rows = self._cache.get(key)
        if not rows:
            return None
        df = pd.DataFrame(list(rows), columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
        df.set_index('open_time', inplace=True)
        return df

    def is_ready(self, ticker: str) -> bool:
        key = (ticker.upper(), self.interval)
        return bool(self._cache.get(key))

    # ── Seeding ───────────────────────────────────────────────────────────────

    async def _seed_all(self) -> None:
        """Pre-fill cache from Binance REST so we have history before WS starts."""
        from src.intelligence.ta_engine.ohlcv_fetcher import fetch_binance_ohlcv
        tasks = [self._seed_one(t) for t in self.tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for ticker, result in zip(self.tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"[BinanceWS] Seed failed for {ticker}: {result}")

    async def _seed_one(self, ticker: str) -> None:
        from src.intelligence.ta_engine.ohlcv_fetcher import fetch_binance_ohlcv
        df = await fetch_binance_ohlcv(ticker, self.interval, limit=self.seed_limit)
        key = (ticker, self.interval)
        q: deque = deque(maxlen=_MAX_BARS)
        for ts, row in df.iterrows():
            q.append((ts, row['open'], row['high'], row['low'], row['close'], row['volume']))
        self._cache[key] = q
        logger.debug(f"[BinanceWS] Seeded {ticker}: {len(q)} bars")

    # ── WebSocket loop ────────────────────────────────────────────────────────

    async def _run_forever(self) -> None:
        while self._running:
            try:
                await self._connect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[BinanceWS] Connection error: {e}. Reconnecting in {_RECONNECT_DELAY}s...")
                await asyncio.sleep(_RECONNECT_DELAY)

    async def _connect(self) -> None:
        import websockets

        streams_param = '/'.join(self._streams)
        url = f'{_WS_BASE}?streams={streams_param}'
        logger.info(f"[BinanceWS] Connecting: {url[:80]}...")

        async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
            logger.info("[BinanceWS] Connected")
            async for raw in ws:
                if not self._running:
                    break
                try:
                    msg = json.loads(raw)
                    self._handle_message(msg)
                except Exception as e:
                    logger.debug(f"[BinanceWS] Message parse error: {e}")

    def _handle_message(self, msg: dict) -> None:
        """Process a single kline message from the combined stream."""
        data = msg.get('data', msg)
        if data.get('e') != 'kline':
            return

        k = data['k']
        is_closed = k.get('x', False)  # True when bar is closed
        symbol = k.get('s', '').upper()  # e.g. 'BTCUSDT'

        # Derive ticker from symbol
        ticker = symbol.replace('USDT', '').replace('USDC', '')
        key = (ticker, self.interval)

        if key not in self._cache:
            self._cache[key] = deque(maxlen=_MAX_BARS)

        row = _kline_to_row(k)

        if is_closed:
            # Closed bar → append as confirmed history
            self._cache[key].append(row)
            logger.debug(f"[BinanceWS] {ticker} bar closed: {row[0]} close={row[4]:.4f}")
        else:
            # Live (in-progress) bar → update the last entry
            q = self._cache[key]
            if q and q[-1][0] == row[0]:
                # Replace existing in-progress bar
                lst = list(q)
                lst[-1] = row
                self._cache[key] = deque(lst, maxlen=_MAX_BARS)
            else:
                # First tick of a new bar — append
                q.append(row)


# ── Module-level singleton ────────────────────────────────────────────────────
# main.py can import and use this singleton directly.

_DEFAULT_TICKERS = [
    'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'AVAX', 'SUI', 'LINK',
    'DOGE', 'SHIB', 'PEPE',
    'AAVE', 'UNI', 'CRV', 'LDO',
]

_ws_client: Optional[BinanceWSClient] = None


def get_ws_client(
    tickers: Optional[List[str]] = None,
    interval: str = '4h',
) -> BinanceWSClient:
    """Return (or create) the module-level singleton WS client."""
    global _ws_client
    if _ws_client is None:
        _ws_client = BinanceWSClient(
            tickers=tickers or _DEFAULT_TICKERS,
            interval=interval,
        )
    return _ws_client
