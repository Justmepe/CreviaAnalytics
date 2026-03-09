/**
 * Payment API helpers — all calls to /api/payments/*
 */

import { getStoredToken } from '@/lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function authHeaders(): HeadersInit {
  const token = getStoredToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Types ──────────────────────────────────────────────────

export interface PaymentIntent {
  intent_id: number;
  tier: string;
  receive_address: string;
  expected_usdc_units: string;
  amount_usd_cents: number;
  expires_at: string;
  chain_id: number;
}

export interface IntentStatus {
  intent_id: number;
  status: 'pending' | 'paid' | 'expired' | 'failed';
  tier: string;
  tx_hash: string | null;
  paid_at: string | null;
}

export interface Subscription {
  tier: string;
  status: string;
  is_trial: boolean;
  current_period_end: string | null;
  payment_pathway: string | null;
}

export interface PaymentHistory {
  id: number;
  tier: string;
  amount_usd: number;
  pathway: string;
  tx_hash: string | null;
  paid_at: string | null;
}

// ── Intent ─────────────────────────────────────────────────

export async function createPaymentIntent(
  tier: string,
  senderAddress?: string
): Promise<PaymentIntent> {
  const res = await fetch(`${API}/api/payments/intent`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier, sender_address: senderAddress }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create payment intent');
  }
  return res.json();
}

export async function pollIntentStatus(intentId: number): Promise<IntentStatus> {
  const res = await fetch(`${API}/api/payments/status/${intentId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch intent status');
  return res.json();
}

export async function verifyPayment(
  intentId: number,
  txHash: string
): Promise<{ status: string; tier: string; tx_hash: string }> {
  const res = await fetch(`${API}/api/payments/verify`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ intent_id: intentId, tx_hash: txHash }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Payment verification failed');
  }
  return res.json();
}

// ── NexaPay ────────────────────────────────────────────────

export async function createNexaPayOrder(
  tier: string
): Promise<{ intent_id: number; redirect_url: string; order_id: string }> {
  const res = await fetch(`${API}/api/payments/nexapay/create`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create NexaPay order');
  }
  return res.json();
}

// ── Trial ──────────────────────────────────────────────────

export async function startTrial(
  tier: string
): Promise<{ status: string; tier: string; trial_ends: string; trial_days: number }> {
  const res = await fetch(`${API}/api/payments/trial`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start trial');
  }
  return res.json();
}

// ── Subscription ───────────────────────────────────────────

export async function getSubscription(): Promise<Subscription> {
  const res = await fetch(`${API}/api/payments/subscription`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch subscription');
  return res.json();
}

export async function getPaymentHistory(): Promise<PaymentHistory[]> {
  const res = await fetch(`${API}/api/payments/history`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch payment history');
  return res.json();
}

export async function cancelSubscription(): Promise<{
  status: string;
  active_until: string | null;
  message: string;
}> {
  const res = await fetch(`${API}/api/payments/cancel`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to cancel subscription');
  }
  return res.json();
}

// ── Transak fiat bridge URL builder ───────────────────────

const TIER_USD: Record<string, number> = { basic: 20, pro: 100, enterprise: 200 };
const TRANSAK_API_KEY = process.env.NEXT_PUBLIC_TRANSAK_API_KEY || '';

export function getTransakUrl(tier: string, receiveWallet: string): string {
  const amount = TIER_USD[tier] || 0;
  const params = new URLSearchParams({
    apiKey: TRANSAK_API_KEY,
    defaultCryptoCurrency: 'USDC',
    network: 'base',
    walletAddress: receiveWallet,
    fiatAmount: String(amount),
    fiatCurrency: 'USD',
    disableWalletAddressForm: 'true',
  });
  return `https://global.transak.com/?${params.toString()}`;
}
