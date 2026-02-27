'use client';

import { useState, useEffect, useCallback } from 'react';

interface MarketContext {
  regime: { name: string; confidence: number; color: string; trader_action: string } | null;
  funding_rate: number | null;
  liquidations_24h: number | null;
  volatility: string;
  fear_greed: number | null;
}

interface CalcResult {
  positionSize: number;
  riskReward: number;
  maxLoss: number;
  potentialGain: number;
  notionalValue: number;
  requiredMargin: number;
  liquidationPrice: number | null;
  dailyFundingCost: number | null;
}

interface Warning {
  severity: 'green' | 'amber' | 'red' | 'neutral';
  icon: string;
  title: string;
  desc: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ── Asset config ─────────────────────────────────────────── */
const ASSETS = [
  { ticker: 'BTC',  grad: 'linear-gradient(135deg,#f7931a,#e07c10)', textColor: '#08090c', defaultPrice: 67000 },
  { ticker: 'ETH',  grad: 'linear-gradient(135deg,#627eea,#4f67c8)', textColor: '#fff',    defaultPrice: 3200  },
  { ticker: 'SOL',  grad: 'linear-gradient(135deg,#9945ff,#14f195)', textColor: '#fff',    defaultPrice: 120   },
  { ticker: 'BNB',  grad: 'linear-gradient(135deg,#f3ba2f,#d4a228)', textColor: '#08090c', defaultPrice: 580   },
  { ticker: 'XMR',  grad: 'linear-gradient(135deg,#f06020,#c84010)', textColor: '#fff',    defaultPrice: 160   },
  { ticker: 'AAVE', grad: 'linear-gradient(135deg,#2ebac6,#1a9aaa)', textColor: '#fff',    defaultPrice: 95    },
  { ticker: 'DOGE', grad: 'linear-gradient(135deg,#c2a633,#a88b28)', textColor: '#08090c', defaultPrice: 0.08  },
  { ticker: 'UNI',  grad: 'linear-gradient(135deg,#ff007a,#cc005c)', textColor: '#fff',    defaultPrice: 8     },
];

/* ── Regime helpers ──────────────────────────────────────── */
const REGIME_COLORS: Record<string, string> = {
  red: '#f03e5a', green: '#00d68f', amber: '#f0a030', blue: '#4a8cf0', purple: '#9b7cf4',
};
const RISK_OFF_REGIMES = ['RISK_OFF', 'DISTRIBUTION', 'VOLATILITY_EXPANSION'];

function getRegimeAccent(color: string): string {
  return REGIME_COLORS[color] ?? '#3d4562';
}

function isRegimeConflicting(regime: string | undefined, direction: 'long' | 'short'): boolean {
  if (!regime) return false;
  if (RISK_OFF_REGIMES.includes(regime) && direction === 'long') return true;
  if (regime === 'RISK_ON' && direction === 'short') return true;
  return false;
}

/* ── Field component ─────────────────────────────────────── */
function Field({ label, value, onChange, prefix, suffix, placeholder }: {
  label: string; value: string; onChange: (v: string) => void;
  prefix?: string; suffix?: string; placeholder?: string;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', background: '#10141c', border: '1px solid #1a2030', borderRadius: 4, transition: 'border-color 0.2s' }}
        onFocus={() => {}} onBlur={() => {}}
      >
        {prefix && <span className="font-mono-cc" style={{ fontSize: 11, color: '#38405a', padding: '0 8px 0 10px', flexShrink: 0 }}>{prefix}</span>}
        <input
          type="number"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder ?? '0.00'}
          step="any"
          style={{ background: 'none', border: 'none', outline: 'none', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500, color: '#e2e6f0', padding: '9px 10px 9px 0', width: '100%' }}
          onFocus={e => (e.currentTarget.parentElement!.style.borderColor = '#00d68f')}
          onBlur={e  => (e.currentTarget.parentElement!.style.borderColor = '#1a2030')}
        />
        {suffix && <span className="font-mono-cc" style={{ fontSize: 10, color: '#38405a', padding: '0 10px 0 0', flexShrink: 0 }}>{suffix}</span>}
      </div>
    </div>
  );
}

/* ── Warning card ────────────────────────────────────────── */
function WarningCard({ w }: { w: Warning }) {
  const colors = {
    green:   { bg: 'rgba(0,214,143,0.08)',  border: 'rgba(0,214,143,0.2)',  title: '#00d68f', desc: 'rgba(0,214,143,0.7)'   },
    amber:   { bg: 'rgba(240,160,48,0.08)', border: 'rgba(240,160,48,0.2)', title: '#f0a030', desc: 'rgba(240,160,48,0.7)'  },
    red:     { bg: 'rgba(240,62,90,0.08)',  border: 'rgba(240,62,90,0.2)',  title: '#f03e5a', desc: 'rgba(240,62,90,0.7)'   },
    neutral: { bg: '#151a26',               border: '#1a2030',              title: '#788098', desc: '#38405a'                },
  }[w.severity];
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 14px', borderRadius: 5, border: `1px solid ${colors.border}`, background: colors.bg }}>
      <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{w.icon}</span>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: colors.title, marginBottom: 2 }}>{w.title}</div>
        <div style={{ fontSize: 11.5, lineHeight: 1.55, color: colors.desc }}>{w.desc}</div>
      </div>
    </div>
  );
}

/* ── Main component ──────────────────────────────────────── */
export default function RiskCalculator() {
  const [selectedAsset, setSelectedAsset] = useState(0);
  const [direction, setDirection]   = useState<'long' | 'short'>('long');
  const [entry, setEntry]           = useState('');
  const [stopLoss, setStopLoss]     = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [leverage, setLeverage]     = useState(1);
  const [accountSize, setAccountSize] = useState('10000');
  const [riskPct, setRiskPct]       = useState('2');

  const [result, setResult]   = useState<CalcResult | null>(null);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [context, setContext]  = useState<MarketContext | null>(null);

  // Fetch market context
  useEffect(() => {
    fetch(`${API_BASE}/api/intelligence/market-context`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setContext(d); })
      .catch(() => {});
  }, []);

  // Auto-fill entry price when asset selected
  const handleAssetSelect = (idx: number) => {
    setSelectedAsset(idx);
    if (!entry) setEntry(String(ASSETS[idx].defaultPrice));
  };

  const lev = Math.max(1, Math.round(leverage));
  const regimeName = context?.regime?.name;
  const regimeAccent = context?.regime ? getRegimeAccent(context.regime.color) : '#3d4562';
  const conflicting = isRegimeConflicting(regimeName, direction);

  const bannerColor = !context?.regime ? '#3d4562' : conflicting ? '#f0a030' : '#00d68f';
  const bannerBg    = !context?.regime ? 'rgba(61,69,98,0.06)' : conflicting ? 'rgba(240,160,48,0.06)' : 'rgba(0,214,143,0.06)';
  const bannerText  = !context?.regime
    ? 'Fetching market regime…'
    : conflicting
    ? `Caution: ${direction === 'long' ? regimeName?.replace(/_/g, '-') : 'Risk-On'} regime conflicts with ${direction} direction`
    : `${direction === 'long' ? 'Long' : 'Short'} aligned with ${context.regime.name.replace(/_/g, '-')} regime`;

  const calculate = useCallback(() => {
    const e   = parseFloat(entry);
    const sl  = parseFloat(stopLoss);
    const tp  = parseFloat(takeProfit);
    const acc = parseFloat(accountSize) || 10000;
    const rp  = parseFloat(riskPct) / 100;

    if (!e || !sl || !tp || e <= 0 || sl <= 0 || tp <= 0) {
      setResult(null); setWarnings([]); return;
    }

    const riskAmount    = acc * rp;
    const stopDistance  = Math.abs(e - sl);
    if (stopDistance === 0) return;

    const positionSize  = riskAmount / stopDistance;
    const notional      = positionSize * e;
    const requiredMargin = notional / lev;
    const profitDistance = direction === 'long' ? tp - e : e - tp;
    const rr            = profitDistance / stopDistance;
    const potentialGain = riskAmount * rr;

    let liqPrice: number | null = null;
    if (lev > 1) {
      const mm = 0.005;
      liqPrice = direction === 'long' ? e * (1 - (1 / lev) + mm) : e * (1 + (1 / lev) - mm);
    }

    let dailyFunding: number | null = null;
    if (context?.funding_rate != null && lev > 1) {
      dailyFunding = Math.abs(context.funding_rate) * notional * 3;
    }

    setResult({
      positionSize: Math.round(positionSize * 10000) / 10000,
      riskReward: Math.round(rr * 100) / 100,
      maxLoss: Math.round(riskAmount * 100) / 100,
      potentialGain: Math.round(potentialGain * 100) / 100,
      notionalValue: Math.round(notional * 100) / 100,
      requiredMargin: Math.round(requiredMargin * 100) / 100,
      liquidationPrice: liqPrice ? Math.round(liqPrice * 100) / 100 : null,
      dailyFundingCost: dailyFunding ? Math.round(dailyFunding * 100) / 100 : null,
    });

    // Build warnings
    const w: Warning[] = [];

    if (rr >= 2.5) {
      w.push({ severity: 'green', icon: '✓', title: 'Good R/R Ratio', desc: `${rr.toFixed(2)}:1 ratio — risk is well justified by the potential reward.` });
    } else if (rr >= 1.5) {
      w.push({ severity: 'amber', icon: '⚠', title: 'Moderate R/R Ratio', desc: `${rr.toFixed(2)}:1 ratio — acceptable but consider finding a better entry or tighter stop.` });
    } else {
      w.push({ severity: 'red', icon: '✕', title: 'Poor R/R Ratio', desc: `${rr.toFixed(2)}:1 ratio — reward doesn't justify the risk. Rethink the setup.` });
    }

    if (rp > 0.05) {
      w.push({ severity: 'red', icon: '⚠', title: 'Ruin Risk Elevated', desc: `Risking ${(rp * 100).toFixed(1)}% of account per trade. Stay at 1–2% to survive drawdown periods.` });
    } else if (rp > 0.02) {
      w.push({ severity: 'amber', icon: '⚠', title: 'High Risk per Trade', desc: `${(rp * 100).toFixed(1)}% account risk. Professional standard is ≤2%.` });
    }

    if (lev >= 50) {
      w.push({ severity: 'red', icon: '⚡', title: `${lev}x — Extreme Leverage`, desc: `Liquidation is only ${(100 / lev).toFixed(1)}% from entry. A 1% adverse move wipes your margin entirely. This level requires a live stop-loss order, not a mental stop. Experienced traders only.` });
    } else if (lev >= 25) {
      w.push({ severity: 'red', icon: '⚡', title: `${lev}x — High Leverage`, desc: `Liquidation is ${(100 / lev).toFixed(1)}% from entry. Funding fees and wick-through can trigger liquidation before your stop. Reduce position size to compensate.` });
    } else if (lev > 10) {
      w.push({ severity: 'amber', icon: '⚡', title: `${lev}x — Elevated Leverage`, desc: `Liquidation is ${(100 / lev).toFixed(1)}% from entry. Monitor funding rates and volatility closely. Consider 5–10x for a safer margin buffer.` });
    }

    if (context?.regime) {
      if (conflicting) {
        w.push({ severity: 'amber', icon: '📡', title: `${direction === 'long' ? 'Short' : 'Long'}-bias Regime`, desc: `Current ${context.regime.name.replace(/_/g, '-')} regime conflicts with your ${direction} direction. ${context.regime.trader_action || 'Reduce position size.'}` });
      }
    }

    if (dailyFunding && dailyFunding > riskAmount * 0.05) {
      w.push({ severity: 'amber', icon: '💸', title: 'High Funding Cost', desc: `$${dailyFunding.toFixed(2)}/day in funding. At this rate, funding erodes ${((dailyFunding / riskAmount) * 100).toFixed(1)}% of your risk budget daily.` });
    }

    setWarnings(w);
  }, [entry, stopLoss, takeProfit, accountSize, riskPct, lev, direction, context, conflicting]);

  useEffect(() => { calculate(); }, [calculate]);

  const rrColor = !result ? '#e2e6f0' : result.riskReward >= 2.5 ? '#00d68f' : result.riskReward >= 1.5 ? '#f0a030' : '#f03e5a';
  const rrPct   = !result ? 0 : Math.min(100, (result.riskReward / 4) * 100);

  const entryNum = parseFloat(entry) || 0;
  const slNum    = parseFloat(stopLoss) || 0;
  const tpNum    = parseFloat(takeProfit) || 0;

  const priceFmt = (p: number) => p > 0 ? (p >= 1000 ? `$${p.toLocaleString()}` : `$${p.toFixed(4).replace(/\.?0+$/, '')}`) : '--';

  const tpPct    = entryNum && tpNum ? ((tpNum - entryNum) / entryNum * (direction === 'long' ? 100 : -100)) : 0;
  const slPct    = entryNum && slNum ? ((slNum - entryNum) / entryNum * (direction === 'long' ? 100 : -100)) : 0;

  return (
    <div style={{ background: '#07080a', minHeight: '100vh', color: '#e2e6f0' }}>

      {/* ══ REGIME BANNER ══ */}
      <div style={{ background: '#10141c', borderBottom: '1px solid #1a2030', padding: '14px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Regime pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: `${regimeAccent}1a`, border: `1px solid ${regimeAccent}40`, padding: '6px 14px', borderRadius: 4 }}>
            <span className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a' }}>Regime</span>
            <span className="font-bebas" style={{ fontSize: 16, letterSpacing: 1, color: regimeAccent }}>
              {context?.regime?.name?.replace(/_/g, '-') ?? 'LOADING'}
            </span>
            {context?.regime && (
              <span className="font-mono-cc" style={{ fontSize: 10, color: `${regimeAccent}cc` }}>
                {Math.round(context.regime.confidence * 100)}%
              </span>
            )}
          </div>
          {/* Signal */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: 'var(--font-mono)', fontSize: 10, color: bannerColor, background: bannerBg, border: `1px solid ${bannerColor}26`, padding: '6px 12px', borderRadius: 4 }}>
            <span>{conflicting ? '⚠' : '✓'}</span>
            {bannerText}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite', display: 'inline-block' }} />
          Updates live
        </div>
      </div>

      {/* ══ MAIN LAYOUT ══ */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', minHeight: 'calc(100vh - 53px)' }}>

        {/* ── LEFT: INPUTS ── */}
        <div style={{ borderRight: '1px solid #1a2030', padding: 24, display: 'flex', flexDirection: 'column', gap: 0, background: '#0c0e12' }}>

          {/* Page header */}
          <div style={{ marginBottom: 24 }}>
            <div className="font-bebas" style={{ fontSize: 28, letterSpacing: 3, color: '#e2e6f0', lineHeight: 1, marginBottom: 4 }}>Risk Calculator</div>
            <div style={{ fontSize: 12, color: '#38405a' }}>Position sizing with real-time market condition warnings</div>
          </div>

          {/* Asset selector */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 6, marginBottom: 20 }}>
            {ASSETS.map((a, i) => (
              <button
                key={a.ticker}
                onClick={() => handleAssetSelect(i)}
                style={{
                  background: selectedAsset === i ? 'rgba(0,214,143,0.08)' : '#10141c',
                  border: selectedAsset === i ? '1px solid rgba(0,214,143,0.3)' : '1px solid #1a2030',
                  borderRadius: 5, padding: '8px 6px', cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ width: 24, height: 24, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 500, color: a.textColor, background: a.grad }}>
                  {a.ticker.slice(0, 3)}
                </div>
                <span className="font-mono-cc" style={{ fontSize: 9, color: selectedAsset === i ? '#00d68f' : '#788098' }}>{a.ticker}</span>
              </button>
            ))}
          </div>

          {/* Direction toggle */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', background: '#10141c', border: '1px solid #1a2030', borderRadius: 5, overflow: 'hidden', marginBottom: 20 }}>
            <button
              onClick={() => setDirection('long')}
              className="font-mono-cc"
              style={{ padding: 10, textAlign: 'center', cursor: 'pointer', fontSize: 11, letterSpacing: '1px', textTransform: 'uppercase', border: 'none', transition: 'all 0.2s', background: direction === 'long' ? '#00d68f' : 'none', color: direction === 'long' ? '#08090c' : '#38405a', fontWeight: direction === 'long' ? 500 : 300 }}
            >
              Long
            </button>
            <button
              onClick={() => setDirection('short')}
              className="font-mono-cc"
              style={{ padding: 10, textAlign: 'center', cursor: 'pointer', fontSize: 11, letterSpacing: '1px', textTransform: 'uppercase', border: 'none', transition: 'all 0.2s', background: direction === 'short' ? '#f03e5a' : 'none', color: direction === 'short' ? '#fff' : '#38405a', fontWeight: direction === 'short' ? 500 : 300 }}
            >
              Short
            </button>
          </div>

          {/* Price fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
            <Field label="Entry Price"  value={entry}      onChange={setEntry}      prefix="$" />
            <Field label="Stop Loss"    value={stopLoss}   onChange={setStopLoss}   prefix="$" />
            <Field label="Take Profit"  value={takeProfit} onChange={setTakeProfit} prefix="$" />
            <Field label="Leverage"     value={String(lev)} onChange={v => setLeverage(parseFloat(v) || 1)} suffix="x" />
          </div>

          {/* Leverage slider */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a' }}>Leverage</span>
              <span className="font-bebas" style={{ fontSize: 22, lineHeight: 1, color: lev >= 50 ? '#f03e5a' : lev > 20 ? '#f0a030' : '#00d68f' }}>{lev}x</span>
            </div>
            <div style={{ position: 'relative', height: 4, background: '#1a2030', borderRadius: 2, marginBottom: 8 }}>
              <div style={{ height: '100%', borderRadius: 2, background: lev >= 50 ? '#f03e5a' : lev > 20 ? '#f0a030' : '#00d68f', width: `${Math.min(100, (lev / 80) * 100)}%`, transition: 'width 0.1s, background 0.3s' }} />
              <input type="range" min={1} max={80} value={lev} onChange={e => setLeverage(parseInt(e.target.value))}
                style={{ position: 'absolute', top: -7, left: 0, width: '100%', opacity: 0, cursor: 'pointer', height: 18 }} />
            </div>
            {/* Zone markers */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              {[
                { pos: '0%',   label: '1x',  color: '#00d68f' },
                { pos: '25%',  label: '20x', color: '#f0a030' },
                { pos: '61%',  label: '50x', color: '#f03e5a' },
                { pos: '100%', label: '80x', color: '#f03e5a' },
              ].map(m => (
                <span key={m.label} className="font-mono-cc" style={{ fontSize: 8, color: m.color, opacity: 0.5 }}>{m.label}</span>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 5 }}>
              {[1, 5, 10, 25, 50, 80].map(p => (
                <button key={p} onClick={() => setLeverage(p)} className="font-mono-cc"
                  style={{
                    flex: 1, fontSize: 9, letterSpacing: '0.5px',
                    color: lev === p ? '#e2e6f0' : p >= 50 ? '#f03e5a99' : p >= 25 ? '#f0a03099' : '#38405a',
                    background: lev === p ? '#151a26' : '#10141c',
                    border: `1px solid ${lev === p ? '#222c42' : p >= 50 ? 'rgba(240,62,90,0.15)' : p >= 25 ? 'rgba(240,160,48,0.15)' : '#1a2030'}`,
                    padding: '3px 0', borderRadius: 3, cursor: 'pointer', textAlign: 'center',
                  }}>
                  {p}x
                </button>
              ))}
            </div>
            {/* Inline caution note for high leverage */}
            {lev >= 25 && (
              <div style={{ marginTop: 10, padding: '9px 12px', borderRadius: 4, background: lev >= 50 ? 'rgba(240,62,90,0.07)' : 'rgba(240,160,48,0.07)', border: `1px solid ${lev >= 50 ? 'rgba(240,62,90,0.2)' : 'rgba(240,160,48,0.2)'}`, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 13, flexShrink: 0 }}>{lev >= 50 ? '🚨' : '⚠️'}</span>
                <div className="font-mono-cc" style={{ fontSize: 9.5, lineHeight: 1.55, color: lev >= 50 ? '#f03e5a' : '#f0a030' }}>
                  {lev >= 50
                    ? `${lev}x — liquidation sits within ${(100 / lev).toFixed(1)}% of entry. A single 1% adverse move can wipe your margin. Use only if you have a hard stop-loss order live.`
                    : `${lev}x — your liquidation price is ${(100 / lev).toFixed(1)}% from entry. Slippage or a wick can trigger it before your stop. Size down or tighten your stop.`}
                </div>
              </div>
            )}
          </div>

          {/* Account + Risk % */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
            <Field label="Account Size" value={accountSize} onChange={setAccountSize} prefix="$" />
            <Field label="Risk %" value={riskPct} onChange={setRiskPct} suffix="%" />
          </div>

          {/* Calculate CTA */}
          <button
            onClick={calculate}
            className="font-mono-cc"
            style={{ width: '100%', padding: 13, fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '1px', textTransform: 'uppercase', color: '#08090c', background: '#00d68f', border: 'none', borderRadius: 5, cursor: 'pointer', fontWeight: 500, boxShadow: '0 0 24px rgba(0,214,143,0.2)', transition: 'all 0.2s' }}
          >
            Calculate →
          </button>
        </div>

        {/* ── RIGHT: RESULTS ── */}
        <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 16, background: '#07080a' }}>

          {/* ── Regime context card ── */}
          <div style={{ background: '#10141c', border: '1px solid #222c42', borderRadius: 6, padding: '16px 20px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse at top right, ${conflicting ? '#f0a030' : regimeAccent}0d 0%, transparent 60%)`, pointerEvents: 'none' }} />
            <div>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 6 }}>Regime Context</div>
              <div className="font-serif-cc" style={{ fontSize: 20, lineHeight: 1.2, color: '#e2e6f0', marginBottom: 6 }}>
                {!context?.regime ? (
                  'Fetching live market regime…'
                ) : conflicting ? (
                  <>This <em style={{ fontStyle: 'italic', color: '#f0a030' }}>{direction}</em> conflicts with current conditions</>
                ) : (
                  <>This <em style={{ fontStyle: 'italic', color: '#00d68f' }}>{direction}</em> is aligned with the current market regime</>
                )}
              </div>
              {context?.regime?.trader_action && (
                <div style={{ fontSize: 12, color: '#788098', lineHeight: 1.6, maxWidth: 380 }}>{context.regime.trader_action}</div>
              )}
            </div>
            <div style={{ flexShrink: 0, textAlign: 'right' }}>
              <div className="font-bebas" style={{ fontSize: 28, letterSpacing: 2, lineHeight: 1, color: regimeAccent }}>
                {context?.regime?.name?.replace(/_/g, '-') ?? '--'}
              </div>
              {context?.regime && (
                <>
                  <div className="font-mono-cc" style={{ fontSize: 10, color: '#38405a', marginTop: 2 }}>
                    {Math.round(context.regime.confidence * 100)}% confidence
                  </div>
                  <div className="font-mono-cc" style={{ fontSize: 9.5, letterSpacing: '0.5px', padding: '4px 10px', borderRadius: 3, display: 'inline-block', marginTop: 8, color: conflicting ? '#f0a030' : '#00d68f', background: conflicting ? 'rgba(240,160,48,0.08)' : 'rgba(0,214,143,0.08)', border: `1px solid ${conflicting ? 'rgba(240,160,48,0.2)' : 'rgba(0,214,143,0.2)'}` }}>
                    {conflicting ? '⚠ Caution' : '✓ Aligned'}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* ── Hero metrics ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* R/R */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '18px 20px', position: 'relative', overflow: 'hidden' }}>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 8 }}>Risk / Reward</div>
              <div className="font-bebas" style={{ fontSize: 42, lineHeight: 1, color: rrColor, marginBottom: 4, transition: 'color 0.3s' }}>
                {result ? `${result.riskReward}:1` : '--'}
              </div>
              <div className="font-mono-cc" style={{ fontSize: 10, color: '#38405a', marginBottom: 10 }}>
                {result ? (result.riskReward >= 2.5 ? 'Excellent setup' : result.riskReward >= 1.5 ? 'Acceptable' : 'Poor setup') : 'Enter prices'}
              </div>
              <div style={{ height: 3, background: '#1a2030', borderRadius: 2 }}>
                <div style={{ height: 3, borderRadius: 2, background: rrColor, width: `${rrPct}%`, transition: 'width 1s ease, background 0.3s' }} />
              </div>
            </div>
            {/* Position Size */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '18px 20px' }}>
              <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 8 }}>Position Size</div>
              <div className="font-bebas" style={{ fontSize: 42, lineHeight: 1, color: '#e2e6f0', marginBottom: 4 }}>
                {result ? (result.positionSize > 0.001 ? result.positionSize.toFixed(4) : result.positionSize.toFixed(8)) : '--'}
              </div>
              <div className="font-mono-cc" style={{ fontSize: 10, color: '#38405a' }}>
                {result ? `${ASSETS[selectedAsset].ticker} · $${result.notionalValue.toLocaleString()} notional` : 'units of asset'}
              </div>
            </div>
          </div>

          {/* ── Secondary metrics ── */}
          {result && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              {[
                { label: 'Required Margin', value: `$${result.requiredMargin.toLocaleString()}`, sub: `${lev}x leverage` },
                { label: 'Liquidation Price', value: result.liquidationPrice ? priceFmt(result.liquidationPrice) : 'N/A (spot)', sub: result.liquidationPrice ? (direction === 'long' ? '↓ below entry' : '↑ above entry') : '' },
                { label: 'Funding Cost', value: result.dailyFundingCost ? `$${result.dailyFundingCost.toFixed(2)}/day` : 'N/A', sub: result.dailyFundingCost ? 'paid 3× daily' : 'spot or no data' },
              ].map((m) => (
                <div key={m.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '14px 16px' }}>
                  <div className="font-mono-cc" style={{ fontSize: 8.5, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#38405a', marginBottom: 6 }}>{m.label}</div>
                  <div className="font-bebas" style={{ fontSize: 22, color: '#e2e6f0', lineHeight: 1, marginBottom: 2 }}>{m.value}</div>
                  <div className="font-mono-cc" style={{ fontSize: 9, color: '#38405a' }}>{m.sub}</div>
                </div>
              ))}
            </div>
          )}

          {/* ── Trade Visualiser ── */}
          {result && entryNum > 0 && tpNum > 0 && slNum > 0 && (
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '18px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a' }}>Trade Visualiser</div>
                <div className="font-mono-cc" style={{ fontSize: 10, color: '#788098' }}>{ASSETS[selectedAsset].ticker} · {direction.toUpperCase()}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 0, position: 'relative' }}>
                {/* Vertical connector line */}
                <div style={{ position: 'absolute', left: 90, top: 0, bottom: 0, width: 2, background: '#1a2030', zIndex: 0 }} />
                {[
                  { cls: 'tp', label: 'Take Profit', dot: '#00d68f', price: tpNum, pct: tpPct, pnl: result.potentialGain, gain: true },
                  { cls: 'entry', label: 'Entry', dot: '#788098', price: entryNum, pct: 0, pnl: 0, gain: null },
                  { cls: 'sl', label: 'Stop Loss', dot: '#f03e5a', price: slNum, pct: slPct, pnl: result.maxLoss, gain: false },
                ].map((row) => (
                  <div key={row.cls} style={{ display: 'grid', gridTemplateColumns: '90px 2px 1fr', alignItems: 'center', gap: 0, position: 'relative', zIndex: 1, padding: '6px 0' }}>
                    <div className="font-mono-cc" style={{ fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', textAlign: 'right', paddingRight: 14, color: row.dot }}>
                      {row.label}
                    </div>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', marginLeft: -4, flexShrink: 0, border: '2px solid #07080a', background: row.dot, zIndex: 2 }} />
                    <div style={{ paddingLeft: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="font-mono-cc" style={{ fontSize: 13, fontWeight: 500, color: row.dot }}>{priceFmt(row.price)}</span>
                      {row.gain !== null && (
                        <div style={{ textAlign: 'right' }}>
                          <span className="font-mono-cc" style={{ fontSize: 9, color: '#38405a' }}>{row.pct >= 0 ? '+' : ''}{row.pct.toFixed(2)}%</span>
                          <span className="font-mono-cc" style={{ fontSize: 10, fontWeight: 500, color: row.dot, marginLeft: 8 }}>
                            {row.gain ? '+' : '-'}${row.pnl.toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Dynamic warnings ── */}
          {warnings.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {warnings.map((w, i) => <WarningCard key={i} w={w} />)}
            </div>
          )}

          {/* Empty state */}
          {!result && (
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '32px 24px', textAlign: 'center' }}>
              <div className="font-mono-cc" style={{ fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 8 }}>Awaiting inputs</div>
              <p style={{ fontSize: 13, color: '#38405a' }}>Select an asset, set direction, and enter entry / stop-loss / take-profit prices.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
