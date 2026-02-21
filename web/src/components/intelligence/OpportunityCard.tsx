'use client';

import type { Opportunity } from '@/types';

const recommendationConfig: Record<string, { label: string; color: string; bg: string }> = {
  STRONG: { label: 'STRONG', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
  MODERATE: { label: 'MODERATE', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
  WEAK: { label: 'WEAK', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  AVOID: { label: 'AVOID', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
};

const scoreLabels = [
  { key: 'confidence', label: 'Conf', max: 2.5 },
  { key: 'rr', label: 'R/R', max: 2.5 },
  { key: 'regime_alignment', label: 'Regime', max: 2.5 },
  { key: 'volume_momentum', label: 'Vol/Mom', max: 2.5 },
];

function formatPrice(price: number): string {
  if (price >= 1000) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (price >= 1) return `$${price.toFixed(2)}`;
  return `$${price.toFixed(4)}`;
}

export default function OpportunityCard({ opportunity, rank }: { opportunity: Opportunity; rank: number }) {
  const rec = recommendationConfig[opportunity.recommendation] || recommendationConfig.WEAK;
  const dirColor = opportunity.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400';

  return (
    <div className={`rounded-xl border ${rec.bg} p-4 space-y-3`}>
      {/* Header with rank */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-black text-zinc-600">#{rank}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-bold ${dirColor}`}>{opportunity.direction}</span>
              <span className="text-lg font-bold text-white">{opportunity.asset}</span>
            </div>
            {opportunity.setup_type && (
              <span className="text-xs text-zinc-500">{opportunity.setup_type}</span>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-black ${rec.color}`}>{opportunity.score.toFixed(1)}</div>
          <div className={`text-xs font-semibold ${rec.color}`}>{rec.label}</div>
        </div>
      </div>

      {/* Score Breakdown Bar */}
      <div className="space-y-1.5">
        {scoreLabels.map(({ key, label, max }) => {
          const val = opportunity.score_breakdown[key] || 0;
          const pct = Math.min((val / max) * 100, 100);
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-zinc-500 w-14 text-right">{label}</span>
              <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-zinc-600 to-zinc-400"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 w-8">{val.toFixed(1)}</span>
            </div>
          );
        })}
      </div>

      {/* Key metrics */}
      <div className="flex gap-4 text-sm">
        <div>
          <span className="text-xs text-zinc-500">Best R/R</span>
          <div className="font-mono font-bold text-emerald-400">{opportunity.best_rr.toFixed(1)}:1</div>
        </div>
        <div>
          <span className="text-xs text-zinc-500">Confidence</span>
          <div className="font-mono font-bold text-white">{Math.round(opportunity.confidence * 100)}%</div>
        </div>
        {opportunity.entry_zones.length > 0 && (
          <div>
            <span className="text-xs text-zinc-500">Entry</span>
            <div className="font-mono font-bold text-white">
              {formatPrice(opportunity.entry_zones[0].price)}
            </div>
          </div>
        )}
        {opportunity.stop_loss && (
          <div>
            <span className="text-xs text-zinc-500">Stop</span>
            <div className="font-mono font-bold text-red-400">
              {formatPrice(opportunity.stop_loss.price)}
            </div>
          </div>
        )}
      </div>

      {/* Top reasoning point */}
      {opportunity.reasoning.length > 0 && (
        <p className="text-xs text-zinc-400 truncate">{opportunity.reasoning[0]}</p>
      )}
    </div>
  );
}
