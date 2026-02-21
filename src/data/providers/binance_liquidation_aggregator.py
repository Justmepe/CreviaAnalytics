"""
Binance Liquidation Aggregator - Real-time WebSocket Aggregation

Connects to Binance Futures WebSocket to aggregate liquidation events
in real-time. Provides rolling time window totals (1h, 4h, 12h, 24h).

100% FREE - No API key required (public WebSocket stream)

WebSocket URL: wss://fstream.binance.com/ws/<symbol>@forceOrder
"""

import json
import time
import threading
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
import websocket


class BinanceLiquidationAggregator:
    """
    Real-time liquidation aggregator using Binance Futures WebSocket

    Features:
    - Subscribes to multiple symbols simultaneously
    - Aggregates liquidations over rolling time windows
    - Thread-safe data access
    - Auto-reconnect on disconnection
    - 100% free (public WebSocket, no authentication)
    """

    WS_URL = "wss://fstream.binance.com/stream"

    # Symbol mappings
    SYMBOL_MAP = {
        'BTC': 'btcusdt',
        'ETH': 'ethusdt',
        'SOL': 'solusdt',
        'BNB': 'bnbusdt',
        'XRP': 'xrpusdt',
        'DOGE': 'dogeusdt',
        'SHIB': 'shibusdt',
        'PEPE': 'pepeusdt',
        'AVAX': 'avaxusdt',
        'LINK': 'linkusdt',
    }

    def __init__(self, symbols: List[str] = None):
        """
        Initialize liquidation aggregator

        Args:
            symbols: List of symbols to track (default: BTC, ETH, SOL, BNB)
        """
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'BNB']

        # Data storage: {symbol: deque of (timestamp, side, usd_value)}
        self.liquidations = {sym: deque(maxlen=10000) for sym in self.symbols}

        # Lock for thread-safe access
        self.lock = threading.Lock()

        # WebSocket connection
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.connected = False

        # Reconnection settings
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 60

    def start(self):
        """Start the WebSocket connection in background thread"""
        if self.running:
            return

        self.running = True
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

        # Wait for connection
        time.sleep(2)

    def stop(self):
        """Stop the WebSocket connection"""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ws_thread:
            self.ws_thread.join(timeout=5)

    def _get_binance_symbol(self, ticker: str) -> str:
        """Convert ticker to Binance symbol"""
        ticker = ticker.upper()
        return self.SYMBOL_MAP.get(ticker, f"{ticker.lower()}usdt")

    def _run_websocket(self):
        """Run WebSocket connection with auto-reconnect"""
        reconnect_delay = self.reconnect_delay

        while self.running:
            try:
                # Build subscription streams
                streams = [f"{self._get_binance_symbol(sym)}@forceOrder"
                          for sym in self.symbols]
                streams_param = "/".join(streams)
                ws_url = f"{self.WS_URL}?streams={streams_param}"

                # Create WebSocket connection
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )

                # Run forever (blocking)
                self.ws.run_forever()

                # If we get here, connection closed
                if self.running:
                    print(f"WebSocket disconnected, reconnecting in {reconnect_delay}s...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                if self.running:
                    print(f"WebSocket error: {e}, reconnecting in {reconnect_delay}s...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

    def _on_open(self, ws):
        """WebSocket opened"""
        self.connected = True
        print(f"✅ Liquidation aggregator connected (tracking {len(self.symbols)} symbols)")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket closed"""
        self.connected = False
        if self.running:
            print(f"⚠️  Liquidation aggregator disconnected")

    def _on_error(self, ws, error):
        """WebSocket error"""
        if self.running:
            print(f"WebSocket error: {error}")

    def _on_message(self, ws, message):
        """
        Process liquidation message

        Format:
        {
          "stream": "btcusdt@forceOrder",
          "data": {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
              "s": "BTCUSDT",
              "S": "SELL",    # SELL = long liq, BUY = short liq
              "q": "0.014",   # Quantity
              "p": "9910",    # Price
              "ap": "9910",   # Average price
              ...
            }
          }
        }
        """
        try:
            msg = json.loads(message)

            # Extract data
            data = msg.get('data', {})
            if data.get('e') != 'forceOrder':
                return

            order = data.get('o', {})

            # Extract relevant fields
            symbol_raw = order.get('s', '').upper()  # BTCUSDT
            side = order.get('S', '')  # SELL or BUY
            quantity = float(order.get('q', 0))
            price = float(order.get('ap', 0) or order.get('p', 0))
            timestamp = data.get('E', 0) / 1000  # Convert ms to seconds

            # Calculate USD value
            usd_value = quantity * price

            # Determine if long or short liquidation
            # SELL order = long position liquidated
            # BUY order = short position liquidated
            liq_side = 'long' if side == 'SELL' else 'short'

            # Find matching symbol
            symbol = None
            for sym in self.symbols:
                if self._get_binance_symbol(sym).upper() == symbol_raw:
                    symbol = sym
                    break

            if not symbol or usd_value <= 0:
                return

            # Store liquidation (thread-safe)
            with self.lock:
                self.liquidations[symbol].append((timestamp, liq_side, usd_value))

        except Exception as e:
            print(f"Error processing liquidation: {e}")

    def get_liquidations(self, ticker: str, hours: int = 24) -> Dict[str, float]:
        """
        Get aggregated liquidations for a symbol over time window

        Args:
            ticker: Symbol (e.g., 'BTC', 'ETH')
            hours: Time window (1, 4, 12, 24)

        Returns:
            Dict with long/short/total liquidations in USD
        """
        ticker = ticker.upper()

        if ticker not in self.symbols:
            return {
                'long': 0.0,
                'short': 0.0,
                'total': 0.0,
                'note': f'{ticker} not tracked by aggregator'
            }

        # Calculate cutoff time
        cutoff = time.time() - (hours * 3600)

        long_total = 0.0
        short_total = 0.0

        # Aggregate liquidations (thread-safe)
        with self.lock:
            for timestamp, side, usd_value in self.liquidations[ticker]:
                if timestamp >= cutoff:
                    if side == 'long':
                        long_total += usd_value
                    else:
                        short_total += usd_value

        return {
            'long': long_total,
            'short': short_total,
            'total': long_total + short_total,
            'note': f'Binance WebSocket ({hours}h aggregated)',
            'timestamp': int(time.time()),
            'connected': self.connected
        }

    def get_all_liquidations(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """
        Get liquidations for all tracked symbols

        Args:
            hours: Time window

        Returns:
            Dict mapping ticker to liquidation data
        """
        return {
            symbol: self.get_liquidations(symbol, hours)
            for symbol in self.symbols
        }

    def get_stats(self) -> Dict:
        """Get aggregator statistics"""
        with self.lock:
            total_events = sum(len(liq) for liq in self.liquidations.values())

            return {
                'connected': self.connected,
                'symbols_tracked': len(self.symbols),
                'total_events_stored': total_events,
                'events_per_symbol': {
                    sym: len(self.liquidations[sym])
                    for sym in self.symbols
                }
            }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    import sys

    # Fix Windows encoding
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 80)
    print("BINANCE LIQUIDATION AGGREGATOR TEST")
    print("=" * 80)
    print()

    # Initialize aggregator
    print("Initializing aggregator for BTC, ETH, SOL, BNB...")
    aggregator = BinanceLiquidationAggregator(['BTC', 'ETH', 'SOL', 'BNB'])

    print("Starting WebSocket connection...")
    aggregator.start()

    print("Waiting 30 seconds to collect liquidation data...")
    print("(Market must have active liquidations to see data)")
    print()

    # Wait and periodically check
    for i in range(6):
        time.sleep(5)
        stats = aggregator.get_stats()
        print(f"[{i*5+5}s] Events collected: {stats['total_events_stored']} | Connected: {stats['connected']}")

    print()
    print("=" * 80)
    print("LIQUIDATION SUMMARY (Last 1 hour)")
    print("=" * 80)

    for symbol in ['BTC', 'ETH', 'SOL', 'BNB']:
        liq = aggregator.get_liquidations(symbol, hours=1)
        print(f"\n{symbol}:")
        print(f"  Long Liquidations:  ${liq['long']:,.2f}")
        print(f"  Short Liquidations: ${liq['short']:,.2f}")
        print(f"  Total:              ${liq['total']:,.2f}")
        if liq['total'] > 0:
            long_pct = (liq['long'] / liq['total'] * 100)
            short_pct = (liq['short'] / liq['total'] * 100)
            print(f"  Breakdown: {long_pct:.1f}% Long / {short_pct:.1f}% Short")

    print()
    print("Stopping aggregator...")
    aggregator.stop()

    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    print()
    print("NOTE: If you see $0.00 for all symbols, it means:")
    print("  1. No liquidations occurred in the test period (low volatility)")
    print("  2. OR WebSocket connection issue")
    print()
    print("Run main.py to use the aggregator in production.")
