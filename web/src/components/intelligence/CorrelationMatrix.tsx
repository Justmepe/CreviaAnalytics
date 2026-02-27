'use client';

import type { CorrelationSnapshot } from '@/types';

interface Props {
  data: CorrelationSnapshot;
}

// Convert backend enum strings to human-readable tags
function strengthToTag(strength: string | undefined, value: number): {
  label: string;
  bg: string;
  color: string;
  border: string;
  barColor: string;
  barWidth: number;
} {
  const abs = Math.abs(value);
  const pct = Math.round(abs * 100);

  if (strength === 'very_strong' || abs >= 0.9) {
    return {
      label: 'Very Strong',
      bg: 'rgba(0,214,143,0.08)', color: '#00d68f', border: 'rgba(0,214,143,0.2)',
      barColor: '#00d68f', barWidth: pct,
    };
  }
  if (strength === 'strong' || abs >= 0.7) {
    // Check if this is a Watch situation (price vs OI both high = overleveraged)
    return {
      label: value > 0 ? 'Watch — Overleveraged' : 'Strong Negative',
      bg: 'rgba(240,160,48,0.08)', color: '#f0a030', border: 'rgba(240,160,48,0.2)',
      barColor: '#f0a030', barWidth: pct,
    };
  }
  if (strength === 'moderate' || abs >= 0.4) {
    return {
      label: 'Moderate',
      bg: 'rgba(74,140,240,0.08)', color: '#4a8cf0', border: 'rgba(74,140,240,0.2)',
      barColor: '#4a8cf0', barWidth: pct,
    };
  }
  return {
    label: 'Weak',
    bg: '#161b28', color: '#3d4562', border: '#1c2235',
    barColor: '#3d4562', barWidth: pct,
  };
}

function formatPairLabel(metric1: string, metric2: string): { a: string; b: string } {
  const fmt = (s: string) =>
    s.replace(/_/g, ' ')
     .replace(/\b\w/g, (c) => c.toUpperCase())
     .replace('Btc', 'BTC')
     .replace('Oi', 'OI');
  return { a: fmt(metric1), b: fmt(metric2) };
}

export default function CorrelationMatrix({ data }: Props) {
  const pairs = data.strongest_pairs || [];

  if (pairs.length === 0) {
    return (
      <div
        className="rounded-[6px] p-5"
        style={{ background: '#111520', border: '1px solid #1c2235' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-syne text-[13px] font-semibold" style={{ color: '#dfe3f0' }}>
            Correlation Matrix
          </h3>
        </div>
        {/* Placeholder rows */}
        {['Liq ↔ Volume', 'Price ↔ OI', 'Liq ↔ OI'].map((label) => (
          <div
            key={label}
            className="flex items-center gap-3 px-2 py-2 rounded-[4px] mb-2 opacity-25"
            style={{ background: '#0d0f14', border: '1px solid #1c2235' }}
          >
            <span className="font-mono-cc text-[11px] w-[140px] shrink-0" style={{ color: '#7a839e' }}>
              {label}
            </span>
            <div className="flex-1 h-[4px] rounded-full" style={{ background: '#1c2235' }} />
            <span className="font-mono-cc text-[12px] w-12 text-right" style={{ color: '#3d4562' }}>—</span>
          </div>
        ))}
        <p className="font-mono-cc text-[11px] italic mt-3" style={{ color: '#3d4562' }}>
          Collecting historical data — correlations appear once enough data points are recorded.
        </p>
      </div>
    );
  }

  // Detect elevated risk note
  const hasElevatedRisk = pairs.some(
    (p) => (p.metric1.toLowerCase().includes('liq') || p.metric2.toLowerCase().includes('liq')) && Math.abs(p.correlation) > 0.7
  );

  return (
    <div
      className="rounded-[6px] p-5"
      style={{ background: '#111520', border: '1px solid #1c2235' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-syne text-[13px] font-semibold" style={{ color: '#dfe3f0' }}>
          Correlation Matrix
        </h3>
        <span className="font-mono-cc text-[10px]" style={{ color: '#3d4562' }}>
          Rolling {data.timeframe_hours}d
        </span>
      </div>

      {/* Pair rows */}
      <div className="flex flex-col gap-2">
        {pairs.slice(0, 5).map((pair, i) => {
          const tag = strengthToTag(pair.strength, pair.correlation);
          const { a, b } = formatPairLabel(pair.metric1, pair.metric2);
          const isPositive = pair.correlation >= 0;

          return (
            <div
              key={i}
              className="grid items-center gap-3 px-2.5 py-2 rounded-[4px]"
              style={{
                gridTemplateColumns: '140px 1fr 48px 90px',
                background: '#0d0f14',
                border: '1px solid #1c2235',
              }}
            >
              {/* Pair label */}
              <span className="font-mono-cc text-[11px]" style={{ color: '#7a839e' }}>
                <strong style={{ color: '#dfe3f0', fontWeight: 500 }}>{a}</strong>
                {' '}↔ {b}
              </span>

              {/* Bar */}
              <div className="h-[4px] rounded-full overflow-hidden" style={{ background: '#1c2235' }}>
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ width: `${tag.barWidth}%`, background: tag.barColor }}
                />
              </div>

              {/* Value */}
              <span
                className="font-mono-cc text-[12px] font-medium text-right"
                style={{ color: isPositive ? tag.barColor : '#f03e5a' }}
              >
                {isPositive ? '+' : ''}{pair.correlation.toFixed(2)}
              </span>

              {/* Tag */}
              <span
                className="font-mono-cc text-[9px] tracking-[0.5px] uppercase px-1.5 py-0.5 rounded-[3px] text-center"
                style={{ background: tag.bg, color: tag.color, border: `1px solid ${tag.border}` }}
              >
                {tag.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Warning note */}
      {hasElevatedRisk && (
        <p className="font-mono-cc text-[11px] italic mt-3" style={{ color: '#3d4562' }}>
          ⚠ Elevated liquidation signals detected — positions being flushed. Monitor closely.
        </p>
      )}
    </div>
  );
}
