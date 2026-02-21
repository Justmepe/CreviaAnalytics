'use client';

import { useState } from 'react';
import type { CorrelationSnapshot, CorrelationPair } from '@/types';
import { timeAgo } from '@/lib/api';

interface Props {
  data: CorrelationSnapshot;
}

function correlationColor(value: number): string {
  if (value >= 0.8) return 'bg-emerald-500/80 text-white';
  if (value >= 0.6) return 'bg-emerald-500/50 text-emerald-100';
  if (value >= 0.4) return 'bg-emerald-500/25 text-emerald-200';
  if (value >= 0.2) return 'bg-emerald-500/10 text-zinc-300';
  if (value > -0.2) return 'bg-zinc-800 text-zinc-400';
  if (value > -0.4) return 'bg-red-500/10 text-zinc-300';
  if (value > -0.6) return 'bg-red-500/25 text-red-200';
  if (value > -0.8) return 'bg-red-500/50 text-red-100';
  return 'bg-red-500/80 text-white';
}

function strengthBadge(strength: string | undefined): string {
  switch (strength) {
    case 'very_strong': return 'bg-emerald-500/20 text-emerald-400';
    case 'strong': return 'bg-blue-500/20 text-blue-400';
    case 'moderate': return 'bg-yellow-500/20 text-yellow-400';
    default: return 'bg-zinc-500/20 text-zinc-400';
  }
}

export default function CorrelationMatrix({ data }: Props) {
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null);

  const matrix = data.correlation_matrix;
  const labels = data.labels;
  const pairs = data.strongest_pairs || [];

  if (!matrix || !labels || matrix.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h3 className="text-lg font-bold text-white mb-2">Correlation Matrix</h3>
        <p className="text-sm text-zinc-500">
          {data.interpretation || 'No correlation data available yet. The engine needs to collect historical metrics first.'}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-lg font-bold text-white">Correlation Matrix</h3>
          <p className="text-xs text-zinc-500 mt-0.5">
            {data.timeframe_hours}h timeframe &middot; {data.data_points} data points
            {data.captured_at && ` \u00b7 ${timeAgo(data.captured_at)}`}
          </p>
        </div>
      </div>

      {/* Heat Map Grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-1.5 text-right text-zinc-500 font-normal" />
              {labels.map((label, i) => (
                <th
                  key={i}
                  className="p-1.5 text-center text-zinc-400 font-medium whitespace-nowrap"
                  style={{ minWidth: '70px' }}
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <td className="p-1.5 text-right text-zinc-400 font-medium whitespace-nowrap pr-2">
                  {labels[i]}
                </td>
                {row.map((value, j) => {
                  const isHovered = hoveredCell?.row === i && hoveredCell?.col === j;
                  const isDiagonal = i === j;
                  return (
                    <td
                      key={j}
                      className={`p-1.5 text-center cursor-default transition-all ${
                        isDiagonal
                          ? 'bg-zinc-700/50 text-zinc-500'
                          : correlationColor(value)
                      } ${isHovered ? 'ring-1 ring-white/30' : ''}`}
                      onMouseEnter={() => setHoveredCell({ row: i, col: j })}
                      onMouseLeave={() => setHoveredCell(null)}
                    >
                      {isDiagonal ? '1.00' : value.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Color legend */}
      <div className="flex items-center justify-center gap-1 mt-3 text-[10px] text-zinc-500">
        <span>-1.0</span>
        <div className="flex gap-0.5">
          <div className="w-4 h-2 rounded-sm bg-red-500/80" />
          <div className="w-4 h-2 rounded-sm bg-red-500/40" />
          <div className="w-4 h-2 rounded-sm bg-zinc-700" />
          <div className="w-4 h-2 rounded-sm bg-emerald-500/40" />
          <div className="w-4 h-2 rounded-sm bg-emerald-500/80" />
        </div>
        <span>+1.0</span>
      </div>

      {/* Strongest Pairs */}
      {pairs.length > 0 && (
        <div className="mt-5 border-t border-zinc-800 pt-4">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
            Strongest Correlations
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {pairs.slice(0, 6).map((pair, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg bg-zinc-800/60 px-3 py-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-zinc-200">
                      {pair.metric1} &harr; {pair.metric2}
                    </span>
                    <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                      pair.correlation > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {pair.correlation > 0 ? '+' : ''}{pair.correlation.toFixed(2)}
                    </span>
                    {pair.strength && (
                      <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${strengthBadge(pair.strength)}`}>
                        {pair.strength.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                  {pair.note && (
                    <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{pair.note}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interpretation */}
      {data.interpretation && (
        <div className="mt-4 rounded-lg bg-zinc-800/60 p-3">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1">
            Interpretation
          </p>
          <p className="text-sm text-zinc-300 leading-relaxed">{data.interpretation}</p>
        </div>
      )}
    </div>
  );
}
