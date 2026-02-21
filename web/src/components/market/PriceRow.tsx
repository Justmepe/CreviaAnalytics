import Link from 'next/link';
import { formatPrice, formatChange, formatLargeNumber } from '@/lib/api';
import type { AssetPrice } from '@/types';

const TICKER_NAMES: Record<string, string> = {
  BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana', BNB: 'BNB',
  DOGE: 'Dogecoin', SHIB: 'Shiba Inu', PEPE: 'Pepe', FLOKI: 'Floki',
  XMR: 'Monero', ZEC: 'Zcash', DASH: 'Dash', SCRT: 'Secret',
  AAVE: 'Aave', UNI: 'Uniswap', CRV: 'Curve', LDO: 'Lido',
};

const TICKER_COLORS: Record<string, string> = {
  BTC: 'bg-orange-500', ETH: 'bg-blue-500', SOL: 'bg-purple-500', BNB: 'bg-yellow-500',
  DOGE: 'bg-amber-500', SHIB: 'bg-red-500', PEPE: 'bg-green-500', FLOKI: 'bg-amber-600',
  XMR: 'bg-orange-600', ZEC: 'bg-yellow-600', DASH: 'bg-blue-600', SCRT: 'bg-indigo-500',
  AAVE: 'bg-cyan-500', UNI: 'bg-pink-500', CRV: 'bg-red-600', LDO: 'bg-sky-500',
};

export default function PriceRow({ asset }: { asset: AssetPrice }) {
  const change = asset.change_24h;
  const isPositive = change != null && change >= 0;

  return (
    <Link
      href={`/asset/${asset.ticker}`}
      className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-3 transition-colors hover:border-zinc-700 hover:bg-zinc-900/60"
    >
      <div className="flex items-center gap-3">
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${TICKER_COLORS[asset.ticker] || 'bg-zinc-600'} text-xs font-bold text-white`}>
          {asset.ticker.slice(0, 2)}
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{asset.ticker}</p>
          <p className="text-xs text-zinc-500">{TICKER_NAMES[asset.ticker] || asset.ticker}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-white">{formatPrice(asset.price_usd)}</p>
        <p className={`text-xs font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {formatChange(change)}
        </p>
      </div>
    </Link>
  );
}
