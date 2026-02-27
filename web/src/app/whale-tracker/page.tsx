'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';

// Static mock data — placeholder until real whale detection is built
const MOCK_WHALE_MOVES = [
  { id: 1, asset: 'BTC', dir: 'out', amount: '3,240 BTC', usd: '$214.5M', from: 'Binance', to: 'Unknown Wallet', time: '4m ago', size: 88 },
  { id: 2, asset: 'ETH', dir: 'out', amount: '42,000 ETH', usd: '$86.2M', from: 'Coinbase', to: 'Cold Wallet', time: '9m ago', size: 72 },
  { id: 3, asset: 'USDT', dir: 'in',  amount: '$120M USDT', usd: '$120M', from: 'Unknown', to: 'Binance', time: '17m ago', size: 95 },
  { id: 4, asset: 'BTC', dir: 'out', amount: '890 BTC', usd: '$59.0M', from: 'Kraken', to: 'OTC Desk', time: '28m ago', size: 55 },
  { id: 5, asset: 'SOL', dir: 'out', amount: '580,000 SOL', usd: '$71.3M', from: 'FTX Wallet', to: 'Binance', time: '34m ago', size: 61 },
  { id: 6, asset: 'ETH', dir: 'in',  amount: '18,500 ETH', usd: '$38.0M', from: 'Unknown', to: 'Binance', time: '41m ago', size: 42 },
  { id: 7, asset: 'BTC', dir: 'out', amount: '1,120 BTC', usd: '$74.2M', from: 'OKX', to: 'Cold Wallet', time: '55m ago', size: 68 },
  { id: 8, asset: 'USDC', dir: 'in',  amount: '$55M USDC', usd: '$55M', from: 'Circle', to: 'Coinbase', time: '1h 8m ago', size: 47 },
];

const MOCK_EXCHANGE_FLOWS = [
  { exchange: 'Binance',  netflow: -1840,  unit: 'BTC', dir: 'out', interpretation: 'Accumulation signal' },
  { exchange: 'Coinbase', netflow: -420,   unit: 'BTC', dir: 'out', interpretation: 'Institutional withdrawal' },
  { exchange: 'OKX',      netflow: +230,   unit: 'BTC', dir: 'in',  interpretation: 'Slight inflow pressure' },
  { exchange: 'Kraken',   netflow: -180,   unit: 'BTC', dir: 'out', interpretation: 'Minor outflows' },
];

const ASSET_COLORS: Record<string, string> = {
  BTC:  'linear-gradient(135deg,#f7931a,#e07c10)',
  ETH:  'linear-gradient(135deg,#627eea,#4f67c8)',
  SOL:  'linear-gradient(135deg,#9945ff,#14f195)',
  USDT: 'linear-gradient(135deg,#26a17b,#1a8060)',
  USDC: 'linear-gradient(135deg,#2775ca,#1a5ca8)',
};

export default function WhaleTrackerPage() {
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

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Page header ── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>
              Whale Tracker
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4, letterSpacing: '0.5px' }}>
              Large on-chain movements &amp; exchange netflows · Static demo — live detection coming soon
            </div>
          </div>
          {/* Coming soon badge */}
          <div style={{
            padding: '6px 14px', borderRadius: 5,
            background: 'rgba(155,124,244,0.08)', border: '1px solid rgba(155,124,244,0.2)',
            fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px',
            textTransform: 'uppercase', color: '#9b7cf4',
          }}>
            ◈ Coming Soon
          </div>
        </div>

        {/* ── 3-col summary cards ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Moves Detected',  value: '8',       sub: 'last 2 hours',    color: '#e2e6f0' },
            { label: 'Total Volume',    value: '$678M',    sub: 'on-chain today',  color: '#00e5a0' },
            { label: 'Net Exchange',    value: '−2,210 BTC', sub: 'net outflow',   color: '#00e5a0' },
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

          {/* Left: large moves feed */}
          <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
                  Large On-Chain Moves
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase',
                  padding: '1px 5px', borderRadius: 2,
                  background: 'rgba(0,229,160,0.08)', color: '#00e5a0',
                  border: '1px solid rgba(0,229,160,0.2)',
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                }}>
                  <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block', animation: 'livePulse 2s ease-in-out infinite' }} />
                  Demo data
                </span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', letterSpacing: '0.5px' }}>
                &gt;$10M threshold
              </span>
            </div>

            {MOCK_WHALE_MOVES.map(move => (
              <div key={move.id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 14px', borderBottom: '1px solid #0f1318',
                transition: 'background 0.15s', cursor: 'default',
              }}
                onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {/* Asset avatar */}
                <div style={{
                  width: 22, height: 22, borderRadius: 4, flexShrink: 0,
                  background: ASSET_COLORS[move.asset] || '#1a2030',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--font-mono)', fontSize: 6.5, fontWeight: 700, color: '#08090c',
                }}>{move.asset.slice(0, 3)}</div>

                {/* Description */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0', marginBottom: 2 }}>
                    {move.amount} moved — <span style={{ color: '#788098', fontWeight: 400 }}>{move.from} → {move.to}</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>
                    {move.usd}
                  </div>
                </div>

                {/* Direction badge */}
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase',
                  padding: '2px 6px', borderRadius: 2, flexShrink: 0,
                  ...(move.dir === 'out'
                    ? { background: 'rgba(0,229,160,0.08)', color: '#00e5a0', border: '1px solid rgba(0,229,160,0.2)' }
                    : { background: 'rgba(255,61,90,0.08)', color: '#ff3d5a', border: '1px solid rgba(255,61,90,0.2)' }
                  ),
                }}>{move.dir === 'out' ? 'Outflow' : 'Inflow'}</div>

                {/* Signal bar */}
                <div style={{ width: 60, flexShrink: 0 }}>
                  <div style={{ height: 2, background: '#1a2030', borderRadius: 1, overflow: 'hidden' }}>
                    <div style={{ height: 2, borderRadius: 1, width: `${move.size}%`, background: '#3d7fff', transition: 'width 1s ease' }} />
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a', marginTop: 2, textAlign: 'right' }}>{move.size}%</div>
                </div>

                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', flexShrink: 0, width: 60, textAlign: 'right' }}>{move.time}</div>
              </div>
            ))}
          </div>

          {/* Right: exchange netflows + coming soon */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Exchange netflows */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Exchange Netflows</span>
              </div>
              {MOCK_EXCHANGE_FLOWS.map(flow => (
                <div key={flow.exchange} style={{ padding: '10px 14px', borderBottom: '1px solid #0f1318' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#e2e6f0' }}>{flow.exchange}</span>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500,
                      color: flow.dir === 'out' ? '#00e5a0' : '#ff3d5a',
                    }}>
                      {flow.netflow > 0 ? '+' : ''}{flow.netflow.toLocaleString()} {flow.unit}
                    </span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a' }}>{flow.interpretation}</div>
                </div>
              ))}
            </div>

            {/* Coming soon notice */}
            <div style={{
              background: 'rgba(155,124,244,0.04)',
              border: '1px solid rgba(155,124,244,0.15)',
              borderRadius: 8, padding: '20px 16px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>🐋</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: '#9b7cf4', marginBottom: 8 }}>
                Real-time Detection
              </div>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', lineHeight: 1.6, marginBottom: 14 }}>
                On-chain whale detection engine is in development. Live alerts and wallet cluster analysis coming soon.
              </p>
              <Link href="/waitlist" style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                color: '#08090c', background: '#9b7cf4', padding: '7px 16px',
                borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
              }}>
                Get Early Access →
              </Link>
            </div>

          </div>
        </div>

      </div>
    </CockpitShell>
  );
}
