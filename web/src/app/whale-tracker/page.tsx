'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';
import CascadeWarningBanner from '@/components/whale/CascadeWarningBanner';
import WhaleAlertFeed from '@/components/whale/WhaleAlertFeed';
import WhaleSentimentBadge from '@/components/whale/WhaleSentimentBadge';
import WhaleFlowMiniChart from '@/components/whale/WhaleFlowMiniChart';

// Tier check — enterprise = Premium+, pro = Premium
const TIER_LEVEL: Record<string, number> = { free: 0, basic: 1, pro: 2, enterprise: 3 };

interface ExchangeFlow {
  exchange: string;
  netflow: number;
  unit: string;
  dir: 'in' | 'out';
  interpretation: string;
}

// Static fallback exchange flows (replaced by flow chart per asset when available)
const STATIC_EXCHANGE_FLOWS: ExchangeFlow[] = [
  { exchange: 'Binance',  netflow: -1840, unit: 'BTC', dir: 'out', interpretation: 'Accumulation signal' },
  { exchange: 'Coinbase', netflow: -420,  unit: 'BTC', dir: 'out', interpretation: 'Institutional withdrawal' },
  { exchange: 'OKX',      netflow: +230,  unit: 'BTC', dir: 'in',  interpretation: 'Slight inflow pressure' },
  { exchange: 'Kraken',   netflow: -180,  unit: 'BTC', dir: 'out', interpretation: 'Minor outflows' },
];

interface SummaryStats {
  moves_detected: number;
  total_volume_usd: number;
  net_exchange_btc: number;
}

export default function WhaleTrackerPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<'BTC' | 'ETH' | 'SOL'>('BTC');

  const tierLevel = TIER_LEVEL[user?.tier ?? 'free'];
  const isEnterprise = tierLevel >= 3;
  const isPro = tierLevel >= 2;

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  // Fetch summary stats from /api/whale/recent if enterprise
  const fetchStats = useCallback(async () => {
    if (!isEnterprise) return;
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      const resp = await fetch('/api/whale/recent?limit=100', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        const txns = data.transactions ?? [];
        const totalUsd = data.total_usd_moved ?? 0;
        const btcOut = txns
          .filter((t: { asset: string; flow_type: string; amount_native: number }) => t.asset === 'BTC' && t.flow_type === 'exchange_withdrawal')
          .reduce((s: number, t: { amount_native: number }) => s + t.amount_native, 0);
        const btcIn = txns
          .filter((t: { asset: string; flow_type: string; amount_native: number }) => t.asset === 'BTC' && t.flow_type === 'exchange_deposit')
          .reduce((s: number, t: { amount_native: number }) => s + t.amount_native, 0);
        setStats({ moves_detected: txns.length, total_volume_usd: totalUsd, net_exchange_btc: -(btcOut - btcIn) });
      }
    } catch { /* silent */ }
  }, [isEnterprise]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#070809', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#38405a', letterSpacing: '1px' }}>LOADING…</span>
      </div>
    );
  }
  if (!user) return null;

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Cascade warning banner (pro+) ── */}
        {isPro && <CascadeWarningBanner />}

        {/* ── Page header ── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>
              Whale Tracker
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4, letterSpacing: '0.5px' }}>
              Large on-chain movements &amp; exchange netflows
              {isEnterprise ? ' · Live data' : isPro ? ' · Sentiment live · Feed requires Premium+' : ' · Upgrade for live tracking'}
            </div>
          </div>

          {/* Sentiment badges (pro+) */}
          {isPro && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {(['BTC', 'ETH', 'SOL'] as const).map(a => (
                <WhaleSentimentBadge key={a} asset={a} />
              ))}
            </div>
          )}

          {!isPro && (
            <div style={{
              padding: '6px 14px', borderRadius: 5,
              background: 'rgba(155,124,244,0.08)', border: '1px solid rgba(155,124,244,0.2)',
              fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px',
              textTransform: 'uppercase', color: '#9b7cf4',
            }}>
              ◈ Premium Feature
            </div>
          )}
        </div>

        {/* ── 3-col summary cards ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 14 }}>
          {[
            {
              label: 'Moves Detected',
              value: isEnterprise && stats ? String(stats.moves_detected) : '—',
              sub: 'last 24 hours',
              color: '#e2e6f0',
            },
            {
              label: 'Total Volume',
              value: isEnterprise && stats
                ? `$${(stats.total_volume_usd / 1e6).toFixed(0)}M`
                : '—',
              sub: 'on-chain today',
              color: '#00e5a0',
            },
            {
              label: 'Net Exchange',
              value: isEnterprise && stats
                ? `${stats.net_exchange_btc > 0 ? '+' : ''}${stats.net_exchange_btc.toFixed(0)} BTC`
                : '—',
              sub: stats && stats.net_exchange_btc < 0 ? 'net outflow ↑ bullish' : 'net inflow',
              color: stats && stats.net_exchange_btc < 0 ? '#00e5a0' : '#ff3d5a',
            },
          ].map(card => (
            <div key={card.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{card.label}</div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 22, lineHeight: 1, color: card.color, marginBottom: 2 }}>{card.value}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>{card.sub}</div>
            </div>
          ))}
        </div>

        {/* ── Main 2-col layout ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 12, alignItems: 'start' }}>

          {/* Left: live alert feed (enterprise) or upgrade prompt */}
          {isEnterprise ? (
            <WhaleAlertFeed limit={20} />
          ) : (
            /* Show the static-design feed for non-enterprise as teaser */
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
                    Large On-Chain Moves
                  </span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase',
                    padding: '1px 5px', borderRadius: 2,
                    background: 'rgba(155,124,244,0.08)', color: '#9b7cf4', border: '1px solid rgba(155,124,244,0.2)',
                  }}>
                    Premium+ Only
                  </span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>≥$10M threshold</span>
              </div>

              {/* Blurred teaser rows */}
              {[
                { asset: 'BTC', amount: '3,240 BTC', usd: '$214.5M', from: 'Binance', to: 'Unknown Wallet', dir: 'out' },
                { asset: 'ETH', amount: '42,000 ETH', usd: '$86.2M', from: 'Coinbase', to: 'Cold Wallet', dir: 'out' },
                { asset: 'USDT', amount: '$120M USDT', usd: '$120M', from: 'Unknown', to: 'Binance', dir: 'in' },
                { asset: 'BTC', amount: '890 BTC', usd: '$59.0M', from: 'Kraken', to: 'OTC Desk', dir: 'out' },
              ].map((row, i) => (
                <div key={i} style={{ filter: 'blur(3px)', opacity: 0.4, padding: '10px 14px', borderBottom: '1px solid #0f1318', display: 'flex', gap: 12, alignItems: 'center', userSelect: 'none', pointerEvents: 'none' }}>
                  <div style={{ width: 22, height: 22, borderRadius: 4, background: '#1a2030', flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0', marginBottom: 2 }}>
                      {row.amount} — {row.from} → {row.to}
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>{row.usd}</div>
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, padding: '2px 6px', borderRadius: 2,
                    background: row.dir === 'out' ? 'rgba(0,229,160,0.08)' : 'rgba(255,61,90,0.08)',
                    color: row.dir === 'out' ? '#00e5a0' : '#ff3d5a',
                    border: `1px solid ${row.dir === 'out' ? 'rgba(0,229,160,0.2)' : 'rgba(255,61,90,0.2)'}`,
                  }}>
                    {row.dir === 'out' ? 'Outflow' : 'Inflow'}
                  </div>
                </div>
              ))}

              <div style={{ padding: '16px', textAlign: 'center', background: '#0d1019' }}>
                <Link href="/pricing" style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: '#08090c', background: '#9b7cf4', padding: '7px 16px',
                  borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
                }}>
                  Upgrade to Premium+ →
                </Link>
              </div>
            </div>
          )}

          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Exchange netflows / flow chart */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
                  Exchange Netflows
                </span>
                {isPro && (
                  <div style={{ display: 'flex', gap: 4 }}>
                    {(['BTC', 'ETH', 'SOL'] as const).map(a => (
                      <button
                        key={a}
                        onClick={() => setSelectedAsset(a)}
                        style={{
                          fontFamily: 'var(--font-mono)', fontSize: 8, padding: '2px 6px', borderRadius: 2,
                          background: selectedAsset === a ? 'rgba(0,229,160,0.1)' : 'transparent',
                          color: selectedAsset === a ? '#00e5a0' : '#38405a',
                          border: `1px solid ${selectedAsset === a ? 'rgba(0,229,160,0.25)' : '#1a2030'}`,
                          cursor: 'pointer',
                        }}
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {isPro ? (
                <div style={{ padding: '12px 14px' }}>
                  <WhaleFlowMiniChart asset={selectedAsset} />
                </div>
              ) : (
                STATIC_EXCHANGE_FLOWS.map(flow => (
                  <div key={flow.exchange} style={{ padding: '10px 14px', borderBottom: '1px solid #0f1318' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span style={{ fontSize: 12, fontWeight: 500, color: '#e2e6f0' }}>{flow.exchange}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500, color: flow.dir === 'out' ? '#00e5a0' : '#ff3d5a' }}>
                        {flow.netflow > 0 ? '+' : ''}{flow.netflow.toLocaleString()} {flow.unit}
                      </span>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a' }}>{flow.interpretation}</div>
                  </div>
                ))
              )}
            </div>

            {/* Upgrade CTA (non-pro) or tier notice */}
            {!isPro && (
              <div style={{
                background: 'rgba(155,124,244,0.04)', border: '1px solid rgba(155,124,244,0.15)',
                borderRadius: 8, padding: '20px 16px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 28, marginBottom: 10 }}>🐋</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: '#9b7cf4', marginBottom: 8 }}>
                  Real-time Detection
                </div>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', lineHeight: 1.6, marginBottom: 14 }}>
                  Live whale alerts, cascade risk detection, and sentiment scores. Upgrade to Premium to unlock.
                </p>
                <Link href="/pricing" style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: '#08090c', background: '#9b7cf4', padding: '7px 16px',
                  borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
                }}>
                  View Plans →
                </Link>
              </div>
            )}

            {/* Sentiment detail (pro+) */}
            {isPro && (
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
                <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
                    Whale Sentiment
                  </span>
                </div>
                <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {(['BTC', 'ETH', 'SOL'] as const).map(a => (
                    <div key={a} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#788098' }}>{a}</span>
                      <WhaleSentimentBadge asset={a} showTooltip={true} />
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>

      </div>
    </CockpitShell>
  );
}
