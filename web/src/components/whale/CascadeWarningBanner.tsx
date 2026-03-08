'use client';

import { useEffect, useState, useCallback } from 'react';

interface CascadeWarning {
  asset: string;
  risk_level: string;
  confidence: number;
  estimated_usd_at_risk: number;
  liq_wall_price: number | null;
  current_price: number | null;
  price_distance_pct: number | null;
  direction: string;
  key_signals: string[];
  human_summary: string;
  expires_at: string;
  created_at: string;
}

const RISK_STYLES: Record<string, { border: string; bg: string; color: string; pulse: boolean }> = {
  LOW:      { border: '#FCD34D', bg: 'rgba(252,211,77,0.05)',  color: '#FCD34D', pulse: false },
  MEDIUM:   { border: '#F97316', bg: 'rgba(249,115,22,0.06)',  color: '#F97316', pulse: false },
  HIGH:     { border: '#EF4444', bg: 'rgba(239,68,68,0.07)',   color: '#EF4444', pulse: true  },
  CRITICAL: { border: '#7F1D1D', bg: 'rgba(127,29,29,0.10)',   color: '#EF4444', pulse: true  },
};

function fmtUsd(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  return `${Math.floor(min / 60)}h ago`;
}

export default function CascadeWarningBanner() {
  const [warnings, setWarnings] = useState<CascadeWarning[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const fetchWarnings = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      const resp = await fetch('/api/whale/cascade-risk', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setWarnings(data.warnings ?? []);
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchWarnings();
    const id = setInterval(fetchWarnings, 60_000);
    return () => clearInterval(id);
  }, [fetchWarnings]);

  const visible = warnings.filter(w => !dismissed.has(`${w.asset}:${w.created_at}`));
  if (visible.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
      {visible.map(w => {
        const style = RISK_STYLES[w.risk_level] ?? RISK_STYLES.MEDIUM;
        const key = `${w.asset}:${w.created_at}`;

        return (
          <div
            key={key}
            style={{
              background: style.bg,
              border: `1px solid ${style.border}`,
              borderRadius: 6,
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            {/* Icon */}
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px',
              padding: '3px 7px', borderRadius: 3, flexShrink: 0, marginTop: 1,
              background: `${style.border}22`, color: style.color,
              border: `1px solid ${style.border}55`,
              textTransform: 'uppercase',
            }}>
              {w.risk_level}
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: style.color, marginBottom: 3 }}>
                {w.human_summary}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#506080', lineHeight: 1.6 }}>
                {w.key_signals.slice(0, 3).join(' · ')}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 5 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a' }}>
                  {fmtUsd(w.estimated_usd_at_risk)} at risk
                </span>
                {w.price_distance_pct !== null && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a' }}>
                    {w.price_distance_pct.toFixed(2)}% from liq wall
                  </span>
                )}
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a' }}>
                  {w.confidence}% confidence
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a' }}>
                  {timeAgo(w.created_at)}
                </span>
              </div>
            </div>

            {/* Dismiss */}
            <button
              onClick={() => setDismissed(prev => new Set(prev).add(key))}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#38405a', fontSize: 12, padding: '0 2px', flexShrink: 0,
                lineHeight: 1,
              }}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
