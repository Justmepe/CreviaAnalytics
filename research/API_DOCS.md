# Whale Analysis — API Reference

All endpoints require authentication via `Authorization: Bearer <token>`. Responses are JSON. Errors follow standard HTTP status codes.

---

## Base URL

```
https://api.yourplatform.com
```

---

## Endpoints

### `GET /api/whale/recent`

Returns the most recent large on-chain whale transactions.

**Auth:** Premium+ tier

**Query Parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 20 | Number of transactions to return (max 100) |
| `chain` | string | `"all"` | Filter by chain: `ETH`, `BTC`, `SOL`, `TRON`, `all` |
| `asset` | string | — | Filter by asset symbol (e.g. `ETH`, `USDT`) |
| `flow_type` | string | `"all"` | Filter by `exchange_deposit`, `exchange_withdrawal`, `otc_suspected`, `wallet_to_wallet`, `all` |

**Example Request**
```
GET /api/whale/recent?limit=10&chain=ETH&flow_type=exchange_deposit
```

**Example Response**
```json
{
  "transactions": [
    {
      "id": "ETH:0xd3ad9f...",
      "chain": "ETH",
      "asset": "ETH",
      "amount_native": 1200.0,
      "amount_usd": 2976000.0,
      "from_address": "0x46340b...",
      "to_address": "0x3f5CE5...",
      "from_label": "Unknown Whale",
      "to_label": "Binance Hot Wallet 1",
      "from_category": "whale",
      "to_category": "cex",
      "flow_type": "exchange_deposit",
      "is_otc_suspected": false,
      "timestamp": "2026-03-08T11:22:00Z",
      "block_number": 21450210,
      "tx_hash": "0xd3ad9f...",
      "alert_tier": "LARGE"
    }
  ],
  "total_usd_moved": 14820000.0,
  "generated_at": "2026-03-08T11:30:00Z"
}
```

**Cache TTL:** 30 seconds  
**Target Response Time:** < 200ms

---

### `GET /api/whale/sentiment/{asset}`

Returns the composite whale sentiment score for a given asset.

**Auth:** Premium tier

**Path Parameters**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `asset` | string | ✅ | `BTC`, `ETH`, or `SOL` |

**Query Parameters**

| Param | Type | Default | Options |
|-------|------|---------|---------|
| `window_hours` | integer | 4 | `1`, `4`, `12`, `24` |

**Example Request**
```
GET /api/whale/sentiment/BTC?window_hours=4
```

**Example Response**
```json
{
  "asset": "BTC",
  "score": 0.72,
  "label": "ACCUMULATING",
  "confidence": 84,
  "key_signal": "Strong withdrawal trend from Binance — 12,400 BTC net outflow over 4h",
  "window_hours": 4,
  "components": {
    "exchange_netflow": {
      "raw_score": 0.81,
      "weight": 0.40,
      "weighted": 0.324,
      "detail": "Net -12,400 BTC from exchanges (withdrawals dominating)"
    },
    "funding_rate": {
      "raw_score": 0.65,
      "weight": 0.25,
      "weighted": 0.163,
      "detail": "Funding -0.02% — negative funding with withdrawals = squeeze setup"
    },
    "open_interest_trend": {
      "raw_score": 0.55,
      "weight": 0.20,
      "weighted": 0.110,
      "detail": "OI rising +8% while whales accumulating — leveraged conviction"
    },
    "stablecoin_ratio": {
      "raw_score": 0.30,
      "weight": 0.15,
      "weighted": 0.045,
      "detail": "$320M USDT flowing into exchanges — moderate dry powder building"
    }
  },
  "computed_at": "2026-03-08T11:30:00Z"
}
```

**Cache TTL:** 5 minutes  
**Target Response Time:** < 300ms

---

### `GET /api/whale/cascade-risk`

Returns active liquidation cascade warnings. Returns an empty `warnings` array if no risk is currently detected.

**Auth:** Premium tier

**Query Parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | `"all"` | `BTC`, `ETH`, `SOL`, or `all` |

**Example Request**
```
GET /api/whale/cascade-risk?asset=BTC
```

**Response — Active Warning**
```json
{
  "warnings": [
    {
      "asset": "BTC",
      "risk_level": "HIGH",
      "confidence": 82,
      "estimated_usd_at_risk": 38000000,
      "liq_wall_price": 76000.0,
      "current_price": 78250.0,
      "price_distance_pct": 2.88,
      "direction": "LONG_SQUEEZE",
      "key_signals": [
        "OI at 92nd percentile (30-day)",
        "Deposit velocity 2.4x 4h baseline",
        "4 Aave positions below HF 1.25",
        "Large bid wall cluster at $76,000 on Binance"
      ],
      "human_summary": "⚠ Liq wall at $76,000 — $38M at risk. Long squeeze likely if BTC loses $76k support.",
      "expires_at": "2026-03-08T13:30:00Z",
      "created_at": "2026-03-08T11:30:00Z"
    }
  ],
  "checked_at": "2026-03-08T11:30:00Z"
}
```

**Response — No Active Warning**
```json
{
  "warnings": [],
  "checked_at": "2026-03-08T11:30:00Z"
}
```

**Cache TTL:** 60 seconds  
**Target Response Time:** < 100ms (in-memory)

---

### `GET /api/whale/flow-chart/{asset}`

Returns hourly netflow data for the past 24 hours, used to power `WhaleFlowMiniChart.tsx`.

**Auth:** Premium tier

**Path Parameters**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `asset` | string | ✅ | `BTC`, `ETH`, or `SOL` |

**Example Request**
```
GET /api/whale/flow-chart/ETH
```

**Example Response**
```json
{
  "asset": "ETH",
  "data": [
    {
      "timestamp": "2026-03-07T12:00:00Z",
      "net_flow_usd": -4200000,
      "deposit_usd": 800000,
      "withdrawal_usd": 5000000,
      "transaction_count": 14
    },
    {
      "timestamp": "2026-03-07T13:00:00Z",
      "net_flow_usd": 1800000,
      "deposit_usd": 3100000,
      "withdrawal_usd": 1300000,
      "transaction_count": 9
    }
  ],
  "summary": {
    "net_24h_usd": -18400000,
    "bias": "OUTFLOW",
    "largest_single": 9200000
  }
}
```

> **Note on `net_flow_usd`:** Negative values mean net withdrawal (coins leaving exchanges) which is bullish. Positive values mean net deposit (coins entering exchanges) which is bearish sell pressure.

**Cache TTL:** 1 hour  
**Target Response Time:** < 400ms

---

## WebSocket

### `WS /ws/whale/alerts`

Real-time push connection for cascade warnings and MEGA-tier whale moves. Premium+ tier only.

**Auth:** Pass token as query param on connect:
```
wss://api.yourplatform.com/ws/whale/alerts?token=<bearer_token>
```

**Message Types**

All messages share the envelope:
```json
{
  "type": "cascade_warning | mega_whale | spoof_alert | heartbeat",
  "payload": { ... }
}
```

#### `cascade_warning`
Fired when a new cascade warning is detected or an existing one is upgraded in severity.
```json
{
  "type": "cascade_warning",
  "payload": { /* CascadeWarning object — see GET /api/whale/cascade-risk */ }
}
```

#### `mega_whale`
Fired for transactions > $50M USD.
```json
{
  "type": "mega_whale",
  "payload": { /* WhaleTransaction object — see GET /api/whale/recent */ }
}
```

#### `spoof_alert`
Fired when a high-confidence spoofing event is detected (confidence > 70%).
```json
{
  "type": "spoof_alert",
  "payload": {
    "asset": "ETH",
    "exchange": "binance",
    "side": "ask",
    "order_size_usd": 2400000,
    "price_level": 3180.0,
    "appeared_at": "2026-03-08T11:28:52Z",
    "vanished_at": "2026-03-08T11:29:00Z",
    "duration_seconds": 8,
    "confidence": 78,
    "interpretation": "Large ask wall at $3,180 appeared and vanished in 8s — possible sell wall spoofing"
  }
}
```

#### `heartbeat`
Sent every 30 seconds to keep the connection alive.
```json
{
  "type": "heartbeat",
  "payload": { "ts": "2026-03-08T11:30:00Z" }
}
```

**Reconnection:** Implement exponential backoff starting at 5 seconds. The HTTP polling endpoint `GET /api/whale/cascade-risk` serves as fallback if WebSocket is unavailable.

---

## Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 403 | `TIER_INSUFFICIENT` | Feature requires higher subscription tier |
| 404 | `ASSET_NOT_FOUND` | Unsupported asset symbol |
| 429 | `RATE_LIMITED` | Too many requests — back off and retry |
| 503 | `DATA_UNAVAILABLE` | Upstream data source temporarily unavailable |

**Error response shape:**
```json
{
  "error": {
    "code": "TIER_INSUFFICIENT",
    "message": "WhaleAlertFeed requires Premium+ subscription.",
    "upgrade_url": "https://yourplatform.com/pricing"
  }
}
```

---

## Rate Limits

| Tier | Requests/minute |
|------|----------------|
| Premium | 60 rpm |
| Premium+ | 300 rpm |

WebSocket connections count as 1 sustained request regardless of message volume.
