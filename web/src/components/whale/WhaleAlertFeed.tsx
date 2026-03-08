'use client';

import { useEffect, useState, useCallback } from 'react';

interface WhaleTxn {
  id: string;
  chain: string;
  asset: string;
  amount_native: number;
  amount_usd: number;
  from_address: string;
  to_address: string;
  from_label: string | null;
  to_label: string | null;
  from_category: string | null;
  to_category: string | null;
  flow_type: string;
  is_otc_suspected: boolean;
  alert_tier: string;
  timestamp: string;
  tx_hash: string;
  block_number?: number;
  liquidation: boolean;
  pending: boolean;
}

interface WhaleRecentResponse {
  transactions: WhaleTxn[];
  total_usd_moved: number;
  generated_at: string;
}

interface Props {
  limit?: number;
  chain?: string;
  asset?: string;
  flowType?: string;
}

// Flow type → display config
const FLOW_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  exchange_deposit:    { label: 'Inflow',    color: '#ff3d5a', bg: 'rgba(255,61,90,0.08)',   border: 'rgba(255,61,90,0.2)'   },
  exchange_withdrawal: { label: 'Outflow',   color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',   border: 'rgba(0,229,160,0.2)'   },
  otc_suspected:       { label: 'OTC',       color: '#a855f7', bg: 'rgba(168,85,247,0.08)',  border: 'rgba(168,85,247,0.2)'  },
  wallet_to_wallet:    { label: 'Transfer',  color: '#788098', bg: 'rgba(120,128,152,0.08)', border: 'rgba(120,128,152,0.2)' },
};

const TIER_CONFIG: Record<string, { icon: string; color: string }> = {
  MEGA:     { icon: '🚨', color: '#EF4444' },
  LARGE:    { icon: '🐋', color: '#F59E0B' },
  STANDARD: { icon: '●',  color: '#94A3B8' },
};

const ASSET_GRAD: Record<string, string> = {
  BTC:  'linear-gradient(135deg,#f7931a,#e07c10)',
  ETH:  'linear-gradient(135deg,#627eea,#4f67c8)',
  SOL:  'linear-gradient(135deg,#9945ff,#14f195)',
  USDT: 'linear-gradient(135deg,#26a17b,#1a8060)',
  USDC: 'linear-gradient(135deg,#2775ca,#1a5ca8)',
};

function fmtUsd(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function fmtNative(amount: number, asset: string): string {
  if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M ${asset}`;
  if (amount >= 1e3) return `${(amount / 1e3).toFixed(1)}K ${asset}`;
  return `${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${asset}`;
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const EXPLORER_TX: Record<string, string> = {
  ETH:      'https://etherscan.io/tx/',
  POLYGON:  'https://polygonscan.com/tx/',
  ARBITRUM: 'https://arbiscan.io/tx/',
  AVALANCHE:'https://snowtrace.io/tx/',
  LINEA:    'https://lineascan.build/tx/',
  SOL:      'https://solscan.io/tx/',
  BTC:      'https://blockstream.info/tx/',
  TRON:     'https://tronscan.org/#/transaction/',
};

function explorerUrl(chain: string, hash: string): string {
  const base = EXPLORER_TX[chain?.toUpperCase()] ?? 'https://etherscan.io/tx/';
  return `${base}${hash}`;
}

function shortenAddress(addr: string): string {
  if (!addr) return '—';
  if (addr.length <= 12) return addr;
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

export default function WhaleAlertFeed({ limit = 20, chain = 'all', asset, flowType = 'all' }: Props) {
  const [data, setData] = useState<WhaleRecentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) { setError('Not authenticated'); setLoading(false); return; }

      const params = new URLSearchParams({ limit: String(limit), chain, flow_type: flowType });
      if (asset) params.set('asset', asset);

      const resp = await fetch(`/api/whale/recent?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (resp.status === 403) { setError('Requires Premium+ subscription'); setLoading(false); return; }
      if (!resp.ok) throw new Error(`${resp.status}`);

      const json = await resp.json();
      setData(json);
      setError(null);
    } catch (e: unknown) {
      setError('Failed to load whale data');
    } finally {
      setLoading(false);
    }
  }, [limit, chain, asset, flowType]);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 60_000);
    return () => clearInterval(id);
  }, [fetchData]);

  // Loading skeleton
  if (loading) return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
          Large On-Chain Moves
        </span>
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{ padding: '10px 14px', borderBottom: '1px solid #0f1318', display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ width: 22, height: 22, borderRadius: 4, background: '#1a2030', flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ height: 10, background: '#1a2030', borderRadius: 3, width: '60%', marginBottom: 4 }} />
            <div style={{ height: 8, background: '#131720', borderRadius: 3, width: '35%' }} />
          </div>
        </div>
      ))}
    </div>
  );

  // Error / upgrade prompt
  if (error) return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '24px 20px', textAlign: 'center' }}>
      <div style={{ fontSize: 22, marginBottom: 8 }}>🐋</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', lineHeight: 1.6 }}>{error}</div>
    </div>
  );

  const txns = data?.transactions ?? [];

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>
            Large On-Chain Moves
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase',
            padding: '1px 5px', borderRadius: 2,
            background: 'rgba(0,229,160,0.08)', color: '#00e5a0', border: '1px solid rgba(0,229,160,0.2)',
            display: 'inline-flex', alignItems: 'center', gap: 3,
          }}>
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
            Live
          </span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a', letterSpacing: '0.5px' }}>
          {txns.length > 0 ? `${fmtUsd(data?.total_usd_moved ?? 0)} total` : '≥$10M threshold'}
        </span>
      </div>

      {/* Feed rows */}
      {txns.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a' }}>
          No whale moves detected in this window
        </div>
      ) : txns.map(tx => {
        const flow = FLOW_CONFIG[tx.flow_type] ?? FLOW_CONFIG.wallet_to_wallet;
        const tier = TIER_CONFIG[tx.alert_tier] ?? TIER_CONFIG.STANDARD;
        const grad = ASSET_GRAD[tx.asset] ?? 'linear-gradient(135deg,#3d7fff,#0050cc)';
        const isExp = expanded === tx.id;

        return (
          <div key={tx.id}>
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 14px', borderBottom: '1px solid #0f1318',
                cursor: 'pointer', transition: 'background 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              onClick={() => setExpanded(isExp ? null : tx.id)}
            >
              {/* Asset avatar */}
              <div style={{
                width: 22, height: 22, borderRadius: 4, flexShrink: 0,
                background: grad, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-mono)', fontSize: 6.5, fontWeight: 700, color: '#08090c',
              }}>
                {tx.asset.slice(0, 3)}
              </div>

              {/* Description */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0', marginBottom: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <span style={{ color: tier.color, marginRight: 4 }}>{tier.icon}</span>
                  {fmtNative(tx.amount_native, tx.asset)}
                  {' '}
                  <span style={{ color: '#788098', fontWeight: 400 }}>
                    {tx.from_label ?? shortenAddress(tx.from_address)} → {tx.to_label ?? shortenAddress(tx.to_address)}
                  </span>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#38405a' }}>
                  {fmtUsd(tx.amount_usd)} · {tx.chain} · {timeAgo(tx.timestamp)}
                  {tx.pending && <span style={{ color: '#9b7cf4', marginLeft: 4 }}>⏳ Pending</span>}
                </div>
              </div>

              {/* Flow badge */}
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase',
                padding: '2px 6px', borderRadius: 2, flexShrink: 0,
                background: flow.bg, color: flow.color, border: `1px solid ${flow.border}`,
              }}>
                {flow.label}
              </div>
            </div>

            {/* Expanded details */}
            {isExp && (
              <div style={{
                padding: '8px 14px 10px 46px',
                background: '#0d1019', borderBottom: '1px solid #0f1318',
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
                  {[
                    ['From', tx.from_label ?? shortenAddress(tx.from_address)],
                    ['To',   tx.to_label   ?? shortenAddress(tx.to_address)],
                    ['Tx Hash', shortenAddress(tx.tx_hash)],
                    ['Block', String(tx.block_number || '—')],
                    ['Flow Type', tx.flow_type.replace(/_/g, ' ')],
                    ['OTC Suspected', tx.is_otc_suspected ? 'Yes' : 'No'],
                  ].map(([k, v]) => (
                    <div key={k} style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a' }}>
                      <span style={{ color: '#506080' }}>{k}: </span>{v}
                    </div>
                  ))}
                </div>
                {tx.tx_hash && (
                  <a
                    href={explorerUrl(tx.chain, tx.tx_hash)}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: '#3d7fff', marginTop: 4, display: 'inline-block' }}
                  >
                    View on Explorer →
                  </a>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
