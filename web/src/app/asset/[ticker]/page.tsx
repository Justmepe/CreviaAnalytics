import { Metadata } from 'next';
import Link from 'next/link';
import ContentCard from '@/components/content/ContentCard';
import { getContentFeed, getLatestPrices, formatPrice, formatChange, formatLargeNumber } from '@/lib/api';

const TICKER_NAMES: Record<string, string> = {
  BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana', BNB: 'BNB',
  DOGE: 'Dogecoin', SHIB: 'Shiba Inu', PEPE: 'Pepe', FLOKI: 'Floki',
  XMR: 'Monero', ZEC: 'Zcash', DASH: 'Dash', SCRT: 'Secret',
  AAVE: 'Aave', UNI: 'Uniswap', CRV: 'Curve', LDO: 'Lido',
};

interface PageProps {
  params: Promise<{ ticker: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { ticker } = await params;
  const name = TICKER_NAMES[ticker.toUpperCase()] || ticker;
  return {
    title: `${name} (${ticker.toUpperCase()}) Analysis`,
    description: `Latest analysis, market memos, and price data for ${name}.`,
  };
}

export const revalidate = 60;

export default async function AssetPage({ params }: PageProps) {
  const { ticker: rawTicker } = await params;
  const ticker = rawTicker.toUpperCase();
  const name = TICKER_NAMES[ticker] || ticker;

  let prices: Awaited<ReturnType<typeof getLatestPrices>> = [];
  let content = null;

  try {
    [prices, content] = await Promise.all([
      getLatestPrices(ticker).catch(() => []),
      getContentFeed({ ticker, page_size: 10 }).catch(() => null),
    ]);
  } catch {
    // API not reachable
  }

  const price = prices.find(p => p.ticker === ticker);
  const isPositive = price?.change_24h != null && price.change_24h >= 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-zinc-500">
        <Link href="/market" className="hover:text-emerald-400">Market</Link>
        <span>/</span>
        <span className="text-zinc-400">{ticker}</span>
      </nav>

      {/* Asset Header */}
      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">{name}</h1>
          <p className="text-lg text-zinc-400">{ticker}</p>
        </div>
        {price && (
          <div className="text-left sm:text-right">
            <p className="text-3xl font-bold text-white">{formatPrice(price.price_usd)}</p>
            <p className={`text-lg font-semibold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
              {formatChange(price.change_24h)} (24h)
            </p>
          </div>
        )}
      </div>

      {/* Price Stats */}
      {price && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <p className="text-xs text-zinc-500 uppercase">24h Volume</p>
            <p className="mt-1 text-lg font-semibold text-white">{formatLargeNumber(price.volume_24h)}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <p className="text-xs text-zinc-500 uppercase">Market Cap</p>
            <p className="mt-1 text-lg font-semibold text-white">{formatLargeNumber(price.market_cap)}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <p className="text-xs text-zinc-500 uppercase">7d Change</p>
            <p className={`mt-1 text-lg font-semibold ${price.change_7d != null && price.change_7d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {formatChange(price.change_7d)}
            </p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <p className="text-xs text-zinc-500 uppercase">Last Updated</p>
            <p className="mt-1 text-sm font-medium text-zinc-300">
              {price.captured_at ? new Date(price.captured_at).toLocaleTimeString() : '--'}
            </p>
          </div>
        </div>
      )}

      {/* Latest Analysis for this asset */}
      <div className="mt-10">
        <h2 className="text-xl font-bold text-white">Latest {ticker} Analysis</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {content && content.items.length > 0 ? (
            content.items.map((post) => <ContentCard key={post.id} post={post} />)
          ) : (
            <div className="col-span-2 rounded-xl border border-zinc-800 bg-zinc-900/30 p-8 text-center">
              <p className="text-zinc-500">No analysis for {ticker} yet.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
