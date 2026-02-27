'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';

// Mock alert types for static demo
const MOCK_ALERTS = [
  {
    id: 1, asset: 'BTC', status: 'active',
    type: 'Price', condition: 'BTC crosses above $72,000',
    note: 'ATH breakout — potential continuation',
    triggered: false, createdAgo: '2h ago',
  },
  {
    id: 2, asset: 'ETH', status: 'active',
    type: 'Price', condition: 'ETH drops below $1,900',
    note: 'SL alert for long position — journal entry #14',
    triggered: false, createdAgo: '3h ago',
  },
  {
    id: 3, asset: 'BTC', status: 'triggered',
    type: 'Regime', condition: 'Market regime changes to RISK_OFF',
    note: 'Defensive posture trigger — reduce exposure',
    triggered: true, createdAgo: '5h ago',
  },
  {
    id: 4, asset: 'SOL', status: 'active',
    type: 'Price', condition: 'SOL reclaims $150',
    note: 'Key resistance level — watch for breakout volume',
    triggered: false, createdAgo: '1d ago',
  },
  {
    id: 5, asset: 'ETH', status: 'inactive',
    type: 'Funding', condition: 'ETH funding rate exceeds 0.15%',
    note: 'Overheated perp market — consider taking profits',
    triggered: false, createdAgo: '2d ago',
  },
];

const TYPE_COLORS: Record<string, { color: string; bg: string; border: string }> = {
  Price:   { color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',   border: 'rgba(0,229,160,0.2)'   },
  Regime:  { color: '#9b7cf4', bg: 'rgba(155,124,244,0.08)', border: 'rgba(155,124,244,0.2)' },
  Funding: { color: '#f0a030', bg: 'rgba(240,160,48,0.08)',  border: 'rgba(240,160,48,0.2)'  },
  Whale:   { color: '#3d7fff', bg: 'rgba(61,127,255,0.08)',  border: 'rgba(61,127,255,0.2)'  },
};

export default function AlertsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<'active' | 'triggered' | 'all'>('active');

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

  const filtered = MOCK_ALERTS.filter(a => {
    if (tab === 'active')    return a.status === 'active';
    if (tab === 'triggered') return a.status === 'triggered';
    return true;
  });

  const activeCount    = MOCK_ALERTS.filter(a => a.status === 'active').length;
  const triggeredCount = MOCK_ALERTS.filter(a => a.status === 'triggered').length;

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Page header ── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>
              My Alerts
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4, letterSpacing: '0.5px' }}>
              Price, regime &amp; whale alerts · Static demo — live alert engine coming soon
            </div>
          </div>
          {/* Create alert button (placeholder) */}
          <button style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
            color: '#08090c', background: '#00e5a0', padding: '7px 16px',
            borderRadius: 3, fontWeight: 500, border: 'none', cursor: 'not-allowed', opacity: 0.7,
          }} title="Alert creation coming soon">
            + New Alert
          </button>
        </div>

        {/* ── Summary row ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Active Alerts',    value: String(activeCount),    color: '#00e5a0' },
            { label: 'Triggered Today',  value: String(triggeredCount), color: '#f0a030' },
            { label: 'Alert Types',      value: '3',                    color: '#3d7fff' },
            { label: 'Max Alerts',       value: user.tier === 'free' ? '—' : user.tier === 'basic' ? '10' : '∞', color: '#9b7cf4' },
          ].map(card => (
            <div key={card.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{card.label}</div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 22, lineHeight: 1, color: card.color }}>{card.value}</div>
            </div>
          ))}
        </div>

        {/* ── Main content ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 12, alignItems: 'start' }}>

          {/* Alerts list */}
          <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
            {/* Tab bar */}
            <div style={{ display: 'flex', borderBottom: '1px solid #1a2030' }}>
              {(['active', 'triggered', 'all'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1, padding: '9px 14px',
                    fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px',
                    textTransform: 'uppercase',
                    color: tab === t ? '#e2e6f0' : '#38405a',
                    background: 'none', border: 'none',
                    borderBottom: `2px solid ${tab === t ? '#00e5a0' : 'transparent'}`,
                    cursor: 'pointer', transition: 'all 0.15s',
                    marginBottom: -1,
                  }}
                >
                  {t} {t === 'active' ? `(${activeCount})` : t === 'triggered' ? `(${triggeredCount})` : `(${MOCK_ALERTS.length})`}
                </button>
              ))}
            </div>

            {filtered.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, marginBottom: 10 }}>🔔</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>No {tab} alerts</div>
              </div>
            ) : filtered.map(alert => {
              const typeStyle = TYPE_COLORS[alert.type] || TYPE_COLORS.Price;
              const isTriggered = alert.status === 'triggered';
              const isInactive = alert.status === 'inactive';
              return (
                <div key={alert.id} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  padding: '12px 14px', borderBottom: '1px solid #0f1318',
                  opacity: isInactive ? 0.5 : 1,
                  transition: 'background 0.15s',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Status dot */}
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%', marginTop: 6, flexShrink: 0,
                    background: isTriggered ? '#f0a030' : isInactive ? '#38405a' : '#00e5a0',
                    animation: (!isTriggered && !isInactive) ? 'livePulse 2s ease-in-out infinite' : 'none',
                  }} />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 500, color: '#e2e6f0' }}>{alert.condition}</span>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px',
                        textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2,
                        ...typeStyle,
                      }}>{alert.type}</span>
                      {isTriggered && (
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px',
                          textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2,
                          background: 'rgba(240,160,48,0.1)', color: '#f0a030',
                          border: '1px solid rgba(240,160,48,0.2)',
                        }}>Triggered</span>
                      )}
                    </div>
                    {alert.note && (
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', lineHeight: 1.5 }}>{alert.note}</div>
                    )}
                  </div>

                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', flexShrink: 0 }}>{alert.createdAgo}</div>
                </div>
              );
            })}
          </div>

          {/* Right: coming soon panel */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Alert types */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Alert Types</span>
              </div>
              {[
                { icon: '💰', type: 'Price Alert',   desc: 'Trigger on price cross, breakout, or range', avail: true  },
                { icon: '📡', type: 'Regime Alert',  desc: 'Alert when market regime shifts', avail: true  },
                { icon: '🐋', type: 'Whale Alert',   desc: 'Large on-chain move detection', avail: false },
                { icon: '📊', type: 'Funding Alert', desc: 'Funding rate spike or reversal', avail: false },
                { icon: '⚡', type: 'Setup Alert',   desc: 'New AI trade setup for your watchlist', avail: false },
              ].map(item => (
                <div key={item.type} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', borderBottom: '1px solid #0f1318', opacity: item.avail ? 1 : 0.45 }}>
                  <span style={{ fontSize: 14, flexShrink: 0 }}>{item.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0' }}>{item.type}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>{item.desc}</div>
                  </div>
                  {!item.avail && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, color: '#9b7cf4', border: '1px solid rgba(155,124,244,0.3)', borderRadius: 2, padding: '1px 5px', flexShrink: 0 }}>Soon</span>
                  )}
                </div>
              ))}
            </div>

            {/* Coming soon */}
            <div style={{
              background: 'rgba(0,229,160,0.04)', border: '1px solid rgba(0,229,160,0.12)',
              borderRadius: 8, padding: '20px 16px', textAlign: 'center',
            }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: '#00e5a0', marginBottom: 8 }}>
                Live Alert Engine
              </div>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', lineHeight: 1.6, marginBottom: 14 }}>
                Real-time SMS, email &amp; Telegram alerts for price targets, regime changes, and whale moves.
              </p>
              <Link href="/waitlist" style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                color: '#08090c', background: '#00e5a0', padding: '7px 16px',
                borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
              }}>
                Join Waitlist →
              </Link>
            </div>
          </div>
        </div>

      </div>
    </CockpitShell>
  );
}
