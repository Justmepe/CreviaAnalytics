"""
WhaleCollector — Layer 1

Polls blockchain APIs and WebSocket streams across ETH, BTC, SOL, TRON, and Hyperliquid.
Applies threshold filtering before emitting raw payloads to the async queue consumed by
WhaleNormalizer.

Sources:
  ETH   — Etherscan REST (30s) + Infura WebSocket (pending txns)
  BTC   — Blockstream.info REST (60s)
  SOL   — Solscan REST (30s)
  TRON  — Tron Grid REST (30s, stablecoin focus)
  Perps — Hyperliquid WebSocket (continuous)
  DeFi  — Aave health factor monitoring (60s)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (loaded from config; hardcoded defaults as fallback)
# ---------------------------------------------------------------------------

_THRESHOLDS: Dict[str, float] = {
    'BTC':  100,
    'ETH':  500,
    'SOL':  10_000,
    'USDT': 5_000_000,
    'USDC': 5_000_000,
    'USD':  1_000_000,
}

_RATE_LIMITS: Dict[str, float] = {
    'etherscan':   5,   # req/s (free tier)
    'blockstream': 10,
    'solscan':     5,
    'tron_grid':   15,
}


def _load_thresholds() -> None:
    """Override defaults with values from whale_thresholds.json if available."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'whale_thresholds.json')
    try:
        with open(config_path, encoding='utf-8') as f:
            cfg = json.load(f)
        for asset, vals in cfg.get('transaction_thresholds', {}).items():
            if isinstance(vals, dict) and 'native' in vals:
                _THRESHOLDS[asset] = vals['native']
        for source, rps in cfg.get('api_rate_limits', {}).items():
            key = source.replace('_free_rps', '').replace('_rps', '')
            if isinstance(rps, (int, float)):
                _RATE_LIMITS[key] = float(rps)
    except Exception as e:
        logger.warning('Could not load whale_thresholds.json, using defaults: %s', e)


_load_thresholds()


# ---------------------------------------------------------------------------
# Simple token-bucket rate limiter
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, rps: float):
        self._interval = 1.0 / max(rps, 0.1)
        self._last: float = 0.0

    async def acquire(self) -> None:
        now = time.monotonic()
        wait = self._interval - (now - self._last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()


# ---------------------------------------------------------------------------
# WhaleCollector
# ---------------------------------------------------------------------------

class WhaleCollector:
    """
    Collects large on-chain transactions across 4 chains and emits raw dicts
    to an asyncio.Queue for downstream processing by WhaleNormalizer.
    """

    THRESHOLDS = _THRESHOLDS

    def __init__(self, queue: Optional[asyncio.Queue] = None):
        self._queue: asyncio.Queue = queue or asyncio.Queue(maxsize=10_000)
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

        # Per-source rate limiters
        self._rl_eth   = _RateLimiter(_RATE_LIMITS.get('etherscan',   5))
        self._rl_btc   = _RateLimiter(_RATE_LIMITS.get('blockstream', 10))
        self._rl_sol   = _RateLimiter(_RATE_LIMITS.get('solscan',     5))
        self._rl_tron  = _RateLimiter(_RATE_LIMITS.get('tron_grid',   15))

        # API keys from environment
        self._etherscan_key  = os.getenv('ETHERSCAN_API_KEY', '')
        self._solscan_key    = os.getenv('SOLSCAN_API_KEY', '')
        self._infura_id      = os.getenv('INFURA_PROJECT_ID', '')

    @property
    def queue(self) -> asyncio.Queue:
        return self._queue

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={'User-Agent': 'CreviaAnalytics/1.0'},
            )
        return self._session

    async def _close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_json(self, url: str, params: Dict = None, retries: int = 3) -> Any:
        session = await self._get_session()
        backoff = 2.0
        for attempt in range(retries):
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                        continue
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                if attempt == retries - 1:
                    logger.warning('GET %s failed after %d attempts: %s', url, retries, e)
                    return None
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
        return None

    def _usd_value(self, asset: str, native_amount: float) -> float:
        """Best-effort USD estimation — real impl would call a price feed."""
        # Rough prices; the normalizer will enrich with live pricing
        prices = {'BTC': 80_000, 'ETH': 2_000, 'SOL': 100, 'USDT': 1, 'USDC': 1}
        return native_amount * prices.get(asset, 1)

    async def _emit(self, raw: dict) -> None:
        try:
            self._queue.put_nowait(raw)
        except asyncio.QueueFull:
            logger.warning('Collector queue full, dropping transaction %s', raw.get('tx_hash', '?'))

    # ------------------------------------------------------------------
    # Layer 1a — ETH large transfers (Etherscan)
    # ------------------------------------------------------------------

    def _load_eth_watch_addresses(self) -> List[str]:
        """
        Build a flat list of all ETH exchange wallet addresses from known_addresses.json.
        Falls back to the Binance hot wallet 1 if the file cannot be read.
        """
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'known_addresses.json'
        )
        try:
            with open(config_path) as f:
                data = json.load(f)
            addresses: List[str] = []
            for _exchange, info in data.get('ETH', {}).items():
                if not isinstance(info, dict):
                    continue
                for wallet in info.get('hot_wallets', []):
                    addr = wallet.get('address', '')
                    if addr:
                        addresses.append(addr)
                for wallet in info.get('cold_wallets', []):
                    addr = wallet.get('address', '')
                    if addr:
                        addresses.append(addr)
            if addresses:
                logger.debug('Loaded %d ETH watch addresses', len(addresses))
                return addresses
        except Exception as e:
            logger.warning('Could not load known_addresses.json: %s', e)
        return ['0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE']  # Binance Hot Wallet 1

    async def poll_eth_large_transfers(self) -> List[dict]:
        """
        Fetch latest ETH transactions above threshold from Etherscan.
        Polls every known exchange wallet from known_addresses.json so that
        both deposits (→ exchange) and withdrawals (← exchange) are captured.
        """
        if not self._etherscan_key:
            return []  # silently skip — key not configured

        addresses = self._load_eth_watch_addresses()
        threshold = self.THRESHOLDS.get('ETH', 500)
        results: List[dict] = []
        seen_hashes: set = set()

        for address in addresses:
            await self._rl_eth.acquire()
            # Etherscan API V2 (V1 deprecated 2025)
            data = await self._get_json('https://api.etherscan.io/v2/api', params={
                'chainid': 1,
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'sort': 'desc',
                'page': 1,
                'offset': 25,
                'apikey': self._etherscan_key,
            })

            if not data or data.get('status') != '1':
                continue

            for tx in (data.get('result') or []):
                try:
                    tx_hash = tx.get('hash', '')
                    if tx_hash in seen_hashes:
                        continue  # deduplicate txns seen via multiple watched addresses
                    seen_hashes.add(tx_hash)

                    value_eth = int(tx.get('value', 0)) / 1e18
                    if value_eth < threshold:
                        continue
                    raw = {
                        'source': 'etherscan',
                        'chain': 'ETH',
                        'asset': 'ETH',
                        'amount_native': value_eth,
                        'amount_usd': self._usd_value('ETH', value_eth),
                        'from_address': tx.get('from', ''),
                        'to_address': tx.get('to', ''),
                        'tx_hash': tx_hash,
                        'block_number': int(tx.get('blockNumber', 0)),
                        'timestamp_unix': int(tx.get('timeStamp', 0)),
                        'confirmed': True,
                        'pending': False,
                    }
                    results.append(raw)
                    await self._emit(raw)
                except Exception as e:
                    logger.debug('ETH tx parse error: %s', e)

        return results

    # ------------------------------------------------------------------
    # Layer 1b — BTC large UTXOs (Blockstream)
    # ------------------------------------------------------------------

    async def poll_btc_large_utxos(self) -> List[dict]:
        """Fetch recent BTC transactions and filter by size."""
        await self._rl_btc.acquire()

        # Blockstream mempool API for recent confirmed txns
        data = await self._get_json('https://blockstream.info/api/mempool/recent')
        results = []
        if not data:
            return results

        threshold = self.THRESHOLDS.get('BTC', 100)
        for tx in data[:50]:  # process top 50 recent mempool txns
            try:
                # Sum output values (in satoshis)
                total_sats = sum(
                    v.get('value', 0)
                    for v in tx.get('vout', [])
                    if not v.get('scriptpubkey_type') == 'op_return'
                )
                btc_amount = total_sats / 1e8
                if btc_amount < threshold:
                    continue
                # Extract primary recipient (largest output)
                vout = sorted(tx.get('vout', []), key=lambda x: x.get('value', 0), reverse=True)
                to_addr = vout[0].get('scriptpubkey_address', '') if vout else ''
                raw = {
                    'source': 'blockstream',
                    'chain': 'BTC',
                    'asset': 'BTC',
                    'amount_native': btc_amount,
                    'amount_usd': self._usd_value('BTC', btc_amount),
                    'from_address': '',  # BTC UTXO model — difficult to determine single sender
                    'to_address': to_addr,
                    'tx_hash': tx.get('txid', ''),
                    'block_number': tx.get('status', {}).get('block_height', 0) or 0,
                    'timestamp_unix': tx.get('status', {}).get('block_time', 0) or 0,
                    'confirmed': tx.get('status', {}).get('confirmed', False),
                    'pending': not tx.get('status', {}).get('confirmed', False),
                }
                results.append(raw)
                await self._emit(raw)
            except Exception as e:
                logger.debug('BTC tx parse error: %s', e)

        return results

    # ------------------------------------------------------------------
    # Layer 1c — SOL large transfers (Solscan)
    # ------------------------------------------------------------------

    def _load_sol_watch_addresses(self) -> List[str]:
        """
        Build a flat list of all SOL exchange wallet addresses from known_addresses.json.
        Falls back to Binance SOL hot wallet if the file cannot be read.
        """
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'known_addresses.json'
        )
        try:
            with open(config_path, encoding='utf-8') as f:
                data = json.load(f)
            addresses: List[str] = []
            for _exchange, info in data.get('SOL', {}).items():
                if not isinstance(info, dict):
                    continue
                for wallet in info.get('hot_wallets', []):
                    addr = wallet.get('address', '')
                    if addr:
                        addresses.append(addr)
                for wallet in info.get('cold_wallets', []):
                    addr = wallet.get('address', '')
                    if addr:
                        addresses.append(addr)
            if addresses:
                logger.debug('Loaded %d SOL watch addresses', len(addresses))
                return addresses
        except Exception as e:
            logger.warning('Could not load SOL known_addresses: %s', e)
        return ['9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM']  # Binance SOL hot wallet

    async def _solana_rpc(self, method: str, params: list) -> Any:
        """POST a single JSON-RPC call to the Solana public mainnet endpoint."""
        session = await self._get_session()
        try:
            async with session.post(
                'https://api.mainnet-beta.solana.com',
                json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params},
                headers={'Content-Type': 'application/json'},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get('result')
        except Exception as e:
            logger.warning('Solana RPC %s failed: %s', method, e)
            return None

    async def poll_sol_large_transfers(self) -> List[dict]:
        """
        Fetch large SOL transfers using the Solana public JSON-RPC.
        Solscan public-api endpoints are deprecated (404) and Pro V2 requires a paid plan.
        For each known exchange wallet:
          1. getSignaturesForAddress → recent confirmed signatures
          2. getTransaction → pre/post balances to compute SOL moved
        """
        addresses = self._load_sol_watch_addresses()
        threshold = self.THRESHOLDS.get('SOL', 10_000)
        results: List[dict] = []
        seen_sigs: set = set()

        for address in addresses:
            await self._rl_sol.acquire()

            # Step 1: get recent confirmed signatures for this exchange wallet
            sigs_result = await self._solana_rpc(
                'getSignaturesForAddress',
                [address, {'limit': 15, 'commitment': 'confirmed'}],
            )
            if not sigs_result:
                continue

            for sig_info in sigs_result:
                sig = sig_info.get('signature', '')
                if not sig or sig in seen_sigs:
                    continue
                seen_sigs.add(sig)

                await self._rl_sol.acquire()

                # Step 2: fetch full transaction to read pre/post balances
                tx_result = await self._solana_rpc(
                    'getTransaction',
                    [sig, {'encoding': 'json', 'maxSupportedTransactionVersion': 0,
                           'commitment': 'confirmed'}],
                )
                if not tx_result:
                    continue

                try:
                    meta = tx_result.get('meta') or {}
                    if meta.get('err'):
                        continue  # skip failed transactions

                    pre = meta.get('preBalances', [])
                    post = meta.get('postBalances', [])
                    account_keys = (
                        tx_result.get('transaction', {})
                        .get('message', {})
                        .get('accountKeys', [])
                    )

                    # Find this exchange address in the account key list
                    try:
                        idx = account_keys.index(address)
                    except ValueError:
                        idx = None

                    if idx is not None and idx < len(pre) and idx < len(post):
                        # Positive delta = SOL arrived at exchange (deposit)
                        # Negative delta = SOL left exchange (withdrawal)
                        delta_lamports = post[idx] - pre[idx]
                        sol_amount = abs(delta_lamports) / 1e9
                        if sol_amount < threshold:
                            continue

                        # Determine counterparty (the account with the opposing delta)
                        counterparty = ''
                        for i, key in enumerate(account_keys):
                            if i == idx or i >= len(pre) or i >= len(post):
                                continue
                            if abs(post[i] - pre[i]) > abs(delta_lamports) * 0.5:
                                counterparty = key
                                break

                        from_addr = counterparty if delta_lamports > 0 else address
                        to_addr   = address if delta_lamports > 0 else counterparty

                        raw = {
                            'source': 'solana_rpc',
                            'chain': 'SOL',
                            'asset': 'SOL',
                            'amount_native': sol_amount,
                            'amount_usd': self._usd_value('SOL', sol_amount),
                            'from_address': from_addr,
                            'to_address': to_addr,
                            'tx_hash': sig,
                            'block_number': tx_result.get('slot', 0),
                            'timestamp_unix': tx_result.get('blockTime', 0) or 0,
                            'confirmed': True,
                            'pending': False,
                        }
                        results.append(raw)
                        await self._emit(raw)

                except Exception as e:
                    logger.debug('SOL tx parse error for %s: %s', sig[:16], e)

        return results

    # ------------------------------------------------------------------
    # Layer 1d — TRON stablecoin flows (Tron Grid)
    # ------------------------------------------------------------------

    async def poll_tron_stablecoin_flows(self) -> List[dict]:
        """Fetch large USDT/USDC transfers on TRON via Tron Grid."""
        await self._rl_tron.acquire()

        # TRC20 token transfers (USDT on TRON: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t)
        usdt_contract = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
        data = await self._get_json(
            'https://api.trongrid.io/v1/contracts/{contract}/events'.format(contract=usdt_contract),
            params={'event_name': 'Transfer', 'limit': 50, 'order_by': 'block_timestamp,desc'},
        )

        results = []
        if not data or not data.get('data'):
            return results

        threshold = self.THRESHOLDS.get('USDT', 5_000_000)
        for event in data.get('data', []):
            try:
                result = event.get('result', {})
                value_raw = int(result.get('value', 0))
                usdt_amount = value_raw / 1e6  # USDT has 6 decimals on TRON
                if usdt_amount < threshold:
                    continue
                raw = {
                    'source': 'tron_grid',
                    'chain': 'TRON',
                    'asset': 'USDT',
                    'amount_native': usdt_amount,
                    'amount_usd': usdt_amount,
                    'from_address': result.get('from', ''),
                    'to_address': result.get('to', ''),
                    'tx_hash': event.get('transaction_id', ''),
                    'block_number': event.get('block_number', 0),
                    'timestamp_unix': event.get('block_timestamp', 0) // 1000,
                    'confirmed': True,
                    'pending': False,
                }
                results.append(raw)
                await self._emit(raw)
            except Exception as e:
                logger.debug('TRON tx parse error: %s', e)

        return results

    # ------------------------------------------------------------------
    # Layer 1e — Hyperliquid perp liquidations (WebSocket)
    # ------------------------------------------------------------------

    async def stream_hyperliquid_liquidations(self) -> AsyncGenerator[dict, None]:
        """
        Stream large perp trades from Hyperliquid WebSocket as liquidation proxies.

        Hyperliquid does not expose a dedicated 'liquidations' WS channel.
        Instead we subscribe to 'trades' for BTC/ETH/SOL and flag trades whose
        notional value exceeds the USD threshold — these are overwhelmingly
        liquidation-driven at whale size.  We also poll /info metaAndAssetCtxs
        every 30 s to detect sudden OI drops (mass liquidation events).
        """
        import websockets  # lazy import

        uri = 'wss://api.hyperliquid.xyz/ws'
        coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK']
        min_usd = self.THRESHOLDS.get('USD', 1_000_000)

        # Rough per-coin price map for notional calc; normalizer will enrich
        _prices = {'BTC': 80_000, 'ETH': 2_000, 'SOL': 100, 'AVAX': 20, 'LINK': 10}

        while self._running:
            try:
                async with websockets.connect(uri, ping_interval=30) as ws:
                    # Subscribe to trades for each major coin
                    for coin in coins:
                        await ws.send(json.dumps({
                            'method': 'subscribe',
                            'subscription': {'type': 'trades', 'coin': coin},
                        }))
                    logger.info('Hyperliquid WS connected — monitoring trades on %s', coins)

                    async for message in ws:
                        try:
                            data = json.loads(message)
                            if data.get('channel') != 'trades':
                                continue
                            for trade in (data.get('data') or []):
                                coin = trade.get('coin', 'UNKNOWN')
                                sz = float(trade.get('sz', 0))
                                px = float(trade.get('px', _prices.get(coin, 1)))
                                usd_val = sz * px
                                if usd_val < min_usd:
                                    continue
                                users = trade.get('users', ['', ''])
                                raw = {
                                    'source': 'hyperliquid_ws',
                                    'chain': 'PERP',
                                    'asset': coin,
                                    'amount_native': sz,
                                    'amount_usd': usd_val,
                                    'from_address': users[0] if users else '',
                                    'to_address': users[1] if len(users) > 1 else '',
                                    'tx_hash': trade.get('hash', ''),
                                    'block_number': 0,
                                    'timestamp_unix': trade.get('time', int(time.time() * 1000)) // 1000,
                                    'confirmed': True,
                                    'pending': False,
                                    'liquidation': True,  # large perp trade — likely liquidation-driven
                                    'direction': 'buy' if trade.get('side') == 'B' else 'sell',
                                }
                                await self._emit(raw)
                                yield raw
                        except Exception as e:
                            logger.debug('Hyperliquid message parse error: %s', e)
            except Exception as e:
                logger.warning('Hyperliquid WS disconnected: %s — reconnecting in 5s', e)
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Layer 1e-b — Infura multi-chain pending large transactions (WebSocket)
    # ------------------------------------------------------------------

    # Chains that support Infura WebSocket (eth_subscribe confirmed working)
    _INFURA_WS_CHAINS: List[Dict] = [
        {'chain': 'ETH',     'asset': 'ETH',  'threshold_key': 'ETH',
         'ws':   'wss://mainnet.infura.io/ws/v3/{id}',
         'http': 'https://mainnet.infura.io/v3/{id}'},
        {'chain': 'POLYGON', 'asset': 'MATIC', 'threshold_key': 'USD',
         'ws':   'wss://polygon-mainnet.infura.io/ws/v3/{id}',
         'http': 'https://polygon-mainnet.infura.io/v3/{id}'},
        {'chain': 'LINEA',   'asset': 'ETH',  'threshold_key': 'ETH',
         'ws':   'wss://linea-mainnet.infura.io/ws/v3/{id}',
         'http': 'https://linea-mainnet.infura.io/v3/{id}'},
    ]

    # Chains where Infura WS returns -32601 — use HTTP block polling instead
    _INFURA_POLL_CHAINS: List[Dict] = [
        {'chain': 'ARBITRUM', 'asset': 'ETH',  'threshold_key': 'ETH',
         'http': 'https://arbitrum-mainnet.infura.io/v3/{id}'},
        {'chain': 'AVALANCHE','asset': 'AVAX', 'threshold_key': 'USD',
         'http': 'https://avalanche-mainnet.infura.io/v3/{id}'},
    ]

    # Keep for backward compat — full list used in stream_infura_pending_eth
    @property
    def _INFURA_CHAINS(self) -> List[Dict]:
        return self._INFURA_WS_CHAINS

    async def _stream_infura_chain(self, chain_cfg: Dict) -> AsyncGenerator[dict, None]:
        """
        Subscribe to newBlockHeaders on one Infura chain, then fetch each block's
        transactions in full and filter by threshold.

        Uses newBlockHeaders instead of newPendingTransactions to avoid the
        high-volume pattern of fetching every pending tx before value filtering
        (which causes ~40% failure rate from dropped/replaced transactions).
        One block header event (~15s) → one eth_getBlockByNumber call with full txns.
        """
        import websockets  # lazy import

        chain     = chain_cfg['chain']
        asset     = chain_cfg['asset']
        ws_uri    = chain_cfg['ws'].format(id=self._infura_id)
        rpc       = chain_cfg['http'].format(id=self._infura_id)
        threshold = self.THRESHOLDS.get(chain_cfg['threshold_key'], 500)
        session   = await self._get_session()

        while self._running:
            try:
                async with websockets.connect(
                    ws_uri,
                    ping_interval=20,
                    ping_timeout=60,
                    close_timeout=10,
                ) as ws:
                    await ws.send(json.dumps({
                        'jsonrpc': '2.0', 'id': 1,
                        'method': 'eth_subscribe',
                        'params': ['newBlockHeaders'],
                    }))
                    resp = json.loads(await ws.recv())
                    logger.info('Infura %s block-header stream active (sub=%s)', chain, resp.get('result'))

                    async for message in ws:
                        try:
                            msg       = json.loads(message)
                            block_hex = msg.get('params', {}).get('result', {}).get('number')
                            if not block_hex:
                                continue

                            # Fetch full block with transactions (confirmed only)
                            async with session.post(rpc,
                                json={'jsonrpc': '2.0', 'id': 2,
                                      'method': 'eth_getBlockByNumber',
                                      'params': [block_hex, True]},
                            ) as r:
                                block_data = (await r.json()).get('result') or {}

                            block_num = int(block_hex, 16)
                            block_ts  = int(block_data.get('timestamp', '0x0'), 16)

                            for tx in block_data.get('transactions', []):
                                try:
                                    value_native = int(tx.get('value', '0x0'), 16) / 1e18
                                    if value_native < threshold:
                                        continue
                                    raw = {
                                        'source':          f'infura_block_{chain.lower()}',
                                        'chain':           chain,
                                        'asset':           asset,
                                        'amount_native':   value_native,
                                        'amount_usd':      self._usd_value(asset, value_native),
                                        'from_address':    tx.get('from', ''),
                                        'to_address':      tx.get('to', '') or '',
                                        'tx_hash':         tx.get('hash', ''),
                                        'block_number':    block_num,
                                        'timestamp_unix':  block_ts,
                                        'confirmed':       True,
                                        'pending':         False,
                                    }
                                    await self._emit(raw)
                                    yield raw
                                except Exception as e:
                                    logger.debug('Infura %s tx parse error: %s', chain, e)

                        except Exception as e:
                            logger.debug('Infura %s block parse error: %s', chain, e)

            except Exception as e:
                logger.warning('Infura %s WS disconnected: %s — reconnecting in 30s', chain, e)
                await asyncio.sleep(30)

    async def _poll_infura_chain_blocks(self, chain_cfg: Dict) -> None:
        """
        HTTP block polling for Infura chains that don't support eth_subscribe WS.
        Fetches the latest block every 15s and filters txns above threshold.
        Used for Arbitrum and Avalanche.
        """
        chain     = chain_cfg['chain']
        asset     = chain_cfg['asset']
        rpc       = chain_cfg['http'].format(id=self._infura_id)
        threshold = self.THRESHOLDS.get(chain_cfg['threshold_key'], 500)
        session   = await self._get_session()
        last_block: int = 0

        while self._running:
            try:
                # Get latest block number
                async with session.post(rpc,
                    json={'jsonrpc':'2.0','id':1,'method':'eth_blockNumber','params':[]}) as r:
                    data = await r.json()
                block_num = int(data.get('result', '0x0'), 16)

                if block_num <= last_block:
                    await asyncio.sleep(15)
                    continue

                # Fetch full block with transactions
                async with session.post(rpc,
                    json={'jsonrpc':'2.0','id':2,'method':'eth_getBlockByNumber',
                          'params':[hex(block_num), True]}) as r:
                    block_data = (await r.json()).get('result') or {}

                last_block = block_num
                txs = block_data.get('transactions', [])

                for tx in txs:
                    try:
                        value_native = int(tx.get('value', '0x0'), 16) / 1e18
                        if value_native < threshold:
                            continue
                        raw = {
                            'source': f'infura_block_{chain.lower()}',
                            'chain': chain,
                            'asset': asset,
                            'amount_native': value_native,
                            'amount_usd': self._usd_value(asset, value_native),
                            'from_address': tx.get('from', ''),
                            'to_address': tx.get('to', '') or '',
                            'tx_hash': tx.get('hash', ''),
                            'block_number': block_num,
                            'timestamp_unix': int(block_data.get('timestamp', '0x0'), 16),
                            'confirmed': True,
                            'pending': False,
                        }
                        await self._emit(raw)
                    except Exception as e:
                        logger.debug('Infura %s block tx parse error: %s', chain, e)

            except Exception as e:
                logger.warning('Infura %s block poll error: %s', chain, e)

            await asyncio.sleep(15)

    async def stream_infura_pending_eth(self) -> AsyncGenerator[dict, None]:
        """
        Multi-chain Infura monitoring:
        - WS pending tx stream: ETH mainnet, Polygon, Linea (eth_subscribe supported)
        - HTTP block polling:   Arbitrum, Avalanche (eth_subscribe not supported)
        Requires INFURA_PROJECT_ID in environment.
        """
        if not self._infura_id:
            logger.debug('Infura stream skipped — INFURA_PROJECT_ID not set')
            return

        tasks = [
            asyncio.create_task(self._run_infura_chain(cfg))
            for cfg in self._INFURA_WS_CHAINS
        ] + [
            asyncio.create_task(self._poll_infura_chain_blocks(cfg))
            for cfg in self._INFURA_POLL_CHAINS
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
        # This is a coroutine, not a true generator — yield nothing (emits via queue)
        return
        yield  # make Python treat this as an AsyncGenerator

    async def _run_infura_chain(self, chain_cfg: Dict) -> None:
        """Drain one Infura WS chain stream — emits directly to queue."""
        async for _ in self._stream_infura_chain(chain_cfg):
            pass

    # ------------------------------------------------------------------
    # Layer 1f — Aave health factor monitoring
    # ------------------------------------------------------------------

    async def watch_aave_health_factors(self) -> AsyncGenerator[dict, None]:
        """
        Poll Aave v3 subgraph for large positions with health factor < 1.25.
        These are potential cascade triggers.
        """
        url = 'https://api.thegraph.com/subgraphs/name/aave/protocol-v3'
        query = """
        {
          users(
            where: { healthFactor_lt: "1250000000000000000" }
            orderBy: totalBorrowsUSD
            orderDirection: desc
            first: 20
          ) {
            id
            healthFactor
            totalBorrowsUSD
            totalCollateralUSD
          }
        }
        """
        while self._running:
            try:
                session = await self._get_session()
                async with session.post(url, json={'query': query}) as resp:
                    data = await resp.json() if resp.status == 200 else None

                if data and data.get('data', {}).get('users'):
                    for user in data['data']['users']:
                        try:
                            borrows_usd = float(user.get('totalBorrowsUSD', 0))
                            if borrows_usd < 500_000:
                                continue
                            hf_raw = int(user.get('healthFactor', 0))
                            hf = hf_raw / 1e18
                            raw = {
                                'source': 'aave_health',
                                'chain': 'ETH',
                                'asset': 'USD',
                                'amount_native': borrows_usd,
                                'amount_usd': borrows_usd,
                                'from_address': user.get('id', ''),
                                'to_address': 'aave_protocol',
                                'tx_hash': '',
                                'block_number': 0,
                                'timestamp_unix': int(time.time()),
                                'confirmed': True,
                                'pending': False,
                                'aave_health_factor': hf,
                                'collateral_usd': float(user.get('totalCollateralUSD', 0)),
                            }
                            await self._emit(raw)
                            yield raw
                        except Exception as e:
                            logger.debug('Aave user parse error: %s', e)

            except Exception as e:
                logger.warning('Aave health factor fetch failed: %s', e)

            await asyncio.sleep(60)

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start all pollers and streams. Runs until stopped."""
        self._running = True
        logger.info('WhaleCollector starting')

        async def _poll_eth_loop():
            while self._running:
                try:
                    await self.poll_eth_large_transfers()
                except Exception as e:
                    logger.error('ETH poller error: %s', e)
                await asyncio.sleep(30)

        async def _poll_btc_loop():
            while self._running:
                try:
                    await self.poll_btc_large_utxos()
                except Exception as e:
                    logger.error('BTC poller error: %s', e)
                await asyncio.sleep(60)

        async def _poll_sol_loop():
            while self._running:
                try:
                    await self.poll_sol_large_transfers()
                except Exception as e:
                    logger.error('SOL poller error: %s', e)
                await asyncio.sleep(30)

        async def _poll_tron_loop():
            while self._running:
                try:
                    await self.poll_tron_stablecoin_flows()
                except Exception as e:
                    logger.error('TRON poller error: %s', e)
                await asyncio.sleep(30)

        async def _drain_hyperliquid():
            async for _ in self.stream_hyperliquid_liquidations():
                pass  # raw payloads already emitted to queue

        async def _drain_infura():
            async for _ in self.stream_infura_pending_eth():
                pass  # raw payloads already emitted to queue

        async def _drain_aave():
            async for _ in self.watch_aave_health_factors():
                pass

        tasks = [
            _poll_eth_loop(),
            _poll_btc_loop(),
            _poll_sol_loop(),
            _poll_tron_loop(),
            _drain_hyperliquid(),
            _drain_aave(),
        ]
        if self._infura_id:
            tasks.append(_drain_infura())

        try:
            await asyncio.gather(*tasks)
        finally:
            self._running = False
            await self._close()
            logger.info('WhaleCollector stopped')

    def stop(self) -> None:
        self._running = False
