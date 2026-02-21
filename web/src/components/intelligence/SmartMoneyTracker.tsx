'use client';

import { timeAgo } from '@/lib/api';

interface SmartMoneySignal {
  signal_type: string;
  asset: string;
  data: Record<string, unknown> | null;
  interpretation: string | null;
  impact: string;
  confidence: string;
  timestamp: string | null;
}

interface SmartMoneyScan {
  signals: SmartMoneySignal[];
  signal_count: number;
  net_sentiment: string;
  aggregate_interpretation: string | null;
}

interface Props {
  data: SmartMoneyScan;
}

const impactConfig: Record<string, { icon: string; badge: string }> = {
  bullish: { icon: '+', badge: 'bg-emerald-500/20 text-emerald-400' },
  bearish: { icon: '-', badge: 'bg-red-500/20 text-red-400' },
  neutral: { icon: '~', badge: 'bg-zinc-500/20 text-zinc-400' },
};

const sentimentConfig: Record<string, { badge: string }> = {
  BULLISH: { badge: 'bg-emerald-500/20 text-emerald-400' },
  'NEUTRAL-BULLISH': { badge: 'bg-emerald-500/15 text-emerald-300' },
  NEUTRAL: { badge: 'bg-zinc-500/20 text-zinc-400' },
  'NEUTRAL-BEARISH': { badge: 'bg-red-500/15 text-red-300' },
  BEARISH: { badge: 'bg-red-500/20 text-red-400' },
};

const typeLabels: Record<string, string> = {
  funding_rate: 'Funding Rate',
  liquidation_spike: 'Liquidation Spike',
  oi_change: 'Open Interest',
  stablecoin_flow: 'Capital Flow',
  volume_anomaly: 'Volume Anomaly',
};

export default function SmartMoneyTracker({ data }: Props) {
  const sentimentStyle = sentimentConfig[data.net_sentiment] || sentimentConfig.NEUTRAL;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-white">Smart Money Activity</h3>
          <p className="text-xs text-zinc-500 mt-0.5">{data.signal_count} signals detected</p>
        </div>
        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${sentimentStyle.badge}`}>
          {data.net_sentiment}
        </span>
      </div>

      {/* Aggregate Interpretation */}
      {data.aggregate_interpretation && (
        <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
          {data.aggregate_interpretation}
        </p>
      )}

      {/* Signal Cards */}
      {data.signals.length > 0 ? (
        <div className="space-y-2">
          {data.signals.map((signal, i) => {
            const impact = impactConfig[signal.impact] || impactConfig.neutral;
            return (
              <div
                key={i}
                className="rounded-lg bg-zinc-800/60 px-3 py-2.5 flex items-start gap-3"
              >
                {/* Impact icon */}
                <span className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${impact.badge}`}>
                  {impact.icon}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-zinc-300 uppercase">
                      {typeLabels[signal.signal_type] || signal.signal_type}
                    </span>
                    <span className="text-xs text-zinc-600">{signal.asset}</span>
                    <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${impact.badge}`}>
                      {signal.impact}
                    </span>
                    {signal.confidence === 'high' && (
                      <span className="inline-flex rounded-full bg-yellow-500/15 px-1.5 py-0.5 text-[10px] font-medium text-yellow-400">
                        high confidence
                      </span>
                    )}
                  </div>
                  {signal.interpretation && (
                    <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                      {signal.interpretation}
                    </p>
                  )}
                </div>

                {/* Timestamp */}
                {signal.timestamp && (
                  <span className="text-[10px] text-zinc-600 shrink-0">
                    {timeAgo(signal.timestamp)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-zinc-600">
          No significant signals in the current window. Market activity within normal ranges.
        </p>
      )}
    </div>
  );
}
