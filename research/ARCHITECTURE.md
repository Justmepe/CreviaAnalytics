# Whale Analysis — Architecture

Deep technical reference for the 4-layer whale tracking system.

---

## Layer 1 — Data Collection (`whale_collector.py`)

### Responsibilities

- Poll REST APIs and maintain WebSocket connections across 4 chains
- Apply threshold filters before writing to the queue (reduce downstream load)
- Handle rate limiting, retries, and connection drops gracefully
- Emit raw `dict` payloads to an internal async queue consumed by the normalizer

### Data Sources

| Source | Chain | Method | Cadence | Free Tier Limit |
|--------|-------|--------|---------|-----------------|
| Etherscan API | ETH | REST polling | 30s | 5 req/s |
| Infura / Alchemy | ETH | WebSocket `eth_subscribe` | Continuous | — |
| Blockstream.info | BTC | REST polling | 60s | 10 req/s |
| Solscan | SOL | REST polling | 30s | 5 req/s |
| Tron Grid | TRON | REST polling | 30s | 15 req/s |
| Hyperliquid | Perps | WebSocket (public) | Continuous | No auth required |
| Coinglass | Multi | REST (existing) | Existing cadence | Already integrated |
| Aave on-chain | ETH | REST read | 60s | — |

### Collector Interface

```python
class WhaleCollector:
    THRESHOLDS = {
        'BTC':  100,
        'ETH':  500,
        'SOL':  10_000,
        'USDT': 5_000_000,
        'USDC': 5_000_000,
        'USD':  1_000_000,   # fallback if price unavailable
    }

    async def poll_eth_large_transfers(self) -> List[dict]
    async def poll_btc_large_utxos(self) -> List[dict]
    async def poll_sol_large_transfers(self) -> List[dict]
    async def poll_tron_stablecoin_flows(self) -> List[dict]
    async def stream_hyperliquid_liquidations(self) -> AsyncGenerator[dict]
    async def watch_aave_health_factors(self) -> AsyncGenerator[dict]
    async def run(self) -> None  # main loop: starts all pollers + streams
```

### Rate Limit Strategy

All REST pollers use a shared `RateLimiter` that:
1. Respects per-source limits (configurable in `whale_thresholds.json`)
2. Implements exponential backoff on 429 responses (base: 2s, max: 60s)
3. Falls back to cached last-known result rather than failing loudly

### Mempool Watching (ETH)

The Infura WebSocket subscription `eth_subscribe newPendingTransactions` gives us ETH transfers _before_ they confirm. This is used to:
- Pre-label a transaction as "pending whale move" so the frontend can show "⏳ Pending" status
- Feed early signal into the sentiment score (unconfirmed but directional)

Pending transactions expire from the feed if not confirmed within 10 minutes.

---

## Layer 2 — Normalization (`whale_normalizer.py`)

### Responsibilities

- Consume raw collector output and produce typed `WhaleTransaction` dataclasses
- Label `from_address` and `to_address` using the address database
- Classify `flow_type` based on address categories
- Detect OTC-suspected movements
- Write normalized transactions to Redis (sorted set by timestamp, TTL 24h)

### WhaleTransaction Schema

```python
@dataclass
class WhaleTransaction:
    id: str                     # 'ETH:0xabc...'
    chain: str                  # 'ETH' | 'BTC' | 'SOL' | 'TRON'
    asset: str                  # 'ETH' | 'BTC' | 'SOL' | 'USDT' | 'USDC'
    amount_native: float
    amount_usd: float
    from_address: str
    to_address: str
    from_label: str | None
    to_label: str | None
    from_category: str | None   # 'cex' | 'dex' | 'fund' | 'whale' | 'miner' | 'legal'
    to_category: str | None
    flow_type: str              # 'exchange_deposit' | 'exchange_withdrawal' | 'otc_suspected' | 'wallet_to_wallet'
    is_otc_suspected: bool
    alert_tier: str             # 'MEGA' | 'LARGE' | 'STANDARD'
    timestamp: datetime
    block_number: int
    tx_hash: str
```

### Flow Type Classification Logic

```
if to_category == 'cex':
    flow_type = 'exchange_deposit'

elif from_category == 'cex':
    flow_type = 'exchange_withdrawal'

elif amount_usd >= 10_000_000 and from_category != 'cex' and to_category != 'cex':
    flow_type = 'otc_suspected'
    is_otc_suspected = True

else:
    flow_type = 'wallet_to_wallet'
```

### Address Label Resolution

```
1. Check flat_lookup in known_addresses.json (in-memory dict, O(1))
   → Hit: use stored label + category

2. Check Redis label cache (TTL 7 days)
   → Hit: use cached label

3. Query Etherscan name tag API (ETH only)
   → Hit: cache in Redis, use label
   → Miss: label = None, category = None → display as 'Unknown Wallet'

4. Background job: apply behavioral clustering tags (Phase 2)
```

### Alert Tier Assignment

```
amount_usd >= 50_000_000  → MEGA  (triggers WebSocket push)
amount_usd >= 10_000_000  → LARGE (highlighted feed row)
amount_usd >= 1_000_000   → STANDARD
```

---

## Layer 3 — Analysis (`whale_analyzer.py`)

### Responsibilities

- Aggregate normalized transactions into per-asset signals
- Compute composite `WhaleSentiment` score every 5 minutes (cached)
- Run `CascadeWarning` detection every 60 seconds (fast, in-memory)
- Run spoofing detection on order book snapshots (continuous)

### Composite Sentiment Score

The score is a weighted sum of 4 normalized sub-scores, each in [-1.0, +1.0]:

```python
score = (
    netflow_score    * 0.40 +   # exchange_netflow
    funding_score    * 0.25 +   # funding_rate alignment
    oi_score         * 0.20 +   # open_interest trend
    stablecoin_score * 0.15     # stablecoin ratio
)
```

#### Exchange Netflow Sub-Score

```
net_flow = total_withdrawal_usd - total_deposit_usd  (over window)

netflow_score = tanh(net_flow / normalizer)
  where normalizer = 30-day rolling average of |net_flow|

Positive net_flow (more withdrawals) → positive score → ACCUMULATING
Negative net_flow (more deposits) → negative score → DISTRIBUTING
```

#### Funding Rate Sub-Score

```
funding_score = -tanh(funding_rate / 0.01)
  (inverted: negative funding is bullish for longs = positive score)

Combine with netflow direction for squeeze detection:
  if funding_score > 0 and netflow_score < -0.5:
      label += ' + LONG SQUEEZE SETUP'
  if funding_score < 0 and netflow_score > 0.5:
      label += ' + SHORT SQUEEZE SETUP'
```

#### OI Trend Sub-Score

```
oi_change_pct = (current_oi - oi_4h_ago) / oi_4h_ago

oi_score = tanh(oi_change_pct / 0.05)
  Amplified when aligned with netflow direction:
  if sign(oi_score) == sign(netflow_score):
      oi_score *= 1.2  # cap at 1.0
```

#### Stablecoin Ratio Sub-Score

```
stablecoin_inflow = USDT + USDC net flow into exchanges (TRON + ETH)

stablecoin_score = tanh(stablecoin_inflow / 50_000_000)
  Positive = stables flowing IN (dry powder) = mild bullish
  Negative = stables flowing OUT (deployed or withdrawn) = mild bearish
```

### Cascade Risk Detection

Fires when `signals_met >= signals_required` (default 3 of 6):

```
Signal 1: OI percentile >= 90th (30-day lookback)             [weight: heavy]
Signal 2: Liq wall within 3% of current price (Coinglass)    [weight: heavy]
Signal 3: Deposit velocity > 2x 4h baseline                   [weight: medium]
Signal 4: Aave health factor < 1.25 for 3+ large positions   [weight: medium]
Signal 5: Funding rate > 0.05% (crowded longs at risk)        [weight: light]
Signal 6: Price rejected from resistance 2+ times in 4h       [weight: light]

risk_level:
  3 signals → LOW
  4 signals → MEDIUM
  5 signals → HIGH
  6 signals → CRITICAL

confidence = (signals_met / 6) * 100 + alignment_bonus
  alignment_bonus: up to +15 if all signals point same direction
```

### Spoofing Detection

Runs on 10-level order book snapshots from Binance, Coinbase, Bybit:

```
1. Record order at level L with size S at time T
2. At T + delta (delta <= 15s): if order at L is gone with no execution
3. Compute confidence:
   base = 0.50
   + 0.15 if same price level appeared/vanished > 2x in last 10 minutes
   + 0.20 if price moved against the spoof wall direction after vanish
   + 0.10 if vanish happened within 2s of a large trade on the other side
4. Surface if confidence >= 0.70
```

---

## Layer 4 — Frontend

### React Components

#### `WhaleAlertFeed.tsx`
- Polls `GET /api/whale/recent?limit=20` every 60 seconds
- Renders transactions as a scrollable feed, newest first
- Row colors: amber = deposit, green = withdrawal, purple = OTC, gray = wallet-to-wallet
- Clicking a row expands to show full tx details + block explorer link
- Shows a loading skeleton on initial mount, graceful error state if API fails

#### `WhaleSentimentBadge.tsx`
- Used in `SectorRail.tsx` header: `"DeFi +6.2% · 🐋 Accumulating"`
- Polls `GET /api/whale/sentiment/{asset}?window_hours=4` every 5 minutes
- Renders: score bar + label + confidence percentage
- Tooltip on hover shows the 4 component scores
- Gated behind Premium tier — shows blurred teaser to Basic users

#### `CascadeWarningBanner.tsx`
- Receives push via `WS /ws/whale/alerts` (Premium+) or polls `GET /api/whale/cascade-risk` every 60s (Premium)
- Pinned to top of dashboard
- Animation: pulse border for CRITICAL, static amber for LOW/MEDIUM
- Auto-dismisses after 2 hours; manual dismiss stored in component state
- CTA: "View Full Analysis" → opens `CascadeDetailModal.tsx`

#### `WhaleFlowMiniChart.tsx`
- Rendered inside asset hover cards
- Fetches `GET /api/whale/flow-chart/{asset}` on hover (lazy)
- 24-bar chart (1 bar = 1 hour): green bars = net outflow (bullish), red bars = net inflow (bearish)
- Summary line: "Net -$18.4M outflow over 24h — OUTFLOW bias"

### State Management

Whale data does not go into global app state. Each component manages its own polling via `useEffect` + `useState`. The WebSocket connection for cascade alerts is managed by a singleton `WhaleSocketService` class that components subscribe to.

---

## Data Flow Diagram

```
Etherscan ─────────┐
Blockstream ────────┤
Solscan ────────────┤──► WhaleCollector ──► async queue ──► WhaleNormalizer
Tron Grid ──────────┤                                              │
Hyperliquid WS ─────┘                                             ▼
                                                           Redis sorted set
Coinglass ──────────────────────────────────────────────►        │
Aave health ────────────────────────────────────────────►        │
                                                                  ▼
                                                          WhaleAnalyzer
                                                          ├── WhaleSentiment (5min cache)
                                                          ├── CascadeWarning (60s check)
                                                          └── SpoofAlert (continuous)
                                                                  │
                                                          API Route Handlers
                                                          ├── GET /api/whale/recent
                                                          ├── GET /api/whale/sentiment/{asset}
                                                          ├── GET /api/whale/cascade-risk
                                                          ├── GET /api/whale/flow-chart/{asset}
                                                          └── WS /ws/whale/alerts
                                                                  │
                                                          React Frontend
                                                          ├── WhaleAlertFeed
                                                          ├── WhaleSentimentBadge
                                                          ├── CascadeWarningBanner
                                                          └── WhaleFlowMiniChart
```

---

## Infrastructure Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Redis | >= 6.0 | For transaction cache, label cache, sentiment cache |
| Python | >= 3.11 | `asyncio`, `aiohttp`, `websockets` |
| API keys | Etherscan, Infura/Alchemy, Solscan | TRON Grid is keyless |
| Background workers | 2 async workers | Collector + Analyzer can share one process |
| WebSocket server | FastAPI with `websockets` | Standard uvicorn setup |

---

## Phase 2 Additions (Post-Launch)

- **Behavioral clustering** — tag wallets that consistently trade profitably as "smart money"
- **Cross-chain entity mapping** — link Binance ETH address to Binance BTC address as same entity
- **Deribit options whale tracking** — large options positions as directional signal
- **Historical playback** — let users replay whale activity during past major price moves
- **Arkham Intel API integration** — augment our label DB with their 800M+ address database (licensing cost TBD)
