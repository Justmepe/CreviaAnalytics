import { Metadata } from 'next';
import MetricCard from '@/components/market/MetricCard';
import PriceRow from '@/components/market/PriceRow';
import { getLatestSnapshot, getLatestPrices, formatLargeNumber, formatPrice, formatChange } from '@/lib/api';

export const metadata: Metadata = {
  title: 'Market Dashboard',
  description: 'Live crypto market data — prices, Fear & Greed, dominance, and volume.',
};

export const revalidate = 60;

export default async function MarketPage() {
  let snapshot = null;
  let prices: Awaited<ReturnType<typeof getLatestPrices>> = [];

  try {
    [snapshot, prices] = await Promise.all([
      getLatestSnapshot().catch(() => null),
      getLatestPrices().catch(() => []),
    ]);
  } catch {
    // API not available
  }

  // Group prices by sector
  const majors = prices.filter(p => ['BTC', 'ETH', 'SOL', 'BNB'].includes(p.ticker));
  const memecoins = prices.filter(p => ['DOGE', 'SHIB', 'PEPE', 'FLOKI'].includes(p.ticker));
  const privacy = prices.filter(p => ['XMR', 'ZEC', 'DASH', 'SCRT'].includes(p.ticker));
  const defi = prices.filter(p => ['AAVE', 'UNI', 'CRV', 'LDO'].includes(p.ticker));

  const fgIndex = snapshot?.fear_greed_index;
  const fgLabel = snapshot?.fear_greed_label || 'N/A';
  const fgColor = fgIndex != null
    ? fgIndex < 25 ? 'text-red-400' : fgIndex < 45 ? 'text-orange-400' : fgIndex < 55 ? 'text-yellow-400' : fgIndex < 75 ? 'text-emerald-400' : 'text-green-400'
    : 'text-zinc-400';

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold text-white">Market Dashboard</h1>
      <p className="mt-2 text-zinc-400">Live crypto market overview with data from Binance, CoinGecko, and more.</p>

      {/* Global Metrics */}
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <MetricCard label="BTC Price" value={formatPrice(snapshot?.btc_price)} />
        <MetricCard label="ETH Price" value={formatPrice(snapshot?.eth_price)} />
        <MetricCard label="Market Cap" value={formatLargeNumber(snapshot?.total_market_cap)} />
        <MetricCard label="24h Volume" value={formatLargeNumber(snapshot?.total_volume_24h)} />
        <MetricCard label="BTC Dominance" value={snapshot?.btc_dominance ? `${snapshot.btc_dominance.toFixed(1)}%` : '--'} />
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Fear & Greed</p>
          <p className={`mt-1 text-xl font-semibold ${fgColor}`}>{fgIndex ?? '--'}</p>
          <p className={`mt-1 text-sm font-medium ${fgColor}`}>{fgLabel}</p>
        </div>
      </div>

      {/* Asset Prices by Sector */}
      <div className="mt-10 grid gap-8 md:grid-cols-2">
        <PriceSection title="Majors" assets={majors} />
        <PriceSection title="Memecoins" assets={memecoins} />
        <PriceSection title="Privacy Coins" assets={privacy} />
        <PriceSection title="DeFi Protocols" assets={defi} />
      </div>

      {!snapshot && prices.length === 0 && (
        <div className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900/30 p-12 text-center">
          <p className="text-lg text-zinc-500">No market data available yet.</p>
          <p className="mt-2 text-sm text-zinc-600">Start the FastAPI server and engine to populate data.</p>
        </div>
      )}
    </div>
  );
}

function PriceSection({ title, assets }: { title: string; assets: Awaited<ReturnType<typeof getLatestPrices>> }) {
  if (assets.length === 0) return null;
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>
      <div className="space-y-2">
        {assets.map((asset) => (
          <PriceRow key={asset.ticker} asset={asset} />
        ))}
      </div>
    </div>
  );
}
