"""
WhaleNormalizer — Layer 2

Consumes raw collector output and produces typed WhaleTransaction dataclasses.
Responsibilities:
  - Label from/to addresses using known_addresses.json + Redis cache + Etherscan name tags
  - Classify flow_type (exchange_deposit / exchange_withdrawal / otc_suspected / wallet_to_wallet)
  - Assign alert tier (MEGA / LARGE / STANDARD)
  - Write normalized transactions to Redis sorted set (key: 'whale:txns:{chain}', score = timestamp)
  - TTL: 24h per entry
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WhaleTransaction dataclass
# ---------------------------------------------------------------------------

@dataclass
class WhaleTransaction:
    id: str                         # '{CHAIN}:{tx_hash}'
    chain: str                      # 'ETH' | 'BTC' | 'SOL' | 'TRON' | 'PERP'
    asset: str                      # 'ETH' | 'BTC' | 'SOL' | 'USDT' | 'USDC'
    amount_native: float
    amount_usd: float
    from_address: str
    to_address: str
    from_label: Optional[str]
    to_label: Optional[str]
    from_category: Optional[str]    # 'cex' | 'dex' | 'fund' | 'whale' | 'miner' | 'legal'
    to_category: Optional[str]
    flow_type: str                  # 'exchange_deposit' | 'exchange_withdrawal' | 'otc_suspected' | 'wallet_to_wallet'
    is_otc_suspected: bool
    alert_tier: str                 # 'MEGA' | 'LARGE' | 'STANDARD'
    timestamp: datetime
    block_number: int
    tx_hash: str
    # Optional extra fields
    liquidation: bool = False
    aave_health_factor: Optional[float] = None
    pending: bool = False

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'chain': self.chain,
            'asset': self.asset,
            'amount_native': self.amount_native,
            'amount_usd': self.amount_usd,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'from_label': self.from_label,
            'to_label': self.to_label,
            'from_category': self.from_category,
            'to_category': self.to_category,
            'flow_type': self.flow_type,
            'is_otc_suspected': self.is_otc_suspected,
            'alert_tier': self.alert_tier,
            'timestamp': self.timestamp.isoformat(),
            'block_number': self.block_number,
            'tx_hash': self.tx_hash,
            'liquidation': self.liquidation,
            'aave_health_factor': self.aave_health_factor,
            'pending': self.pending,
        }


# ---------------------------------------------------------------------------
# Address label store (loaded from known_addresses.json)
# ---------------------------------------------------------------------------

class _AddressLabelStore:
    """
    In-memory flat lookup for known addresses.
    Structure: address (lowercased) → {'label': str, 'category': str}
    """

    def __init__(self):
        self._lookup: Dict[str, Dict[str, str]] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'known_addresses.json')
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            logger.warning('Could not load known_addresses.json: %s', e)
            self._loaded = True
            return

        # Build flat lookup from nested structure
        for chain, exchanges in data.items():
            if chain.startswith('_'):
                continue
            if not isinstance(exchanges, dict):
                continue
            for exchange_key, exchange_data in exchanges.items():
                if not isinstance(exchange_data, dict):
                    continue
                label = exchange_data.get('label', exchange_key)
                category = exchange_data.get('category', 'unknown')
                for wallet_type in ('hot_wallets', 'cold_wallets', 'wallets'):
                    for wallet in exchange_data.get(wallet_type, []):
                        addr = wallet.get('address', '').lower()
                        if addr:
                            note = wallet.get('note', label)
                            self._lookup[addr] = {
                                'label': note or label,
                                'category': category,
                            }

        # Also load flat_lookup if present
        if 'flat_lookup' in data:
            for addr, info in data['flat_lookup'].items():
                self._lookup[addr.lower()] = info

        logger.info('AddressLabelStore loaded %d addresses', len(self._lookup))
        self._loaded = True

    def get(self, address: str) -> Tuple[Optional[str], Optional[str]]:
        """Returns (label, category) or (None, None) if unknown."""
        if not address:
            return None, None
        info = self._lookup.get(address.lower())
        if info:
            return info.get('label'), info.get('category')
        return None, None


_label_store = _AddressLabelStore()


# ---------------------------------------------------------------------------
# WhaleNormalizer
# ---------------------------------------------------------------------------

class WhaleNormalizer:
    """
    Reads raw transaction dicts from WhaleCollector queue and emits
    WhaleTransaction objects to the output queue for WhaleAnalyzer.
    """

    # Alert tier thresholds (USD)
    TIER_MEGA     = 50_000_000
    TIER_LARGE    = 10_000_000
    TIER_STANDARD =  1_000_000

    # OTC threshold: wallet-to-wallet above this USD → flag as suspected OTC
    OTC_MIN_USD   = 10_000_000

    def __init__(
        self,
        input_queue: Optional[asyncio.Queue] = None,
        output_queue: Optional[asyncio.Queue] = None,
        redis_client=None,
    ):
        self._in_queue: asyncio.Queue = input_queue or asyncio.Queue()
        self._out_queue: asyncio.Queue = output_queue or asyncio.Queue(maxsize=10_000)
        self._redis = redis_client
        self._etherscan_key = os.getenv('ETHERSCAN_API_KEY', '')
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        _label_store.load()

    @property
    def output_queue(self) -> asyncio.Queue:
        return self._out_queue

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    # ------------------------------------------------------------------
    # Address label resolution (3-layer: memory → Redis → Etherscan)
    # ------------------------------------------------------------------

    async def _resolve_label(self, address: str, chain: str) -> Tuple[Optional[str], Optional[str]]:
        """Returns (label, category) for an address."""
        if not address:
            return None, None

        # Layer 1: in-memory known addresses
        label, category = _label_store.get(address)
        if label:
            return label, category

        # Layer 2: Redis label cache
        if self._redis:
            try:
                cached = await self._redis.get(f'whale:label:{address.lower()}')
                if cached:
                    info = json.loads(cached)
                    return info.get('label'), info.get('category')
            except Exception:
                pass

        # Layer 3: Etherscan name tag (ETH only)
        if chain == 'ETH' and self._etherscan_key:
            label, category = await self._fetch_etherscan_label(address)
            if label and self._redis:
                try:
                    await self._redis.setex(
                        f'whale:label:{address.lower()}',
                        7 * 86400,  # 7-day TTL
                        json.dumps({'label': label, 'category': category}),
                    )
                except Exception:
                    pass
            return label, category

        return None, None

    async def _fetch_etherscan_label(self, address: str) -> Tuple[Optional[str], Optional[str]]:
        """Query Etherscan for address name tag."""
        try:
            session = await self._get_session()
            async with session.get('https://api.etherscan.io/api', params={
                'module': 'account',
                'action': 'gettokeninfo',
                'contractaddress': address,
                'apikey': self._etherscan_key,
            }) as resp:
                data = await resp.json() if resp.status == 200 else None
            if data and data.get('status') == '1' and data.get('result'):
                name = data['result'].get('tokenName') or data['result'].get('contractName')
                if name:
                    return name, 'contract'
        except Exception:
            pass
        return None, None

    # ------------------------------------------------------------------
    # Flow type classification
    # ------------------------------------------------------------------

    def _classify_flow(
        self,
        from_category: Optional[str],
        to_category: Optional[str],
        amount_usd: float,
    ) -> Tuple[str, bool]:
        """Returns (flow_type, is_otc_suspected)."""
        if to_category == 'cex':
            return 'exchange_deposit', False
        if from_category == 'cex':
            return 'exchange_withdrawal', False
        if amount_usd >= self.OTC_MIN_USD and from_category != 'cex' and to_category != 'cex':
            return 'otc_suspected', True
        return 'wallet_to_wallet', False

    # ------------------------------------------------------------------
    # Alert tier assignment
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_tier(amount_usd: float) -> str:
        if amount_usd >= WhaleNormalizer.TIER_MEGA:
            return 'MEGA'
        if amount_usd >= WhaleNormalizer.TIER_LARGE:
            return 'LARGE'
        return 'STANDARD'

    # ------------------------------------------------------------------
    # Normalize a single raw transaction dict
    # ------------------------------------------------------------------

    async def normalize(self, raw: dict) -> Optional[WhaleTransaction]:
        """Convert a raw collector dict into a WhaleTransaction."""
        try:
            chain = raw.get('chain', 'ETH')
            tx_hash = raw.get('tx_hash', '')
            txn_id = f"{chain}:{tx_hash}" if tx_hash else f"{chain}:{int(time.time() * 1000)}"

            from_addr = raw.get('from_address', '')
            to_addr   = raw.get('to_address', '')

            from_label, from_category = await self._resolve_label(from_addr, chain)
            to_label,   to_category   = await self._resolve_label(to_addr,   chain)

            amount_usd = float(raw.get('amount_usd', 0))
            flow_type, is_otc = self._classify_flow(from_category, to_category, amount_usd)
            tier = self._assign_tier(amount_usd)

            ts_unix = raw.get('timestamp_unix', 0)
            timestamp = (
                datetime.fromtimestamp(ts_unix, tz=timezone.utc)
                if ts_unix
                else datetime.now(timezone.utc)
            )

            tx = WhaleTransaction(
                id=txn_id,
                chain=chain,
                asset=raw.get('asset', 'UNKNOWN'),
                amount_native=float(raw.get('amount_native', 0)),
                amount_usd=amount_usd,
                from_address=from_addr,
                to_address=to_addr,
                from_label=from_label or ('Unknown Wallet' if from_addr else None),
                to_label=to_label or ('Unknown Wallet' if to_addr else None),
                from_category=from_category,
                to_category=to_category,
                flow_type=flow_type,
                is_otc_suspected=is_otc,
                alert_tier=tier,
                timestamp=timestamp,
                block_number=int(raw.get('block_number', 0)),
                tx_hash=tx_hash,
                liquidation=bool(raw.get('liquidation', False)),
                aave_health_factor=raw.get('aave_health_factor'),
                pending=bool(raw.get('pending', False)),
            )

            return tx
        except Exception as e:
            logger.warning('Normalization error for raw tx: %s', e)
            return None

    # ------------------------------------------------------------------
    # Redis persistence
    # ------------------------------------------------------------------

    async def _persist(self, tx: WhaleTransaction) -> None:
        """Write transaction to Redis sorted set (score = unix timestamp)."""
        if not self._redis:
            return
        try:
            score = tx.timestamp.timestamp()
            key   = f'whale:txns:{tx.chain}'
            value = json.dumps(tx.to_dict())
            await self._redis.zadd(key, {value: score})
            # Trim to last 24h — keep entries from score > (now - 86400)
            cutoff = score - 86400
            await self._redis.zremrangebyscore(key, '-inf', cutoff)
        except Exception as e:
            logger.warning('Redis persist error: %s', e)

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Consume from input_queue, normalize, emit to output_queue."""
        self._running = True
        logger.info('WhaleNormalizer starting')
        try:
            while self._running:
                try:
                    raw = await asyncio.wait_for(self._in_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                tx = await self.normalize(raw)
                if tx is None:
                    continue

                await self._persist(tx)

                try:
                    self._out_queue.put_nowait(tx)
                except asyncio.QueueFull:
                    logger.warning('Normalizer output queue full, dropping %s', tx.id)

                self._in_queue.task_done()
        finally:
            self._running = False
            if self._session and not self._session.closed:
                await self._session.close()
            logger.info('WhaleNormalizer stopped')

    def stop(self) -> None:
        self._running = False
