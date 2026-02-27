import { getCurrentRegime, getLatestCorrelations, getSmartMoneySignals, getLatestTradeSetups, getLatestOpportunities, getLatestSnapshot } from '@/lib/api';
import MarketRegimeIndicator from '@/components/intelligence/MarketRegimeIndicator';
import CorrelationMatrix from '@/components/intelligence/CorrelationMatrix';
import SmartMoneyTracker from '@/components/intelligence/SmartMoneyTracker';
import TradeSetupCard from '@/components/intelligence/TradeSetupCard';
import OpportunityCard from '@/components/intelligence/OpportunityCard';
import ProGate from '@/components/auth/ProGate';
import Link from 'next/link';
import type { Metadata } from 'next';

export const revalidate = 60;

export const metadata: Metadata = {
  title: 'Intelligence',
  description: 'Market regime detection, correlation analysis, smart money tracking, and trading intelligence.',
};

/* ── Ghost rows shown blurred behind Pro locks ──────────────── */

function OpportunityGhostRows() {
  const rows = [
    { ticker: 'BTC', grad: 'linear-gradient(135deg,#f7931a,#e87d16)', name: 'Bitcoin',  sub: 'Breakout Setup · 4H',    price: '$68,296', change: '+5.07%', up: true,  signal: 'LONG',  sc: '#00d68f', sb: 'rgba(0,214,143,0.1)',  border: 'rgba(0,214,143,0.25)' },
    { ticker: 'ETH', grad: 'linear-gradient(135deg,#627eea,#4f67c8)', name: 'Ethereum', sub: 'Support Retest · 1D',   price: '$2,058',  change: '−2.1%',  up: false, signal: 'WATCH', sc: '#f0a030', sb: 'rgba(240,160,48,0.1)', border: 'rgba(240,160,48,0.25)' },
    { ticker: 'SOL', grad: 'linear-gradient(135deg,#9945ff,#14f195)', name: 'Solana',   sub: 'Momentum Fade · 4H',   price: '$87.34',  change: '−1.4%',  up: false, signal: 'SHORT', sc: '#f03e5a', sb: 'rgba(240,62,90,0.1)',  border: 'rgba(240,62,90,0.25)' },
  ];
  return (
    <div style={{ borderRadius: 6, overflow: 'hidden', background: '#111520', border: '1px solid #1c2235' }}>
      {rows.map((r) => (
        <div
          key={r.ticker}
          style={{ display: 'grid', gridTemplateColumns: '48px 1fr auto auto auto', alignItems: 'center', gap: 12, padding: '14px 18px', borderBottom: '1px solid #1c2235' }}
        >
          <div style={{ width: 36, height: 36, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500, color: '#08090c', background: r.grad, flexShrink: 0 }}>
            {r.ticker}
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>{r.name}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#3d4562', marginTop: 2 }}>{r.sub}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500, color: '#dfe3f0', textAlign: 'right' }}>{r.price}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#3d4562', textAlign: 'right' }}>Entry zone</div>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: r.up ? '#00d68f' : '#f03e5a', textAlign: 'right', minWidth: 56 }}>{r.change}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '3px 8px', borderRadius: 3, minWidth: 72, textAlign: 'center', background: r.sb, color: r.sc, border: `1px solid ${r.border}` }}>{r.signal}</span>
        </div>
      ))}
    </div>
  );
}

function SetupGhostRows() {
  const setups = [
    { dir: 'LONG',  dc: '#00d68f', db: 'rgba(0,214,143,0.1)', asset: 'BTC / USDT', entry: '$66,800', tp: '$72,500', sl: '$64,200', rr: '2.8R' },
    { dir: 'SHORT', dc: '#f03e5a', db: 'rgba(240,62,90,0.1)',  asset: 'ETH / USDT', entry: '$2,100',  tp: '$1,880',  sl: '$2,200',  rr: '2.2R' },
    { dir: 'LONG',  dc: '#00d68f', db: 'rgba(0,214,143,0.1)', asset: 'SOL / USDT', entry: '$82.00',  tp: '$97.50',  sl: '$77.00',  rr: '3.1R' },
  ];
  return (
    <div style={{ borderRadius: 6, overflow: 'hidden', background: '#111520', border: '1px solid #1c2235' }}>
      {setups.map((s, i) => (
        <div
          key={i}
          style={{ display: 'grid', gridTemplateColumns: '44px 1fr auto', alignItems: 'center', gap: 14, padding: '14px 18px', borderBottom: '1px solid #1c2235' }}
        >
          <div style={{ fontFamily: 'var(--font-syne)', fontSize: 11, fontWeight: 700, letterSpacing: '0.5px', padding: '5px 8px', borderRadius: 4, textAlign: 'center', background: s.db, color: s.dc }}>
            {s.dir}
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>{s.asset}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#3d4562', marginTop: 3, display: 'flex', gap: 12 }}>
              <span>Entry <span style={{ color: '#7a839e' }}>{s.entry}</span></span>
              <span>TP <span style={{ color: '#7a839e' }}>{s.tp}</span></span>
              <span>SL <span style={{ color: '#7a839e' }}>{s.sl}</span></span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500, color: '#f0a030' }}>{s.rr}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#3d4562', textTransform: 'uppercase', letterSpacing: '0.8px', marginTop: 2 }}>Risk/Reward</div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Sidebar widgets ─────────────────────────────────────────── */

function FearGreedCard({ value, label }: { value: number | null; label: string | null }) {
  const score = value ?? 50;
  const displayLabel = label ?? 'Neutral';

  const color =
    score <= 25 ? '#f03e5a' :
    score <= 45 ? '#f0a030' :
    score <= 55 ? '#7a839e' :
    score <= 75 ? '#4a8cf0' :
    '#00d68f';

  const note =
    score <= 20 ? 'Historically a buying zone. Often signals capitulation — consider DCA entry.' :
    score <= 40 ? 'Fear in the market. Caution recommended but watch for reversal signals.' :
    score <= 60 ? 'Market neutral. No strong directional bias — range-bound conditions.' :
    score <= 80 ? 'Greed taking over. Momentum strong but watch for mean reversion.' :
    'Extreme greed. Historically precedes corrections — consider taking profits.';

  return (
    <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: 18 }}>
      <div style={{ textAlign: 'center', marginBottom: 12 }}>
        <span style={{ fontFamily: 'var(--font-syne)', fontSize: 48, fontWeight: 800, lineHeight: 1, color, display: 'block' }}>
          {score}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color, marginTop: 4, display: 'block' }}>
          {displayLabel}
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'linear-gradient(90deg, #00d68f 0%, #f0a030 50%, #f03e5a 100%)', position: 'relative', margin: '12px 0' }}>
        <div style={{ position: 'absolute', top: '50%', left: `${score}%`, transform: 'translate(-50%, -50%)', width: 12, height: 12, background: '#dfe3f0', borderRadius: '50%', border: '2px solid #08090c' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 9, color: '#3d4562', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
        <span>Fear</span>
        <span>Neutral</span>
        <span>Greed</span>
      </div>
      <p style={{ fontSize: 12, color: '#7a839e', lineHeight: 1.5, textAlign: 'center', marginTop: 12 }}>
        {note}
      </p>
    </div>
  );
}

function DominanceCard({ btcDominance }: { btcDominance: number | null }) {
  const btc = btcDominance ?? 0;
  const eth = +(btc * 0.31).toFixed(1);
  const stables = 9.0;
  const others = Math.max(0, +(100 - btc - eth - stables).toFixed(1));

  const bars = [
    { label: 'Bitcoin',     pct: btc,     color: '#f0a030' },
    { label: 'Ethereum',    pct: eth,     color: '#4a8cf0' },
    { label: 'Stablecoins', pct: stables, color: '#3d4562' },
    { label: 'Others',      pct: others,  color: '#242c42' },
  ];

  const note =
    btc > 55 ? 'BTC dominance elevated. Risk-off rotation in progress — alts losing relative share.' :
    btc > 50 ? 'BTC dominance stable. Market balanced between BTC and altcoin exposure.' :
    'BTC dominance declining. Alt season conditions may be forming.';

  if (!btcDominance) return null;

  return (
    <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '16px 18px' }}>
      {bars.map((b, i) => (
        <div key={b.label} style={{ marginTop: i > 0 ? 10 : 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontFamily: 'var(--font-syne)', fontSize: 12, fontWeight: 600, color: '#dfe3f0' }}>{b.label}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500, color: '#7a839e' }}>{b.pct.toFixed(1)}%</span>
          </div>
          <div style={{ height: 4, background: '#1c2235', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', background: b.color, borderRadius: 2, width: `${b.pct}%` }} />
          </div>
        </div>
      ))}
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#3d4562', marginTop: 12, lineHeight: 1.5 }}>
        {note}
      </p>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────── */

export default async function IntelligencePage() {
  const [regimeRes, corrRes, smartRes, setupsRes, oppsRes, snapshotRes] = await Promise.allSettled([
    getCurrentRegime(),
    getLatestCorrelations(24),
    getSmartMoneySignals(6),
    getLatestTradeSetups(undefined, 4),
    getLatestOpportunities(),
    getLatestSnapshot(),
  ]);

  const regime      = regimeRes.status      === 'fulfilled' ? regimeRes.value      : null;
  const correlations = corrRes.status       === 'fulfilled' ? corrRes.value        : null;
  const smartMoney  = smartRes.status       === 'fulfilled' ? smartRes.value       : null;
  const tradeSetups = setupsRes.status      === 'fulfilled' ? setupsRes.value      : [];
  const opportunities = oppsRes.status      === 'fulfilled' ? oppsRes.value        : null;
  const snapshot    = snapshotRes.status    === 'fulfilled' ? snapshotRes.value    : null;

  const topOpportunities = opportunities?.opportunities?.slice(0, 3) ?? [];
  const smartMoneyData = smartMoney ?? { signals: [], signal_count: 0, net_sentiment: 'neutral', aggregate_interpretation: null };

  const sectionLink: React.CSSProperties = {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    letterSpacing: '0.8px',
    textTransform: 'uppercase',
    color: '#3d4562',
    textDecoration: 'none',
  };

  return (
    <div style={{ background: '#08090c', minHeight: '100vh' }}>
      <div
        className="mx-auto"
        style={{ display: 'grid', gridTemplateColumns: '1fr 320px', maxWidth: 1280 }}
      >

        {/* ── Main Column ── */}
        <div style={{ borderRight: '1px solid #1c2235', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Regime */}
          {regime ? (
            <MarketRegimeIndicator regime={regime} />
          ) : (
            <div style={{ background: '#111520', border: '1px solid #1c2235', borderLeft: '3px solid #3d4562', borderRadius: 6, padding: '22px 24px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562' }}>Market Regime Detected</span>
              <div style={{ fontFamily: 'var(--font-syne)', fontSize: 20, fontWeight: 700, color: '#dfe3f0', marginTop: 6 }}>No Data Yet</div>
              <p style={{ fontSize: 13, color: '#7a839e', marginTop: 8, fontWeight: 300 }}>Start the engine to begin detecting market regimes.</p>
            </div>
          )}

          {/* Correlation Matrix */}
          {correlations ? (
            <CorrelationMatrix data={correlations} />
          ) : (
            <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '18px 20px' }}>
              <span style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>Correlation Matrix</span>
              <p style={{ fontSize: 12, color: '#3d4562', marginTop: 8, fontStyle: 'italic' }}>No correlation data yet. Engine needs historical metrics first.</p>
            </div>
          )}

          {/* Top Opportunities */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>Top Opportunities</span>
              <Link href="/intelligence/scanner" style={sectionLink}>Full Scanner →</Link>
            </div>
            <ProGate featureName="Opportunity Scanner" minTier="pro" ghostRows={<OpportunityGhostRows />}>
              {topOpportunities.length > 0 ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  {topOpportunities.map((opp, i) => (
                    <OpportunityCard key={`${opp.asset}-${opp.direction}`} opportunity={opp} rank={i + 1} />
                  ))}
                </div>
              ) : (
                <OpportunityGhostRows />
              )}
            </ProGate>
          </div>

          {/* Trade Setups */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>Latest Trade Setups</span>
              <Link href="/intelligence/setups" style={sectionLink}>View All →</Link>
            </div>
            <ProGate featureName="AI Trade Setups" minTier="pro" ghostRows={<SetupGhostRows />}>
              {tradeSetups.length > 0 ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  {tradeSetups.map((setup) => (
                    <TradeSetupCard key={setup.id} setup={setup} />
                  ))}
                </div>
              ) : (
                <SetupGhostRows />
              )}
            </ProGate>
          </div>

        </div>

        {/* ── Sidebar ── */}
        <div style={{ background: '#0d0f14', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Fear & Greed */}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 10 }}>
              Fear &amp; Greed Index
            </div>
            <FearGreedCard value={snapshot?.fear_greed_index ?? null} label={snapshot?.fear_greed_label ?? null} />
          </div>

          {/* Smart Money */}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 10 }}>
              Smart Money Activity
            </div>
            <SmartMoneyTracker data={smartMoneyData} />
          </div>

          {/* Market Dominance */}
          {snapshot?.btc_dominance ? (
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 10 }}>
                Market Dominance
              </div>
              <DominanceCard btcDominance={snapshot.btc_dominance} />
            </div>
          ) : null}

        </div>

      </div>
    </div>
  );
}
