interface MetricCardProps {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
}

export default function MetricCard({ label, value, change, positive }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</p>
      <p className="mt-1 text-xl font-semibold text-white">{value}</p>
      {change && (
        <p className={`mt-1 text-sm font-medium ${positive ? 'text-emerald-400' : positive === false ? 'text-red-400' : 'text-zinc-400'}`}>
          {change}
        </p>
      )}
    </div>
  );
}
