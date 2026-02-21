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
              Intelligent Crypto{' '}
              <span className="text-emerald-400">Market Intelligence</span>
            </h1>
            <p className="mt-5 text-lg text-zinc-400 sm:text-xl">
              Stop guessing. Get regime detection, contextual analysis, and actionable trade intelligence
              for 16+ assets. Know what the market means, not just what it shows.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/analysis"
                className="rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-400"
              >
                View Analysis
              </Link>
              <Link
                href="/pricing"
                className="rounded-lg border border-zinc-700 px-6 py-3 text-sm font-semibold text-zinc-300 transition-colors hover:border-zinc-600 hover:bg-zinc-900"
              >
                Get Pro Access
              </Link>
            </div>
          </div>
        </div>
      </section>

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
              <h2 className="text-xl font-bold text-white">Latest Analysis</h2>
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
                  <p className="text-zinc-500">No analysis published yet. Start the engine to generate content.</p>
                  <p className="mt-2 text-sm text-zinc-600">Run: <code className="rounded bg-zinc-800 px-2 py-0.5 text-emerald-400">python main.py</code></p>
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Asset Prices</h2>
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
