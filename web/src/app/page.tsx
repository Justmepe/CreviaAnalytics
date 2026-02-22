import Link from 'next/link';
import PriceRow from '@/components/market/PriceRow';
import ContentCard from '@/components/content/ContentCard';
import NewsTicker from '@/components/content/NewsTicker';
import MarketRegimeIndicator from '@/components/intelligence/MarketRegimeIndicator';
import IntelligentMetricCard from '@/components/intelligence/IntelligentMetricCard';
import { getContentFeed, getLatestSnapshot, getLatestPrices, getCurrentRegime, formatLargeNumber, formatPrice, formatChange } from '@/lib/api';

export const revalidate = 60;

function getFearGreedContext(index: number | null | undefined): { context: string; action?: string; severity?: 'low' | 'medium' | 'high' } {
  if (index == null) return { context: '' };
  if (index <= 20) return {
    context: 'Extreme fear often signals capitulation. Historically a buying zone.',
    action: 'Consider DCA entry',
    severity: 'medium',
  };
  if (index <= 35) return {
    context: 'Fear is elevated. Smart money often accumulates at these levels.',
    action: 'Watch for reversal signals',
    severity: 'low',
  };
  if (index <= 55) return { context: 'Sentiment is balanced. No extreme positioning either way.' };
  if (index <= 75) return {
    context: 'Greed building. Markets can stay greedy longer than expected.',
  };
  return {
    context: 'Extreme greed. Historically precedes corrections within 1-2 weeks.',
    action: 'Consider taking profits',
    severity: 'high',
  };
}

function getBtcDominanceContext(dom: number | null | undefined): { context: string; action?: string; severity?: 'low' | 'medium' | 'high' } {
  if (dom == null) return { context: '' };
  if (dom > 58) return {
    context: 'Very high BTC dominance. Capital in safe-haven mode. Alts underperforming.',
    action: 'Favor BTC over alts',
    severity: 'medium',
  };
  if (dom > 54) return {
    context: 'BTC dominance elevated. Risk-off rotation in progress.',
  };
  if (dom > 48) return { context: 'BTC dominance in normal range. No strong rotation signal.' };
  return {
    context: 'Low BTC dominance. Alt season conditions. Capital rotating into altcoins.',
    action: 'Look for alt setups',
    severity: 'low',
  };
}

// Set NEXT_PUBLIC_DEMO_VIDEO_URL in Vercel env vars once video is ready.
// Supports YouTube (youtube.com/watch?v=ID) and Loom (loom.com/share/ID) URLs.
function getEmbedUrl(url: string): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.hostname.includes('youtube.com') || u.hostname.includes('youtu.be')) {
      const videoId = u.searchParams.get('v') || u.pathname.split('/').pop();
      return `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
    }
    if (u.hostname.includes('loom.com')) {
      const videoId = u.pathname.split('/').pop();
      return `https://www.loom.com/embed/${videoId}`;
    }
  } catch {
    // invalid URL
  }
  return null;
}

function DemoVideoSection() {
  const rawUrl = process.env.NEXT_PUBLIC_DEMO_VIDEO_URL || '';
  const embedUrl = getEmbedUrl(rawUrl);

  return (
    <section className="border-b border-zinc-800 bg-zinc-950">
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 sm:py-20">
        <div className="text-center mb-10">
          <p className="text-sm font-semibold uppercase tracking-widest text-emerald-500 mb-3">
            See it in action
          </p>
          <h2 className="text-3xl font-bold text-white sm:text-4xl">
            Crypto intelligence that actually tells you what to do
          </h2>
          <p className="mt-3 text-zinc-400 max-w-2xl mx-auto">
            Watch how Crevia detects market regimes, surfaces smart money signals, and generates
            trade setups in real time — no noise, just signal.
          </p>
        </div>

        {embedUrl ? (
          <div className="relative mx-auto overflow-hidden rounded-2xl border border-zinc-700 shadow-2xl shadow-emerald-950/20"
               style={{ paddingBottom: '56.25%', height: 0 }}>
            <iframe
              src={embedUrl}
              className="absolute inset-0 h-full w-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        ) : (
          /* Placeholder shown until NEXT_PUBLIC_DEMO_VIDEO_URL is set */
          <div className="relative mx-auto overflow-hidden rounded-2xl border border-zinc-700 bg-zinc-900/50"
               style={{ paddingBottom: '56.25%', height: 0 }}>
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-8 text-center">
              {/* Mock screen lines */}
              <div className="absolute inset-0 opacity-5 pointer-events-none overflow-hidden">
                <div className="flex h-full flex-col gap-2 p-6">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="h-4 rounded bg-emerald-500" style={{ width: `${60 + (i % 4) * 10}%`, opacity: 0.3 + (i % 3) * 0.2 }} />
                  ))}
                </div>
              </div>
              {/* Play icon */}
              <div className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full border-2 border-emerald-500/50 bg-emerald-500/10">
                <svg className="h-7 w-7 text-emerald-400 ml-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              <p className="relative z-10 text-sm font-medium text-zinc-400">Demo video coming soon</p>
              <p className="relative z-10 text-xs text-zinc-600">
                Follow{' '}
                <a href="https://x.com/CreviaCockpit" target="_blank" rel="noopener noreferrer"
                   className="text-emerald-500 hover:text-emerald-400">
                  @CreviaCockpit
                </a>
                {' '}for a preview
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

export default async function HomePage() {
  let snapshot = null;
  let prices: Awaited<ReturnType<typeof getLatestPrices>> = [];
  let content = null;
  let newsItems = null;
  let regime = null;

  try {
    [snapshot, prices, content, newsItems, regime] = await Promise.all([
      getLatestSnapshot().catch(() => null),
      getLatestPrices('BTC,ETH,SOL,BNB').catch(() => []),
      getContentFeed({ page_size: 6 }).catch(() => null),
      getContentFeed({ content_type: 'news_tweet', page_size: 10 }).catch(() => null),
      getCurrentRegime().catch(() => null),
    ]);
  } catch {
    // API not available — render with empty state
  }

  const fgIndex = snapshot?.fear_greed_index;
  const fgLabel = snapshot?.fear_greed_label || 'N/A';
  const fgCtx = getFearGreedContext(fgIndex);
  const domCtx = getBtcDominanceContext(snapshot?.btc_dominance);

  const btcPrice = prices.find(p => p.ticker === 'BTC');
  const btcChange = btcPrice?.change_24h;

  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-zinc-800">
        <div className="absolute inset-0 bg-linear-to-br from-emerald-950/20 via-zinc-950 to-zinc-950" />
        <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-emerald-500/5 blur-3xl" />

        <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-400">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live market intelligence
            </div>
            <h1 className="mt-6 text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
              Crypto Intelligence That{' '}
              <span className="text-emerald-400">Actually Tells You What to Do</span>
            </h1>
            <p className="mt-5 text-lg text-zinc-400 sm:text-xl">
              Real-time regime detection, AI trade setups, and risk-aware position sizing for 16+ assets.
              Pro members see live intelligence. Free preview shows analysis delayed 6 hours.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/waitlist"
                className="rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-400"
              >
                Get Early Access →
              </Link>
              <Link
                href="/tools/risk-calculator"
                className="rounded-lg border border-zinc-700 px-6 py-3 text-sm font-semibold text-zinc-300 transition-colors hover:border-zinc-600 hover:bg-zinc-900"
              >
                Try Risk Calculator Free
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Video Section */}
      <DemoVideoSection />

      {/* Market Regime Indicator — Hero intelligence component */}
      {regime && <MarketRegimeIndicator regime={regime} />}

      {/* Live News Ticker */}
      <NewsTicker initialNews={newsItems?.items || []} />

      {/* Intelligent Market Metrics Bar */}
      {snapshot && (
        <section className="border-b border-zinc-800 bg-zinc-900/30">
          <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <IntelligentMetricCard
                label="BTC Price"
                value={formatPrice(snapshot.btc_price)}
                change={btcChange != null ? formatChange(btcChange) : undefined}
                positive={btcChange != null ? btcChange >= 0 : undefined}
                context={
                  btcChange != null
                    ? Math.abs(btcChange) < 1
                      ? 'Range-bound. Waiting for directional catalyst.'
                      : btcChange > 3
                        ? 'Strong momentum. Watch for follow-through or exhaustion.'
                        : btcChange < -3
                          ? 'Significant selling pressure. Monitor support levels.'
                          : undefined
                    : undefined
                }
              />
              <IntelligentMetricCard
                label="Total Market Cap"
                value={formatLargeNumber(snapshot.total_market_cap)}
                context={snapshot.total_volume_24h
                  ? `24h Vol: ${formatLargeNumber(snapshot.total_volume_24h)}`
                  : undefined
                }
              />
              <IntelligentMetricCard
                label="BTC Dominance"
                value={snapshot.btc_dominance ? `${snapshot.btc_dominance.toFixed(1)}%` : '--'}
                context={domCtx.context || undefined}
                actionHint={domCtx.action}
                severity={domCtx.severity}
              />
              <IntelligentMetricCard
                label="Fear & Greed"
                value={fgIndex != null ? `${fgIndex}` : '--'}
                change={fgLabel}
                positive={fgIndex != null ? fgIndex >= 50 : undefined}
                context={fgCtx.context || undefined}
                actionHint={fgCtx.action}
                severity={fgCtx.severity}
              />
            </div>
          </div>
        </section>
      )}

      {/* Two-column: Content Feed + Prices */}
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white">Latest Analysis</h2>
                <span className="inline-flex items-center gap-1 rounded-full border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-500">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z" />
                  </svg>
                  Free preview · 6h delay
                </span>
              </div>
              <Link href="/analysis" className="text-sm font-medium text-emerald-400 hover:text-emerald-300">
                View all &rarr;
              </Link>
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {content && content.items.length > 0 ? (
                content.items.map((post) => (
                  <ContentCard key={post.id} post={post} />
                ))
              ) : (
                <div className="col-span-2 rounded-xl border border-zinc-800 bg-zinc-900/30 p-10 text-center">
                  <p className="text-zinc-500">Analysis is published multiple times daily.</p>
                  <p className="mt-2 text-sm text-zinc-600">
                    Join the waitlist for real-time access.{' '}
                    <Link href="/waitlist" className="text-emerald-400 hover:text-emerald-300">Get early access →</Link>
                  </p>
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white">Asset Prices</h2>
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
                  Live
                </span>
              </div>
              <Link href="/market" className="text-sm font-medium text-emerald-400 hover:text-emerald-300">
                Dashboard &rarr;
              </Link>
            </div>
            <div className="mt-5 space-y-2">
              {prices.length > 0 ? (
                prices.map((asset) => (
                  <PriceRow key={asset.ticker} asset={asset} />
                ))
              ) : (
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-6 text-center">
                  <p className="text-sm text-zinc-500">Price data will appear once the engine runs.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Waitlist CTA Section */}
      <section className="border-t border-zinc-800 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-400 mb-5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Limited early access
          </div>
          <h2 className="text-2xl font-bold text-white sm:text-3xl">
            Get real-time intelligence before anyone else
          </h2>
          <p className="mt-3 text-zinc-400 max-w-xl mx-auto">
            Regime detection, AI trade setups, opportunity scanner, and risk calculator — all live.
            Early access members get Pro features free during beta.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/waitlist"
              className="rounded-lg bg-emerald-500 px-8 py-3 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
            >
              Join the Waitlist →
            </Link>
            <Link
              href="/tools/risk-calculator"
              className="rounded-lg border border-zinc-700 px-8 py-3 text-sm font-semibold text-zinc-400 hover:border-zinc-600 hover:text-white transition-colors"
            >
              Try Risk Calculator Free
            </Link>
          </div>
          <p className="mt-5 text-xs text-zinc-600">
            Already have an account?{' '}
            <Link href="/auth/login" className="text-emerald-400 hover:text-emerald-300">Sign in →</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
