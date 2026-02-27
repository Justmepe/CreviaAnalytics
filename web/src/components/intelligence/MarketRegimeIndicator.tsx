import type { MarketRegime } from '@/types';

/* ── Config ─────────────────────────────────────────────────── */

const regimeCfg: Record<string, { label: string; heading: string; color: string; bg: string }> = {
  RISK_OFF:             { label: 'RISK-OFF',            heading: 'Risk-Off Conditions Active',   color: '#f03e5a', bg: 'rgba(240,62,90,0.04)'   },
  RISK_ON:              { label: 'RISK-ON',              heading: 'Risk-On Conditions Active',    color: '#00d68f', bg: 'rgba(0,214,143,0.04)'   },
  ACCUMULATION:         { label: 'ACCUMULATION',         heading: 'Accumulation Phase Active',    color: '#4a8cf0', bg: 'rgba(74,140,240,0.04)'  },
  DISTRIBUTION:         { label: 'DISTRIBUTION',         heading: 'Distribution Phase Active',    color: '#f0a030', bg: 'rgba(240,160,48,0.04)'  },
  VOLATILITY_EXPANSION: { label: 'VOL. EXPANSION',       heading: 'Volatility Expansion Active',  color: '#9945ff', bg: 'rgba(153,69,255,0.04)'  },
  ALTSEASON_CONFIRMED:  { label: 'ALTSEASON',            heading: 'Alt Season Confirmed',         color: '#f0d030', bg: 'rgba(240,208,48,0.04)'  },
  NEUTRAL:              { label: 'NEUTRAL',              heading: 'Neutral Market Conditions',    color: '#3d4562', bg: 'rgba(61,69,98,0.04)'    },
};

/* ── Helpers ─────────────────────────────────────────────────── */

function formatDuration(dateStr: string | null): string {
  if (!dateStr) return '';
  const minutes = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  if (h < 24) return `${h}h ${minutes % 60}m`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

function formatSignalValue(v: number | string): string {
  if (typeof v === 'number') {
    if (Math.abs(v) < 0.001) return v.toFixed(4);
    if (Math.abs(v) < 1)     return v.toFixed(4);
    if (Math.abs(v) > 1e6)   return `$${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) > 1000)  return v.toLocaleString();
    return v.toFixed(2);
  }
  return String(v);
}

/* ── Component ───────────────────────────────────────────────── */

interface Props { regime: MarketRegime }

export default function MarketRegimeIndicator({ regime }: Props) {
  const cfg          = regimeCfg[regime.regime_name] ?? regimeCfg.NEUTRAL;
  const confidencePct = Math.round(regime.confidence * 100);
  const accuracyPct   = regime.historical_accuracy != null ? Math.round(regime.historical_accuracy * 100) : null;
  const duration      = formatDuration(regime.detected_at);
  const signals       = regime.supporting_signals ?? [];

  // SVG arc: r=14 → circumference ≈ 87.96
  const circ = 87.96;
  const dash  = (confidencePct / 100) * circ;

  return (
    <div style={{
      background: cfg.bg,
      border: '1px solid #1c2235',
      borderLeft: `3px solid ${cfg.color}`,
      borderRadius: 6,
      padding: '22px 24px',
    }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          {/* Badge + duration */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span
              className="font-mono-cc"
              style={{
                fontSize: 9, letterSpacing: '1px', padding: '3px 8px', borderRadius: 3,
                border: `1px solid ${cfg.color}`, color: cfg.color,
                background: `${cfg.color}18`,
              }}
            >
              {cfg.label}
            </span>
            {duration && (
              <span className="font-mono-cc" style={{ fontSize: 10, color: '#3d4562' }}>
                Active for {duration}
              </span>
            )}
          </div>
          {/* Heading */}
          <div className="font-syne" style={{ fontSize: 22, fontWeight: 800, color: '#dfe3f0', lineHeight: 1.1 }}>
            {cfg.heading}
          </div>
        </div>

        {/* Confidence + Accuracy + arc */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexShrink: 0 }}>
          <div style={{ textAlign: 'right' }}>
            <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 2 }}>
              Confidence
            </div>
            <div className="font-bebas" style={{ fontSize: 28, lineHeight: 1, color: cfg.color }}>
              {confidencePct}%
            </div>
          </div>
          {accuracyPct != null && (
            <div style={{ textAlign: 'right' }}>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 2 }}>
                Accuracy
              </div>
              <div className="font-bebas" style={{ fontSize: 28, lineHeight: 1, color: '#dfe3f0' }}>
                {accuracyPct}%
              </div>
            </div>
          )}
          <svg width="42" height="42" viewBox="0 0 36 36" style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
            <circle cx="18" cy="18" r="14" fill="none" stroke="#1c2235" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="14" fill="none"
              stroke={cfg.color} strokeWidth="3"
              strokeDasharray={`${dash} ${circ}`}
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* ── Description quote ── */}
      {regime.description && (
        <div style={{ borderLeft: `2px solid ${cfg.color}`, paddingLeft: 12, margin: '16px 0 4px' }}>
          <p className="font-mono-cc" style={{ fontSize: 12, color: '#7a839e', fontStyle: 'italic', lineHeight: 1.55 }}>
            &ldquo;{regime.description}&rdquo;
          </p>
        </div>
      )}

      {/* ── Supporting Signals ── */}
      {signals.length > 0 && (
        <div style={{ marginTop: 18 }}>
          <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 10 }}>
            Supporting Signals
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {signals.map((sig, i) => {
              const pct = Math.round(sig.contribution * 100);
              return (
                <div
                  key={i}
                  style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 4, padding: '10px 12px' }}
                >
                  <div className="font-mono-cc" style={{ fontSize: 9, color: '#3d4562', marginBottom: 6 }}>
                    {sig.metric}
                  </div>
                  <div className="font-syne" style={{ fontSize: 18, fontWeight: 700, color: '#dfe3f0', marginBottom: 8, lineHeight: 1 }}>
                    {formatSignalValue(sig.value)}
                  </div>
                  <div style={{ height: 2, background: '#1c2235', borderRadius: 1 }}>
                    <div style={{ height: 2, borderRadius: 1, width: `${pct}%`, background: cfg.color }} />
                  </div>
                  <div className="font-mono-cc" style={{ fontSize: 9, color: '#3d4562', textAlign: 'right', marginTop: 4 }}>
                    {pct}% weight
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── What This Means / Trader Action ── */}
      {(regime.expected_outcome || regime.trader_action) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 10 }}>
          {regime.expected_outcome && (
            <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 4, padding: '10px 12px' }}>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 6 }}>
                What This Means
              </div>
              <p className="font-mono-cc" style={{ fontSize: 11, color: '#7a839e', lineHeight: 1.55 }}>
                {regime.expected_outcome}
              </p>
            </div>
          )}
          {regime.trader_action && (
            <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 4, padding: '10px 12px' }}>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#3d4562', marginBottom: 6 }}>
                Trader Action
              </div>
              <p className="font-mono-cc" style={{ fontSize: 11, color: cfg.color, lineHeight: 1.55 }}>
                {regime.trader_action}
              </p>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
