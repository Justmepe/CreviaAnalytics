'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';

const TIER_META: Record<string, { icon: string; label: string; color: string; bg: string; border: string }> = {
  free:       { icon: '○',  label: 'Free',     color: '#788098', bg: 'rgba(30,35,50,0.5)',        border: '#222c42'               },
  basic:      { icon: '⬡',  label: 'Basic',    color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',      border: 'rgba(0,229,160,0.2)'   },
  pro:        { icon: '⚡', label: 'Premium',  color: '#3d7fff', bg: 'rgba(61,127,255,0.08)',     border: 'rgba(61,127,255,0.2)'  },
  enterprise: { icon: '◈',  label: 'Premium+', color: '#9b7cf4', bg: 'rgba(155,124,244,0.08)',   border: 'rgba(155,124,244,0.2)' },
};

const PLANS = [
  {
    tier: 'basic',
    name: 'Basic',
    label: 'Observer',
    price: '$20',
    period: '/mo',
    trial: '3-day trial',
    color: '#00e5a0',
    features: [
      'Real-time risk calculator',
      'Market regime detection',
      'All 16+ assets',
      '10 custom alerts',
      '6h analysis delay',
      'Weekly digest email',
    ],
  },
  {
    tier: 'pro',
    name: 'Premium',
    label: 'Pilot',
    price: '$100',
    period: '/mo',
    trial: '7-day trial',
    color: '#3d7fff',
    featured: true,
    features: [
      'Everything in Basic',
      'Unlimited alerts',
      'AI trade setups',
      'Whale intelligence',
      'Instant analysis feed',
      '500 API calls/day',
      '90-day trade history',
    ],
  },
  {
    tier: 'enterprise',
    name: 'Premium+',
    label: 'Command',
    price: '$200',
    period: '/mo',
    trial: '14-day trial',
    color: '#9b7cf4',
    features: [
      'Everything in Premium',
      'First-hour analysis access',
      'Custom analysis requests',
      'Unlimited API calls',
      'Priority support',
      'Early feature access',
    ],
  },
];

export default function BillingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

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

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Page header ── */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>
            Billing &amp; Plan
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4, letterSpacing: '0.5px' }}>
            Manage your subscription and see what&apos;s included in each plan
          </div>
        </div>

        {/* ── Current plan card ── */}
        <div style={{
          background: currentMeta.bg,
          border: `1px solid ${currentMeta.border}`,
          borderRadius: 8, padding: '20px 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 26 }}>{currentMeta.icon}</span>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 3 }}>
                Current Plan
              </div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 28, letterSpacing: '2px', color: currentMeta.color, lineHeight: 1 }}>
                {currentMeta.label}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098', marginTop: 4 }}>
                {isFree
                  ? 'Free access · Cockpit Feed only'
                  : `Active subscription · renews monthly`}
              </div>
            </div>
          </div>
          {isFree ? (
            <Link href="/waitlist" style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
              color: '#08090c', background: '#f0a030', padding: '9px 20px',
              borderRadius: 3, fontWeight: 500, textDecoration: 'none',
            }}>
              Upgrade Plan →
            </Link>
          ) : (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginBottom: 8 }}>
                Billing managed via Stripe
              </div>
              <Link href="/waitlist" style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                color: '#788098', border: '1px solid #222c42', padding: '7px 14px',
                borderRadius: 3, textDecoration: 'none', display: 'inline-block',
              }}>
                Manage →
              </Link>
            </div>
          )}
        </div>

        {/* ── Waitlist notice (for all users for now) ── */}
        <div style={{
          background: 'rgba(240,160,48,0.06)', border: '1px solid rgba(240,160,48,0.18)',
          borderRadius: 6, padding: '12px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{ fontSize: 16, flexShrink: 0 }}>⏳</span>
          <div>
            <div style={{ fontFamily: 'var(--font-syne)', fontSize: 12, fontWeight: 600, color: '#f0a030', marginBottom: 2 }}>
              Paid plans are launching soon
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#788098' }}>
              Join the waitlist to get early access, lock in launch pricing, and be first in the cockpit.
            </div>
          </div>
          <Link href="/waitlist" style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
            color: '#08090c', background: '#f0a030', padding: '7px 16px',
            borderRadius: 3, fontWeight: 500, textDecoration: 'none', flexShrink: 0, marginLeft: 'auto',
          }}>
            Join Waitlist →
          </Link>
        </div>

        {/* ── Plans comparison ── */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 12 }}>
            Available Plans
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {PLANS.map(plan => {
              const isCurrentPlan = user.tier === plan.tier;
              return (
                <div key={plan.tier} style={{
                  background: plan.featured ? '#10141c' : '#0c0e12',
                  border: `1px solid ${isCurrentPlan ? plan.color : plan.featured ? 'rgba(61,127,255,0.25)' : '#1a2030'}`,
                  borderRadius: 8, padding: '20px',
                  position: 'relative', overflow: 'hidden',
                }}>
                  {/* Featured glow line */}
                  {plan.featured && (
                    <div style={{
                      position: 'absolute', top: 0, left: 0, right: 0, height: 1,
                      background: `linear-gradient(90deg, transparent, ${plan.color}, transparent)`,
                    }} />
                  )}
                  {isCurrentPlan && (
                    <div style={{
                      position: 'absolute', top: 10, right: 12,
                      fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px',
                      textTransform: 'uppercase', padding: '2px 6px', borderRadius: 2,
                      background: `${plan.color}15`, color: plan.color,
                      border: `1px solid ${plan.color}40`,
                    }}>Current</div>
                  )}

                  {/* Plan header */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>
                      {plan.label}
                    </div>
                    <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 22, letterSpacing: '1.5px', color: plan.color, lineHeight: 1 }}>
                      {plan.name}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 2, marginTop: 6 }}>
                      <span style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, color: '#e2e6f0', lineHeight: 1 }}>{plan.price}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>{plan.period}</span>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#f0a030', marginTop: 4 }}>
                      Free {plan.trial}
                    </div>
                  </div>

                  {/* Features */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 18 }}>
                    {plan.features.map(feat => (
                      <div key={feat} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <span style={{ color: plan.color, fontSize: 10, flexShrink: 0, marginTop: 1 }}>✓</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#788098', lineHeight: 1.4 }}>{feat}</span>
                      </div>
                    ))}
                  </div>

                  {/* CTA */}
                  {isCurrentPlan ? (
                    <div style={{
                      width: '100%', padding: '8px', textAlign: 'center',
                      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.5px',
                      textTransform: 'uppercase', color: '#38405a',
                      border: '1px solid #1a2030', borderRadius: 3,
                    }}>
                      Current Plan
                    </div>
                  ) : (
                    <Link href="/waitlist" style={{
                      display: 'block', width: '100%', padding: '8px',
                      textAlign: 'center', textDecoration: 'none',
                      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px',
                      textTransform: 'uppercase', color: '#08090c',
                      background: plan.color, borderRadius: 3, fontWeight: 500,
                    }}>
                      Join Waitlist →
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Note ── */}
        <div style={{ marginTop: 16, fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', textAlign: 'center', letterSpacing: '0.3px' }}>
          No credit card required to join waitlist · Secure payment via Stripe when billing launches
        </div>

      </div>
    </CockpitShell>
  );
}
