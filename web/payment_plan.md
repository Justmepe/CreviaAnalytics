# Crevia Cockpit — Payment System Implementation Plan

## Overview

Three payment pathways, implemented in priority order:

| Priority | Pathway | Audience | Effort |
|----------|---------|----------|--------|
| 1 | NexaPay Gateway (card → USDC) | Broadest reach — cards | High |
| 2 | MetaMask Direct (USDC on Base) | Crypto-native users | Medium |
| 3 | Fiat Bridge (Transak/MoonPay) | Fiat on-ramp fallback | Low |

**Settlement:** All pathways settle as USDC on Base L2.
**Subscription model:** Monthly recurring. No Stripe. Crypto-native.

---

## Tier Pricing

| Tier | DB Value | Monthly | Trial |
|------|----------|---------|-------|
| Basic (Observer) | `basic` | $20 USDC | 3 days |
| Premium (Pilot) | `pro` | $100 USDC | 7 days |
| Premium+ (Command) | `enterprise` | $200 USDC | 14 days |

USDC on Base: `parseUnits("20", 6)` / `parseUnits("100", 6)` / `parseUnits("200", 6)`

---

## Architecture

```
User clicks "Subscribe"
       │
       ├── MetaMask available? ──► Wagmi v2 + ConnectKit → USDC transfer on Base
       │                           └── Frontend polls /api/payments/status/{id}
       │
       ├── Card (NexaPay) ──────► POST /api/payments/nexapay/create
       │                           └── Redirect to NexaPay hosted page
       │                           └── NexaPay webhook → /api/payments/nexapay/webhook
       │
       └── Fiat Bridge ─────────► Redirect to Transak/MoonPay widget URL
                                   └── Manual verification or webhook
```

---

## Phase 1 — Database Models

### New File: `api/models/payment.py`

```python
class PaymentIntent(Base):
    __tablename__ = 'payment_intents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tier = Column(String(20), nullable=False)          # basic / pro / enterprise
    amount_usd = Column(Integer, nullable=False)        # cents: 2000 / 10000 / 20000
    pathway = Column(String(20), nullable=False)        # metamask / nexapay / fiat_bridge

    # Crypto correlation
    receive_address = Column(String(42))               # Our wallet address to receive USDC
    expected_amount = Column(String(30))               # USDC raw units (parseUnits result)
    sender_address = Column(String(42))                # User's wallet (provided at intent creation)

    # Settlement
    tx_hash = Column(String(66), unique=True)          # UNIQUE — idempotent settlement
    block_number = Column(Integer)

    # Status machine
    status = Column(String(20), default='pending')     # pending / paid / expired / failed
    expires_at = Column(DateTime(timezone=True))       # now() + 15 minutes (crypto) or 1 hour (card)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # NexaPay reference
    nexapay_order_id = Column(String(100))
    nexapay_status = Column(String(50))

class SubscriptionRecord(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    tier = Column(String(20), nullable=False)
    payment_pathway = Column(String(20))               # how they paid
    tx_hash = Column(String(66))                       # settlement tx
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))  # +30 days from paid_at
    auto_renew = Column(Boolean, default=False)        # manual renewal for now
    status = Column(String(20), default='active')      # active / canceled / expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Migration: `api/models/user.py`
Remove Stripe-specific fields (stripe_customer_id), add:
```python
wallet_address = Column(String(42))   # User's preferred USDC receive wallet (optional)
```

### `api/database.py`
Add `from api.models import payment` to `create_tables()`.

---

## Phase 2 — Backend Service

### New File: `api/services/payment_service.py`

**Core functions:**

```python
TIER_AMOUNTS = {
    'basic':      {'usd_cents': 2000,  'usdc_units': '20000000'},    # $20, 6 decimals
    'pro':        {'usd_cents': 10000, 'usdc_units': '100000000'},   # $100
    'enterprise': {'usd_cents': 20000, 'usdc_units': '200000000'},   # $200
}

USDC_CONTRACT_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
RECEIVE_WALLET = os.getenv('PAYMENT_RECEIVE_WALLET')  # Our treasury wallet on Base

async def create_payment_intent(user_id, tier, pathway, sender_address=None):
    """Creates a 15-min TTL payment intent."""
    ...

async def verify_usdc_transfer(tx_hash: str, intent_id: int):
    """
    Verify a USDC transfer on Base using Viem-equivalent logic.
    Uses parseEventLogs for Transfer events — transaction.value is always 0n for ERC-20.
    Checks: correct USDC contract, to=RECEIVE_WALLET, from=intent.sender_address, amount matches.
    """
    ...

async def activate_subscription(user_id, tier, tx_hash, pathway):
    """
    Sets user.tier, creates SubscriptionRecord, sets current_period_end = now + 30 days.
    Idempotent: checks tx_hash uniqueness before processing.
    """
    ...

async def check_expired_intents():
    """Cron: mark pending intents expired after TTL. Run every 5 minutes."""
    ...
```

**USDC Transfer Verification (Base L2):**

Uses `web3.py` (Python equivalent of Viem `parseEventLogs`):

```python
# pip install web3
from web3 import Web3

TRANSFER_ABI = [{
    "name": "Transfer",
    "type": "event",
    "inputs": [
        {"name": "from", "type": "address", "indexed": True},
        {"name": "to", "type": "address", "indexed": True},
        {"name": "value", "type": "uint256", "indexed": False},
    ]
}]

async def verify_usdc_transfer(tx_hash, intent):
    w3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL')))  # Base mainnet RPC
    receipt = w3.eth.get_transaction_receipt(tx_hash)

    contract = w3.eth.contract(address=USDC_CONTRACT_BASE, abi=TRANSFER_ABI)
    logs = contract.events.Transfer().process_receipt(receipt)

    for log in logs:
        if (log['args']['to'].lower() == RECEIVE_WALLET.lower() and
            log['args']['from'].lower() == intent.sender_address.lower() and
            log['args']['value'] >= int(intent.expected_amount)):
            return True  # Valid payment
    return False
```

---

## Phase 3 — Payment Router

### New File: `api/routers/payments.py`

**Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/payments/intent` | JWT | Create payment intent (MetaMask flow) |
| `GET` | `/api/payments/status/{intent_id}` | JWT | Poll payment status |
| `POST` | `/api/payments/verify` | JWT | Submit tx_hash for verification |
| `POST` | `/api/payments/nexapay/create` | JWT | Create NexaPay order, return redirect URL |
| `POST` | `/api/payments/nexapay/webhook` | HMAC | NexaPay settlement webhook |
| `GET` | `/api/payments/subscription` | JWT | Get current subscription details |
| `POST` | `/api/payments/cancel` | JWT | Cancel auto-renewal |

**`POST /api/payments/intent`** (MetaMask flow)
```json
Request:  { "tier": "pro", "sender_address": "0x..." }
Response: { "intent_id": 42, "receive_address": "0x...", "amount_usdc": "100000000",
            "expires_at": "2026-03-10T14:15:00Z", "chain_id": 8453 }
```

**`POST /api/payments/nexapay/webhook`** (NexaPay)
```python
# HMAC-SHA256 validation
expected_sig = hmac.new(NEXAPAY_SECRET.encode(), raw_body, 'sha256').hexdigest()
if not hmac.compare_digest(expected_sig, request.headers['X-NexaPay-Signature']):
    raise HTTPException(401)

# Idempotent settlement
if await intent_already_settled(payload['txHash']):
    return {'status': 'ok'}  # Already processed

await activate_subscription(user_id, tier, payload['txHash'], 'nexapay')
```

---

## Phase 4 — Frontend Integration

### New Packages

```bash
npm install wagmi viem @wagmi/core connectkit
```

### New File: `web/src/lib/wagmi.ts`

```typescript
import { createConfig, http } from 'wagmi'
import { base } from 'wagmi/chains'
import { getDefaultConfig } from 'connectkit'

export const wagmiConfig = createConfig(
  getDefaultConfig({
    chains: [base],
    transports: { [base.id]: http() },
    walletConnectProjectId: process.env.NEXT_PUBLIC_WC_PROJECT_ID!,
    appName: 'Crevia Cockpit',
  })
)

export const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
export const USDC_ABI = [/* ERC-20 transfer ABI */]
```

### New File: `web/src/components/payment/PaymentModal.tsx`

3-tab modal — MetaMask | Card | Fiat Bridge:

```
┌─────────────────────────────────────────────────┐
│  Subscribe to Premium (Pilot) — $100/mo          │
├─────────────────────────────────────────────────┤
│  [MetaMask / Wallet]  [Credit Card]  [Fiat]      │
├─────────────────────────────────────────────────┤
│                                                   │
│  Tab 1 — MetaMask:                               │
│    ConnectButton (ConnectKit)                    │
│    "Send 100 USDC on Base"                       │
│    [Pay with Wallet] button                      │
│    Status: Waiting for confirmation...           │
│                                                   │
│  Tab 2 — Credit Card (NexaPay):                  │
│    Your wallet: [0x...      ] (optional)         │
│    [Pay $100 with Card] → redirect               │
│                                                   │
│  Tab 3 — Fiat Bridge (Transak):                  │
│    "Buy USDC and pay directly"                   │
│    [Open Transak] → new tab                      │
│                                                   │
└─────────────────────────────────────────────────┘
```

### New File: `web/src/components/payment/MetaMaskPayButton.tsx`

```typescript
'use client'
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { parseUnits } from 'viem'
import { USDC_ADDRESS, USDC_ABI } from '@/lib/wagmi'

export function MetaMaskPayButton({ tier, receiveAddress, amountRaw, intentId, onSuccess }) {
  const { writeContract, data: hash } = useWriteContract()
  const { isSuccess } = useWaitForTransactionReceipt({ hash })

  // When confirmed on-chain, submit to backend for verification
  useEffect(() => {
    if (isSuccess && hash) {
      fetch('/api/payments/verify', {
        method: 'POST',
        body: JSON.stringify({ intent_id: intentId, tx_hash: hash })
      }).then(() => onSuccess())
    }
  }, [isSuccess, hash])

  return (
    <button onClick={() => writeContract({
      address: USDC_ADDRESS,
      abi: USDC_ABI,
      functionName: 'transfer',
      args: [receiveAddress, BigInt(amountRaw)],  // parseUnits already done server-side
    })}>
      Pay {amount} USDC with Wallet
    </button>
  )
}
```

**Key:** `parseUnits("100", 6)` = `100000000n` — USDC has 6 decimals (NOT 18). Do NOT use `parseEther`.

### Modify: `web/src/app/pricing/page.tsx`

Replace every `href="/waitlist"` button with `<PaymentModal tier="..." />` component.

### Modify: `web/src/app/billing/page.tsx`

Replace waitlist notice with:
- Active subscription card (tier, renewal date, cancel button)
- Upgrade/downgrade flow via PaymentModal
- Payment history table (from `/api/payments/history`)

### Modify: `web/src/app/layout.tsx` (or root providers)

Wrap app in `WagmiProvider` + `ConnectKitProvider`:

```tsx
<WagmiProvider config={wagmiConfig}>
  <QueryClientProvider client={queryClient}>
    <ConnectKitProvider>{children}</ConnectKitProvider>
  </QueryClientProvider>
</WagmiProvider>
```

---

## Phase 5 — Trial System

Trials are **free access** without payment. No wallet required.

**Flow:**
1. User clicks "Start 3-Day Free Trial" → `POST /api/payments/trial { tier }`
2. Backend sets `user.tier = tier`, creates `SubscriptionRecord` with `status='trial'`, `current_period_end = now + 3/7/14 days`
3. Cron job: check `subscription_end < now` → downgrade tier to `free`

**Trial endpoint:** `POST /api/payments/trial`
```json
{ "tier": "basic" }
→ Sets trial, returns { "trial_ends": "2026-03-13T..." }
```

**Email reminders:** 1 day before trial ends → prompt to pay.

---

## Phase 6 — Subscription Renewal

Manual renewal for v1 (no auto-charge):

1. 3 days before `current_period_end` → email reminder
2. Day of expiry → `user.tier = 'free'`, `subscription_status = 'expired'`
3. User logs in → billing page shows "Renew" button → PaymentModal

Future v2: Store wallet address → generate renewal invoice → user signs transaction.

---

## Environment Variables Required

```bash
# api/.env additions
PAYMENT_RECEIVE_WALLET=0x...          # Treasury wallet on Base L2
BASE_RPC_URL=https://mainnet.base.org  # Or Alchemy/Infura Base endpoint
NEXAPAY_API_KEY=...
NEXAPAY_SECRET=...                     # For HMAC webhook validation
NEXAPAY_MERCHANT_ID=...
NEXT_PUBLIC_WC_PROJECT_ID=...          # WalletConnect Cloud project ID
```

---

## Build Order (6 Weeks)

### Week 1 — Foundation
- [ ] `api/models/payment.py` — PaymentIntent + SubscriptionRecord models
- [ ] `api/services/payment_service.py` — core functions (intent, verify, activate)
- [ ] `api/routers/payments.py` — intent + status + verify endpoints
- [ ] Run `create_tables()` to migrate DB
- [ ] Register payments router in `api/main.py`

### Week 2 — NexaPay (Broadest Reach)
- [ ] NexaPay account setup + API credentials
- [ ] `POST /api/payments/nexapay/create` — order creation
- [ ] `POST /api/payments/nexapay/webhook` — HMAC validation + settlement
- [ ] Test end-to-end card → USDC → tier upgrade

### Week 3 — MetaMask / Wagmi
- [ ] Install wagmi + viem + connectkit
- [ ] `web/src/lib/wagmi.ts` — Base chain config
- [ ] `PaymentModal.tsx` + `MetaMaskPayButton.tsx`
- [ ] Update providers in app layout
- [ ] Wire `POST /api/payments/verify` to frontend
- [ ] Test: connect wallet → send USDC → tier activates

### Week 4 — Fiat Bridge
- [ ] Transak widget URL generation (pre-fill amount + wallet)
- [ ] MoonPay as fallback
- [ ] `FiatBridgeButton.tsx` component
- [ ] Add to PaymentModal as Tab 3

### Week 5 — Trial System + Billing UI
- [ ] `POST /api/payments/trial` endpoint
- [ ] Cron: `check_expired_subscriptions()` — daily check
- [ ] Update `pricing/page.tsx` — replace waitlist CTAs
- [ ] Update `billing/page.tsx` — subscription status + renewal
- [ ] Email reminders (3 days before expiry)

### Week 6 — Hardening
- [ ] Idempotency test: submit same tx_hash twice → no double-upgrade
- [ ] Expired intent test: submit tx after 15-min TTL → rejected
- [ ] Wrong amount test: send $50 for $100 tier → rejected
- [ ] Wrong sender test: tx from different wallet → rejected
- [ ] Load test payment endpoint
- [ ] Monitoring: alert if pending intents > 50 (possible attack)

---

## Security Checklist

| Risk | Mitigation |
|------|-----------|
| Double-spend | `UNIQUE` constraint on `tx_hash` |
| Wrong sender | Intent stores `sender_address`; verify `Transfer.from` matches |
| Wrong amount | Verify `Transfer.value >= expected_amount` (allow overpay) |
| Webhook replay | NexaPay HMAC-SHA256 + `nexapay_order_id` idempotency |
| Expired intent | Check `expires_at` before processing any verification |
| Intent flooding | Rate-limit `POST /api/payments/intent` to 5/hour per user |
| RPC manipulation | Use trusted Base RPC (Alchemy/Infura), not user-supplied |

---

## Files Summary

### New Files
| File | Purpose |
|------|---------|
| `api/models/payment.py` | PaymentIntent + SubscriptionRecord DB models |
| `api/services/payment_service.py` | Core payment logic (intent, verify, activate) |
| `api/routers/payments.py` | All payment HTTP endpoints |
| `web/src/lib/wagmi.ts` | Wagmi + Base chain config |
| `web/src/components/payment/PaymentModal.tsx` | 3-tab payment modal |
| `web/src/components/payment/MetaMaskPayButton.tsx` | Wagmi USDC transfer button |
| `web/src/components/payment/NexaPayButton.tsx` | NexaPay card redirect |
| `web/src/components/payment/FiatBridgeButton.tsx` | Transak/MoonPay redirect |

### Modified Files
| File | Change |
|------|--------|
| `api/models/user.py` | Add `wallet_address` field |
| `api/database.py` | Import payment model in `create_tables()` |
| `api/main.py` | Register payments router |
| `web/src/app/pricing/page.tsx` | Replace waitlist CTAs with PaymentModal |
| `web/src/app/billing/page.tsx` | Replace waitlist with live subscription UI |
| `web/src/app/layout.tsx` | Add WagmiProvider + ConnectKitProvider |

---

## NexaPay Integration Notes

- Non-custodial: card → USDC → your wallet directly
- API: `POST https://api.nexapay.io/v1/orders` with `{ amount, currency: 'USDC', network: 'base', wallet: RECEIVE_WALLET, orderId: intent.id }`
- Webhook fires on settlement with `txHash` — verify HMAC then call `activate_subscription()`
- No KYC burden on our side — NexaPay handles compliance
- Webhook secret set in NexaPay dashboard; store as `NEXAPAY_SECRET`

## Transak / MoonPay Notes

- Zero backend code — pure redirect
- Transak URL: `https://global.transak.com/?apiKey=...&defaultCryptoCurrency=USDC&network=base&walletAddress={RECEIVE_WALLET}&fiatAmount=100&fiatCurrency=USD`
- After purchase, user manually tells us or we poll wallet address for incoming USDC
- Best as "last resort" fallback — no automatic tier upgrade without webhook
- Consider: show "Manual activation within 24h" note for fiat bridge users

---

*Plan created: 2026-03-10*
