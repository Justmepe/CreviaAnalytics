'use client';

import type { TradeSetup } from '@/types';

const directionConfig = {
  LONG: { label: 'LONG', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
  SHORT: { label: 'SHORT', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
};

const entryTypeColors: Record<string, string> = {
  aggressive: 'text-orange-400',
  conservative: 'text-blue-400',
  patient: 'text-violet-400',
};

function formatPrice(price: number): string {
  if (price >= 1000) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (price >= 1) return `$${price.toFixed(2)}`;
  return `$${price.toFixed(4)}`;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function TradeSetupCard({ setup }: { setup: TradeSetup }) {
  const dir = directionConfig[setup.direction] || directionConfig.LONG;
  const confidence = setup.confidence ? Math.round(setup.confidence * 100) : 0;

  return (
    <div className={`rounded-xl border ${dir.bg} p-5 space-y-4`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`text-lg font-bold ${dir.color}`}>{dir.label}</span>
          <span className="text-lg font-bold text-white">{setup.asset}</span>
          {setup.setup_type && (
            <span className="text-xs text-zinc-400 bg-zinc-800 rounded px-2 py-0.5">
              {setup.setup_type}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-xs text-zinc-500">Confidence</div>
            <div className={`text-sm font-bold ${confidence >= 70 ? 'text-emerald-400' : confidence >= 50 ? 'text-yellow-400' : 'text-zinc-400'}`}>
              {confidence}%
            </div>
          </div>
          {setup.regime_at_creation && (
            <span className="text-xs text-zinc-500 bg-zinc-800/50 rounded px-2 py-0.5">
              {setup.regime_at_creation.replace('_', ' ')}
            </span>
          )}
        </div>
      </div>

      {/* Entry Zones */}
      {setup.entry_zones && setup.entry_zones.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Entry Zones</h4>
          <div className="space-y-1">
            {setup.entry_zones.map((ez, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={`font-mono font-bold ${entryTypeColors[ez.type] || 'text-zinc-300'}`}>
                    {formatPrice(ez.price)}
                  </span>
                  <span className="text-xs text-zinc-500 capitalize">{ez.type}</span>
                </div>
                <span className="text-xs text-zinc-500 max-w-[50%] text-right truncate">{ez.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stop Loss & Take Profits */}
      <div className="grid grid-cols-2 gap-4">
        {setup.stop_loss && (
          <div>
            <h4 className="text-xs font-semibold text-red-400/70 uppercase tracking-wide mb-1">Stop Loss</h4>
            <div className="font-mono text-sm font-bold text-red-400">
              {formatPrice(setup.stop_loss.price)}
            </div>
            {setup.stop_loss.distance_pct != null && (
              <div className="text-xs text-zinc-500">-{Math.abs(setup.stop_loss.distance_pct).toFixed(1)}%</div>
            )}
            <div className="text-xs text-zinc-600 mt-0.5 truncate">{setup.stop_loss.reason}</div>
          </div>
        )}

        {setup.take_profits && setup.take_profits.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-emerald-400/70 uppercase tracking-wide mb-1">Take Profits</h4>
            <div className="space-y-1">
              {setup.take_profits.map((tp, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="font-mono font-bold text-emerald-400">{formatPrice(tp.price)}</span>
                  <span className="text-xs text-zinc-500">{tp.percentage}%</span>
                  <span className="text-xs text-emerald-600">{tp.rr.toFixed(1)}R</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Position Sizing */}
      {setup.position_sizing && (
        <div>
          <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Position Sizing</h4>
          <div className="flex gap-3">
            {Object.entries(setup.position_sizing).map(([key, val]) => {
              const riskAmt = key.replace('risk_', '$');
              return (
                <div key={key} className="bg-zinc-800/50 rounded px-3 py-1.5 text-center">
                  <div className="text-xs text-zinc-500">{riskAmt} risk</div>
                  <div className="text-sm font-mono font-bold text-white">{(val as number).toFixed(4)}</div>
                  <div className="text-xs text-zinc-600">units</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reasoning */}
      {setup.reasoning && setup.reasoning.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Reasoning</h4>
          <ul className="space-y-1">
            {setup.reasoning.map((r, i) => (
              <li key={i} className="text-sm text-zinc-300 flex gap-2">
                <span className="text-zinc-600 shrink-0">{i + 1}.</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risk Factors */}
      {setup.risk_factors && setup.risk_factors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-amber-400/70 uppercase tracking-wide mb-2">Risk Factors</h4>
          <ul className="space-y-1">
            {setup.risk_factors.map((rf, i) => (
              <li key={i} className="text-xs text-zinc-400 flex gap-1.5">
                <span className="text-amber-500 shrink-0">!</span>
                {rf}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-zinc-800/50">
        <span className="text-xs text-zinc-600" suppressHydrationWarning>{timeAgo(setup.created_at)}</span>
        {setup.outcome && (
          <span className={`text-xs px-2 py-0.5 rounded ${
            setup.outcome === 'pending' ? 'bg-zinc-800 text-zinc-400' :
            setup.outcome === 'hit_tp' ? 'bg-emerald-500/10 text-emerald-400' :
            setup.outcome === 'hit_sl' ? 'bg-red-500/10 text-red-400' :
            'bg-zinc-800 text-zinc-500'
          }`}>
            {setup.outcome.replace('_', ' ').toUpperCase()}
          </span>
        )}
      </div>
    </div>
  );
}
