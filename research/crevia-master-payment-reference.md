# Crevia Cockpit — Master Payment Reference

> **Stack:** Next.js 15 · Wagmi v2 · Viem · Base L2 · USDC  
> **Version:** 1.0 Final · March 2026

---

## The Three Pathways at a Glance

| | Pathway 1 — MetaMask Direct | Pathway 2 — Fiat Bridge | Pathway 3 — NexaPay Gateway |
|---|---|---|---|
| **User type** | Crypto-native, holds USDC | Non-crypto, willing to do light KYC | Anyone, wants to pay by card |
| **Merchant KYC** | None | None | None |
| **User KYC** | None | Required by Transak/MoonPay (their ID, not yours) | None |
| **Fees** | ~$0.001 gas (absorbable) | 1–3% spread charged by on-ramp to user | 1–3% conversion fee passed to user |
| **Revenue** | 100% of $29 | $29 arrives to you — user covers on-ramp | $29 USDC lands directly in your wallet |
| **Privacy** | Maximum — wallet address only | High | High — email + wallet only |
| **Build time** | 5–6 weeks (custom stack) | Hours — it's a link | 1–2 days (API + webhook) |
| **Ship order** | Build first | Ship day one | Ship week 2 |

---

## Corrections from Research

> **Bcon** — No active developer documentation, API reference, or community activity found as of March 2026. Do not use as a production dependency. NexaPay occupies the same "no-KYC, non-custodial, email-only signup" niche with verified uptime, an active API, and Base USDC support.

> **Helio** — Acquired by MoonPay, rebranded as MoonPay Commerce. Its embeddable checkout widget runs on **Solana**, not EVM chains. For a Base/USDC stack, Helio's React SDK will not work without significant modification. MoonPay Commerce supports Base via API but is a heavier integration — consider for v2, not v1.

---

## Pathway 1 — Pure MetaMask Direct

For users who already hold USDC. You own the full stack — no middleware, no processor fees.

### User flow

1. User clicks **"Pay with Wallet"**
2. ConnectKit modal — connects MetaMask / Coinbase Wallet / WalletConnect
3. Frontend enforces switch to Base network via `useSwitchChain`
4. Server creates a payment intent — stores `{ userId, planId, walletAddress }`
5. `writeContractAsync` calls `USDC.transfer(businessWallet, parseUnits("29", 6))`
6. txHash returned immediately — submitted to `/api/payment/verify`
7. Backend awaits receipt, parses `Transfer` event log, activates subscription

### The critical decimal mistake

```ts
// ❌ WRONG — parseEther uses 18 decimals
value: parseEther("29")

// ✅ CORRECT — USDC uses 6 decimals
args: [recipientAddress, parseUnits("29", 6)]
```

### Frontend hook

```ts
// hooks/useUsdcPayment.ts
import { parseUnits, erc20Abi } from 'viem'
import { useWriteContract } from 'wagmi'

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

export function useUsdcPayment(recipientAddress: `0x${string}`) {
  const { writeContractAsync } = useWriteContract()

  const pay = async (amountUsd: string, intentId: string) => {
    const txHash = await writeContractAsync({
      address: USDC_BASE,
      abi: erc20Abi,
      functionName: 'transfer',
      args: [recipientAddress, parseUnits(amountUsd, 6)], // ← 6 decimals
    })
    await fetch('/api/payment/verify', {
      method: 'POST',
      body: JSON.stringify({ txHash, intentId }),
    })
    return txHash
  }

  return { pay }
}
```

---

## Pathway 2 — Fiat Bridge (Redirection)

**Ships day one. Zero backend code.**

Add one paragraph to your checkout UI:

> *Don't have USDC? [Buy inside MetaMask →](https://metamask.app.link/buy) or use [Transak](https://global.transak.com/?cryptoCurrencyCode=USDC&network=base). Once you have USDC on Base, return here to complete your subscription.*

That's it. The on-ramp provider handles card processing and user KYC — you are not involved. Once the user has USDC they return and use Pathway 1.

**Why it works legally:** You are not selling crypto. Transak/MoonPay is. Their license covers the conversion. You receive USDC from a user's wallet — identical to Pathway 1 from your backend's perspective.

---

## Pathway 3 — Non-Custodial Gateway (NexaPay)

Card payment UI → NexaPay converts → $29 USDC arrives at your Base wallet → webhook fires → same `verifyUsdcPayment()` as Pathway 1.

### Create a checkout session

```ts
// app/api/fiat/checkout-session/route.ts
export async function POST(req: Request) {
  const { planId, userId } = await req.json()

  const intent = await db.paymentIntents.create({
    data: { userId, planId, provider: 'nexapay', status: 'pending' }
  })

  const res = await fetch('https://api.nexapay.one/v1/checkout', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${process.env.NEXAPAY_API_KEY}` },
    body: JSON.stringify({
      amount:        29,
      currency:      'USD',
      settleTo:      'USDC',
      walletAddress: process.env.BUSINESS_WALLET_ADDRESS,
      network:       'base',
      metadata:      { intentId: intent.id, userId, planId }, // ← correlation key
      webhookUrl:    `${process.env.NEXT_PUBLIC_URL}/api/webhook/nexapay`,
    }),
  })

  const { checkoutUrl } = await res.json()
  return Response.json({ checkoutUrl })
}
```

### Receive and validate the webhook

```ts
// app/api/webhook/nexapay/route.ts
import { createHmac } from 'crypto'

export async function POST(req: Request) {
  const body      = await req.text()
  const signature = req.headers.get('x-nexapay-signature') ?? ''

  // Step 1: Reject anything unsigned
  const expected = createHmac('sha256', process.env.NEXAPAY_WEBHOOK_SECRET!)
    .update(body).digest('hex')
  if (expected !== signature) return new Response('Unauthorized', { status: 401 })

  const event = JSON.parse(body)
  if (event.status !== 'success') return new Response('ok')

  // Step 2: Independently verify on-chain — never trust the webhook alone
  await verifyUsdcPayment(event.txHash, event.metadata.planId)

  // Step 3: Idempotent activation — txHash uniqueness prevents replay
  await db.subscriptions.upsert({
    where:  { txHash: event.txHash },
    create: { userId: event.metadata.userId, planId: event.metadata.planId,
              txHash: event.txHash, provider: 'nexapay' },
    update: {} // no-op if already exists
  })

  return new Response('ok')
}
```

---

## The Metadata Trick — What Actually Works

The tip "embed a unique ID in the transaction's data field" works for raw ETH sends. **It does not work for USDC.**

USDC transfers are ABI-encoded function calls: `transfer(address to, uint256 amount)`. The ABI is fixed. There is no slot for extra bytes — appending them causes the call to revert.

### The correct approach — wallet address correlation

```ts
// app/api/payment/intent/route.ts
export async function POST(req: Request) {
  const { userId, planId, walletAddress } = await req.json()

  // The wallet address IS the metadata — no on-chain encoding needed
  const intent = await db.paymentIntents.create({
    data: {
      userId,
      planId,
      walletAddress: walletAddress.toLowerCase(),
      status: 'pending',
      expiresAt: new Date(Date.now() + 15 * 60_000), // 15-minute TTL
    }
  })

  return Response.json({ intentId: intent.id })
}

// When USDC arrives, match payment to user via the sender address
async function activateFromTransfer(transfer: TransferLog, txHash: string) {
  const intent = await db.paymentIntents.findFirst({
    where: {
      walletAddress: transfer.args.from.toLowerCase(),
      status: 'pending',
      expiresAt: { gt: new Date() },
    }
  })
  if (!intent) throw new Error('No matching intent for sender address')
  await activateSubscription(intent.userId, intent.planId, txHash)
}
```

| Approach | Works for USDC? | Complexity | Verdict |
|---|---|---|---|
| **Wallet address correlation** | ✅ Yes | Low | Use this |
| Unique deposit address per user | ✅ Yes | Medium | Consider at high volume |
| Wrapper smart contract | ✅ Yes | High | V3+ only |
| Raw ETH with encoded `data` field | ❌ No (two-tx, race conditions) | Medium | Avoid |

---

## Shared Backend Verification — Write Once, Used by All Three Pathways

All three pathways result in USDC arriving at your Base wallet and a txHash. This function handles all of them.

```ts
// lib/verifyPayment.ts
import { createPublicClient, http, parseEventLogs, erc20Abi, parseUnits } from 'viem'
import { base } from 'viem/chains'

const client = createPublicClient({
  chain: base,
  transport: http(process.env.ALCHEMY_BASE_RPC_URL),
})

const USDC_BASE   = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
const PLAN_PRICES = {
  starter: parseUnits('29', 6),
  pro:     parseUnits('79', 6),
  team:    parseUnits('199', 6),
}

export async function verifyUsdcPayment(hash: `0x${string}`, planId: string) {
  const receipt = await client.waitForTransactionReceipt({
    hash,
    timeout: 300_000,
    confirmations: 2, // reorg protection
  })
  if (receipt.status !== 'success') throw new Error('Transaction reverted')

  // ERC-20 amounts are in logs — tx.value is always 0n for token transfers
  const logs = parseEventLogs({ abi: erc20Abi, logs: receipt.logs, eventName: 'Transfer' })
  const transfer = logs.find(
    l => l.address.toLowerCase() === USDC_BASE.toLowerCase()
      && l.args.to?.toLowerCase() === process.env.BUSINESS_WALLET?.toLowerCase()
  )
  if (!transfer) throw new Error('No USDC transfer to business wallet found')

  const expected  = PLAN_PRICES[planId]
  const actual    = transfer.args.value as bigint
  const tolerance = expected / 100n // 1% for conversion spreads
  if (actual < expected - tolerance) throw new Error(`Underpayment: ${actual} < ${expected}`)

  return { from: transfer.args.from, amount: actual }
}
```

> ⚠️ **Never check `transaction.value` for ERC-20 payments.** It will always be `0n`. The actual USDC amount is in the `Transfer` event log. Always use `parseEventLogs`.

---

## Checkout Router — Surface the Right Pathway Automatically

```tsx
// components/CheckoutRouter.tsx
'use client'
import { useAccount, useBalance } from 'wagmi'
import { parseUnits } from 'viem'

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

export function CheckoutRouter({ plan }: { plan: Plan }) {
  const { isConnected, address } = useAccount()
  const { data: balance } = useBalance({ address, token: USDC_BASE })

  const hasEnoughUsdc = balance && balance.value >= parseUnits(plan.price, 6)
  const hasWallet     = typeof window !== 'undefined' && 'ethereum' in window

  return (
    <div className="flex flex-col gap-3">
      {/* Always show both — never hide an option */}
      <WalletPayButton plan={plan} disabled={!hasEnoughUsdc} />
      <FiatPayButton   plan={plan} secondary={hasWallet} />

      {isConnected && !hasEnoughUsdc && (
        <p className="text-sm text-muted">
          Need USDC?{' '}
          <a href="https://metamask.app.link/buy" target="_blank">Buy in MetaMask</a>
          {' '}or{' '}
          <a href="https://global.transak.com/?cryptoCurrencyCode=USDC&network=base" target="_blank">
            use Transak
          </a>
        </p>
      )}
    </div>
  )
}
```

---

## Risk Register

| Risk | Description | Mitigation |
|---|---|---|
| Chain reorg | A confirmed tx disappears after a shallow reorg | Wait for `confirmations: 2` in `waitForTransactionReceipt` |
| Duplicate webhooks | Alchemy or NexaPay fires the same event twice | `txHash` UNIQUE constraint in DB — upsert with `update: {}` no-op |
| Underpayment | User sends slightly less due to conversion spread | 1% tolerance (`expected / 100n`). Reject anything more than 1% short |
| Stuck transaction | Low-gas tx sits unconfirmed indefinitely | 5-minute server timeout. Mark intent `expired`. Show retry UI. Funds are safe |
| Wrong chain | User sends USDC on Ethereum mainnet instead of Base | Enforce `useSwitchChain` to Base before enabling Pay button. Validate chain ID from receipt |
| Webhook spoofing | Malicious actor POSTs fake confirmation | HMAC-SHA256 validation on all webhooks. Always re-verify on-chain regardless |
| Replay attack | Same txHash used to activate multiple subscriptions | `txHash` UNIQUE DB constraint. One hash = one subscription record |
| Shared wallet | Two users paying from the same address simultaneously | One pending intent per wallet address at a time. Creating a second invalidates the first |

---

## Environment Variables

| Variable | Pathway | Source |
|---|---|---|
| `ALCHEMY_BASE_RPC_URL` | All | Alchemy dashboard |
| `ALCHEMY_WEBHOOK_SECRET` | P1 | Alchemy Notify → signing key |
| `BUSINESS_WALLET_ADDRESS` | All | Your MetaMask address on Base |
| `NEXT_PUBLIC_USDC_ADDRESS` | P1 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | P1 | cloud.walletconnect.com (free tier) |
| `NEXAPAY_API_KEY` | P3 | nexapay.one dashboard → API keys |
| `NEXAPAY_WEBHOOK_SECRET` | P3 | NexaPay dashboard → Webhooks |
| `NEXT_PUBLIC_CHAIN` | All | `base` or `base-sepolia` |
| `NEXT_PUBLIC_CDP_PAYMASTER_URL` | P1 + AA | Coinbase CDP (only for ERC-4337 gasless) |

---

## Build Checklist

### Week 1–2 · Foundation

- [ ] Install `wagmi`, `viem`, `connectkit`, `@tanstack/react-query`
- [ ] Configure `WagmiProvider`, `QueryClientProvider`, `ConnectKit` in app layout
- [ ] DB schema: `payment_intents`, `subscriptions` — `txHash` as UNIQUE
- [ ] Build `CheckoutRouter` — detect wallet, surface correct CTAs
- [ ] Add Pathway 2 links: MetaMask buy deep-link + Transak public URL
- [ ] Sign up NexaPay, configure Base USDC settlement to your wallet address

### Week 3–4 · Core Payment Logic

- [ ] P1: `useUsdcPayment` hook — `writeContractAsync` + `parseUnits(amount, 6)`
- [ ] P1: `POST /api/payment/intent` — stores `walletAddress` + `userId`
- [ ] Shared: `verifyUsdcPayment()` — `parseEventLogs`, 2-block confirmation, 1% tolerance
- [ ] P1: `POST /api/payment/verify` — calls `verifyUsdcPayment()`
- [ ] P3: `POST /api/fiat/checkout-session` — NexaPay session creation
- [ ] P3: `POST /api/webhook/nexapay` — HMAC validation + calls `verifyUsdcPayment()`

### Week 5–6 · Hardening

- [ ] HMAC validation on all webhooks (Alchemy + NexaPay)
- [ ] Idempotency: `txHash` UNIQUE + `upsert` with `update: {}` no-op
- [ ] Intent expiry: 15-minute TTL, "expired — start again" UI state
- [ ] Wrong-chain guard: `useSwitchChain` enforced before payment enabled
- [ ] Full E2E test on Base Sepolia — all three pathways
- [ ] Deploy to Base mainnet

### Phase 4 (Optional) · ERC-4337 Gasless Payments

- [ ] Create Coinbase CDP account, configure Paymaster with monthly spend limits
- [ ] Install `permissionless` — `npm install permissionless viem`
- [ ] Build `createSponsoredClient()` using `toCoinbaseSmartAccount` + `sponsorUserOperation`
- [ ] Batch `approve` + `transfer` into a single `sendUserOperation` call
- [ ] Backend unchanged — UserOps settle as normal txHashes on Base

---

## Pro-Tip: ERC-4337 Cost Analysis

At $0.001 gas per transaction on Base, sponsoring gas costs you:

| Subscribers | Monthly gas cost | As % of $29 revenue |
|---|---|---|
| 100 | $0.10 | 0.003% |
| 1,000 | $1.00 | 0.003% |
| 10,000 | $10.00 | 0.003% |
| 100,000 | $100.00 | 0.003% |

Compare to Stripe: 2.9% + $0.30 = **$1.14 per subscriber per month** on a $29 plan. Sponsored crypto gas is approximately 1,000× cheaper per transaction than card processing.
