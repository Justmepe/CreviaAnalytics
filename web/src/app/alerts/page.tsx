'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

const TYPE_META: Record<string, { label: string; color: string; desc: (v: number) => string }> = {
  price_above:     { label: 'Above', color: '#00d4aa', desc: (v) => `crosses above $${v.toLocaleString()}` },
  price_below:     { label: 'Below', color: '#f03e5a', desc: (v) => `drops below $${v.toLocaleString()}`   },
  pct_change_up:   { label: '+%',    color: '#00d4aa', desc: (v) => `is up ${v}% in 24h`                  },
  pct_change_down: { label: '-%',    color: '#f03e5a', desc: (v) => `is down ${v}% in 24h`                },
};

const FREQ_META: Record<string, string> = { once: 'Once', daily: 'Daily', always: 'Always' };

function conditionText(a: Alert) {
  const m = TYPE_META[a.alert_type];
  return m ? `${a.asset} ${m.desc(a.threshold_value)}` : `${a.asset} alert`;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function dotColor(status: string) {
  if (status === 'active')    return '#00d4aa';
  if (status === 'triggered') return '#f0a030';
  return '#38405a';
}

// ---------------------------------------------------------------------------
// Discord message preview
// ---------------------------------------------------------------------------

function DiscordPreview({ asset, alertType, value }: { asset: string; alertType: string; value: number }) {
  const m = TYPE_META[alertType] || TYPE_META.price_above;
  return (
    <div style={{ background: '#36393f', borderRadius: 8, overflow: 'hidden', border: '1px solid #202225' }}>
      <div style={{ background: '#2f3136', padding: '8px 12px', borderBottom: '1px solid #202225', display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#00d4aa', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#0d1117' }}>C</div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#dcddde' }}>Crevia Analytics</div>
          <div style={{ fontSize: 9, color: '#72767d' }}>#price-alerts</div>
        </div>
      </div>
      <div style={{ padding: '12px 14px' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#00d4aa', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🔔</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#00d4aa', marginBottom: 3 }}>
              Crevia Alerts <span style={{ fontSize: 9, color: '#72767d', fontWeight: 400, background: '#5865f2', padding: '1px 4px', borderRadius: 2, marginLeft: 4 }}>BOT</span>
            </div>
            <div style={{ background: '#2f3136', borderLeft: '3px solid #00d4aa', borderRadius: '0 4px 4px 0', padding: '10px 12px' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#ffffff', marginBottom: 6 }}>🔔 Crevia Alert Triggered</div>
              <div style={{ fontSize: 11, color: '#dcddde', marginBottom: 10 }}>
                <strong>{asset}</strong> {m.desc(value)}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                {[
                  { name: 'Current Price', value: alertType.startsWith('pct') ? '—' : `$${value.toLocaleString()}` },
                  { name: '24h Change',    value: '+3.2%' },
                  { name: 'Frequency',     value: 'Once' },
                ].map(f => (
                  <div key={f.name}>
                    <div style={{ fontSize: 9, fontWeight: 700, color: '#b9bbbe', textTransform: 'uppercase', marginBottom: 1 }}>{f.name}</div>
                    <div style={{ fontSize: 11, color: '#dcddde' }}>{f.value}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 9, color: '#72767d', marginTop: 8 }}>Crevia Analytics · creviacockpit.com</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Webhook modal
// ---------------------------------------------------------------------------

function WebhookModal({ onClose, token }: { onClose: () => void; token: string }) {
  const [url, setUrl]           = useState('');
  const [masked, setMasked]     = useState<string | null>(null);
  const [hasWebhook, setHasWH]  = useState(false);
  const [saving, setSaving]     = useState(false);
  const [testing, setTesting]   = useState(false);
  const [msg, setMsg]           = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/alerts/webhook`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(d => { setHasWH(d.has_webhook); setMasked(d.masked_url); }).catch(() => {});
  }, [token]);

  const save = async () => {
    if (!url.includes('discord.com/api/webhooks/')) { setMsg({ type: 'err', text: 'Must be a valid Discord webhook URL' }); return; }
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/alerts/webhook`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ webhook_url: url }) });
      if (!r.ok) throw new Error();
      setHasWH(true); setMasked(url.slice(0, 40) + '...' + url.slice(-8)); setUrl('');
      setMsg({ type: 'ok', text: 'Webhook saved' });
    } catch { setMsg({ type: 'err', text: 'Failed to save' }); }
    finally { setSaving(false); }
  };

  const test = async () => {
    setTesting(true); setMsg(null);
    try {
      const r = await fetch(`${API}/api/alerts/webhook/test`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Test failed');
      setMsg({ type: 'ok', text: 'Test message sent to Discord!' });
    } catch (e: unknown) { setMsg({ type: 'err', text: e instanceof Error ? e.message : 'Webhook test failed' }); }
    finally { setTesting(false); }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={{ ...modalStyle, maxWidth: 500 }} onClick={e => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <span style={modalTitleStyle}>Discord Webhook</span>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: hasWebhook ? 'rgba(0,212,170,0.07)' : 'rgba(240,163,48,0.07)', border: `1px solid ${hasWebhook ? 'rgba(0,212,170,0.2)' : 'rgba(240,163,48,0.2)'}`, borderRadius: 6, padding: '10px 14px' }}>
            <span style={{ fontSize: 18 }}>{hasWebhook ? '✅' : '⚠️'}</span>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#e2e6f0' }}>{hasWebhook ? 'Webhook Connected' : 'No Webhook Configured'}</div>
              {masked && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098', marginTop: 2 }}>{masked}</div>}
            </div>
          </div>

          <div>
            <div style={labelStyle}>Webhook URL</div>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://discord.com/api/webhooks/..." style={inputStyle} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 4 }}>
              Discord: Channel Settings → Integrations → Webhooks → New Webhook → Copy URL
            </div>
          </div>

          {msg && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: msg.type === 'ok' ? '#00d4aa' : '#f03e5a', padding: '8px 10px', background: msg.type === 'ok' ? 'rgba(0,212,170,0.07)' : 'rgba(240,62,90,0.07)', borderRadius: 4 }}>{msg.text}</div>}

          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a' }}>Preview</div>
          <DiscordPreview asset="BTC" alertType="price_above" value={72000} />

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={save} disabled={saving || !url} style={{ ...btnPrimaryStyle, flex: 1, opacity: saving || !url ? 0.5 : 1 }}>{saving ? 'Saving…' : 'Save Webhook'}</button>
            {hasWebhook && <button onClick={test} disabled={testing} style={{ ...btnSecondaryStyle, flex: 1, opacity: testing ? 0.5 : 1 }}>{testing ? 'Testing…' : 'Send Test'}</button>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create alert modal (3 steps)
// ---------------------------------------------------------------------------

const ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'ARB', 'OP', 'INJ', 'TIA'];
const ALERT_TYPES = [
  { value: 'price_above',     label: 'Price above',   icon: '↑',  color: '#00d4aa' },
  { value: 'price_below',     label: 'Price below',   icon: '↓',  color: '#f03e5a' },
  { value: 'pct_change_up',   label: '% Change up',   icon: '+%', color: '#00d4aa' },
  { value: 'pct_change_down', label: '% Change down', icon: '-%', color: '#f03e5a' },
];
const FREQS = [
  { value: 'once',   label: 'Once',   desc: 'Fire once then deactivate'     },
  { value: 'daily',  label: 'Daily',  desc: 'Re-arm every 24 hours'         },
  { value: 'always', label: 'Always', desc: '5-min cooldown between fires'  },
];

function CreateModal({ onClose, onCreated, token }: { onClose: () => void; onCreated: (a: Alert) => void; token: string }) {
  const [step, setStep]         = useState(1);
  const [asset, setAsset]       = useState('BTC');
  const [alertType, setType]    = useState('price_above');
  const [value, setValue]       = useState('');
  const [frequency, setFreq]    = useState('once');
  const [note, setNote]         = useState('');
  const [submitting, setSub]    = useState(false);
  const [err, setErr]           = useState('');

  const isPct = alertType.startsWith('pct_');

  const submit = async () => {
    setSub(true); setErr('');
    try {
      const r = await fetch(`${API}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ asset, alert_type: alertType, threshold_value: parseFloat(value), frequency, note: note || null }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Failed');
      onCreated(data); onClose();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : 'Error'); }
    finally { setSub(false); }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={{ ...modalStyle, maxWidth: 480 }} onClick={e => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <span style={modalTitleStyle}>New Alert</span>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {[1, 2, 3].map(s => (
              <div key={s} style={{ width: 18, height: 18, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 700, background: step >= s ? '#00d4aa' : '#1a2030', color: step >= s ? '#0d1117' : '#38405a', fontFamily: 'var(--font-mono)' }}>{s}</div>
            ))}
            <button onClick={onClose} style={{ ...closeBtnStyle, marginLeft: 6 }}>✕</button>
          </div>
        </div>

        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {step === 1 && (
            <>
              <div>
                <div style={labelStyle}>Asset</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                  {ASSETS.map(a => (
                    <button key={a} onClick={() => setAsset(a)} style={{ ...chipStyle, background: asset === a ? '#00d4aa' : '#151c28', color: asset === a ? '#0d1117' : '#788098', border: `1px solid ${asset === a ? '#00d4aa' : '#1a2030'}` }}>{a}</button>
                  ))}
                </div>
              </div>
              <div>
                <div style={labelStyle}>Alert Type</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                  {ALERT_TYPES.map(t => (
                    <button key={t.value} onClick={() => setType(t.value)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 6, border: `1px solid ${alertType === t.value ? t.color + '55' : '#1a2030'}`, background: alertType === t.value ? t.color + '11' : '#10141c', cursor: 'pointer' }}>
                      <span style={{ fontSize: 14, width: 22, textAlign: 'center', color: t.color, fontWeight: 700 }}>{t.icon}</span>
                      <span style={{ fontSize: 12, color: alertType === t.value ? '#e2e6f0' : '#788098' }}>{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={() => setStep(2)} style={btnPrimaryStyle}>Next →</button>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <div style={labelStyle}>{isPct ? 'Percentage Threshold (%)' : 'Price Level (USD)'}</div>
                <input type="number" value={value} onChange={e => setValue(e.target.value)} placeholder={isPct ? 'e.g. 5 (for 5%)' : 'e.g. 72000'} style={inputStyle} autoFocus />
                {!isPct && value && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 4 }}>{asset} {TYPE_META[alertType]?.desc(parseFloat(value) || 0)}</div>}
              </div>
              <div>
                <div style={labelStyle}>Frequency</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                  {FREQS.map(f => (
                    <button key={f.value} onClick={() => setFreq(f.value)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 6, border: `1px solid ${frequency === f.value ? '#00d4aa55' : '#1a2030'}`, background: frequency === f.value ? 'rgba(0,212,170,0.08)' : '#10141c', cursor: 'pointer' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, color: frequency === f.value ? '#e2e6f0' : '#788098' }}>{f.label}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>{f.desc}</div>
                      </div>
                      {frequency === f.value && <span style={{ color: '#00d4aa' }}>✓</span>}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div style={labelStyle}>Note (optional)</div>
                <input value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. SL alert for long position" style={inputStyle} />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => setStep(1)} style={btnSecondaryStyle}>← Back</button>
                <button onClick={() => { if (value && parseFloat(value) > 0) setStep(3); }} disabled={!value || parseFloat(value) <= 0} style={{ ...btnPrimaryStyle, flex: 1, opacity: !value || parseFloat(value) <= 0 ? 0.5 : 1 }}>Preview →</button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '12px 14px' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 8 }}>Summary</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {[
                    { label: 'Asset', value: asset },
                    { label: 'Type', value: ALERT_TYPES.find(t => t.value === alertType)?.label || alertType },
                    { label: isPct ? 'Threshold' : 'Price Level', value: isPct ? `${value}%` : `$${parseFloat(value).toLocaleString()}` },
                    { label: 'Frequency', value: FREQS.find(f => f.value === frequency)?.label || frequency },
                  ].map(r => (
                    <div key={r.label}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', marginBottom: 2 }}>{r.label}</div>
                      <div style={{ fontSize: 12, color: '#e2e6f0' }}>{r.value}</div>
                    </div>
                  ))}
                </div>
                {note && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#788098', marginTop: 8, borderTop: '1px solid #1a2030', paddingTop: 8 }}>{note}</div>}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a' }}>Discord Preview</div>
              <DiscordPreview asset={asset} alertType={alertType} value={parseFloat(value)} />
              {err && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#f03e5a' }}>{err}</div>}
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => setStep(2)} style={btnSecondaryStyle}>← Back</button>
                <button onClick={submit} disabled={submitting} style={{ ...btnPrimaryStyle, flex: 1, opacity: submitting ? 0.5 : 1 }}>{submitting ? 'Creating…' : 'Create Alert'}</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const overlayStyle: React.CSSProperties = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' };
const modalStyle: React.CSSProperties   = { background: '#0d1117', border: '1px solid #1a2030', borderRadius: 10, width: '95%', maxHeight: '90vh', overflowY: 'auto' };
const modalHeaderStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid #1a2030' };
const modalTitleStyle: React.CSSProperties  = { fontFamily: 'var(--font-bebas)', fontSize: 20, letterSpacing: '2px', color: '#e2e6f0' };
const closeBtnStyle: React.CSSProperties    = { background: 'none', border: 'none', color: '#38405a', fontSize: 16, cursor: 'pointer', padding: 4 };
const labelStyle: React.CSSProperties      = { fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase' as const, color: '#788098', marginBottom: 4 };
const inputStyle: React.CSSProperties      = { width: '100%', background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '9px 12px', color: '#e2e6f0', fontFamily: 'var(--font-mono)', fontSize: 12, outline: 'none', boxSizing: 'border-box' as const };
const btnPrimaryStyle: React.CSSProperties = { background: '#00d4aa', color: '#0d1117', border: 'none', borderRadius: 6, padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.8px', fontWeight: 600, cursor: 'pointer', textTransform: 'uppercase' as const };
const btnSecondaryStyle: React.CSSProperties = { background: '#10141c', color: '#788098', border: '1px solid #1a2030', borderRadius: 6, padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.8px', cursor: 'pointer', textTransform: 'uppercase' as const };
const chipStyle: React.CSSProperties = { padding: '4px 10px', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 10, cursor: 'pointer', fontWeight: 600 };

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AlertsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [alerts, setAlerts]           = useState<Alert[]>([]);
  const [fetching, setFetching]       = useState(true);
  const [tab, setTab]                 = useState<'active' | 'triggered' | 'all'>('active');
  const [showCreate, setShowCreate]   = useState(false);
  const [showWebhook, setShowWebhook] = useState(false);
  const [webhookOk, setWebhookOk]     = useState(false);
  const tokenRef = useRef('');

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

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
      <div style={{ minHeight: '100vh', background: '#070809', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#38405a', letterSpacing: '1px' }}>LOADING…</span>
      </div>
    );
  }

  const active    = alerts.filter(a => a.status === 'active');
  const triggered = alerts.filter(a => a.status === 'triggered');
  const filtered  = tab === 'active' ? active : tab === 'triggered' ? triggered : alerts;

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 26, letterSpacing: '2px', color: '#e2e6f0', lineHeight: 1 }}>My Alerts</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginTop: 4 }}>Price alerts · delivered to your Discord channel</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setShowWebhook(true)} style={{ ...btnSecondaryStyle, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: webhookOk ? '#00d4aa' : '#38405a', display: 'inline-block' }} />
              Discord
            </button>
            <button onClick={() => setShowCreate(true)} style={btnPrimaryStyle}>+ New Alert</button>
          </div>
        </div>

        {/* Summary cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Active',    value: String(active.length),    color: '#00d4aa' },
            { label: 'Triggered', value: String(triggered.length), color: '#f0a030' },
            { label: 'Total',     value: String(alerts.length),    color: '#3d7fff' },
            { label: 'Discord',   value: webhookOk ? 'On' : 'Off', color: webhookOk ? '#00d4aa' : '#38405a' },
          ].map(c => (
            <div key={c.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{c.label}</div>
              <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 22, lineHeight: 1, color: c.color }}>{c.value}</div>
            </div>
          ))}
        </div>

        {/* Main grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 12, alignItems: 'start' }}>

          {/* Alert list */}
          <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid #1a2030' }}>
              {(['active', 'triggered', 'all'] as const).map(t => (
                <button key={t} onClick={() => setTab(t)} style={{ flex: 1, padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: tab === t ? '#e2e6f0' : '#38405a', background: 'none', border: 'none', borderBottom: `2px solid ${tab === t ? '#00d4aa' : 'transparent'}`, cursor: 'pointer', marginBottom: -1 }}>
                  {t} ({t === 'active' ? active.length : t === 'triggered' ? triggered.length : alerts.length})
                </button>
              ))}
            </div>

            {fetching ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a' }}>Loading…</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, marginBottom: 10 }}>🔔</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', marginBottom: 12 }}>No {tab} alerts</div>
                {tab === 'active' && <button onClick={() => setShowCreate(true)} style={{ ...btnPrimaryStyle, fontSize: 9 }}>Create First Alert</button>}
              </div>
            ) : filtered.map(alert => {
              const typeMeta = TYPE_META[alert.alert_type];
              return (
                <div
                  key={alert.id}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 14px', borderBottom: '1px solid #0f1318', opacity: alert.status === 'paused' ? 0.5 : 1 }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ width: 6, height: 6, borderRadius: '50%', marginTop: 6, flexShrink: 0, background: dotColor(alert.status) }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 12, fontWeight: 500, color: '#e2e6f0' }}>{conditionText(alert)}</span>
                      {typeMeta && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2, background: typeMeta.color + '15', color: typeMeta.color, border: `1px solid ${typeMeta.color}33` }}>{typeMeta.label}</span>}
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, color: '#38405a', padding: '1px 5px', borderRadius: 2, background: '#10141c', border: '1px solid #1a2030' }}>{FREQ_META[alert.frequency]}</span>
                      {alert.status === 'triggered' && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, letterSpacing: '0.5px', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2, background: 'rgba(240,160,48,0.1)', color: '#f0a030', border: '1px solid rgba(240,160,48,0.2)' }}>Triggered</span>}
                    </div>
                    {alert.note && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', lineHeight: 1.5 }}>{alert.note}</div>}
                    {alert.last_triggered && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', marginTop: 2 }}>Last fired: {timeAgo(alert.last_triggered)}</div>}
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0, alignItems: 'center' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', marginRight: 4 }}>{timeAgo(alert.created_at)}</div>
                    {alert.status !== 'triggered' && (
                      <button onClick={() => handleToggle(alert.id)} title={alert.status === 'active' ? 'Pause' : 'Resume'} style={{ background: 'none', border: '1px solid #1a2030', borderRadius: 4, color: '#38405a', fontSize: 11, cursor: 'pointer', padding: '3px 7px', lineHeight: 1 }}>
                        {alert.status === 'active' ? '⏸' : '▶'}
                      </button>
                    )}
                    <button onClick={() => handleDelete(alert.id)} title="Delete" style={{ background: 'none', border: '1px solid #1a2030', borderRadius: 4, color: '#38405a', fontSize: 11, cursor: 'pointer', padding: '3px 7px', lineHeight: 1 }}>✕</button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ background: webhookOk ? 'rgba(0,212,170,0.04)' : 'rgba(88,101,242,0.06)', border: `1px solid ${webhookOk ? 'rgba(0,212,170,0.15)' : 'rgba(88,101,242,0.2)'}`, borderRadius: 8, padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{webhookOk ? '✅' : '🔔'}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: webhookOk ? '#00d4aa' : '#788098', marginBottom: 6 }}>{webhookOk ? 'Discord Connected' : 'Connect Discord'}</div>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', lineHeight: 1.6, marginBottom: 12 }}>
                {webhookOk ? 'Alerts fire to your Discord channel when conditions are met.' : 'Add your Discord webhook to receive alerts directly in your server.'}
              </p>
              <button onClick={() => setShowWebhook(true)} style={{ ...btnPrimaryStyle, fontSize: 9 }}>{webhookOk ? 'Manage Webhook' : 'Set Up Webhook →'}</button>
            </div>

            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Alert Types</span>
              </div>
              {[
                { icon: '↑↓', type: 'Price Above / Below', desc: 'Trigger on price cross',         avail: true  },
                { icon: '%%', type: '% Change 24h',        desc: 'Percentage move threshold',      avail: true  },
                { icon: '🐋', type: 'Whale Move',          desc: 'Large on-chain transaction',     avail: false },
                { icon: '📡', type: 'Regime Change',       desc: 'Market regime shift detection',  avail: false },
                { icon: '⚡', type: 'Setup Alert',         desc: 'New AI trade setup detected',    avail: false },
              ].map(item => (
                <div key={item.type} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', borderBottom: '1px solid #0f1318', opacity: item.avail ? 1 : 0.45 }}>
                  <span style={{ fontSize: 13, flexShrink: 0, width: 20, textAlign: 'center' }}>{item.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0' }}>{item.type}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>{item.desc}</div>
                  </div>
                  {!item.avail && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7.5, color: '#9b7cf4', border: '1px solid rgba(155,124,244,0.3)', borderRadius: 2, padding: '1px 5px', flexShrink: 0 }}>Soon</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {showCreate && (
        <CreateModal token={tokenRef.current} onClose={() => setShowCreate(false)} onCreated={a => setAlerts(prev => [a, ...prev])} />
      )}
      {showWebhook && (
        <WebhookModal token={tokenRef.current} onClose={() => { setShowWebhook(false); refreshWebhook(); }} />
      )}
    </CockpitShell>
  );
}
