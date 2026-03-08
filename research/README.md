# 🐋 Whale Analysis Feature

Real-time on-chain intelligence that tracks large capital movements across BTC, ETH, SOL, and TRON — translating raw blockchain data into actionable trading signals.

---

## What It Does

- **Tracks** large on-chain transactions (>500 ETH, >100 BTC, >10,000 SOL, >$5M stablecoins) in real time across 4 chains
- **Labels** wallets using a curated address database of 500+ known exchange hot/cold wallets and institutional addresses
- **Scores** whale sentiment per asset using a composite signal (exchange netflow + funding rate + OI trend + stablecoin ratio)
- **Detects** liquidation cascade risk before it hits, giving users advance warning
- **Flags** suspected order book spoofing events

---

## System Overview

```
Blockchain APIs / WebSockets
        │
        ▼
┌──────────────────┐
│  WhaleCollector  │  Layer 1 — pulls raw transactions from ETH, BTC, SOL, TRON, Hyperliquid
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ WhaleNormalizer  │  Layer 2 — unifies schema, labels addresses, classifies flow type
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  WhaleAnalyzer   │  Layer 3 — computes sentiment score, cascade risk, spoof detection
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│  API Routes + React Frontend │  Layer 4 — exposes via REST/WebSocket, renders UI components
└──────────────────────────────┘
```

---

## Directory Structure

```
src/
├── data/
│   ├── whale_collector.py        # Layer 1: multi-chain data collection
│   └── whale_normalizer.py       # Layer 2: schema normalization + address labeling
├── intelligence/
│   └── whale_analyzer.py         # Layer 3: signal computation
api/
└── routes/
    └── whale.py                  # REST + WebSocket endpoint handlers
web/src/components/whale/
├── WhaleAlertFeed.tsx            # Live transaction feed
├── WhaleSentimentBadge.tsx       # Per-asset sentiment indicator
├── CascadeWarningBanner.tsx      # Liquidation cascade alert banner
└── WhaleFlowMiniChart.tsx        # Hourly netflow chart (hover card)
data/
├── known_addresses.json          # Seed file: labeled exchange wallets
├── whale_thresholds.json         # Config: all thresholds and parameters
└── api_response_schemas.json     # Canonical API response contracts
```

---

## Quick Start (Local Development)

### 1. Install dependencies
```bash
pip install aiohttp websockets redis aioredis
```

### 2. Set environment variables
```bash
ETHERSCAN_API_KEY=your_key_here
INFURA_PROJECT_ID=your_project_id
SOLSCAN_API_KEY=your_key_here          # optional — public endpoints available
REDIS_URL=redis://localhost:6379
```

### 3. Run the collector
```bash
python -m src.data.whale_collector
```

### 4. Run the analyzer
```bash
python -m src.intelligence.whale_analyzer
```

### 5. Start the API
```bash
uvicorn api.main:app --reload
```

---

## Configuration

All tunable parameters live in `data/whale_thresholds.json`. Key settings:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `transaction_thresholds.ETH.native` | 500 | Minimum ETH to collect |
| `cascade_detection.signals_required` | 3 | Conditions needed to fire a cascade warning |
| `cascade_detection.confidence_min_to_surface` | 75 | Minimum confidence % before showing to users |
| `spoofing_detection.confidence_min_to_surface` | 70 | Minimum confidence for spoof alerts |
| `sentiment_weights.exchange_netflow` | 0.40 | Weight of exchange netflow in sentiment score |

---

## Address Labels

The `data/known_addresses.json` file is the heart of signal quality. It contains:

- **72 seed addresses** across ETH, BTC, SOL, and TRON
- Organized by exchange → hot/cold wallet
- A `flat_lookup` map for O(1) lookups in the normalizer

### Adding new addresses

1. Add to the relevant chain + exchange block in `known_addresses.json`
2. Regenerate the flat lookup:
   ```bash
   python scripts/build_address_lookup.py
   ```
3. The normalizer picks up changes on next restart (no deploy needed for label-only updates)

### Label quality tiers

| Tier | Source | Refresh |
|------|--------|---------|
| Static seed | Community lists + manual verification | Weekly manual review |
| Etherscan API | Auto-enrichment on unknown addresses | 7-day Redis TTL |
| Behavioral clustering | Pattern-based tagging (Phase 2) | Continuous background job |

---

## Tier Gates

| Feature | Tier Required |
|---------|--------------|
| `WhaleSentimentBadge` in sector rail | Premium |
| `WhaleFlowMiniChart` on hover | Premium |
| `/api/whale/sentiment/{asset}` | Premium |
| `WhaleAlertFeed` full feed | Premium+ |
| `CascadeWarningBanner` | Premium |
| `/ws/whale/alerts` WebSocket | Premium+ |
| `/api/whale/recent` | Premium+ |

---

## Sentiment Score

The composite sentiment score runs from **-1.0 (distributing)** to **+1.0 (accumulating)**:

| Score | Label | Color |
|-------|-------|-------|
| +0.6 → +1.0 | ACCUMULATING | 🟢 Green |
| +0.2 → +0.6 | MILD ACCUMULATION | 🟩 Light Green |
| -0.2 → +0.2 | NEUTRAL | ⬜ Gray |
| -0.6 → -0.2 | MILD DISTRIBUTION | 🟡 Amber |
| -1.0 → -0.6 | DISTRIBUTING | 🔴 Red |

**Signal weights:** Exchange Netflow 40% · Funding Rate 25% · OI Trend 20% · Stablecoin Ratio 15%

---

## Related Docs

- [`API_DOCS.md`](./API_DOCS.md) — Full endpoint reference
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — Deep technical design
- [`data/whale_thresholds.json`](../data/whale_thresholds.json) — All config parameters
- [`data/api_response_schemas.json`](../data/api_response_schemas.json) — Response contracts
