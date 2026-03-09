'use client';

/**
 * PaymentModal — 3-tab payment flow
 * Tab 1: MetaMask / Wallet (Wagmi v2 + ConnectKit, USDC on Base)
 * Tab 2: Credit Card (NexaPay redirect)
 * Tab 3: Fiat Bridge (Transak redirect)
 */

import { useState, useEffect, useCallback } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt, useSwitchChain } from 'wagmi';
import { ConnectKitButton } from 'connectkit';
import { parseUnits } from 'viem';
import { USDC_ADDRESS, USDC_ABI, BASE_CHAIN_ID } from '@/lib/wagmi';
import {
  createPaymentIntent,
  createNexaPayOrder,
  startTrial,
  verifyPayment,
  pollIntentStatus,
  getTransakUrl,
  PaymentIntent,
} from '@/lib/payment';

// ── Types ────────────────────────────────────────────────────────────────────

interface Props {
  tier: string;
  tierName: string;
  tierColor: string;
  amountUsd: number;
  trialDays: number;
  onClose: () => void;
  onSuccess: (tier: string) => void;
}

type Tab = 'wallet' | 'card' | 'fiat';
type Stage = 'idle' | 'connecting' | 'creating' | 'waiting' | 'verifying' | 'success' | 'error';

// ── Tier config (must match backend TIER_CONFIG) ─────────────────────────────
const RECEIVE_WALLET = process.env.NEXT_PUBLIC_PAYMENT_RECEIVE_WALLET || '';

// ── Component ────────────────────────────────────────────────────────────────

export default function PaymentModal({
  tier, tierName, tierColor, amountUsd, trialDays, onClose, onSuccess,
}: Props) {
  const [tab, setTab] = useState<Tab>('wallet');
  const [stage, setStage] = useState<Stage>('idle');
  const [error, setError] = useState('');
  const [intent, setIntent] = useState<PaymentIntent | null>(null);
  const [statusMsg, setStatusMsg] = useState('');

  // Wagmi hooks
  const { address, chainId, isConnected } = useAccount();
  const { switchChain } = useSwitchChain();
  const { writeContract, data: txHash, error: writeError, isPending: isWritePending } = useWriteContract();
  const { isSuccess: isTxConfirmed, isLoading: isTxWaiting } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  // After wallet tx confirms → verify on backend
  useEffect(() => {
    if (isTxConfirmed && txHash && intent) {
      setStage('verifying');
      setStatusMsg('Confirming payment on-chain…');
      verifyPayment(intent.intent_id, txHash)
        .then(() => {
          setStage('success');
          setStatusMsg('');
          onSuccess(tier);
        })
        .catch((e) => {
          setError(e.message || 'Verification failed. Contact support with your tx hash.');
          setStage('error');
        });
    }
  }, [isTxConfirmed, txHash, intent, tier, onSuccess]);

  // Propagate wagmi write errors
  useEffect(() => {
    if (writeError) {
      setError(writeError.message || 'Transaction rejected');
      setStage('error');
    }
  }, [writeError]);

  // ── MetaMask pay flow ────────────────────────────────────────────────────

  const handleWalletPay = useCallback(async () => {
    if (!isConnected || !address) return;
    if (chainId !== BASE_CHAIN_ID) {
      switchChain?.({ chainId: BASE_CHAIN_ID });
      return;
    }

    setError('');
    try {
      // Create server-side intent with sender address for correlation
      setStage('creating');
      setStatusMsg('Preparing payment…');
      const newIntent = await createPaymentIntent(tier, address);
      setIntent(newIntent);

      // Send USDC transfer — parseUnits("100", 6) NOT parseEther
      setStage('waiting');
      setStatusMsg('Confirm in your wallet…');
      writeContract({
        address: USDC_ADDRESS,
        abi: USDC_ABI,
        functionName: 'transfer',
        args: [newIntent.receive_address as `0x${string}`, BigInt(newIntent.expected_usdc_units)],
        chainId: BASE_CHAIN_ID,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Payment setup failed');
      setStage('error');
    }
  }, [isConnected, address, chainId, tier, writeContract, switchChain]);

  // ── Trial flow ───────────────────────────────────────────────────────────

  const handleStartTrial = useCallback(async () => {
    setStage('creating');
    setStatusMsg('Activating trial…');
    setError('');
    try {
      await startTrial(tier);
      setStage('success');
      onSuccess(tier);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start trial');
      setStage('error');
    }
  }, [tier, onSuccess]);

  // ── NexaPay (card) flow ──────────────────────────────────────────────────

  const handleCardPay = useCallback(async () => {
    setStage('creating');
    setStatusMsg('Creating payment order…');
    setError('');
    try {
      const order = await createNexaPayOrder(tier);
      if (order.redirect_url) {
        window.location.href = order.redirect_url;
      } else {
        throw new Error('No redirect URL from payment gateway');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Card payment unavailable');
      setStage('error');
    }
  }, [tier]);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const isOnBase = chainId === BASE_CHAIN_ID;
  const busy = stage === 'creating' || stage === 'waiting' || stage === 'verifying' || isWritePending || isTxWaiting;

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(7,8,9,0.88)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
    >
      <div style={{
        width: '100%', maxWidth: 480,
        background: '#0d1117',
        border: `1px solid ${tierColor}30`,
        borderRadius: 10,
        boxShadow: `0 0 60px ${tierColor}15`,
        overflow: 'hidden',
      }}>

        {/* ── Header ── */}
        <div style={{
          padding: '20px 24px 0',
          borderBottom: '1px solid #1a2030',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>
                Subscribe
              </div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '1px', color: tierColor, lineHeight: 1 }}>
                {tierName}
              </div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 20, color: '#e2e6f0', marginTop: 2 }}>
                ${amountUsd} USDC / month
              </div>
            </div>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#38405a', fontSize: 18, cursor: 'pointer', padding: '4px 8px' }}
            >
              ×
            </button>
          </div>

          {/* Trial banner */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'rgba(0,214,143,0.07)', border: '1px solid rgba(0,214,143,0.2)',
            borderRadius: 4, padding: '7px 14px', marginBottom: 16, width: '100%',
          }}>
            <span style={{ fontSize: 13 }}>⚡</span>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#00d68f' }}>
                Start with a {trialDays}-day free trial
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>
                No payment charged during trial · Cancel anytime
              </div>
            </div>
            {stage !== 'success' && (
              <button
                onClick={handleStartTrial}
                disabled={busy}
                style={{
                  marginLeft: 'auto', flexShrink: 0,
                  fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: '#08090c', background: '#00d68f', border: 'none',
                  padding: '6px 14px', borderRadius: 3, cursor: busy ? 'not-allowed' : 'pointer',
                  opacity: busy ? 0.5 : 1,
                }}
              >
                {stage === 'creating' ? 'Starting…' : 'Try Free →'}
              </button>
            )}
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 0 }}>
            {([
              { id: 'wallet', label: '⬡ MetaMask / Wallet' },
              { id: 'card',   label: '💳 Credit Card' },
              { id: 'fiat',   label: '🌐 Fiat Bridge' },
            ] as { id: Tab; label: string }[]).map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  flex: 1, padding: '10px 8px',
                  fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.5px',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: tab === t.id ? tierColor : '#38405a',
                  borderBottom: tab === t.id ? `2px solid ${tierColor}` : '2px solid transparent',
                  transition: 'color 0.15s',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Tab content ── */}
        <div style={{ padding: '24px' }}>

          {/* Success state */}
          {stage === 'success' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 24, color: '#00d68f', marginBottom: 8 }}>
                {tier === 'trial' ? 'Trial Activated!' : 'Payment Complete!'}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#788098', marginBottom: 20 }}>
                Your {tierName} access is now active. Redirecting…
              </div>
              <button onClick={onClose} style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase',
                color: '#08090c', background: '#00d68f', border: 'none',
                padding: '10px 24px', borderRadius: 4, cursor: 'pointer',
              }}>
                Enter Cockpit →
              </button>
            </div>
          )}

          {/* Error state */}
          {stage === 'error' && (
            <div style={{ marginBottom: 16, padding: '12px 14px', background: 'rgba(240,62,90,0.08)', border: '1px solid rgba(240,62,90,0.2)', borderRadius: 5 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#f03e5a' }}>{error}</div>
              <button onClick={() => { setStage('idle'); setError(''); }} style={{
                marginTop: 8, fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098',
                background: 'none', border: '1px solid #222c42', padding: '4px 12px', borderRadius: 3, cursor: 'pointer',
              }}>
                Try again
              </button>
            </div>
          )}

          {/* Status spinner */}
          {busy && statusMsg && stage !== 'success' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098' }}>
              <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
              {statusMsg}
            </div>
          )}

          {stage !== 'success' && (
            <>
              {/* ── WALLET TAB ── */}
              {tab === 'wallet' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', lineHeight: 1.6 }}>
                    Pay <strong style={{ color: '#e2e6f0' }}>{amountUsd} USDC</strong> on Base L2 directly from your wallet.
                    Fast, low-fee, non-custodial.
                  </div>

                  <div style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 6, padding: '14px 16px' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 10 }}>
                      Payment details
                    </div>
                    {[
                      { label: 'Amount', value: `${amountUsd} USDC` },
                      { label: 'Token', value: 'USD Coin (USDC)' },
                      { label: 'Network', value: 'Base (L2)' },
                      { label: 'Chain ID', value: '8453' },
                    ].map(row => (
                      <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>{row.label}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#e2e6f0' }}>{row.value}</span>
                      </div>
                    ))}
                  </div>

                  {!isConnected ? (
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <ConnectKitButton />
                    </div>
                  ) : !isOnBase ? (
                    <button
                      onClick={() => switchChain?.({ chainId: BASE_CHAIN_ID })}
                      style={{
                        width: '100%', padding: '12px',
                        fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase',
                        color: '#f0a030', background: 'rgba(240,160,48,0.08)',
                        border: '1px solid rgba(240,160,48,0.3)', borderRadius: 5, cursor: 'pointer',
                      }}
                    >
                      Switch to Base Network →
                    </button>
                  ) : (
                    <button
                      onClick={handleWalletPay}
                      disabled={busy}
                      style={{
                        width: '100%', padding: '13px',
                        fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase',
                        color: '#08090c', background: tierColor, border: 'none', borderRadius: 5,
                        cursor: busy ? 'not-allowed' : 'pointer', fontWeight: 500,
                        boxShadow: `0 0 20px ${tierColor}30`,
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      {isWritePending || isTxWaiting ? 'Confirming…' : `Pay ${amountUsd} USDC →`}
                    </button>
                  )}

                  {isConnected && (
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', textAlign: 'center' }}>
                      Connected: {address?.slice(0, 6)}…{address?.slice(-4)}
                      {!isOnBase && ' · Switch to Base to continue'}
                    </div>
                  )}
                </div>
              )}

              {/* ── CARD TAB ── */}
              {tab === 'card' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', lineHeight: 1.6 }}>
                    Pay by card via <strong style={{ color: '#e2e6f0' }}>NexaPay</strong> — card payment is processed and
                    settled as USDC on Base. Non-custodial, no wallet needed.
                  </div>

                  <div style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 6, padding: '14px 16px' }}>
                    {[
                      { label: 'Amount', value: `$${amountUsd} USD` },
                      { label: 'Settled as', value: `${amountUsd} USDC on Base` },
                      { label: 'Gateway', value: 'NexaPay (non-custodial)' },
                    ].map(row => (
                      <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>{row.label}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#e2e6f0' }}>{row.value}</span>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={handleCardPay}
                    disabled={busy}
                    style={{
                      width: '100%', padding: '13px',
                      fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase',
                      color: '#08090c', background: tierColor, border: 'none', borderRadius: 5,
                      cursor: busy ? 'not-allowed' : 'pointer', fontWeight: 500,
                      opacity: busy ? 0.6 : 1,
                    }}
                  >
                    {busy ? 'Preparing…' : `Pay $${amountUsd} by Card →`}
                  </button>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', textAlign: 'center' }}>
                    You will be redirected to NexaPay&apos;s secure payment page
                  </div>
                </div>
              )}

              {/* ── FIAT BRIDGE TAB ── */}
              {tab === 'fiat' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', lineHeight: 1.6 }}>
                    Use <strong style={{ color: '#e2e6f0' }}>Transak</strong> to buy USDC with your local currency and send it
                    directly to our payment address on Base. Best if NexaPay isn&apos;t available in your country.
                  </div>

                  <div style={{ background: 'rgba(240,160,48,0.06)', border: '1px solid rgba(240,160,48,0.18)', borderRadius: 5, padding: '12px 14px' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#f0a030', marginBottom: 4 }}>Manual activation</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098' }}>
                      After purchasing, your subscription will be activated within 24 hours. Email support@creviacockpit.com with your transaction hash.
                    </div>
                  </div>

                  <a
                    href={getTransakUrl(tier, RECEIVE_WALLET)}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'block', width: '100%', padding: '13px',
                      fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase',
                      color: '#08090c', background: '#f0a030', border: 'none', borderRadius: 5,
                      cursor: 'pointer', fontWeight: 500, textAlign: 'center', textDecoration: 'none',
                    }}
                  >
                    Open Transak →
                  </a>

                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', textAlign: 'center' }}>
                    Opens in a new tab · Buy {amountUsd} USDC on Base
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* ── Footer ── */}
        <div style={{ padding: '12px 24px 16px', borderTop: '1px solid #1a2030', display: 'flex', justifyContent: 'center', gap: 24 }}>
          {['🔒 Secure', '⚡ Instant', '↩ Cancel anytime'].map(item => (
            <span key={item} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>{item}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
