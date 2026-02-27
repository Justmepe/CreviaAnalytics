import Link from 'next/link';
import ContentCard from '@/components/content/ContentCard';
import NewsTicker from '@/components/content/NewsTicker';
import VideoModal from '@/components/layout/VideoModal';
import HeroPricePanel from '@/components/home/HeroPricePanel';
import {
  getContentFeed, getLatestSnapshot,
  getCurrentRegime, formatLargeNumber, formatChange,
} from '@/lib/api';

export const revalidate = 60;

/* ── Helpers ─────────────────────────────────────────────────── */

function getEmbedUrl(url: string): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.hostname.includes('youtube.com') || u.hostname.includes('youtu.be')) {
      const videoId = u.searchParams.get('v') || u.pathname.split('/').pop();
      return `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
    }
    if (u.hostname.includes('loom.com')) {
      return `https://www.loom.com/embed/${u.pathname.split('/').pop()}`;
    }
  } catch { /* invalid URL */ }
  return null;
}

/* ── Sub-components ──────────────────────────────────────────── */

const features = [
  { icon: '🔬', title: 'Market Regime Detection', desc: 'Real-time classification of market conditions — Risk-Off, Risk-On, Accumulation, Distribution, Volatility Expansion. Know the environment before trading.', tag: 'Live', tagStyle: { background: 'rgba(0,214,143,0.08)', color: '#00d68f', border: '1px solid rgba(0,214,143,0.2)' }, accent: '#00d68f' },
  { icon: '⚡', title: 'AI Trade Setups',          desc: 'Claude-generated entry zones, stop-loss, take-profit, and risk/reward for all 16 tracked assets — aligned with the live market regime.', tag: 'Pro', tagStyle: { background: 'rgba(240,160,48,0.08)', color: '#f0a030', border: '1px solid rgba(240,160,48,0.2)' }, accent: '#f0a030' },
  { icon: '🐋', title: 'Whale Intelligence',        desc: 'Large wallet movements, exchange netflows, funding rate spikes, and composite sentiment score — updated as smart money moves.', tag: 'Pro', tagStyle: { background: 'rgba(240,160,48,0.08)', color: '#f0a030', border: '1px solid rgba(240,160,48,0.2)' }, accent: '#f0a030' },
  { icon: '🎯', title: 'Opportunity Scanner',       desc: 'Composite scoring across confidence, R/R ratio, regime alignment, and momentum. Ranked list of actionable setups across all sectors.', tag: 'Pro', tagStyle: { background: 'rgba(240,160,48,0.08)', color: '#f0a030', border: '1px solid rgba(240,160,48,0.2)' }, accent: '#f0a030' },
  { icon: '⚖️', title: 'Risk Calculator',           desc: 'Position sizing, risk per trade, leverage, and portfolio exposure — always free. Size correctly regardless of your plan.', tag: 'Free', tagStyle: { background: 'rgba(74,140,240,0.08)', color: '#4a8cf0', border: '1px solid rgba(74,140,240,0.2)' }, accent: '#4a8cf0' },
  { icon: '📡', title: 'Analysis Feed',             desc: 'Daily threads, market memos, and risk alerts across BTC, ETH, DeFi, Privacy, and Memecoins. Pro sees live. Free sees 6h later.', tag: 'Free after 6h', tagStyle: { background: 'rgba(74,140,240,0.08)', color: '#4a8cf0', border: '1px solid rgba(74,140,240,0.2)' }, accent: '#4a8cf0' },
];

const howSteps = [
  { num: '01', title: 'Engine collects live data', desc: 'Prices, derivatives, funding rates, liquidations, stablecoin flows, on-chain signals — pulled from Binance, CoinGecko, Coinglass, and more.' },
  { num: '02', title: 'Regime is detected',        desc: 'Five market regime patterns evaluated against weighted signal conditions. Confidence scored, regime classified, context provided.' },
  { num: '03', title: 'Claude generates intelligence', desc: 'AI trade setups, threads, memos, and opportunity scans generated in-context with the live regime. Not generic TA — regime-aware output.' },
  { num: '04', title: 'You act with confidence',   desc: 'Pro members see everything live. Free users see analysis 6 hours later. Risk calculator available to everyone, always.' },
];

const instruments = [
  { label: 'Regime', value: 'RISK-OFF', valueColor: '#f03e5a', sub: 'Active 5h 21m', fillColor: '#f03e5a', fillPct: 60 },
  { label: 'Confidence', value: '60%', valueColor: '#f0a030', sub: '78% historical', fillColor: '#f0a030', fillPct: 60 },
  { label: 'Fear & Greed', value: '11', valueColor: '#f03e5a', sub: 'Extreme Fear', fillColor: '#f03e5a', fillPct: 11 },
  { label: 'BTC Dominance', value: '56.2%', valueColor: '#f0a030', sub: 'Elevated', fillColor: '#f0a030', fillPct: 56.2 },
  { label: 'Funding Rate', value: '−0.009%', valueColor: '#4a8cf0', sub: 'Shorts paying', fillColor: '#4a8cf0', fillPct: 40, span2: false },
  { label: 'Opportunities', value: '3', valueColor: '#00d68f', sub: 'High conviction', fillColor: '#00d68f', fillPct: 75, span2: false },
];

/* ── Page ────────────────────────────────────────────────────── */

export default async function HomePage() {
  const [snapshot, content, newsItems, regime] = await Promise.allSettled([
    getLatestSnapshot(),
    getContentFeed({ page_size: 6 }),
    getContentFeed({ content_type: 'news_tweet', page_size: 10 }),
    getCurrentRegime(),
  ]).then(([s, c, n, r]) => [
    s.status === 'fulfilled' ? s.value : null,
    c.status === 'fulfilled' ? c.value : null,
    n.status === 'fulfilled' ? n.value : null,
    r.status === 'fulfilled' ? r.value : null,
  ] as const);

  const rawVideoUrl = process.env.NEXT_PUBLIC_DEMO_VIDEO_URL || '';
  const embedUrl = getEmbedUrl(rawVideoUrl);

  // Regime for mini card on hero right
  const regimeData = regime as Awaited<ReturnType<typeof getCurrentRegime>> | null;
  const regimeColor = regimeData?.color ?? '#3d4562';
  const regimeAccent =
    regimeColor === 'red'    ? '#f03e5a' :
    regimeColor === 'green'  ? '#00d68f' :
    regimeColor === 'amber'  ? '#f0a030' :
    regimeColor === 'blue'   ? '#4a8cf0' :
    '#3d4562';

  return (
    <div className="grain-overlay" style={{ background: '#07080a', minHeight: '100vh' }}>

      {/* ── Live News Ticker ── */}
      <NewsTicker initialNews={(newsItems as { items: Parameters<typeof NewsTicker>[0]['initialNews'] } | null)?.items ?? []} />

      {/* ══ HERO ══ */}
      <section
        className="hero-grid-bg hero-section"
        style={{ alignItems: 'center', position: 'relative', overflow: 'hidden' }}
      >
        {/* Glow orb */}
        <div style={{ position: 'absolute', width: 600, height: 600, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,214,143,0.06) 0%, transparent 70%)', right: -100, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />

        {/* Left: Brand + Headline */}
        <div className="animate-fade-up hero-left" style={{ position: 'relative', zIndex: 2 }}>
          <div
            className="font-mono-cc"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#00d68f', background: 'rgba(0,214,143,0.07)', border: '1px solid rgba(0,214,143,0.2)', padding: '5px 12px', borderRadius: 20, marginBottom: 28 }}
          >
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite' }} />
            Live market intelligence
          </div>

          {/* Typographic brand */}
          <div className="font-bebas hero-brand" style={{ fontSize: 80, lineHeight: 0.92, letterSpacing: 2, marginBottom: 8, color: '#e2e6f0' }}>
            <span style={{ display: 'block' }}>CREO</span>
            <span style={{ display: 'block', WebkitTextStroke: '1px #00d68f', color: 'transparent', letterSpacing: 12 }}>VIA</span>
            <span style={{ display: 'block', fontSize: 52, color: '#3d4562', letterSpacing: 8 }}>COCKPIT</span>
          </div>

          <h1 className="font-serif-cc hero-h1" style={{ fontSize: 40, lineHeight: 1.15, color: '#e2e6f0', marginBottom: 20, letterSpacing: -0.5 }}>
            We create the path.<br />
            <em style={{ fontStyle: 'italic', color: '#00d68f' }}>You control the outcome.</em>
          </h1>

          <p style={{ fontSize: 15, fontWeight: 300, color: '#7a839e', lineHeight: 1.7, maxWidth: 440, marginBottom: 28 }}>
            Real-time regime detection, AI trade setups, whale intelligence, and risk-aware position sizing for 16+ assets. No noise — just the signal that tells you what to do next.
          </p>

          {/* Latin etymology tags */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 32 }}>
            {[
              { word: 'CREO', mean: '— I create', bg: 'rgba(0,214,143,0.06)', border: 'rgba(0,214,143,0.15)' },
              { word: 'VIA',  mean: '— the way',  bg: 'rgba(74,140,240,0.06)', border: 'rgba(74,140,240,0.15)' },
              { word: 'COCKPIT', mean: '— command', bg: 'rgba(240,160,48,0.06)', border: 'rgba(240,160,48,0.15)' },
            ].map((t) => (
              <span
                key={t.word}
                className="font-mono-cc"
                style={{ fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '4px 10px', borderRadius: 3, display: 'flex', alignItems: 'center', gap: 6, background: t.bg, border: `1px solid ${t.border}` }}
              >
                <span style={{ color: '#e2e6f0', fontWeight: 500 }}>{t.word}</span>
                <span style={{ color: '#3d4562' }}>{t.mean}</span>
              </span>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Link
              href="/pricing"
              className="font-mono-cc"
              style={{ fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#00d68f', border: 'none', padding: '14px 28px', borderRadius: 5, fontWeight: 500, boxShadow: '0 0 30px rgba(0,214,143,0.25)', textDecoration: 'none' }}
            >
              Get Early Access →
            </Link>
            <VideoModal embedUrl={embedUrl ?? undefined} />
          </div>

          {/* Social proof */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 24 }}>
            <div style={{ display: 'flex' }}>
              {[
                { initials: 'JK', grad: 'linear-gradient(135deg,#f7931a,#e07c10)' },
                { initials: 'MR', grad: 'linear-gradient(135deg,#627eea,#4f67c8)' },
                { initials: 'TA', grad: 'linear-gradient(135deg,#00d68f,#00a870)' },
                { initials: 'SL', grad: 'linear-gradient(135deg,#f03e5a,#c02040)' },
              ].map((a, i) => (
                <div
                  key={a.initials}
                  style={{ width: 26, height: 26, borderRadius: '50%', border: '2px solid #07080a', marginLeft: i > 0 ? -6 : 0, fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 500, color: '#08090c', display: 'flex', alignItems: 'center', justifyContent: 'center', background: a.grad }}
                >
                  {a.initials}
                </div>
              ))}
            </div>
            <span className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562', letterSpacing: '0.3px' }}>
              <strong style={{ color: '#7a839e' }}>340+ traders</strong> on the waitlist
            </span>
          </div>
        </div>

        {/* Right: Live preview panel */}
        <div className="hero-right" style={{ position: 'relative', zIndex: 2 }}>
          <div
            className="font-mono-cc"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', padding: '6px 0' }}
          >
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite' }} />
            Live preview
          </div>

          {/* Mini regime card */}
          <div style={{ background: '#111520', border: `1px solid #242c42`, borderLeft: `3px solid ${regimeAccent}`, borderRadius: 8, padding: '18px 20px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse at top left, ${regimeAccent}0d 0%, transparent 60%)`, pointerEvents: 'none' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 4 }}>Market Regime Detected</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    className="font-mono-cc"
                    style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: regimeAccent, background: `${regimeAccent}1a`, border: `1px solid ${regimeAccent}40`, padding: '2px 9px', borderRadius: 3 }}
                  >
                    {regimeData?.regime_name?.replace(/_/g, '-') ?? 'NO DATA'}
                  </span>
                  <span className="font-mono-cc" style={{ fontSize: 9, color: '#3d4562' }}>
                    {regimeData ? 'Active' : 'Engine starting'}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 16, textAlign: 'right' }}>
                <div>
                  <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562' }}>Conf.</div>
                  <div className="font-bebas" style={{ fontSize: 28, lineHeight: 1, color: '#f0a030' }}>
                    {regimeData?.confidence ? `${Math.round(regimeData.confidence)}%` : '--'}
                  </div>
                </div>
              </div>
            </div>
            {regimeData?.trader_action && (
              <div className="font-mono-cc" style={{ fontSize: 10, color: regimeAccent, background: `${regimeAccent}0f`, padding: '8px 12px', borderRadius: 4, border: `1px solid ${regimeAccent}26` }}>
                {regimeData.trader_action}
              </div>
            )}
            {!regimeData && (
              <div className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562', padding: '8px 12px', borderRadius: 4, border: '1px solid #1c2235' }}>
                Start the engine to detect live market regime.
              </div>
            )}
          </div>

          {/* Mini prices panel — live via shared WebSocket context */}
          <HeroPricePanel />
        </div>
      </section>

      {/* ══ BRAND STORY ══ */}
      <section className="brand-story-grid">
        <div style={{ position: 'absolute', top: 0, left: '33.33%', width: 1, height: '100%', background: '#1c2235' }} />
        <div style={{ position: 'absolute', top: 0, left: '66.66%', width: 1, height: '100%', background: '#1c2235' }} />
        {[
          { latin: 'CREO',    translation: 'I create',  color: '#00d68f', desc: 'The engine doesn\'t retrieve data — it creates intelligence from raw signals. Every output is synthesized, contextualized, regime-aware.' },
          { latin: 'VIA',     translation: 'The way',   color: '#4a8cf0', desc: 'Not a dashboard of numbers. A path through the noise. From regime detection to trade setup to position sizing — the way is lit.' },
          { latin: 'COCKPIT', translation: 'Command',   color: '#f0a030', desc: 'The cockpit is where decisions are made under pressure. Every instrument in view. Everything needed to command the trade.' },
        ].map((b) => (
          <div key={b.latin} className="brand-story-item">
            <div className="font-bebas" style={{ fontSize: 52, lineHeight: 1, color: '#e2e6f0', marginBottom: 4, letterSpacing: 2 }}>{b.latin}</div>
            <div className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: b.color, marginBottom: 16 }}>{b.translation}</div>
            <p className="font-serif-cc" style={{ fontSize: 17, lineHeight: 1.6, color: '#7a839e', fontStyle: 'italic' }}>{b.desc}</p>
          </div>
        ))}
      </section>

      {/* ══ FEATURES GRID ══ */}
      <section className="features-section">
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <span className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: '#00d68f', display: 'block', marginBottom: 14 }}>The Intelligence Platform</span>
          <h2 className="font-serif-cc" style={{ fontSize: 40, color: '#e2e6f0', lineHeight: 1.2, letterSpacing: -0.5 }}>
            Everything a trader needs.<br /><em style={{ fontStyle: 'italic', color: '#00d68f' }}>Nothing they don&apos;t.</em>
          </h2>
        </div>

        <div className="features-grid">
          {features.map((f) => (
            <div
              key={f.title}
              className="group"
              style={{ background: '#0d0f14', padding: '32px 28px', position: 'relative', overflow: 'hidden', transition: 'background 0.2s' }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: f.accent, opacity: 0 }} className="group-hover:opacity-100" />
              <span style={{ fontSize: 24, marginBottom: 14, display: 'block' }}>{f.icon}</span>
              <div className="font-syne" style={{ fontSize: 15, fontWeight: 700, color: '#e2e6f0', marginBottom: 8, letterSpacing: -0.2 }}>{f.title}</div>
              <p style={{ fontSize: 13, color: '#7a839e', lineHeight: 1.6 }}>{f.desc}</p>
              <span
                className="font-mono-cc"
                style={{ display: 'inline-block', marginTop: 14, fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '3px 8px', borderRadius: 3, ...f.tagStyle }}
              >
                {f.tag}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ══ HOW IT WORKS ══ */}
      <section className="how-section">
        <div>
          <span className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: '#00d68f', display: 'block', marginBottom: 14 }}>Under the hood</span>
          <h2 className="font-serif-cc" style={{ fontSize: 38, color: '#e2e6f0', lineHeight: 1.2, letterSpacing: -0.5, marginBottom: 16 }}>
            Built for the market,<br /><em style={{ fontStyle: 'italic', color: '#00d68f' }}>not for the feed.</em>
          </h2>
          <p style={{ fontSize: 14, color: '#7a839e', lineHeight: 1.7, marginBottom: 36 }}>
            The cockpit engine runs on a continuous cycle — collecting, classifying, generating. Every output is timed to the market, not a content calendar.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {howSteps.map((s, i) => (
              <div key={s.num} style={{ display: 'grid', gridTemplateColumns: '40px 1fr', gap: 16, padding: '20px 0', borderBottom: i < howSteps.length - 1 ? '1px solid #1c2235' : 'none', alignItems: 'start' }}>
                <div className="font-bebas" style={{ fontSize: 28, color: '#3d4562', lineHeight: 1, paddingTop: 2 }}>{s.num}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#dfe3f0', marginBottom: 4 }}>{s.title}</div>
                  <div style={{ fontSize: 12, color: '#3d4562', lineHeight: 1.6 }}>{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Instrument panel visual */}
        <div className="instrument-panel" style={{ background: '#111520', border: '1px solid #242c42', borderRadius: 10, padding: 24, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center top, rgba(0,214,143,0.04) 0%, transparent 60%)', pointerEvents: 'none' }} />
          {instruments.map((inst) => (
            <div
              key={inst.label}
              style={{ background: '#0d0f14', border: '1px solid #1c2235', borderRadius: 6, padding: 14, display: 'flex', flexDirection: 'column', gap: 6, ...(inst.span2 ? { gridColumn: 'span 2' } : {}) }}
            >
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562' }}>{inst.label}</div>
              <div className="font-bebas" style={{ fontSize: 32, lineHeight: 1, color: inst.valueColor }}>{inst.value}</div>
              <div className="font-mono-cc" style={{ fontSize: 9, color: '#3d4562' }}>{inst.sub}</div>
              <div style={{ height: 3, background: '#1c2235', borderRadius: 2, overflow: 'hidden', marginTop: 4 }}>
                <div style={{ height: '100%', borderRadius: 2, background: inst.fillColor, width: `${inst.fillPct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>


      {/* ══ LATEST ANALYSIS ══ */}
      {(content as Awaited<ReturnType<typeof getContentFeed>> | null)?.items && (content as Awaited<ReturnType<typeof getContentFeed>>).items.length > 0 && (
        <section className="latest-section">
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
              <h2 className="font-bebas" style={{ fontSize: 24, letterSpacing: 2, color: '#e8eaf0' }}>Latest Analysis</h2>
              <span className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#f0a030', animation: 'livePulse 2s ease-in-out infinite' }} />
                Pro · Live &nbsp;|&nbsp; Free · 6h delay
              </span>
            </div>
            <Link href="/analysis" className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#3d4562', textDecoration: 'none' }}>
              View all →
            </Link>
          </div>
          <div className="analysis-grid">
            {(content as Awaited<ReturnType<typeof getContentFeed>>).items.slice(0, 6).map((post) => (
              <ContentCard key={post.id} post={post} />
            ))}
          </div>
        </section>
      )}

      {/* ══ WAITLIST CTA ══ */}
      <div className="cta-wrapper">
        <div style={{ background: '#111520', border: '1px solid #242c42', borderRadius: 10, padding: '60px 40px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(0,214,143,0.07) 0%, transparent 70%)', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: 0, left: '20%', right: '20%', height: 1, background: 'linear-gradient(90deg, transparent, #00d68f, transparent)' }} />

          <span className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: '#00d68f', display: 'block', marginBottom: 14 }}>Limited early access</span>
          <h2 className="font-serif-cc" style={{ fontSize: 38, color: '#e2e6f0', lineHeight: 1.2, letterSpacing: -0.5, marginBottom: 12 }}>
            The cockpit is ready.<br /><em style={{ fontStyle: 'italic', color: '#00d68f' }}>Are you?</em>
          </h2>
          <p style={{ fontSize: 14, color: '#7a839e', maxWidth: 480, margin: '0 auto 32px', lineHeight: 1.7 }}>
            Regime detection, AI trade setups, opportunity scanner, and risk calculator — all live. Early access members get Pro features free during beta.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 16 }}>
            <Link
              href="/pricing"
              className="font-mono-cc"
              style={{ padding: '14px 32px', borderRadius: 5, color: '#08090c', background: '#00d68f', fontWeight: 500, fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase', textDecoration: 'none', boxShadow: '0 0 24px rgba(0,214,143,0.25)' }}
            >
              Join the Waitlist →
            </Link>
            <Link
              href="/tools/risk-calculator"
              className="font-mono-cc"
              style={{ padding: '13px 24px', borderRadius: 5, color: '#7a839e', background: 'none', border: '1px solid #242c42', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase', textDecoration: 'none' }}
            >
              Try Risk Calc Free
            </Link>
          </div>
          <p className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562' }}>
            Already have an account?{' '}
            <Link href="/auth/login" style={{ color: '#00d68f', textDecoration: 'none' }}>Sign in →</Link>
          </p>
        </div>
      </div>

    </div>
  );
}
