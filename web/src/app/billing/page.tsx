'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';
import PaymentModal from '@/components/payment/PaymentModal';
import { getSubscription, getPaymentHistory, cancelSubscription, Subscription, PaymentHistory } from '@/lib/payment';
import { fetchProfile } from '@/lib/auth';

// ── Tier metadata ─────────────────────────────────────────────────────────────

const TIER_META: Record<string, { icon: string; label: string; color: string; bg: string; border: string }> = {
  free:       { icon: '○',  label: 'Free',     color: '#788098', bg: 'rgba(30,35,50,0.5)',      border: '#222c42'               },
  basic:      { icon: '⬡',  label: 'Basic',    color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',    border: 'rgba(0,229,160,0.2)'   },
  pro:        { icon: '⚡', label: 'Premium',  color: '#3d7fff', bg: 'rgba(61,127,255,0.08)',   border: 'rgba(61,127,255,0.2)'  },
  enterprise: { icon: '◈',  label: 'Premium+', color: '#9b7cf4', bg: 'rgba(155,124,244,0.08)', border: 'rgba(155,124,244,0.2)' },
};

const PLANS = [
  {
    tier: 'basic',
    name: 'Basic',
    label: 'Observer',
    price: 20,
    trialDays: 3,
    color: '#00e5a0',
    features: ['Real-time risk calculator', 'Market regime detection', 'All 16+ assets', '10 custom alerts', '6h analysis delay', 'Weekly digest email'],
  },
  {
    tier: 'pro',
    name: 'Premium',
    label: 'Pilot',
    price: 100,
    trialDays: 7,
    color: '#3d7fff',
    featured: true,
    features: ['Everything in Basic', 'Unlimited alerts', 'AI trade setups', 'Whale intelligence', 'Instant analysis feed', '500 API calls/day', '90-day trade history'],
  },
  {
    tier: 'enterprise',
    name: 'Premium+',
    label: 'Command',
    price: 200,
    trialDays: 14,
    color: '#9b7cf4',
    features: ['Everything in Premium', 'First-hour analysis access', 'Custom analysis requests', 'Unlimited API calls', 'Priority support'],
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: '#00d68f', trial: '#f0a030', canceled: '#f03e5a', expired: '#788098', none: '#38405a',
  };
  const c = colors[status] || '#38405a';
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase',
      color: c, background: `${c}15`, border: `1px solid ${c}40`,
      padding: '2px 8px', borderRadius: 3,
    }}>
      {status}
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [sub, setSub] = useState<Subscription | null>(null);
  const [history, setHistory] = useState<PaymentHistory[]>([]);
  const [modalTier, setModalTier] = useState<typeof PLANS[0] | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [cancelMsg, setCancelMsg] = useState('');

  const loadSub = useCallback(async () => {
    try {
      const [s, h] = await Promise.all([getSubscription(), getPaymentHistory()]);
      setSub(s);
      setHistory(h);
    } catch {
      // Non-blocking — free tier users may have no records
    }
  }, []);

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  useEffect(() => {
    if (user) loadSub();
  }, [user, loadSub]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#070809', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#38405a', letterSpacing: '1px' }}>LOADING…</span>
      </div>
    );
  }
  if (!user) return null;

  const currentMeta = TIER_META[user.tier] || TIER_META.free;
  const isFree = user.tier === 'free';
  const isTrialing = sub?.status === 'trial';

  const handleSuccess = async () => {
    setModalTier(null);
    await fetchProfile();
    await loadSub();
    router.refresh();
  };

  const handleCancel = async () => {
    if (!confirm('Cancel your subscription? You will retain access until the billing period ends.')) return;
    setCanceling(true);
    try {
      const result = await cancelSubscription();
      setCancelMsg(`Subscription canceled. Access continues until ${formatDate(result.active_until)}.`);
      await loadSub();
    } catch (e: unknown) {
      setCancelMsg(e instanceof Error ? e.message : 'Failed to cancel');
    } finally {
      setCanceling(false);
    }
  };

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Page header ── */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>
            Billing &amp; Plan
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4, letterSpacing: '0.5px' }}>
            Manage your subscription — USDC payments on Base L2
          </div>
        </div>

        {/* ── Current plan card ── */}
        <div style={{
          background: currentMeta.bg, border: `1px solid ${currentMeta.border}`,
          borderRadius: 8, padding: '20px 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 16, flexWrap: 'wrap', gap: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 26 }}>{currentMeta.icon}</span>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 3 }}>
                Current Plan
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 28, letterSpacing: '2px', color: currentMeta.color, lineHeight: 1 }}>
                  {currentMeta.label}
                </div>
                {sub && <StatusBadge status={sub.status} />}
              </div>
              {sub?.current_period_end && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098', marginTop: 4 }}>
                  {isTrialing ? 'Trial ends' : 'Renews'}: {formatDate(sub.current_period_end)}
                </div>
              )}
              {isFree && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', marginTop: 4 }}>
                  Free access · Start a trial to unlock full features
                </div>
              )}
            </div>
          </div>
          {!isFree && sub?.status !== 'canceled' && (
            <button
              onClick={handleCancel}
              disabled={canceling}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                color: '#788098', border: '1px solid #222c42', background: 'none',
                padding: '7px 14px', borderRadius: 3, cursor: canceling ? 'not-allowed' : 'pointer',
              }}
            >
              {canceling ? 'Canceling…' : 'Cancel Plan'}
            </button>
          )}
        </div>

        {cancelMsg && (
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(240,160,48,0.08)', border: '1px solid rgba(240,160,48,0.2)', borderRadius: 5 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#f0a030' }}>{cancelMsg}</div>
          </div>
        )}

        {/* ── Trial notice ── */}
        {isTrialing && (
          <div style={{
            background: 'rgba(0,214,143,0.06)', border: '1px solid rgba(0,214,143,0.18)',
            borderRadius: 6, padding: '12px 16px', marginBottom: 20,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <span style={{ fontSize: 16 }}>⏳</span>
            <div>
              <div style={{ fontFamily: 'var(--font-syne)', fontSize: 12, fontWeight: 600, color: '#00d68f', marginBottom: 2 }}>
                Trial active — expires {formatDate(sub?.current_period_end || null)}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#788098' }}>
                Subscribe below before your trial ends to keep uninterrupted access.
              </div>
            </div>
          </div>
        )}

        {/* ── Plans grid ── */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 12 }}>
            {isFree || isTrialing ? 'Choose a Plan' : 'Available Plans'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            {PLANS.map(plan => {
              const isCurrentPlan = user.tier === plan.tier;
              return (
                <div key={plan.tier} style={{
                  background: plan.featured ? '#10141c' : '#0c0e12',
                  border: `1px solid ${isCurrentPlan ? plan.color : (plan.featured ? 'rgba(61,127,255,0.25)' : '#1a2030')}`,
                  borderRadius: 8, padding: '20px', position: 'relative', overflow: 'hidden',
                }}>
                  {plan.featured && (
                    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${plan.color}, transparent)` }} />
                  )}
                  {isCurrentPlan && (
                    <div style={{
                      position: 'absolute', top: 10, right: 12,
                      fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px', textTransform: 'uppercase',
                      padding: '2px 6px', borderRadius: 2,
                      background: `${plan.color}15`, color: plan.color, border: `1px solid ${plan.color}40`,
                    }}>Current</div>
                  )}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{plan.label}</div>
                    <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 22, letterSpacing: '1.5px', color: plan.color, lineHeight: 1 }}>{plan.name}</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 2, marginTop: 6 }}>
                      <span style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, color: '#e2e6f0', lineHeight: 1 }}>${plan.price}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>/mo</span>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#f0a030', marginTop: 4 }}>Free {plan.trialDays}-day trial</div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 18 }}>
                    {plan.features.map(feat => (
                      <div key={feat} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <span style={{ color: plan.color, fontSize: 10, flexShrink: 0, marginTop: 1 }}>✓</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#788098', lineHeight: 1.4 }}>{feat}</span>
                      </div>
                    ))}
                  </div>
                  {isCurrentPlan && !isTrialing ? (
                    <div style={{ width: '100%', padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.5px', textTransform: 'uppercase', color: '#38405a', border: '1px solid #1a2030', borderRadius: 3 }}>
                      Current Plan
                    </div>
                  ) : (
                    <button
                      onClick={() => setModalTier(plan)}
                      style={{ display: 'block', width: '100%', padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: plan.color, border: 'none', borderRadius: 3, fontWeight: 500, cursor: 'pointer' }}
                    >
                      {isCurrentPlan && isTrialing ? 'Subscribe Now →' : 'Start Trial →'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Payment history ── */}
        {history.length > 0 && (
          <div style={{ marginTop: 28 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 12 }}>
              Payment History
            </div>
            <div style={{ border: '1px solid #1a2030', borderRadius: 6, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#0c0e12' }}>
                    {['Date', 'Plan', 'Amount', 'Method', 'Tx'].map(h => (
                      <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', fontWeight: 400, borderBottom: '1px solid #1a2030' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map(row => (
                    <tr key={row.id} style={{ borderBottom: '1px solid #1a2030' }}>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098' }}>{formatDate(row.paid_at)}</td>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 10, color: '#e2e6f0', textTransform: 'capitalize' }}>{row.tier}</td>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 10, color: '#00d68f' }}>${row.amount_usd}</td>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', textTransform: 'capitalize' }}>{row.pathway}</td>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>
                        {row.tx_hash ? `${row.tx_hash.slice(0, 8)}…${row.tx_hash.slice(-6)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div style={{ marginTop: 16, fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', textAlign: 'center', letterSpacing: '0.3px' }}>
          Payments settled as USDC on Base L2 · Non-custodial · Cancel anytime
        </div>

      </div>

      {/* ── Payment modal ── */}
      {modalTier && (
        <PaymentModal
          tier={modalTier.tier}
          tierName={modalTier.name}
          tierColor={modalTier.color}
          amountUsd={modalTier.price}
          trialDays={modalTier.trialDays}
          onClose={() => setModalTier(null)}
          onSuccess={handleSuccess}
        />
      )}
    </CockpitShell>
  );
}
