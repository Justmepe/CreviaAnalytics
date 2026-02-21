'use client';

import { useMarketStream } from '@/hooks/useMarketStream';
import { formatPrice, formatLargeNumber } from '@/lib/api';

export default function LiveMarketBar() {
  const { snapshot, regime, connected } = useMarketStream();

  if (!snapshot) return null;

  const regimeColors: Record<string, string> = {
    RISK_ON: 'text-emerald-400',
    ACCUMULATION: 'text-blue-400',
    ALTSEASON_CONFIRMED: 'text-yellow-400',
    NEUTRAL: 'text-zinc-400',
    DISTRIBUTION: 'text-orange-400',
    RISK_OFF: 'text-red-400',
    VOLATILITY_EXPANSION: 'text-violet-400',
  };

  return (
    <div className="border-b border-zinc-800 bg-zinc-900/50 text-xs">
      <div className="mx-auto max-w-7xl px-4 py-1.5 sm:px-6">
        <div className="flex items-center gap-6 overflow-x-auto scrollbar-hide">
          {/* Live indicator */}
          <div className="flex items-center gap-1.5 shrink-0">
            <div className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`} />
            <span className="text-zinc-600">{connected ? 'LIVE' : 'OFFLINE'}</span>
          </div>

          {snapshot.btc_price && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">BTC</span>
              <span className="text-white font-mono font-medium">{formatPrice(snapshot.btc_price)}</span>
            </div>
          )}

          {snapshot.eth_price && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">ETH</span>
              <span className="text-white font-mono font-medium">{formatPrice(snapshot.eth_price)}</span>
            </div>
          )}

          {snapshot.total_market_cap && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">MCAP</span>
              <span className="text-white font-mono">{formatLargeNumber(snapshot.total_market_cap)}</span>
            </div>
          )}

          {snapshot.btc_dominance && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">BTC.D</span>
              <span className="text-white font-mono">{snapshot.btc_dominance.toFixed(1)}%</span>
            </div>
          )}

          {snapshot.fear_greed_index != null && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">F&G</span>
              <span className={`font-mono ${
                snapshot.fear_greed_index >= 75 ? 'text-red-400' :
                snapshot.fear_greed_index >= 55 ? 'text-yellow-400' :
                snapshot.fear_greed_index >= 45 ? 'text-zinc-300' :
                snapshot.fear_greed_index >= 25 ? 'text-blue-400' :
                'text-emerald-400'
              }`}>
                {snapshot.fear_greed_index} {snapshot.fear_greed_label ? `(${snapshot.fear_greed_label})` : ''}
              </span>
            </div>
          )}

          {regime && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-zinc-500">REGIME</span>
              <span className={`font-semibold ${regimeColors[regime.regime_name] || 'text-zinc-400'}`}>
                {regime.regime_name.replace('_', ' ')}
              </span>
              <span className="text-zinc-600">({Math.round(regime.confidence * 100)}%)</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
