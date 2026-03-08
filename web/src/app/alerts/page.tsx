'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';

// ---------------------------------------------------------------------------
// Canonical 22 assets (order = display order). Emojis are UI-only decoration.
// ---------------------------------------------------------------------------

const SYMBOL_EMOJI: Record<string, string> = {
  BTC: '₿', ETH: 'Ξ', BNB: 'B', SOL: '◎', AAVE: 'A', UNI: '🦄',
  CRV: 'C', LDO: 'L', LINK: '⬡', MKR: 'M', XMR: 'X', ZEC: 'Z',
  DASH: 'D', DOGE: 'Ð', SHIB: 'S', PEPE: 'P', FLOKI: 'F', DOT: '●',
  ADA: 'A', AVAX: 'A', ATOM: '⚛', SUI: 'S',
};

const ALL_SYMBOLS = [
  'BTC','ETH','BNB','SOL','AAVE','UNI','CRV','LDO','LINK','MKR',
  'XMR','ZEC','DASH','DOGE','SHIB','PEPE','FLOKI','DOT','ADA','AVAX','ATOM','SUI',
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AssetPrice {
  ticker: string;
  price_usd: number | null;
  change_24h: number | null;
}

interface Alert {
  id: number;
  asset: string;
  alert_type: string;
  threshold_value: number;
  frequency: string;
  status: string;
  note: string | null;
  last_triggered: string | null;
  created_at: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function alertColor(type: string): string {
  if (type === 'price_above' || type === 'pct_change_up')   return '#3fb950';
  if (type === 'price_below' || type === 'pct_change_down') return '#f85149';
  return '#8b949e';
}

function formatPrice(p: number | null): string {
  if (p == null) return '—';
  return p < 10 ? p.toFixed(4) : p.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const ALERT_TYPES = [
  { id: 'price_above',     label: 'Price Rises Above', icon: '↑',  category: 'price',   unit: '$' },
  { id: 'price_below',     label: 'Price Falls Below', icon: '↓',  category: 'price',   unit: '$' },
  { id: 'pct_change_up',   label: '% Gain (24h)',      icon: '📈', category: 'percent', unit: '%' },
  { id: 'pct_change_down', label: '% Drop (24h)',      icon: '📉', category: 'percent', unit: '%' },
];

const FREQUENCIES = [
  { id: 'once',   label: 'Once only',    desc: 'Alert fires once, then disables'         },
  { id: 'daily',  label: 'Once per day', desc: 'Maximum one alert per 24 hours'          },
  { id: 'always', label: 'Every time',   desc: 'Alert fires each time condition is met'  },
];

// ---------------------------------------------------------------------------
// Discord message preview
// ---------------------------------------------------------------------------

function DiscordMessage({
  asset, alertType, value, prices,
}: {
  asset: string; alertType: string; value: number; prices: AssetPrice[];
}) {
  const a     = prices.find(p => p.ticker === asset);
  const t     = ALERT_TYPES.find(x => x.id === alertType) || ALERT_TYPES[0];
  const color = alertColor(alertType);
  const condText = `${t.label} ${t.unit}${value?.toLocaleString() ?? ''}`;
  const now   = new Date().toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

  return (
    <div style={{ fontFamily: "'gg sans', Whitney, Arial, sans-serif", fontSize: 14 }}>
      <div style={{ background: '#36393f', borderRadius: 8, overflow: 'hidden', border: '1px solid #202225', maxWidth: 440 }}>
        <div style={{ background: '#2f3136', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 6, borderBottom: '1px solid #202225' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#5865F2' }} />
          <span style={{ color: '#dcddde', fontSize: 12, fontWeight: 600 }}>AlertBot <span style={{ color: '#72767d', fontWeight: 400 }}>— #price-alerts</span></span>
        </div>
        <div style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg,#5865F2,#7289da)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>🔔</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'baseline', marginBottom: 4 }}>
                <span style={{ color: '#ffffff', fontWeight: 700, fontSize: 15 }}>AlertBot</span>
                <span style={{ color: '#72767d', fontSize: 11 }}>Today at {now}</span>
              </div>
              <div style={{ background: '#2f3136', borderRadius: 4, borderLeft: `4px solid ${color}`, padding: '10px 12px', marginTop: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color, fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t.icon} ALERT TRIGGERED</span>
                  <span style={{ color: '#72767d', fontSize: 11 }}>#{asset}/USD</span>
                </div>
                <div style={{ color: '#dcddde', fontSize: 20, fontWeight: 800, margin: '6px 0 2px' }}>
                  {SYMBOL_EMOJI[asset] ?? asset[0]} {asset}
                </div>
                <div style={{ color: '#b9bbbe', fontSize: 13, marginBottom: 8 }}>Condition: <span style={{ color: '#ffffff' }}>{condText}</span></div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <div style={{ color: '#72767d', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Current Price</div>
                    <div style={{ color: '#ffffff', fontWeight: 700 }}>${formatPrice(a?.price_usd ?? null)}</div>
                  </div>
                  <div>
                    <div style={{ color: '#72767d', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>24h Change</div>
                    <div style={{ color: (a?.change_24h ?? 0) > 0 ? '#3ba55d' : '#ed4245', fontWeight: 700 }}>
                      {a?.change_24h != null ? `${a.change_24h > 0 ? '+' : ''}${a.change_24h.toFixed(2)}%` : '—'}
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #40444b', color: '#72767d', fontSize: 11 }}>⏰ creviacockpit.com</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Webhook settings modal
// ---------------------------------------------------------------------------

function WebhookSettings({
  onClose, token, onSaved, prices,
}: {
  onClose: () => void; token: string; onSaved: () => void; prices: AssetPrice[];
}) {
  const [input, setInput]     = useState('');
  const [masked, setMasked]   = useState<string | null>(null);
  const [hasWH, setHasWH]     = useState(false);
  const [saving, setSaving]   = useState(false);
  const [testing, setTesting] = useState(false);
  const [testOk, setTestOk]   = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API}/api/alerts/webhook`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(d => { setHasWH(d.has_webhook); setMasked(d.masked_url); }).catch(() => {});
  }, [token]);

  const isValid = input.startsWith('https://discord.com/api/webhooks/');

  const save = async () => {
    if (!isValid) return;
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/alerts/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ webhook_url: input }),
      });
      if (!r.ok) throw new Error();
      setHasWH(true); setMasked(input.slice(0, 40) + '...' + input.slice(-8)); setInput('');
      onSaved();
    } catch { /* ignored */ }
    finally { setSaving(false); }
  };

  const test = async () => {
    setTesting(true); setTestOk(null);
    try {
      const r = await fetch(`${API}/api/alerts/webhook/test`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
      setTestOk(r.ok);
    } catch { setTestOk(false); }
    finally { setTesting(false); }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={{ ...modalStyle, maxWidth: 500 }} onClick={e => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>Discord Webhook</div>
            <div style={{ color: '#8b949e', fontSize: 12, marginTop: 2 }}>Receive alerts in your Discord server</div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>
        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
          {hasWH && masked && (
            <div style={{ background: 'rgba(63,185,80,0.1)', border: '1px solid rgba(63,185,80,0.3)', borderRadius: 8, padding: '10px 14px', display: 'flex', gap: 10, alignItems: 'center' }}>
              <span>✅</span>
              <div>
                <div style={{ color: '#3fb950', fontWeight: 600, fontSize: 13 }}>Webhook Connected</div>
                <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#8b949e', marginTop: 2 }}>{masked}</div>
              </div>
            </div>
          )}
          <div style={{ background: '#161b22', border: '1px solid #1f6feb', borderRadius: 8, padding: '12px 14px' }}>
            <div style={{ color: '#58a6ff', fontWeight: 600, fontSize: 13, marginBottom: 6 }}>ℹ How to get your Webhook URL</div>
            <ol style={{ color: '#8b949e', fontSize: 12, margin: 0, paddingLeft: 16, lineHeight: 1.8 }}>
              <li>Open your Discord server → Channel Settings</li>
              <li>Go to <strong style={{ color: '#c9d1d9' }}>Integrations → Webhooks</strong></li>
              <li>Click <strong style={{ color: '#c9d1d9' }}>New Webhook</strong> and copy the URL</li>
              <li>Paste it below and click Save</li>
            </ol>
          </div>
          <div>
            <label style={labelStyle}>Webhook URL</label>
            <input
              value={input} onChange={e => { setInput(e.target.value); setTestOk(null); }}
              placeholder="https://discord.com/api/webhooks/..."
              style={{ ...inputStyle, borderColor: isValid && input ? '#00d4aa' : input && !isValid ? '#f85149' : '#30363d', fontFamily: 'monospace', fontSize: 12 }}
            />
            {input && !isValid && <div style={{ color: '#f85149', fontSize: 11, marginTop: 4 }}>⚠ Must start with https://discord.com/api/webhooks/</div>}
          </div>
          {hasWH && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <button onClick={test} disabled={testing} style={{ ...btnSecondaryStyle, fontSize: 12 }}>
                {testing ? '🔄 Sending…' : '🧪 Test Webhook'}
              </button>
              {testOk === true  && <span style={{ color: '#3fb950', fontSize: 12 }}>✓ Test message sent!</span>}
              {testOk === false && <span style={{ color: '#f85149', fontSize: 12 }}>✗ Test failed — check URL</span>}
            </div>
          )}
          <div style={{ color: '#8b949e', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>Message Format Preview</div>
          <DiscordMessage asset="BTC" alertType="price_above" value={100000} prices={prices} />
        </div>
        <div style={{ padding: '16px 24px', borderTop: '1px solid #21262d', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onClose} style={btnSecondaryStyle}>Cancel</button>
          <button onClick={save} disabled={!isValid || !input || saving} style={{ ...btnPrimaryStyle, opacity: !isValid || !input ? 0.5 : 1 }}>
            {saving ? 'Saving…' : 'Save Webhook'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create alert modal (3 steps)
// ---------------------------------------------------------------------------

function CreateModal({
  onClose, onCreated, token, prices,
}: {
  onClose: () => void; onCreated: (a: Alert) => void; token: string; prices: AssetPrice[];
}) {
  const [step, setStep]       = useState(1);
  const [asset, setAsset]     = useState('BTC');
  const [type, setType]       = useState('price_above');
  const [value, setValue]     = useState('');
  const [freq, setFreq]       = useState('once');
  const [note, setNote]       = useState('');
  const [submitting, setSub]  = useState(false);
  const [err, setErr]         = useState('');

  const aData        = prices.find(p => p.ticker === asset);
  const selectedType = ALERT_TYPES.find(t => t.id === type);
  const isPct        = type.startsWith('pct_');
  const canNext2     = value !== '' && parseFloat(value) > 0;

  const submit = async () => {
    setSub(true); setErr('');
    try {
      const r = await fetch(`${API}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ asset, alert_type: type, threshold_value: parseFloat(value), frequency: freq, note: note || null }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Failed');
      onCreated(data); onClose();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : 'Error'); }
    finally { setSub(false); }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={{ ...modalStyle, maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>Create Alert</div>
            <div style={{ color: '#8b949e', fontSize: 12, marginTop: 2 }}>Step {step} of 3</div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>
        <div style={{ height: 2, background: '#21262d' }}>
          <div style={{ height: '100%', background: '#00d4aa', transition: 'width 0.3s', width: `${(step / 3) * 100}%` }} />
        </div>

        <div style={{ padding: 24, maxHeight: '65vh', overflowY: 'auto' }}>
          {/* ── Step 1: Asset + type ── */}
          {step === 1 && (
            <>
              <label style={labelStyle}>Select Asset</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 6, marginBottom: 24 }}>
                {ALL_SYMBOLS.map(sym => {
                  const p = prices.find(x => x.ticker === sym);
                  const chg = p?.change_24h ?? null;
                  return (
                    <button key={sym} onClick={() => setAsset(sym)} style={{ padding: '8px 6px', borderRadius: 8, cursor: 'pointer', textAlign: 'center', border: `1px solid ${asset === sym ? '#00d4aa' : '#21262d'}`, background: asset === sym ? 'rgba(0,212,170,0.1)' : '#161b22', color: asset === sym ? '#00d4aa' : '#c9d1d9' }}>
                      <div style={{ fontSize: 16 }}>{SYMBOL_EMOJI[sym] ?? sym[0]}</div>
                      <div style={{ fontSize: 11, fontWeight: 700 }}>{sym}</div>
                      <div style={{ fontSize: 9, color: chg == null ? '#8b949e' : chg > 0 ? '#3fb950' : '#f85149' }}>
                        {chg == null ? '—' : `${chg > 0 ? '+' : ''}${chg.toFixed(1)}%`}
                      </div>
                    </button>
                  );
                })}
              </div>

              <label style={labelStyle}>Alert Condition</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {ALERT_TYPES.map(t => (
                  <button key={t.id} onClick={() => setType(t.id)} style={{ padding: '10px 14px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', border: `1px solid ${type === t.id ? alertColor(t.id) : '#21262d'}`, background: type === t.id ? `${alertColor(t.id)}15` : '#161b22', color: type === t.id ? alertColor(t.id) : '#c9d1d9', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 16 }}>{t.icon}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{t.label}</div>
                      <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'capitalize' }}>{t.category}</div>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* ── Step 2: Value + frequency ── */}
          {step === 2 && (
            <>
              <label style={labelStyle}>{isPct ? 'Percentage Threshold' : 'Target Price'}</label>
              {aData?.price_usd && !isPct && (
                <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#8b949e', marginBottom: 6 }}>
                  Current: <span style={{ color: '#c9d1d9' }}>${formatPrice(aData.price_usd)}</span>
                  {aData.change_24h != null && <span style={{ color: aData.change_24h > 0 ? '#3fb950' : '#f85149', marginLeft: 8 }}>{aData.change_24h > 0 ? '+' : ''}{aData.change_24h.toFixed(2)}% 24h</span>}
                </div>
              )}
              <div style={{ position: 'relative', marginBottom: 8 }}>
                <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#8b949e', fontFamily: 'monospace', fontSize: 16 }}>{selectedType?.unit}</span>
                <input
                  type="number" value={value} onChange={e => setValue(e.target.value)} autoFocus
                  placeholder={isPct ? 'e.g. 5' : aData?.price_usd ? `e.g. ${(aData.price_usd * 1.05).toFixed(aData.price_usd < 1 ? 4 : 0)}` : 'enter target'}
                  style={{ ...inputStyle, paddingLeft: 32, fontSize: 16, fontFamily: 'monospace' }}
                />
              </div>
              {/* Quick-select % buttons using live price */}
              {!isPct && aData?.price_usd && (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
                  {[0.9, 0.95, 1.05, 1.1, 1.2].map(m => (
                    <button key={m} onClick={() => setValue((aData.price_usd! * m).toFixed(aData.price_usd! < 1 ? 4 : 0))} style={{ padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer', border: '1px solid #30363d', background: '#161b22', color: '#8b949e' }}>
                      {m < 1 ? `${((m - 1) * 100).toFixed(0)}%` : `+${((m - 1) * 100).toFixed(0)}%`}
                    </button>
                  ))}
                </div>
              )}
              {(isPct || !aData?.price_usd) && <div style={{ marginBottom: 20 }} />}

              <label style={labelStyle}>Alert Frequency</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                {FREQUENCIES.map(f => (
                  <button key={f.id} onClick={() => setFreq(f.id)} style={{ padding: '12px 14px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', border: `1px solid ${freq === f.id ? '#00d4aa' : '#21262d'}`, background: freq === f.id ? 'rgba(0,212,170,0.1)' : '#161b22', color: freq === f.id ? '#00d4aa' : '#c9d1d9' }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{f.label}</div>
                    <div style={{ color: '#8b949e', fontSize: 11, marginTop: 2 }}>{f.desc}</div>
                  </button>
                ))}
              </div>

              <label style={labelStyle}>Note (Optional)</label>
              <input type="text" value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. Buy zone target, take profit level…" style={inputStyle} />
            </>
          )}

          {/* ── Step 3: Preview ── */}
          {step === 3 && (
            <>
              <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 8, padding: '12px 14px', marginBottom: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div><div style={{ color: '#8b949e', fontSize: 11 }}>Asset</div><div style={{ color: '#f0f6fc', fontWeight: 600 }}>{asset}{aData?.price_usd ? ` · $${formatPrice(aData.price_usd)}` : ''}</div></div>
                <div><div style={{ color: '#8b949e', fontSize: 11 }}>Condition</div><div style={{ color: alertColor(type), fontWeight: 600, fontSize: 13 }}>{selectedType?.icon} {selectedType?.label}</div></div>
                {value && <div><div style={{ color: '#8b949e', fontSize: 11 }}>Target</div><div style={{ color: '#f0f6fc', fontWeight: 600 }}>{selectedType?.unit}{parseFloat(value).toLocaleString()}</div></div>}
                <div><div style={{ color: '#8b949e', fontSize: 11 }}>Frequency</div><div style={{ color: '#f0f6fc', fontWeight: 600 }}>{FREQUENCIES.find(f => f.id === freq)?.label}</div></div>
              </div>
              <div style={{ color: '#8b949e', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Discord Message Preview</div>
              <DiscordMessage asset={asset} alertType={type} value={parseFloat(value)} prices={prices} />
              {err && <div style={{ color: '#f85149', fontSize: 12, marginTop: 12 }}>{err}</div>}
            </>
          )}
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid #21262d', display: 'flex', justifyContent: 'space-between' }}>
          {step > 1
            ? <button onClick={() => setStep(s => s - 1)} style={btnSecondaryStyle}>Back</button>
            : <div />}
          {step < 3
            ? <button onClick={() => setStep(s => s + 1)} disabled={step === 2 && !canNext2} style={{ ...btnPrimaryStyle, opacity: step === 2 && !canNext2 ? 0.5 : 1 }}>Continue →</button>
            : <button onClick={submit} disabled={submitting} style={{ ...btnPrimaryStyle, opacity: submitting ? 0.5 : 1 }}>{submitting ? 'Creating…' : '✓ Create Alert'}</button>}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const overlayStyle: React.CSSProperties    = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)', padding: 20 };
const modalStyle: React.CSSProperties      = { background: '#0d1117', border: '1px solid #21262d', borderRadius: 12, width: '100%', maxHeight: '90vh', overflowY: 'auto' };
const modalHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 16px', borderBottom: '1px solid #21262d' };
const modalTitleStyle: React.CSSProperties  = { color: '#f0f6fc', fontSize: 17, fontWeight: 700 };
const closeBtnStyle: React.CSSProperties    = { background: 'none', border: 'none', color: '#8b949e', fontSize: 20, cursor: 'pointer', lineHeight: 1 };
const labelStyle: React.CSSProperties      = { color: '#8b949e', fontSize: 12, textTransform: 'uppercase' as const, letterSpacing: 1, display: 'block', marginBottom: 8 };
const inputStyle: React.CSSProperties      = { width: '100%', padding: '12px 14px', borderRadius: 8, background: '#161b22', border: '1px solid #30363d', color: '#f0f6fc', fontSize: 14, outline: 'none', boxSizing: 'border-box' as const };
const btnPrimaryStyle: React.CSSProperties   = { padding: '10px 24px', borderRadius: 8, border: 'none', background: '#00d4aa', color: '#0d1117', cursor: 'pointer', fontSize: 14, fontWeight: 700 };
const btnSecondaryStyle: React.CSSProperties = { padding: '10px 20px', borderRadius: 8, border: '1px solid #30363d', background: 'none', color: '#c9d1d9', cursor: 'pointer', fontSize: 14 };

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AlertsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [alerts, setAlerts]           = useState<Alert[]>([]);
  const [prices, setPrices]           = useState<AssetPrice[]>([]);
  const [fetching, setFetching]       = useState(true);
  const [tab, setTab]                 = useState<'active' | 'triggered'>('active');
  const [showCreate, setShowCreate]   = useState(false);
  const [showWebhook, setShowWebhook] = useState(false);
  const [webhookOk, setWebhookOk]     = useState(false);
  const [ticker, setTicker]           = useState(0);
  const tokenRef = useRef('');

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  // Fetch real prices from the market API (public endpoint — no auth needed)
  useEffect(() => {
    const load = () =>
      fetch(`${API}/api/market/prices`)
        .then(r => r.json())
        .then((d: AssetPrice[]) => { if (Array.isArray(d)) setPrices(d); })
        .catch(() => {});
    load();
    const id = setInterval(load, 60_000); // refresh every 60 s
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!user) return;
    const token = localStorage.getItem('access_token') || '';
    tokenRef.current = token;

    fetch(`${API}/api/alerts`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then((d: Alert[]) => setAlerts(Array.isArray(d) ? d : [])).catch(() => setAlerts([]))
      .finally(() => setFetching(false));

    fetch(`${API}/api/alerts/webhook`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(d => setWebhookOk(d.has_webhook)).catch(() => {});
  }, [user]);

  // Subtle live price animation (micro-jitter so ticker feels live)
  useEffect(() => {
    const id = setInterval(() => setTicker(t => t + 1), 3000);
    return () => clearInterval(id);
  }, []);

  const livePrice = useCallback((p: AssetPrice, i: number) =>
    p.price_usd != null ? p.price_usd * (1 + Math.sin(ticker + i) * 0.0002) : null,
  [ticker]);

  const handleDelete = useCallback(async (id: number) => {
    await fetch(`${API}/api/alerts/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${tokenRef.current}` } });
    setAlerts(prev => prev.filter(a => a.id !== id));
  }, []);

  const handleToggle = useCallback(async (id: number) => {
    const r = await fetch(`${API}/api/alerts/${id}/toggle`, { method: 'PUT', headers: { Authorization: `Bearer ${tokenRef.current}` } });
    if (!r.ok) return;
    const updated: Alert = await r.json();
    setAlerts(prev => prev.map(a => a.id === id ? updated : a));
  }, []);

  const refreshWebhook = useCallback(() => {
    fetch(`${API}/api/alerts/webhook`, { headers: { Authorization: `Bearer ${tokenRef.current}` } })
      .then(r => r.json()).then(d => setWebhookOk(d.has_webhook)).catch(() => {});
  }, []);

  if (loading || !user) {
    return (
      <div style={{ minHeight: '100vh', background: '#0d1117', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#8b949e', letterSpacing: 2 }}>LOADING…</span>
      </div>
    );
  }

  const activeAlerts    = alerts.filter(a => a.status === 'active');
  const triggeredAlerts = alerts.filter(a => a.status === 'triggered');
  const listed          = tab === 'active' ? activeAlerts : triggeredAlerts;

  // Ticker bar: show ALL_SYMBOLS that have price data, in canonical order
  const tickerAssets = ALL_SYMBOLS
    .map((sym, i) => ({ sym, p: prices.find(x => x.ticker === sym), i }))
    .filter(x => x.p?.price_usd != null);

  return (
    <CockpitShell>
      <div style={{ fontFamily: "'IBM Plex Mono', 'Cascadia Code', monospace", color: '#c9d1d9', minHeight: '100vh', background: '#0d1117' }}>
        <style>{`
          .alert-card:hover { border-color: #30363d !important; }
          button { transition: opacity 0.15s; }
          button:hover { opacity: 0.85; }
          input:focus { border-color: #00d4aa !important; }
          ::-webkit-scrollbar { width: 4px; }
          ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
        `}</style>

        {/* ── Price ticker ── */}
        <div style={{ background: '#161b22', borderBottom: '1px solid #21262d', padding: '8px 0', overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: 32, padding: '0 24px', overflowX: 'auto', scrollbarWidth: 'none' }}>
            {tickerAssets.length === 0
              ? ALL_SYMBOLS.map(s => (
                  <div key={s} style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                    <span style={{ color: '#8b949e', fontSize: 11 }}>{s}</span>
                    <span style={{ color: '#38405a', fontSize: 12 }}>—</span>
                  </div>
                ))
              : tickerAssets.map(({ sym, p, i }) => {
                  const live = livePrice(p!, i);
                  return (
                    <div key={sym} style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <span style={{ color: '#8b949e', fontSize: 11 }}>{sym}</span>
                      <span style={{ color: '#f0f6fc', fontSize: 12, fontWeight: 600 }}>${formatPrice(live)}</span>
                      {p!.change_24h != null && (
                        <span style={{ color: p!.change_24h > 0 ? '#3fb950' : '#f85149', fontSize: 11 }}>
                          {p!.change_24h > 0 ? '▲' : '▼'}{Math.abs(p!.change_24h).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  );
                })}
          </div>
        </div>

        <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>

          {/* ── Header ── */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#00d4aa', boxShadow: '0 0 8px #00d4aa' }} />
                <h1 style={{ margin: 0, color: '#f0f6fc', fontSize: 22, fontWeight: 700, fontFamily: "'IBM Plex Sans', sans-serif" }}>Price Alerts</h1>
              </div>
              <p style={{ margin: 0, color: '#8b949e', fontSize: 13 }}>
                {activeAlerts.length} active · {triggeredAlerts.length} triggered ·{' '}
                <span style={{ color: webhookOk ? '#3fb950' : '#f85149' }}>
                  {webhookOk ? '⬡ Discord connected' : '⬡ Discord not connected'}
                </span>
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setShowWebhook(true)} style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid #30363d', background: '#161b22', color: '#c9d1d9', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 16 }}>🔔</span> Discord Setup
              </button>
              <button onClick={() => setShowCreate(true)} style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#00d4aa', color: '#0d1117', cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>
                + New Alert
              </button>
            </div>
          </div>

          {/* ── No-webhook warning ── */}
          {!webhookOk && (
            <div onClick={() => setShowWebhook(true)} style={{ background: '#161b22', border: '1px solid #f85149', borderRadius: 8, padding: '12px 16px', marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span style={{ fontSize: 18 }}>⚠️</span>
                <div>
                  <div style={{ color: '#f85149', fontWeight: 600, fontSize: 13 }}>Discord Webhook Not Configured</div>
                  <div style={{ color: '#8b949e', fontSize: 12 }}>Add a Discord webhook to receive alert notifications</div>
                </div>
              </div>
              <span style={{ color: '#8b949e', fontSize: 20 }}>→</span>
            </div>
          )}

          {/* ── Tabs ── */}
          <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '1px solid #21262d' }}>
            {([
              { id: 'active'    as const, label: 'Active',    count: activeAlerts.length    },
              { id: 'triggered' as const, label: 'Triggered', count: triggeredAlerts.length },
            ]).map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{ padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer', fontSize: 14, color: tab === t.id ? '#00d4aa' : '#8b949e', borderBottom: `2px solid ${tab === t.id ? '#00d4aa' : 'transparent'}`, fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: tab === t.id ? 600 : 400, marginBottom: -1 }}>
                {t.label}
                {t.count > 0 && <span style={{ marginLeft: 8, background: tab === t.id ? '#00d4aa' : '#21262d', color: tab === t.id ? '#0d1117' : '#8b949e', padding: '1px 7px', borderRadius: 20, fontSize: 11 }}>{t.count}</span>}
              </button>
            ))}
          </div>

          {/* ── Alert list ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {fetching ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#8b949e', fontSize: 13 }}>Loading…</div>
            ) : listed.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#8b949e' }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>🔔</div>
                <div style={{ fontSize: 16, color: '#c9d1d9', marginBottom: 4 }}>No {tab} alerts</div>
                <div style={{ fontSize: 13, marginBottom: 16 }}>{tab === 'active' ? 'Create your first alert to get started' : 'Triggered alerts will appear here'}</div>
                {tab === 'active' && <button onClick={() => setShowCreate(true)} style={btnPrimaryStyle}>+ New Alert</button>}
              </div>
            ) : listed.map((alert, i) => {
              const pData  = prices.find(p => p.ticker === alert.asset);
              const tData  = ALERT_TYPES.find(t => t.id === alert.alert_type);
              const color  = alertColor(alert.alert_type);
              const lp     = pData ? livePrice(pData, i) : null;

              return (
                <div key={alert.id} className="alert-card" style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 10, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 3, height: 48, borderRadius: 2, background: color, flexShrink: 0 }} />

                  <div style={{ width: 44, height: 44, borderRadius: 10, background: `${color}20`, border: `1px solid ${color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <span style={{ fontSize: 20 }}>{SYMBOL_EMOJI[alert.asset] ?? alert.asset[0]}</span>
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                      <span style={{ color: '#f0f6fc', fontWeight: 700, fontSize: 14 }}>{alert.asset}</span>
                      <span style={{ color, fontSize: 12, background: `${color}20`, padding: '2px 8px', borderRadius: 20 }}>{tData?.icon} {tData?.label}</span>
                      {webhookOk && <span style={{ color: '#8b949e', fontSize: 11 }}>⬡ Discord</span>}
                    </div>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      <span style={{ color: '#8b949e', fontSize: 12 }}>Target: <span style={{ color: '#c9d1d9' }}>{tData?.unit}{alert.threshold_value.toLocaleString()}</span></span>
                      <span style={{ color: '#8b949e', fontSize: 12 }}>{FREQUENCIES.find(f => f.id === alert.frequency)?.label}</span>
                      {alert.last_triggered && <span style={{ color: '#3fb950', fontSize: 12 }}>✓ Triggered {timeAgo(alert.last_triggered)}</span>}
                      {alert.note && <span style={{ color: '#8b949e', fontSize: 11, fontStyle: 'italic' }}>{alert.note}</span>}
                    </div>
                  </div>

                  {/* Live price from DB */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ color: '#f0f6fc', fontWeight: 600, fontSize: 14 }}>{lp != null ? `$${formatPrice(lp)}` : '—'}</div>
                    {pData?.change_24h != null && (
                      <div style={{ color: pData.change_24h > 0 ? '#3fb950' : '#f85149', fontSize: 12 }}>
                        {pData.change_24h > 0 ? '+' : ''}{pData.change_24h.toFixed(2)}%
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {alert.status === 'active'  && <button onClick={() => handleToggle(alert.id)} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #30363d', background: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 12 }}>⏸ Pause</button>}
                    {alert.status === 'paused'  && <button onClick={() => handleToggle(alert.id)} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #30363d', background: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 12 }}>▶ Resume</button>}
                    <button onClick={() => handleDelete(alert.id)} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(248,81,73,0.3)', background: 'rgba(248,81,73,0.1)', color: '#f85149', cursor: 'pointer', fontSize: 12 }}>✕</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {showCreate  && <CreateModal   token={tokenRef.current} prices={prices} onClose={() => setShowCreate(false)}  onCreated={a => setAlerts(prev => [a, ...prev])} />}
      {showWebhook && <WebhookSettings token={tokenRef.current} prices={prices} onClose={() => { setShowWebhook(false); refreshWebhook(); }} onSaved={refreshWebhook} />}
    </CockpitShell>
  );
}
