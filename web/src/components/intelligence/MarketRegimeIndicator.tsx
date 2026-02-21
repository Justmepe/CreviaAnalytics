import type { MarketRegime } from '@/types';
import { timeAgo } from '@/lib/api';

const regimeConfig: Record<string, {
  icon: string;
  label: string;
  border: string;
  bg: string;
  badge: string;
  text: string;
  bar: string;
}> = {
  RISK_OFF: {
    icon: '🔴',
    label: 'RISK-OFF',
    border: 'border-l-red-500',
    bg: 'bg-red-500/5',
    badge: 'bg-red-500/20 text-red-400',
    text: 'text-red-400',
    bar: 'bg-red-500',
  },
  RISK_ON: {
    icon: '🟢',
    label: 'RISK-ON',
    border: 'border-l-emerald-500',
    bg: 'bg-emerald-500/5',
    badge: 'bg-emerald-500/20 text-emerald-400',
    text: 'text-emerald-400',
    bar: 'bg-emerald-500',
  },
  ACCUMULATION: {
    icon: '🔵',
    label: 'ACCUMULATION',
    border: 'border-l-blue-500',
    bg: 'bg-blue-500/5',
    badge: 'bg-blue-500/20 text-blue-400',
    text: 'text-blue-400',
    bar: 'bg-blue-500',
  },
  DISTRIBUTION: {
    icon: '🟠',
    label: 'DISTRIBUTION',
    border: 'border-l-orange-500',
    bg: 'bg-orange-500/5',
    badge: 'bg-orange-500/20 text-orange-400',
    text: 'text-orange-400',
    bar: 'bg-orange-500',
  },
  VOLATILITY_EXPANSION: {
    icon: '🟣',
    label: 'VOLATILITY EXPANSION',
    border: 'border-l-purple-500',
    bg: 'bg-purple-500/5',
    badge: 'bg-purple-500/20 text-purple-400',
    text: 'text-purple-400',
    bar: 'bg-purple-500',
  },
  ALTSEASON_CONFIRMED: {
    icon: '🟡',
    label: 'ALTSEASON',
    border: 'border-l-yellow-500',
    bg: 'bg-yellow-500/5',
    badge: 'bg-yellow-500/20 text-yellow-400',
    text: 'text-yellow-400',
    bar: 'bg-yellow-500',
  },
  NEUTRAL: {
    icon: '⚪',
    label: 'NEUTRAL',
    border: 'border-l-zinc-500',
    bg: 'bg-zinc-500/5',
    badge: 'bg-zinc-500/20 text-zinc-400',
    text: 'text-zinc-400',
    bar: 'bg-zinc-500',
  },
};

interface Props {
  regime: MarketRegime;
}

function formatDuration(dateStr: string | null): string {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const minutes = Math.floor((now.getTime() - date.getTime()) / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMins = minutes % 60;
  if (hours < 24) return `${hours}h ${remainingMins}m`;
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return `${days}d ${remainingHours}h`;
}

export default function MarketRegimeIndicator({ regime }: Props) {
  const config = regimeConfig[regime.regime_name] || regimeConfig.NEUTRAL;
  const confidencePct = Math.round(regime.confidence * 100);
  const duration = formatDuration(regime.detected_at);

  return (
    <section className="border-b border-zinc-800">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div
          className={`rounded-xl border border-zinc-800 ${config.bg} border-l-4 ${config.border} p-5 sm:p-6`}
        >
          {/* Header row */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{config.icon}</span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white sm:text-xl">
                    MARKET REGIME DETECTED
                  </h2>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${config.badge}`}
                  >
                    {config.label}
                  </span>
                  {duration && (
                    <span className="text-xs text-zinc-500">
                      Active for {duration}
                    </span>
                  )}
                  {regime.previous_regime && regime.previous_regime !== regime.regime_name && (
                    <span className="text-xs text-zinc-600">
                      (prev: {regime.previous_regime.replace('_', ' ')})
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Confidence + Accuracy */}
            <div className="flex items-center gap-4 sm:text-right">
              <div className="flex-1 sm:flex-none">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  Confidence
                </p>
                <p className={`text-2xl font-bold ${config.text}`}>
                  {confidencePct}%
                </p>
              </div>
              {regime.historical_accuracy != null && (
                <div className="flex-1 sm:flex-none">
                  <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Accuracy
                  </p>
                  <p className="text-2xl font-bold text-zinc-300">
                    {Math.round(regime.historical_accuracy * 100)}%
                  </p>
                </div>
              )}
              <div className="h-10 w-10 rounded-full border-2 border-zinc-700 flex items-center justify-center">
                <svg className="h-10 w-10 -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18" cy="18" r="14"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="text-zinc-800"
                  />
                  <circle
                    cx="18" cy="18" r="14"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={`${confidencePct * 0.88} 88`}
                    strokeLinecap="round"
                    className={config.text}
                  />
                </svg>
              </div>
            </div>
          </div>

          {/* Description */}
          {regime.description && (
            <p className="mt-4 text-sm text-zinc-300 leading-relaxed">
              &ldquo;{regime.description}&rdquo;
            </p>
          )}

          {/* Supporting Signals */}
          {regime.supporting_signals && regime.supporting_signals.length > 0 && (
            <div className="mt-5">
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
                Supporting Signals
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {regime.supporting_signals.map((signal, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-lg bg-zinc-900/60 px-3 py-2"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-zinc-400 truncate">
                        {signal.metric}
                      </p>
                      <p className="text-sm font-medium text-zinc-200">
                        {String(signal.value)}
                      </p>
                    </div>
                    {/* Weight bar */}
                    <div className="w-16 shrink-0">
                      <div className="h-1.5 w-full rounded-full bg-zinc-800">
                        <div
                          className={`h-1.5 rounded-full ${config.bar}`}
                          style={{ width: `${Math.round(signal.contribution * 100)}%` }}
                        />
                      </div>
                      <p className="mt-0.5 text-right text-[10px] text-zinc-600">
                        {Math.round(signal.contribution * 100)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action + Outcome */}
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {regime.expected_outcome && (
              <div className="rounded-lg bg-zinc-900/60 p-3">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1">
                  What This Means
                </p>
                <p className="text-sm text-zinc-300">
                  {regime.expected_outcome}
                </p>
              </div>
            )}
            {regime.trader_action && (
              <div className="rounded-lg bg-zinc-900/60 p-3">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1">
                  Trader Action
                </p>
                <p className={`text-sm font-medium ${config.text}`}>
                  {regime.trader_action}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
