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

const impactConfig: Record<string, { icon: string; bg: string; color: string }> = {
  bullish: { icon: '↑', bg: 'rgba(0,214,143,0.1)', color: '#00d68f' },
  bearish: { icon: '↓', bg: 'rgba(240,62,90,0.1)', color: '#f03e5a' },
  neutral: { icon: '~', bg: 'rgba(61,69,98,0.3)', color: '#3d4562' },
};

const typeLabels: Record<string, { icon: string; label: string }> = {
  funding_rate:      { icon: '📈', label: 'Funding Rate Spike' },
  liquidation_spike: { icon: '💧', label: 'Liquidation Cascade' },
  oi_change:         { icon: '📊', label: 'Open Interest Shift' },
  stablecoin_flow:   { icon: '🌊', label: 'Capital Flow Alert' },
  volume_anomaly:    { icon: '📡', label: 'Volume Anomaly' },
};

const PLACEHOLDER_SIGNALS = [
  { key: 'funding_rate',      icon: '📈', label: 'Funding Rate Spike' },
  { key: 'liquidation_spike', icon: '💧', label: 'Liquidation Cascade' },
  { key: 'stablecoin_flow',   icon: '🌊', label: 'Capital Flow Alert' },
];

export default function SmartMoneyTracker({ data }: Props) {
  const hasSignals = data.signals && data.signals.length > 0;

  return (
    <div
      className="rounded-[6px] overflow-hidden"
      style={{ background: '#111520', border: '1px solid #1c2235' }}
    >
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid #1c2235' }}
      >
        <h3 className="font-syne text-[13px] font-semibold" style={{ color: '#dfe3f0' }}>
          Smart Money Activity
        </h3>
        {hasSignals && (
          <span
            className="font-mono-cc text-[9px] tracking-[0.8px] uppercase px-2 py-0.5 rounded-[3px]"
            style={{ background: 'rgba(0,214,143,0.08)', color: '#00d68f', border: '1px solid rgba(0,214,143,0.2)' }}
          >
            {data.signal_count} active
          </span>
        )}
      </div>

      {!hasSignals && (
        <>
          {PLACEHOLDER_SIGNALS.map((s) => (
            <div
              key={s.key}
              className="flex items-center gap-2.5 px-3.5 py-2.5 opacity-35"
              style={{ borderBottom: '1px solid #1c2235' }}
            >
              <div
                className="w-7 h-7 rounded-[5px] flex items-center justify-center text-[11px] shrink-0"
                style={{ background: '#161b28', border: '1px solid #242c42' }}
              >
                {s.icon}
              </div>
              <span className="text-[12px] flex-1" style={{ color: '#7a839e' }}>{s.label}</span>
              <span className="font-mono-cc text-[11px]" style={{ color: '#3d4562' }}>—</span>
            </div>
          ))}
          <div className="px-3.5 py-3 text-center" style={{ background: '#0d0f14' }}>
            <p className="text-[12px] italic" style={{ color: '#3d4562' }}>
              No smart money signals active. Signals fire when funding rates, liquidations, or capital flows become notable.
            </p>
          </div>
        </>
      )}

      {hasSignals && data.signals.map((signal, i) => {
        const impact = impactConfig[signal.impact] || impactConfig.neutral;
        const type = typeLabels[signal.signal_type] || { icon: '⚡', label: signal.signal_type.replace(/_/g, ' ') };
        return (
          <div
            key={i}
            className="flex items-start gap-3 px-3.5 py-3"
            style={{ borderBottom: i < data.signals.length - 1 ? '1px solid #1c2235' : 'none' }}
          >
            <div
              className="w-7 h-7 rounded-[5px] flex items-center justify-center text-[11px] shrink-0"
              style={{ background: '#161b28', border: '1px solid #242c42' }}
            >
              {type.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono-cc text-[11px] font-medium" style={{ color: '#dfe3f0' }}>
                  {type.label}
                </span>
                <span className="font-mono-cc text-[10px]" style={{ color: '#3d4562' }}>{signal.asset}</span>
                <span
                  className="font-mono-cc text-[9px] uppercase px-1.5 py-0.5 rounded-[3px]"
                  style={{ background: impact.bg, color: impact.color }}
                >
                  {impact.icon} {signal.impact}
                </span>
              </div>
              {signal.interpretation && (
                <p className="text-[12px] mt-1 leading-relaxed" style={{ color: '#3d4562' }}>
                  {signal.interpretation}
                </p>
              )}
            </div>
            {signal.timestamp && (
              <span className="font-mono-cc text-[10px] shrink-0" style={{ color: '#3d4562' }}>
                {timeAgo(signal.timestamp)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
