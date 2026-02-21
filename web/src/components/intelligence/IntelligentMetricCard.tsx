interface IntelligentMetricCardProps {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
  context?: string;
  actionHint?: string;
  severity?: 'low' | 'medium' | 'high';
}

const severityStyles = {
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  high: 'bg-red-500/10 text-red-400 border-red-500/20',
};

export default function IntelligentMetricCard({
  label,
  value,
  change,
  positive,
  context,
  actionHint,
  severity = 'low',
}: IntelligentMetricCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-zinc-700">
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold text-white">{value}</p>

      {change && (
        <p
          className={`mt-1 text-sm font-medium ${
            positive ? 'text-emerald-400' : positive === false ? 'text-red-400' : 'text-zinc-400'
          }`}
        >
          {change}
        </p>
      )}

      {context && (
        <p className="mt-2 text-xs text-zinc-400 leading-relaxed border-t border-zinc-800 pt-2">
          {context}
        </p>
      )}

      {actionHint && (
        <div
          className={`mt-2 rounded-md border px-2 py-1 text-xs font-medium ${severityStyles[severity]}`}
        >
          {actionHint}
        </div>
      )}
    </div>
  );
}
