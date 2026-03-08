'use client';

import { useEffect, useState } from 'react';

interface FlowPoint {
  timestamp: string;
  net_flow_usd: number;
  deposit_usd: number;
  withdrawal_usd: number;
  transaction_count: number;
}

interface FlowData {
  asset: string;
  data: FlowPoint[];
  summary: {
    net_24h_usd: number;
    bias: string;
    largest_single: number;
  };
}

interface Props {
  asset: string;
  /** If true, only fetches data when mounted (lazy on hover) */
  lazy?: boolean;
}

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function fmtHour(ts: string): string {
  const d = new Date(ts);
  return `${d.getUTCHours().toString().padStart(2, '0')}:00`;
}

export default function WhaleFlowMiniChart({ asset, lazy = false }: Props) {
  const [data, setData] = useState<FlowData | null>(null);
  const [loading, setLoading] = useState(!lazy);

  useEffect(() => {
    if (lazy) return; // caller mounts when visible
    const load = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const resp = await fetch(`/api/whale/flow-chart/${asset}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.ok) setData(await resp.json());
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const id = setInterval(load, 300_000); // refresh every 5 min
    return () => clearInterval(id);
  }, [asset, lazy]);

  if (loading) {
    return (
      <div style={{ height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a' }}>loading…</div>
      </div>
    );
  }

  if (!data) return null;

  const points = data.data;
  const maxAbs = Math.max(...points.map(p => Math.abs(p.net_flow_usd)), 1);
  const BAR_HEIGHT = 40;
  const net24 = data.summary.net_24h_usd;
  const bias = data.summary.bias;
  const biasColor = bias === 'OUTFLOW' ? '#00e5a0' : '#ff3d5a';

  return (
    <div>
      {/* Summary line */}
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#788098',
        marginBottom: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span>24h flow: <span style={{ color: biasColor }}>{fmtUsd(net24)}</span></span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px',
          padding: '1px 5px', borderRadius: 2, textTransform: 'uppercase',
          background: `${biasColor}14`, color: biasColor, border: `1px solid ${biasColor}33`,
        }}>
          {bias}
        </span>
      </div>

      {/* Bar chart */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 1, height: BAR_HEIGHT }}>
        {points.map((p, i) => {
          const isNeg = p.net_flow_usd < 0; // negative = outflow = bullish
          const height = Math.max(2, Math.round((Math.abs(p.net_flow_usd) / maxAbs) * BAR_HEIGHT));
          const color = isNeg ? '#00e5a0' : '#ff3d5a';

          return (
            <div
              key={i}
              title={`${fmtHour(p.timestamp)}: ${fmtUsd(p.net_flow_usd)} (${p.transaction_count} txns)`}
              style={{
                flex: 1,
                height,
                background: `${color}88`,
                borderRadius: 1,
                transition: 'opacity 0.15s',
                cursor: 'default',
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0.85')}
            />
          );
        })}
      </div>

      {/* Axis labels: first and last hour */}
      {points.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: '#38405a' }}>
            {fmtHour(points[0].timestamp)}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: '#38405a' }}>
            {fmtHour(points[points.length - 1].timestamp)}
          </span>
        </div>
      )}
    </div>
  );
}
