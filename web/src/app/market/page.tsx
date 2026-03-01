import { Metadata } from 'next';
import { getLatestSnapshot } from '@/lib/api';
import MarketLiveClient from '@/components/market/MarketLiveClient';
import AuthShell from '@/components/layout/AuthShell';

export const metadata: Metadata = {
  title: 'Live Market Dashboard',
  description: 'Live crypto market data — prices, Fear & Greed, dominance, and volume.',
};

export const revalidate = 60;

/* ── Whale Static Data ───────────────────────────────────────── */

const whaleAlerts = [
  { type: 'deposit',  icon: '📥', amount: '4,200 BTC',   usd: '$286.8M', from: 'Unknown Wallet', to: 'Binance',       tag: 'Exch. Deposit', ago: '2m ago'  },
  { type: 'withdraw', icon: '📤', amount: '18,400 ETH',  usd: '$37.9M',  from: 'Coinbase',       to: 'Cold Wallet',   tag: 'Accumulate',    ago: '5m ago'  },
  { type: 'transfer', icon: '↔',  amount: '2.1M XMR',    usd: '$730.8M', from: 'Unknown',        to: 'Unknown',       tag: 'Transfer',      ago: '11m ago' },
  { type: 'deposit',  icon: '📥', amount: '9,800 SOL',   usd: '$856K',   from: 'Unknown Wallet', to: 'OKX',           tag: 'Exch. Deposit', ago: '14m ago' },
  { type: 'withdraw', icon: '📤', amount: '250K UNI',    usd: '$998K',   from: 'Kraken',         to: 'Cold Wallet',   tag: 'Accumulate',    ago: '19m ago' },
  { type: 'deposit',  icon: '📥', amount: '680 BTC',     usd: '$46.4M',  from: 'Unknown Wallet', to: 'Bybit',         tag: 'Exch. Deposit', ago: '24m ago' },
  { type: 'withdraw', icon: '📤', amount: '42,000 ETH',  usd: '$86.4M',  from: 'Binance',        to: 'Cold Wallet',   tag: 'Accumulate',    ago: '31m ago' },
  { type: 'transfer', icon: '↔',  amount: '5,200 BTC',   usd: '$354.9M', from: 'Cold Wallet A',  to: 'Cold Wallet B', tag: 'Transfer',      ago: '38m ago' },
] as const;

const whaleFactors = [
  { name: 'Exchange Netflow',       pct: 65, color: '#00d68f', label: 'Outflow ↑',  labelColor: '#00d68f' },
  { name: 'Funding Rate Alignment', pct: 42, color: '#f0a030', label: 'Mixed',       labelColor: '#f0a030' },
  { name: 'Open Interest Trend',    pct: 55, color: '#4a8cf0', label: 'Rising',      labelColor: '#4a8cf0' },
  { name: 'Stablecoin Reserves',    pct: 70, color: '#00d68f', label: 'High ↑',     labelColor: '#00d68f' },
] as const;

const heatmapBars = [
  { h: 18, t: 'acc' }, { h: 12, t: 'neut' }, { h: 22, t: 'acc' },  { h: 8,  t: 'dist' },
  { h: 14, t: 'acc' }, { h: 30, t: 'acc'  }, { h: 20, t: 'dist' }, { h: 38, t: 'dist' },
  { h: 24, t: 'acc' }, { h: 46, t: 'acc'  }, { h: 32, t: 'dist' }, { h: 54, t: 'acc'  },
  { h: 42, t: 'acc' }, { h: 28, t: 'dist' }, { h: 36, t: 'acc'  }, { h: 60, t: 'acc'  },
  { h: 44, t: 'dist' },{ h: 50, t: 'acc'  }, { h: 38, t: 'acc'  }, { h: 22, t: 'dist' },
  { h: 30, t: 'acc' }, { h: 18, t: 'acc'  }, { h: 14, t: 'neut' }, { h: 24, t: 'acc'  },
] as const;

const hmColor = { acc: '#00d68f', dist: '#f03e5a', neut: '#3d4562' } as const;
const tagStyle = {
  deposit:  { bg: 'rgba(240,62,90,0.1)',   color: '#f03e5a' },
  withdraw: { bg: 'rgba(0,214,143,0.1)',   color: '#00d68f' },
  transfer: { bg: 'rgba(122,131,158,0.1)', color: '#7a839e' },
} as const;
const iconBg = {
  deposit:  'rgba(240,62,90,0.12)',
  withdraw: 'rgba(0,214,143,0.12)',
  transfer: 'rgba(122,131,158,0.12)',
} as const;

/* ── Whale Intelligence Component ────────────────────────────── */

function WhaleIntelligence() {
  return (
    <div style={{ marginTop: 48, borderTop: '1px solid #1c2235', paddingTop: 40 }}>
      <div style={{ marginBottom: 20 }}>
        <div className="font-syne" style={{ fontSize: 18, fontWeight: 700, color: '#dfe3f0', marginBottom: 4 }}>
          Whale Intelligence
        </div>
        <div className="font-mono-cc" style={{ fontSize: 11, color: '#3d4562' }}>
          Large wallet movements, exchange flows, and sentiment correlations — static preview · live data coming soon
        </div>
      </div>

      <div className="whale-intel-grid">

        {/* Alert Feed */}
        <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #1c2235', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="font-syne" style={{ fontSize: 13, fontWeight: 700, color: '#dfe3f0' }}>Whale Alerts</span>
            <span className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00d68f', display: 'inline-block', animation: 'livePulse 2s ease-in-out infinite' }} />
              Live Feed
            </span>
          </div>
          {whaleAlerts.map((a, i) => {
            const ts = tagStyle[a.type];
            const ib = iconBg[a.type];
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 20px', borderBottom: i < whaleAlerts.length - 1 ? '1px solid #1c2235' : undefined }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: ib, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>
                  {a.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="font-mono-cc" style={{ fontSize: 12, color: '#dfe3f0', fontWeight: 500 }}>
                    {a.amount} · <span style={{ color: '#7a839e' }}>{a.usd}</span>
                  </div>
                  <div className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562', marginTop: 2 }}>
                    <em style={{ fontStyle: 'normal', color: '#4a5275' }}>{a.from}</em>
                    {' → '}
                    <em style={{ fontStyle: 'normal', color: '#4a5275' }}>{a.to}</em>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                  <span className="font-mono-cc" style={{ fontSize: 9, padding: '2px 7px', borderRadius: 3, background: ts.bg, color: ts.color, letterSpacing: '0.3px' }}>
                    {a.tag}
                  </span>
                  <span className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562' }}>{a.ago}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Composite Whale Sentiment */}
          <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '20px' }}>
            <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 14 }}>
              Composite Whale Sentiment
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 16 }}>
              <span className="font-bebas" style={{ fontSize: 52, lineHeight: 1, color: '#00d68f' }}>62</span>
              <span className="font-syne" style={{ fontSize: 13, fontWeight: 600, color: '#00d68f' }}>Slight Accumulation</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {whaleFactors.map((f) => (
                <div key={f.name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                    <span className="font-mono-cc" style={{ fontSize: 9, color: '#4a5275' }}>{f.name}</span>
                    <span className="font-mono-cc" style={{ fontSize: 9, color: f.labelColor }}>{f.label}</span>
                  </div>
                  <div style={{ height: 3, borderRadius: 2, background: '#1c2235' }}>
                    <div style={{ height: 3, borderRadius: 2, width: `${f.pct}%`, background: f.color }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="font-mono-cc" style={{ fontSize: 10, color: '#4a5275', lineHeight: 1.6, marginTop: 16, paddingTop: 14, borderTop: '1px solid #1c2235' }}>
              Exchange outflows + high stablecoin reserves suggest dry powder building. OI rising with mixed funding = potential squeeze incoming, not pure directional conviction.
            </div>
          </div>

          {/* 24h Activity Heatmap */}
          <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '20px' }}>
            <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 4 }}>
              24h Activity Heatmap
            </div>
            <div className="font-mono-cc" style={{ fontSize: 9, color: '#2e3650', marginBottom: 14 }}>
              Whale transaction volume by hour · UTC
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 72 }}>
              {heatmapBars.map((b, i) => (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, justifyContent: 'flex-end' }}>
                  <div style={{ width: '100%', height: b.h, borderRadius: 2, background: hmColor[b.t], opacity: 0.75 }} />
                  {i % 6 === 0 && (
                    <div className="font-mono-cc" style={{ fontSize: 7, color: '#2e3650' }}>
                      {String(i).padStart(2, '0')}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 14, marginTop: 12 }}>
              {([['#00d68f', 'Accumulation'], ['#f03e5a', 'Distribution'], ['#3d4562', 'Neutral']] as const).map(([c, l]) => (
                <div key={l} className="font-mono-cc" style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 9, color: '#3d4562' }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: c }} />
                  {l}
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────── */

export default async function MarketPage() {
  // initialPrices now come from MarketPricesProvider in layout — only need snapshot for MCAP/F&G/BTC.D
  const snapshot = await getLatestSnapshot().catch(() => null);

  return (
    <AuthShell>
    <div style={{ background: '#08090c', minHeight: '100vh' }}>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">

        {/* ── Header ── */}
        <div className="flex items-baseline gap-4 mb-7">
          <h1 className="font-bebas tracking-[2px] text-[28px]" style={{ color: '#e8eaf0' }}>
            Live Market Dashboard
          </h1>
          <span
            className="font-mono-cc text-[11px] tracking-[1px] uppercase flex items-center gap-1.5"
            style={{ color: '#3d4562' }}
          >
            <span
              className="inline-block w-[6px] h-[6px] rounded-full"
              style={{ background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite' }}
            />
            Live
          </span>
        </div>

        {/* ── Client island: reads prices from MarketPricesProvider context ── */}
        <MarketLiveClient snapshot={snapshot} />

        {/* ── No data fallback ── */}
        {!snapshot && (
          <div style={{ borderRadius: 6, padding: '48px 24px', textAlign: 'center', border: '1px solid #1c2235', background: '#111520', marginTop: 16 }}>
            <p className="font-syne" style={{ fontSize: 14, color: '#6b7494' }}>No market data available yet.</p>
            <p style={{ marginTop: 8, fontSize: 12, color: '#3d4562', fontWeight: 300 }}>
              Start the FastAPI server and engine to populate data.
            </p>
          </div>
        )}

        {/* ── Whale Intelligence ── */}
        <WhaleIntelligence />

      </div>
    </div>
    </AuthShell>
  );
}
