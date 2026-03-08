'use client';

import { useEffect, useState } from 'react';

interface SentimentData {
  asset: string;
  score: number;
  label: string;
  confidence: number;
  key_signal: string;
  components: Record<string, { raw_score: number; weight: number; weighted: number; detail: string }>;
  computed_at: string;
}

interface Props {
  asset: string;
  windowHours?: number;
  showTooltip?: boolean;
}

const LABEL_CONFIG: Record<string, { color: string; short: string }> = {
  ACCUMULATING:      { color: '#00e5a0', short: 'Accumulating' },
  MILD_ACCUMULATION: { color: '#86EFAC', short: 'Mild Accum.' },
  NEUTRAL:           { color: '#788098', short: 'Neutral'      },
  MILD_DISTRIBUTION: { color: '#F59E0B', short: 'Mild Dist.'   },
  DISTRIBUTING:      { color: '#ff3d5a', short: 'Distributing' },
};

export default function WhaleSentimentBadge({ asset, windowHours = 4, showTooltip = true }: Props) {
  const [data, setData] = useState<SentimentData | null>(null);
  const [showTip, setShowTip] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const resp = await fetch(`/api/whale/sentiment/${asset}?window_hours=${windowHours}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.ok) setData(await resp.json());
      } catch { /* silent */ }
    };
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, [asset, windowHours]);

  if (!data) return null;

  const cfg = LABEL_CONFIG[data.label] ?? LABEL_CONFIG.NEUTRAL;
  const barWidth = Math.round(((data.score + 1) / 2) * 100); // -1..1 → 0..100%

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 5 }}>

      {/* Badge */}
      <span
        style={{
          fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px',
          padding: '2px 5px', borderRadius: 2,
          background: `${cfg.color}14`, color: cfg.color,
          border: `1px solid ${cfg.color}33`,
          cursor: showTooltip ? 'pointer' : 'default',
          userSelect: 'none',
        }}
        onMouseEnter={() => showTooltip && setShowTip(true)}
        onMouseLeave={() => setShowTip(false)}
      >
        🐋 {cfg.short}
      </span>

      {/* Score bar */}
      <div style={{ width: 36, height: 2, background: '#1a2030', borderRadius: 1, overflow: 'hidden' }}>
        <div style={{ height: 2, width: `${barWidth}%`, background: cfg.color, borderRadius: 1 }} />
      </div>

      {/* Tooltip */}
      {showTip && showTooltip && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 6,
          background: '#10141c', border: '1px solid #1a2030', borderRadius: 6,
          padding: '10px 12px', zIndex: 100, minWidth: 220, pointerEvents: 'none',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098', marginBottom: 6, letterSpacing: '0.5px' }}>
            Whale Sentiment · {asset} · {windowHours}h window
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: cfg.color }}>{data.label.replace(/_/g, ' ')}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098' }}>{data.confidence}% conf.</span>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', marginBottom: 8, lineHeight: 1.5 }}>
            {data.key_signal}
          </div>
          {/* Component breakdown */}
          {Object.entries(data.components).map(([key, comp]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, color: '#38405a', width: 100, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                {key.replace(/_/g, ' ')}
              </span>
              <div style={{ flex: 1, height: 2, background: '#1a2030', borderRadius: 1 }}>
                <div style={{
                  height: 2, borderRadius: 1,
                  width: `${Math.round(((comp.raw_score + 1) / 2) * 100)}%`,
                  background: comp.raw_score > 0 ? '#00e5a0' : '#ff3d5a',
                }} />
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, color: '#38405a', width: 28, textAlign: 'right' }}>
                {comp.raw_score > 0 ? '+' : ''}{comp.raw_score.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
