'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';
import {
  getExchangeKeys,
  addExchangeKey,
  deleteExchangeKey,
  syncPortfolio,
} from '@/lib/api';
import type { ExchangeKey, PortfolioHolding, PortfolioSummary } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EXCHANGE_META: Record<string, { label: string; color: string; bg: string; logo: string }> = {
  binance: { label: 'Binance',  color: '#F0B90B', bg: 'rgba(240,185,11,0.12)',  logo: 'B' },
  bybit:   { label: 'Bybit',    color: '#FF6B6B', bg: 'rgba(255,107,107,0.12)', logo: 'b' },
  okx:     { label: 'OKX',      color: '#7B8794', bg: 'rgba(123,135,148,0.12)', logo: 'O' },
};

const STEP_INSTRUCTIONS: Record<string, { title: string; steps: string[] }> = {
  binance: {
    title: 'Binance Read-Only API Key',
    steps: [
      'Go to binance.com → Profile → API Management',
      'Click "Create API" → choose "System-generated"',
      'Label it (e.g. "Crevia Portfolio")',
      'Under permissions: enable "Read Info" ONLY',
      'Disable "Enable Trading" and "Enable Withdrawals"',
      'Complete 2FA verification and copy both keys',
    ],
  },
  bybit: {
    title: 'Bybit Read-Only API Key',
    steps: [
      'Go to bybit.com → Account → API Management',
      'Click "Create New Key" → choose "System-generated"',
      'Set permissions: "Read-Only" under Account',
      'Disable all trading and withdrawal permissions',
      'Set IP restriction if desired for extra security',
      'Save and copy both API Key and Secret Key',
    ],
  },
  okx: {
    title: 'OKX Read-Only API Key',
    steps: [
      'Go to okx.com → Profile → API',
      'Click "Create V5 API Key"',
      'Set trade permissions to "Read" only',
      'Disable all withdrawal permissions',
      'Complete 2FA and copy your keys',
    ],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtUsd(v: number): string {
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `$${v.toFixed(2)}`;
}

function fmtAmt(v: number): string {
  if (v >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
  if (v >= 1)    return v.toFixed(4);
  return v.toFixed(8);
}

function fmtPrice(v: number): string {
  if (v >= 1000) return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (v >= 1)    return `$${v.toFixed(4)}`;
  return `$${v.toFixed(6)}`;
}

function timeAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60)   return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400)return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// ---------------------------------------------------------------------------
// Connect Exchange Modal
// ---------------------------------------------------------------------------

function ConnectModal({
  onClose,
  onConnected,
}: {
  onClose: () => void;
  onConnected: () => void;
}) {
  const [step, setStep]         = useState(1);
  const [exchange, setExchange] = useState('binance');
  const [apiKey, setApiKey]     = useState('');
  const [secret, setSecret]     = useState('');
  const [label, setLabel]       = useState('');
  const [saving, setSaving]     = useState(false);
  const [err, setErr]           = useState('');

  const meta = EXCHANGE_META[exchange];
  const inst = STEP_INSTRUCTIONS[exchange];

  const connect = async () => {
    if (!apiKey.trim() || !secret.trim()) { setErr('API key and secret are required'); return; }
    setSaving(true); setErr('');
    try {
      await addExchangeKey({ exchange, api_key: apiKey.trim(), api_secret: secret.trim(), label: label.trim() || undefined });
      onConnected();
      onClose();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Failed to connect exchange');
    } finally { setSaving(false); }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={{ ...modalStyle, maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>Connect Exchange</div>
            <div style={{ color: '#8b949e', fontSize: 12, marginTop: 2 }}>Step {step} of 2</div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>
        <div style={{ height: 2, background: '#21262d' }}>
          <div style={{ height: '100%', background: '#00d4aa', transition: 'width 0.3s', width: `${(step / 2) * 100}%` }} />
        </div>

        <div style={{ padding: 24, maxHeight: '70vh', overflowY: 'auto' }}>
          {/* Step 1: pick exchange */}
          {step === 1 && (
            <>
              <label style={labelStyle}>Select Exchange</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 24 }}>
                {(['binance', 'bybit', 'okx'] as const).map(ex => {
                  const m = EXCHANGE_META[ex];
                  return (
                    <button key={ex} onClick={() => setExchange(ex)} style={{ padding: '14px 8px', borderRadius: 10, cursor: 'pointer', textAlign: 'center', border: `1px solid ${exchange === ex ? m.color : '#21262d'}`, background: exchange === ex ? m.bg : '#161b22' }}>
                      <div style={{ width: 36, height: 36, borderRadius: '50%', background: m.bg, border: `1px solid ${m.color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 8px', fontSize: 18, fontWeight: 700, color: m.color }}>{m.logo}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: exchange === ex ? '#f0f6fc' : '#8b949e' }}>{m.label}</div>
                    </button>
                  );
                })}
              </div>

              {/* How-to instructions */}
              <div style={{ background: '#161b22', border: '1px solid #1f6feb', borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
                <div style={{ color: '#58a6ff', fontWeight: 600, fontSize: 13, marginBottom: 10 }}>ℹ {inst.title}</div>
                <ol style={{ color: '#8b949e', fontSize: 12, margin: 0, paddingLeft: 18, lineHeight: 2 }}>
                  {inst.steps.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
              </div>

              <div style={{ background: 'rgba(240,185,11,0.07)', border: '1px solid rgba(240,185,11,0.25)', borderRadius: 8, padding: '10px 14px' }}>
                <div style={{ color: '#F0B90B', fontSize: 12, fontWeight: 600, marginBottom: 2 }}>⚠ Read-Only Keys Only</div>
                <div style={{ color: '#8b949e', fontSize: 11, lineHeight: 1.6 }}>
                  Enable <strong style={{ color: '#c9d1d9' }}>Read Info</strong> permission only. Never enable trading or withdrawal permissions. Crevia only reads your balances — it cannot trade or move your funds.
                </div>
              </div>
            </>
          )}

          {/* Step 2: enter keys */}
          {step === 2 && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, padding: '10px 14px', background: meta.bg, border: `1px solid ${meta.color}44`, borderRadius: 8 }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: meta.bg, border: `1px solid ${meta.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: meta.color }}>{meta.logo}</div>
                <div>
                  <div style={{ color: '#f0f6fc', fontWeight: 600, fontSize: 13 }}>Connecting {meta.label}</div>
                  <div style={{ color: '#8b949e', fontSize: 11 }}>Read-only API key — balances only</div>
                </div>
              </div>

              {err && <div style={{ color: '#f85149', fontSize: 12, marginBottom: 14, padding: '8px 12px', background: 'rgba(248,81,73,0.1)', borderRadius: 6 }}>{err}</div>}

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Label (optional)</label>
                <input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Main spot account" style={inputStyle} />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>API Key</label>
                <input
                  value={apiKey} onChange={e => setApiKey(e.target.value)}
                  placeholder="Paste your read-only API key"
                  autoComplete="off"
                  style={{ ...inputStyle, fontFamily: 'monospace', fontSize: 12 }}
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={labelStyle}>API Secret</label>
                <input
                  type="password" value={secret} onChange={e => setSecret(e.target.value)}
                  placeholder="Paste your API secret"
                  autoComplete="new-password"
                  style={{ ...inputStyle, fontFamily: 'monospace', fontSize: 12 }}
                />
              </div>

              <div style={{ background: 'rgba(63,185,80,0.07)', border: '1px solid rgba(63,185,80,0.2)', borderRadius: 6, padding: '8px 12px', fontSize: 11, color: '#8b949e', lineHeight: 1.6 }}>
                🔒 Keys are encrypted at rest using AES-256. Only the masked key is ever shown after saving. Secrets are never returned to the browser.
              </div>
            </>
          )}
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid #21262d', display: 'flex', justifyContent: 'space-between' }}>
          {step > 1
            ? <button onClick={() => setStep(1)} style={btnSecondaryStyle}>← Back</button>
            : <div />}
          {step === 1
            ? <button onClick={() => setStep(2)} style={btnPrimaryStyle}>Continue →</button>
            : <button onClick={connect} disabled={saving} style={{ ...btnPrimaryStyle, opacity: saving ? 0.6 : 1 }}>
                {saving ? 'Connecting…' : `Connect ${meta.label}`}
              </button>}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const overlayStyle: React.CSSProperties     = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)', padding: 20 };
const modalStyle: React.CSSProperties       = { background: '#0d1117', border: '1px solid #21262d', borderRadius: 12, width: '100%', maxHeight: '90vh', overflowY: 'auto' };
const modalHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 16px', borderBottom: '1px solid #21262d' };
const modalTitleStyle: React.CSSProperties  = { color: '#f0f6fc', fontSize: 17, fontWeight: 700 };
const closeBtnStyle: React.CSSProperties    = { background: 'none', border: 'none', color: '#8b949e', fontSize: 20, cursor: 'pointer', lineHeight: 1 };
const labelStyle: React.CSSProperties       = { color: '#8b949e', fontSize: 11, textTransform: 'uppercase' as const, letterSpacing: 1, display: 'block', marginBottom: 6 };
const inputStyle: React.CSSProperties       = { width: '100%', padding: '11px 14px', borderRadius: 8, background: '#161b22', border: '1px solid #30363d', color: '#f0f6fc', fontSize: 13, outline: 'none', boxSizing: 'border-box' as const };
const btnPrimaryStyle: React.CSSProperties  = { padding: '10px 22px', borderRadius: 8, border: 'none', background: '#00d4aa', color: '#0d1117', cursor: 'pointer', fontSize: 13, fontWeight: 700 };
const btnSecondaryStyle: React.CSSProperties = { padding: '10px 18px', borderRadius: 8, border: '1px solid #30363d', background: 'none', color: '#c9d1d9', cursor: 'pointer', fontSize: 13 };

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PortfolioPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [keys, setKeys]               = useState<ExchangeKey[]>([]);
  const [summaries, setSummaries]     = useState<PortfolioSummary[]>([]);
  const [syncing, setSyncing]         = useState(false);
  const [lastSync, setLastSync]       = useState<string | null>(null);
  const [keysLoading, setKeysLoading] = useState(true);
  const [showConnect, setShowConnect] = useState(false);
  const [activeExchange, setActiveExchange] = useState<string | null>(null);
  const [removingId, setRemovingId]   = useState<number | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  const loadKeys = useCallback(async () => {
    try {
      const k = await getExchangeKeys();
      setKeys(k);
      return k;
    } catch { return []; }
    finally { setKeysLoading(false); }
  }, []);

  const doSync = useCallback(async () => {
    setSyncing(true);
    try {
      const data = await syncPortfolio();
      setSummaries(data);
      setLastSync(new Date().toISOString());
      if (data.length > 0) setActiveExchange(data[0].exchange);
    } catch { /* silent */ }
    finally { setSyncing(false); }
  }, []);

  useEffect(() => {
    if (!user) return;
    loadKeys().then(k => { if (k.length > 0) doSync(); });
  }, [user, loadKeys, doSync]);

  const handleRemoveKey = async (id: number, exchange: string) => {
    if (!confirm(`Remove ${EXCHANGE_META[exchange]?.label ?? exchange} connection?`)) return;
    setRemovingId(id);
    try {
      await deleteExchangeKey(id);
      setKeys(prev => prev.filter(k => k.id !== id));
      setSummaries(prev => prev.filter(s => s.key_id !== id));
    } catch { /* silent */ }
    finally { setRemovingId(null); }
  };

  if (loading || !user) {
    return (
      <div style={{ minHeight: '100vh', background: '#0d1117', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#8b949e', letterSpacing: 2 }}>LOADING…</span>
      </div>
    );
  }

  // Aggregate all holdings across exchanges
  const allHoldings: (PortfolioHolding & { exchange: string })[] = summaries.flatMap(s =>
    s.holdings.map(h => ({ ...h, exchange: s.exchange }))
  );
  const totalUsd    = summaries.reduce((sum, s) => sum + s.total_usd, 0);
  const activeSum   = summaries.find(s => s.exchange === activeExchange);
  const shownHoldings = activeExchange ? (activeSum?.holdings ?? []) : allHoldings;

  // Allocation breakdown (top assets by value across all exchanges)
  const allocMap: Record<string, number> = {};
  allHoldings.forEach(h => { allocMap[h.asset] = (allocMap[h.asset] ?? 0) + h.usd_value; });
  const topAlloc = Object.entries(allocMap).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <CockpitShell>
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", color: '#c9d1d9', minHeight: '100vh', background: '#0d1117' }}>
        <style>{`
          .row-hover:hover { background: #161b22 !important; }
          button { transition: opacity 0.15s; } button:hover { opacity: 0.85; }
          input:focus { border-color: #00d4aa !important; }
          ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
        `}</style>

        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 24px' }}>

          {/* ── Header ── */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 14 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#00d4aa', boxShadow: '0 0 8px #00d4aa' }} />
                <h1 style={{ margin: 0, color: '#f0f6fc', fontSize: 22, fontWeight: 700, fontFamily: "'IBM Plex Sans', sans-serif" }}>Portfolio</h1>
              </div>
              <p style={{ margin: 0, color: '#8b949e', fontSize: 12 }}>
                {keys.length} exchange{keys.length !== 1 ? 's' : ''} connected
                {lastSync && <span style={{ marginLeft: 8 }}>· synced {timeAgo(lastSync)}</span>}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={doSync}
                disabled={syncing || keys.length === 0}
                style={{ ...btnSecondaryStyle, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, opacity: keys.length === 0 ? 0.4 : 1 }}
              >
                <span style={{ display: 'inline-block', animation: syncing ? 'spin 1s linear infinite' : 'none' }}>↻</span>
                {syncing ? 'Syncing…' : 'Sync Now'}
              </button>
              <button onClick={() => setShowConnect(true)} style={{ ...btnPrimaryStyle, fontSize: 12 }}>
                + Connect Exchange
              </button>
            </div>
          </div>

          {/* ── No exchange state ── */}
          {!keysLoading && keys.length === 0 && (
            <div style={{ background: '#161b22', border: '1px dashed #30363d', borderRadius: 12, padding: '52px 24px', textAlign: 'center', marginBottom: 24 }}>
              <div style={{ fontSize: 44, marginBottom: 14 }}>🏦</div>
              <div style={{ color: '#f0f6fc', fontSize: 16, fontWeight: 600, marginBottom: 6 }}>No Exchanges Connected</div>
              <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 22, maxWidth: 400, margin: '0 auto 22px' }}>
                Connect your Binance or Bybit account with a read-only API key to sync your portfolio balances here.
              </div>
              <button onClick={() => setShowConnect(true)} style={btnPrimaryStyle}>+ Connect First Exchange</button>
            </div>
          )}

          {/* ── Summary cards ── */}
          {summaries.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 20 }}>
              {[
                { label: 'Total Value',     value: fmtUsd(totalUsd),                color: '#00d4aa'  },
                { label: 'Exchanges',       value: String(summaries.length),         color: '#58a6ff'  },
                { label: 'Assets',          value: String(shownHoldings.length),     color: '#e3b341'  },
                { label: 'Largest Holding', value: shownHoldings[0]?.asset ?? '—',  color: '#bc8cff'  },
              ].map(c => (
                <div key={c.label} style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 8, padding: '12px 14px' }}>
                  <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: 9, letterSpacing: 1, textTransform: 'uppercase', color: '#8b949e', marginBottom: 4 }}>{c.label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: c.color, lineHeight: 1.1 }}>{c.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* ── Main layout ── */}
          <div style={{ display: 'grid', gridTemplateColumns: summaries.length > 0 ? '1fr 300px' : '1fr', gap: 16, alignItems: 'start' }}>

            {/* ── Holdings table ── */}
            {summaries.length > 0 && (
              <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 10, overflow: 'hidden' }}>

                {/* Exchange tabs */}
                {summaries.length > 1 && (
                  <div style={{ display: 'flex', borderBottom: '1px solid #21262d' }}>
                    <button onClick={() => setActiveExchange(null)} style={{ flex: 1, padding: '9px 14px', fontFamily: 'monospace', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: activeExchange === null ? '#f0f6fc' : '#8b949e', background: 'none', border: 'none', borderBottom: `2px solid ${activeExchange === null ? '#00d4aa' : 'transparent'}`, cursor: 'pointer', marginBottom: -1 }}>
                      All ({allHoldings.length})
                    </button>
                    {summaries.map(s => {
                      const m = EXCHANGE_META[s.exchange];
                      return (
                        <button key={s.key_id} onClick={() => setActiveExchange(s.exchange)} style={{ flex: 1, padding: '9px 14px', fontFamily: 'monospace', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: activeExchange === s.exchange ? '#f0f6fc' : '#8b949e', background: 'none', border: 'none', borderBottom: `2px solid ${activeExchange === s.exchange ? m.color : 'transparent'}`, cursor: 'pointer', marginBottom: -1 }}>
                          {m.label} ({s.holdings.length})
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Table header */}
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 1.2fr 1.2fr 80px', gap: 0, padding: '8px 16px', borderBottom: '1px solid #21262d' }}>
                  {['Asset', 'Amount', 'Price', 'Value', '% Portfolio'].map(h => (
                    <div key={h} style={{ fontFamily: 'monospace', fontSize: 9, letterSpacing: 1, textTransform: 'uppercase', color: '#8b949e' }}>{h}</div>
                  ))}
                </div>

                {/* Table rows */}
                {shownHoldings.length === 0
                  ? <div style={{ padding: '40px 20px', textAlign: 'center', color: '#8b949e', fontSize: 12 }}>No holdings found</div>
                  : shownHoldings.map((h, i) => {
                    const pct    = totalUsd > 0 ? (h.usd_value / totalUsd) * 100 : 0;
                    const exMeta = EXCHANGE_META[(h as PortfolioHolding & { exchange?: string }).exchange ?? ''] ?? EXCHANGE_META.binance;
                    return (
                      <div key={`${h.asset}-${i}`} className="row-hover" style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 1.2fr 1.2fr 80px', gap: 0, padding: '11px 16px', borderBottom: '1px solid #0d1117', background: 'transparent' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ width: 32, height: 32, borderRadius: 8, background: exMeta.bg, border: `1px solid ${exMeta.color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: exMeta.color, flexShrink: 0 }}>
                            {h.asset.slice(0, 3)}
                          </div>
                          <div>
                            <div style={{ color: '#f0f6fc', fontWeight: 600, fontSize: 13 }}>{h.asset}</div>
                            {(h as PortfolioHolding & { exchange?: string }).exchange && (
                              <div style={{ fontFamily: 'monospace', fontSize: 9, color: '#8b949e' }}>{exMeta.label}</div>
                            )}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#c9d1d9' }}>{fmtAmt(h.total)}</div>
                            {h.locked > 0 && <div style={{ fontFamily: 'monospace', fontSize: 9, color: '#8b949e' }}>{fmtAmt(h.locked)} locked</div>}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', fontFamily: 'monospace', fontSize: 12, color: '#c9d1d9' }}>
                          {h.price_usd > 0 ? fmtPrice(h.price_usd) : '—'}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', fontFamily: 'monospace', fontSize: 13, fontWeight: 600, color: '#f0f6fc' }}>
                          {fmtUsd(h.usd_value)}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#8b949e', marginBottom: 3 }}>{pct.toFixed(1)}%</div>
                            <div style={{ height: 3, background: '#21262d', borderRadius: 2, overflow: 'hidden' }}>
                              <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: '#00d4aa', borderRadius: 2 }} />
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}

                {/* Total row */}
                {shownHoldings.length > 0 && (
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 1.2fr 1.2fr 80px', gap: 0, padding: '10px 16px', borderTop: '1px solid #21262d', background: 'rgba(0,0,0,0.2)' }}>
                    <div style={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: '#8b949e' }}>Total</div>
                    <div /><div />
                    <div style={{ fontFamily: 'monospace', fontSize: 14, fontWeight: 700, color: '#00d4aa' }}>
                      {activeExchange && activeSum ? fmtUsd(activeSum.total_usd) : fmtUsd(totalUsd)}
                    </div>
                    <div />
                  </div>
                )}
              </div>
            )}

            {/* ── Right sidebar ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

              {/* Connected exchanges */}
              <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid #21262d' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: '#8b949e' }}>Exchanges</span>
                  <button onClick={() => setShowConnect(true)} style={{ fontFamily: 'monospace', fontSize: 9, letterSpacing: 0.5, textTransform: 'uppercase', color: '#00d4aa', background: 'none', border: '1px solid rgba(0,212,170,0.3)', borderRadius: 4, padding: '3px 8px', cursor: 'pointer' }}>+ Add</button>
                </div>

                {keysLoading ? (
                  <div style={{ padding: '20px 16px', color: '#8b949e', fontSize: 12 }}>Loading…</div>
                ) : keys.length === 0 ? (
                  <div style={{ padding: '20px 16px', textAlign: 'center' }}>
                    <div style={{ color: '#8b949e', fontSize: 12, marginBottom: 10 }}>No exchanges connected</div>
                    <button onClick={() => setShowConnect(true)} style={{ ...btnPrimaryStyle, fontSize: 11 }}>Connect Now</button>
                  </div>
                ) : keys.map(key => {
                  const m   = EXCHANGE_META[key.exchange] ?? EXCHANGE_META.binance;
                  const sum = summaries.find(s => s.key_id === key.id);
                  return (
                    <div key={key.id} style={{ padding: '12px 16px', borderBottom: '1px solid #0d1117', display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 34, height: 34, borderRadius: 8, background: m.bg, border: `1px solid ${m.color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: m.color, flexShrink: 0 }}>{m.logo}</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ color: '#f0f6fc', fontSize: 13, fontWeight: 600 }}>{m.label}</span>
                          {key.label && <span style={{ color: '#8b949e', fontSize: 10 }}>· {key.label}</span>}
                        </div>
                        <div style={{ fontFamily: 'monospace', fontSize: 9, color: '#8b949e', marginTop: 1 }}>{key.api_key_masked}</div>
                        {sum && <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#00d4aa', marginTop: 1 }}>{fmtUsd(sum.total_usd)}</div>}
                        {sum?.error && <div style={{ fontFamily: 'monospace', fontSize: 9, color: '#f85149', marginTop: 1 }}>⚠ {sum.error.slice(0, 40)}</div>}
                      </div>
                      <button
                        onClick={() => handleRemoveKey(key.id, key.exchange)}
                        disabled={removingId === key.id}
                        style={{ background: 'none', border: 'none', color: '#8b949e', fontSize: 12, cursor: 'pointer', padding: 4, opacity: removingId === key.id ? 0.4 : 0.6 }}
                      >✕</button>
                    </div>
                  );
                })}
              </div>

              {/* Allocation breakdown */}
              {topAlloc.length > 0 && (
                <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 10, overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid #21262d' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: '#8b949e' }}>Allocation</span>
                  </div>
                  <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {topAlloc.map(([asset, value]) => {
                      const pct = totalUsd > 0 ? (value / totalUsd) * 100 : 0;
                      const colors = ['#00d4aa','#58a6ff','#e3b341','#bc8cff','#ff7b72','#3fb950','#f0883e','#8b949e'];
                      const c = colors[topAlloc.findIndex(([a]) => a === asset) % colors.length];
                      return (
                        <div key={asset}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 600, color: '#c9d1d9' }}>{asset}</span>
                            <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#8b949e' }}>{pct.toFixed(1)}%  <span style={{ color: c }}>{fmtUsd(value)}</span></span>
                          </div>
                          <div style={{ height: 4, background: '#21262d', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: c, borderRadius: 2 }} />
                          </div>
                        </div>
                      );
                    })}
                    {Object.keys(allocMap).length > 8 && (
                      <div style={{ fontFamily: 'monospace', fontSize: 9, color: '#8b949e', textAlign: 'center', marginTop: 4 }}>
                        + {Object.keys(allocMap).length - 8} more assets
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Sync info */}
              {lastSync && (
                <div style={{ background: 'rgba(0,212,170,0.04)', border: '1px solid rgba(0,212,170,0.12)', borderRadius: 8, padding: '10px 14px', textAlign: 'center' }}>
                  <div style={{ fontFamily: 'monospace', fontSize: 9, letterSpacing: 1, textTransform: 'uppercase', color: '#00d4aa', marginBottom: 4 }}>Last Sync</div>
                  <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#8b949e' }}>{timeAgo(lastSync)}</div>
                  <button onClick={doSync} disabled={syncing} style={{ ...btnPrimaryStyle, fontSize: 10, padding: '7px 16px', marginTop: 10, opacity: syncing ? 0.5 : 1 }}>
                    {syncing ? '↻ Syncing…' : '↻ Refresh'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Keyframe for sync spinner */}
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>

      {showConnect && (
        <ConnectModal
          onClose={() => setShowConnect(false)}
          onConnected={async () => { await loadKeys(); doSync(); }}
        />
      )}
    </CockpitShell>
  );
}
