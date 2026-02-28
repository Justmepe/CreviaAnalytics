
Track 3 — Whale Analysis (New Feature)
This is the biggest new build. It's a 4-layer system.

Layer 1: Data Collection
Sources and what to pull:

Source	Data	Method
Etherscan	ETH large transfers (>500 ETH), known exchange wallet flows	REST API polling (free tier: 5 req/s)
Infura / Alchemy	ETH mempool watching, block confirmations	WebSocket eth_subscribe newPendingTransactions
Bitcoin blockchain	BTC large UTXOs moving (>100 BTC), known exchange labels	Blockstream.info API (free) or Blockcypher
Solscan	SOL large transfers (>10k SOL)	REST API
Coinglass	Exchange netflow data (already integrated)	Already in DataAggregator
Hyperliquid WS	Real-time liquidations + large trades	WebSocket (public, no auth)
New file: src/data/whale_collector.py


class WhaleCollector:
    """Collects large on-chain transactions from multiple chains"""
    
    THRESHOLDS = {
        'BTC': 100,      # BTC
        'ETH': 500,      # ETH
        'SOL': 10000,    # SOL
        'USD': 1_000_000 # $1M+ always qualifies
    }
    
    async def poll_eth_large_transfers(self) -> List[WhaleTransaction]
    async def poll_btc_large_utxos(self) -> List[WhaleTransaction]
    async def poll_sol_large_transfers(self) -> List[WhaleTransaction]
    async def stream_hyperliquid_liquidations(self) -> AsyncGenerator[LiquidationEvent]
Layer 2: Normalization
New file: src/data/whale_normalizer.py

Every transaction from every chain gets normalized into one schema:


@dataclass
class WhaleTransaction:
    id: str                    # chain:txhash
    chain: str                 # 'ETH' | 'BTC' | 'SOL'
    asset: str                 # 'ETH' | 'BTC' | 'SOL'
    amount_native: float       # raw units
    amount_usd: float          # USD value at time of tx
    from_address: str
    to_address: str
    from_label: str | None     # 'Binance Hot Wallet', 'Unknown', etc.
    to_label: str | None
    flow_type: str             # 'exchange_deposit' | 'exchange_withdrawal' | 'wallet_to_wallet'
    timestamp: datetime
    block_number: int
    tx_hash: str
Address labeling (the secret sauce):

Maintain a JSON file data/known_addresses.json with labeled exchange hot/cold wallets
Etherscan provides labels via their API (limited, but useful for major exchanges)
Augment with community lists from Dune Analytics exports
Layer 3: Analysis & Signals
New file: src/intelligence/whale_analyzer.py


class WhaleAnalyzer:
    """Converts normalized whale transactions into actionable signals"""
    
    def compute_whale_sentiment(self, asset: str, window_hours: int = 4) -> WhaleSentiment:
        """
        Composite sentiment score per asset.
        
        Components:
        - Exchange netflow direction (40%): deposits = sell pressure, withdrawals = accumulation
        - Funding rate alignment (25%): negative funding + withdrawals = squeeze setup
        - OI trend (20%): rising OI + whale accumulation = leveraged conviction  
        - Stablecoin ratio (15%): stables flowing in = dry powder / coiled spring
        
        Returns:
        - score: -1.0 (distribution) to +1.0 (accumulation)
        - label: 'ACCUMULATING' | 'DISTRIBUTING' | 'NEUTRAL'
        - confidence: 0-100%
        - key_signal: human-readable top reason
        """
    
    def detect_cascade_risk(self) -> CascadeWarning | None:
        """
        Detect liquidation cascade conditions:
        - Large health factors dropping on Aave/Compound
        - OI + price divergence
        - Liq wall at next level
        Returns warning with estimated $ at risk
        """
    
    def detect_spoofing(self, asset: str) -> SpoofAlert | None:
        """
        Large buy/sell wall on orderbook that vanished in < 15 seconds
        """
Layer 4: Frontend Integration
New components to build:

WhaleAlertFeed.tsx — live polling (60s) from /api/whale/recent?limit=20

Each row: flow type icon, 500 ETH → Binance, $1.2M, 2m ago
Color: amber = deposit, green = withdrawal
WhaleSentimentBadge.tsx — per-sector sentiment

Used in SectorRail.tsx header: "DeFi +6.2% · 🐋 Accumulating"
Mini score bar
CascadeWarningBanner.tsx — appears when cascade risk detected

"⚠ Liq wall at $76k — $38M at risk. Shorts may get squeezed."
New API routes needed:

GET /api/whale/recent — last N transactions
GET /api/whale/sentiment/{asset} — per-asset whale sentiment
GET /api/whale/cascade-risk — current cascade warning if any
Track 4 — Pricing Tier Update
New structure:

Basic         $20/mo   — 3-day trial  — live analysis, daily scans, email alerts
Premium      $100/mo   — 7-day trial  — + trade setups, opportunity scanner, whale feed
Premium+     $200/mo   — 14-day trial — + API access, portfolio sync, Quant-grade data
Pages to update:

web/src/app/pricing/page.tsx — full redesign (convert from HTML example)
api/models/user.py — update tier enum if needed
web/src/components/auth/ProGate.tsx — update tier gate copy