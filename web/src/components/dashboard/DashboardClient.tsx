'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getPortfolioStats, getJournalEntries, syncPortfolio, timeAgo } from '@/lib/api';
import type { PortfolioStats, JournalEntry, MarketRegime, TradeSetup, ContentPost, PortfolioSummary } from '@/types';
import CockpitShell from '@/components/layout/CockpitShell';

interface DashboardClientProps {
  regime: MarketRegime | null;
  setups: TradeSetup[];
  recentContent: ContentPost[];
  btcPrice: number | null;
  ethPrice: number | null;
  marketCap: number | null;
  fearGreed: number | null;
  fearGreedLabel: string | null;
}

// ── Tier system ─────────────────────────────────────────────────────────────
const TIER_LEVEL: Record<string, number> = { free: 0, basic: 1, pro: 2, enterprise: 3 };

const TIER_META: Record<string, { icon: string; label: string; color: string; bg: string; border: string }> = {
  free:       { icon: '○',  label: 'Free',     color: '#788098', bg: 'rgba(30,35,50,0.5)',       border: '#222c42'               },
  basic:      { icon: '⬡',  label: 'Basic',    color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',     border: 'rgba(0,229,160,0.25)'  },
  pro:        { icon: '⚡', label: 'Premium',  color: '#3d7fff', bg: 'rgba(61,127,255,0.08)',    border: 'rgba(61,127,255,0.25)' },
  enterprise: { icon: '◈',  label: 'Premium+', color: '#9b7cf4', bg: 'rgba(155,124,244,0.08)',   border: 'rgba(155,124,244,0.25)'},
};

// ── Regime colours ───────────────────────────────────────────────────────────
const REGIME_COLORS: Record<string, { text: string; bg: string; border: string; hex: string }> = {
  RISK_ON:               { text: '#00e5a0', bg: 'rgba(0,229,160,0.07)',   border: 'rgba(0,229,160,0.2)',   hex: '#00e5a0' },
  ACCUMULATION:          { text: '#00e5a0', bg: 'rgba(0,229,160,0.07)',   border: 'rgba(0,229,160,0.2)',   hex: '#00e5a0' },
  ALTSEASON_CONFIRMED:   { text: '#f0a030', bg: 'rgba(240,160,48,0.07)',  border: 'rgba(240,160,48,0.2)',  hex: '#f0a030' },
  NEUTRAL:               { text: '#788098', bg: 'rgba(30,35,50,0.5)',     border: '#1a2030',               hex: '#788098' },
  DISTRIBUTION:          { text: '#f0a030', bg: 'rgba(240,160,48,0.07)',  border: 'rgba(240,160,48,0.2)',  hex: '#f0a030' },
  RISK_OFF:              { text: '#ff3d5a', bg: 'rgba(255,61,90,0.07)',   border: 'rgba(255,61,90,0.2)',   hex: '#ff3d5a' },
  VOLATILITY_EXPANSION:  { text: '#9b7cf4', bg: 'rgba(155,124,244,0.07)', border: 'rgba(155,124,244,0.2)', hex: '#9b7cf4' },
};

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmtPrice(p: number | null): string {
  if (!p) return '--';
  return p >= 1000
    ? `$${p.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
    : `$${p.toFixed(2)}`;
}
function fmtLarge(n: number | null): string {
  if (!n) return '--';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(1)}B`;
  return `$${n.toLocaleString()}`;
}

// ── TierLock: blur+overlay for sections free users can't access ──────────────
function TierLock({ children, title, minTierLabel = 'Basic' }: {
  children: React.ReactNode;
  title?: string;
  minTierLabel?: string;
}) {
  return (
    <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', border: '1px solid #1a2030' }}>
      <div style={{ filter: 'blur(4px)', userSelect: 'none', pointerEvents: 'none', opacity: 0.35 }}>
        {children}
      </div>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'rgba(7,8,9,0.75)', backdropFilter: 'blur(2px)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 10, zIndex: 10,
      }}>
        <div style={{ fontSize: 22, opacity: 0.6 }}>⬡</div>
        {title && (
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#788098' }}>
            {title}
          </div>
        )}
        <Link href="/waitlist" style={{
          fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
          color: '#08090c', background: '#f0a030', padding: '6px 16px',
          borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
        }}>
          Unlock with {minTierLabel} →
        </Link>
      </div>
    </div>
  );
}

// ── PremiumLock: for sections that need Pro/Premium ──────────────────────────
function PremiumLock({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: 'absolute', inset: 0, backdropFilter: 'blur(4px)', background: 'rgba(7,8,9,0.75)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, zIndex: 10, borderRadius: 8 }}>
      <div style={{ fontSize: 20 }}>⚡</div>
      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '0.5px', textTransform: 'uppercase', color: '#788098' }}>
        Premium Feature
      </div>
      <Link href="/waitlist" style={{
        fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
        color: '#08090c', background: '#f0a030', padding: '5px 14px',
        borderRadius: 3, fontWeight: 500, textDecoration: 'none', display: 'inline-block',
      }}>
        Upgrade to Premium →
      </Link>
      <div style={{ display: 'none' }}>{children}</div>
    </div>
  );
}

// ── Exchange portfolio widget ────────────────────────────────────────────────
const EXCHANGE_ICON: Record<string, string> = { binance: 'B', bybit: 'Y', okx: 'O' };
const EXCHANGE_COLOR: Record<string, string> = { binance: '#f3ba2f', bybit: '#f0a030', okx: '#3d7fff' };

function ExchangePortfolioWidget() {
  const [summaries, setSummaries] = useState<PortfolioSummary[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');

  const doSync = useCallback(async () => {
    setSyncing(true); setError('');
    try { setSummaries(await syncPortfolio()); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : 'Sync failed'); }
    finally { setSyncing(false); }
  }, []);

  const totalUSD = summaries?.reduce((acc, s) => acc + s.total_usd, 0) ?? 0;

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px', marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Exchange Portfolio</div>
          {summaries && totalUSD > 0 && (
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 28, color: '#e2e6f0', lineHeight: 1 }}>
              ${totalUSD.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', marginLeft: 6, fontWeight: 300 }}>USD</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link href="/account" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', letterSpacing: '0.5px' }}>
            Manage keys →
          </Link>
          <button onClick={doSync} disabled={syncing} style={{
            fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
            background: '#151a26', border: '1px solid #1a2030', borderRadius: 4,
            color: '#788098', padding: '5px 12px', cursor: 'pointer', opacity: syncing ? 0.5 : 1,
          }}>
            {syncing ? 'Syncing…' : '↻ Sync'}
          </button>
        </div>
      </div>
      {error && <div style={{ fontSize: 11, color: '#ff3d5a', marginBottom: 10 }}>{error}</div>}
      {summaries === null ? (
        <div style={{ padding: '12px 0', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
          Connect your exchange to see live balances.{' '}
          <Link href="/account" style={{ color: '#00e5a0', textDecoration: 'none' }}>Add API keys →</Link>
        </div>
      ) : summaries.length === 0 ? (
        <div style={{ padding: '12px 0', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
          No exchanges connected yet.{' '}
          <Link href="/account" style={{ color: '#00e5a0', textDecoration: 'none' }}>Connect Exchange →</Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {summaries.map(s => (
            <div key={s.key_id}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 20, height: 20, borderRadius: 4, background: '#1a2030', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 8, fontWeight: 700, color: EXCHANGE_COLOR[s.exchange] || '#788098' }}>
                  {EXCHANGE_ICON[s.exchange] || s.exchange[0].toUpperCase()}
                </div>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: '#e2e6f0', textTransform: 'capitalize' }}>{s.exchange}</span>
                {s.label && <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>— {s.label}</span>}
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: '#e2e6f0' }}>
                  ${s.total_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              {s.error ? (
                <div style={{ fontSize: 10, color: '#ff3d5a', paddingLeft: 28 }}>{s.error}</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5, paddingLeft: 28 }}>
                  {s.holdings.slice(0, 6).map(h => (
                    <div key={h.asset} style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 4, padding: '6px 8px' }}>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, fontWeight: 700, color: '#e2e6f0' }}>{h.asset}</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#38405a' }}>{h.total < 0.01 ? h.total.toFixed(6) : h.total.toFixed(4)}</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#788098', marginTop: 2 }}>
                        ${h.usd_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main dashboard ───────────────────────────────────────────────────────────
export default function DashboardClient({
  regime, setups, recentContent, btcPrice, ethPrice, marketCap, fearGreed, fearGreedLabel,
}: DashboardClientProps) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [openTrades, setOpenTrades] = useState<JournalEntry[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      Promise.all([
        getPortfolioStats().catch(() => null),
        getJournalEntries('open').catch(() => []),
      ]).then(([s, trades]) => {
        setStats(s);
        setOpenTrades(trades);
      }).finally(() => setStatsLoading(false));
    }
  }, [user]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#070809', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 11, color: '#38405a', letterSpacing: '1px' }}>LOADING COCKPIT…</div>
      </div>
    );
  }
  if (!user) return null;

  const tierLevel = TIER_LEVEL[user.tier] ?? 0;
  const isFree    = tierLevel === 0;
  const isPremium = tierLevel >= 2;
  const regimeStyle = regime
    ? REGIME_COLORS[regime.regime_name] || REGIME_COLORS.NEUTRAL
    : REGIME_COLORS.NEUTRAL;
  const totalPnl = stats?.total_pnl_usd ?? 0;
  const openRiskUsd = openTrades.reduce((acc, t) => {
    if (t.stop_loss_price && t.entry_price && t.quantity) {
      return acc + Math.abs(t.entry_price - t.stop_loss_price) * t.quantity;
    }
    return acc;
  }, 0);

  return (
    <CockpitShell>
      <div style={{ padding: '14px 16px' }}>

        {/* ── Page subtitle (context line) ── */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', letterSpacing: '0.5px' }}>
            {isFree
              ? 'Cockpit Feed is live. Upgrade to unlock your full trading dashboard.'
              : `${isPremium ? 'Full cockpit access' : 'Basic cockpit access'} · market intelligence overview`}
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════
            FREE TIER: Feed visible + locked dashboard preview
            ═══════════════════════════════════════════════════ */}
        {isFree ? (
          <>
            {/* Upgrade CTA banner */}
            <div style={{ background: 'rgba(240,160,48,0.07)', border: '1px solid rgba(240,160,48,0.2)', borderRadius: 8, padding: '16px 20px', marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontFamily: 'var(--font-syne)', fontSize: 14, fontWeight: 700, color: '#f0a030', marginBottom: 3 }}>
                  Unlock your full trading dashboard
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', letterSpacing: '0.3px' }}>
                  Regime detection · AI trade setups · Risk calculator · Portfolio tracking · Whale intel
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexShrink: 0, marginLeft: 20 }}>
                <Link href="/waitlist" style={{
                  fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: '#08090c', background: '#f0a030', padding: '7px 16px', borderRadius: 3, fontWeight: 500, textDecoration: 'none',
                }}>
                  Join Waitlist →
                </Link>
              </div>
            </div>

            {/* Dashboard preview — blurred/locked */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <TierLock title="Market Regime · Confidence · Signals">
                <div style={{ background: '#10141c', padding: '20px', borderRadius: 8 }}>
                  <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, color: '#00e5a0' }}>ACCUMULATION</div>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', marginTop: 4 }}>80% confidence · 4 confirming signals</div>
                  <div style={{ height: 3, borderRadius: 2, background: '#1a2030', marginTop: 12 }}>
                    <div style={{ height: 3, borderRadius: 2, width: '80%', background: '#00e5a0' }} />
                  </div>
                </div>
              </TierLock>
              <TierLock title="Portfolio · P&L · Open Positions">
                <div style={{ background: '#10141c', padding: '20px', borderRadius: 8 }}>
                  <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, color: '#e2e6f0' }}>$24,831</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                    {[['Win Rate', '68%', '#00e5a0'], ['P&L', '+$1,248', '#00e5a0'], ['Open', '3', '#e2e6f0'], ['Risk', '$680', '#e2e6f0']].map(([l, v, c]) => (
                      <div key={l}>
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#38405a', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{l}</div>
                        <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 18, color: c as string }}>{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </TierLock>
            </div>

            {/* Cockpit Feed — always visible to free users */}
            <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Cockpit Feed</span>
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5a0', display: 'inline-block', animation: 'livePulse 2s ease-in-out infinite' }} />
                </div>
                <Link href="/analysis" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', letterSpacing: '0.5px' }}>View all →</Link>
              </div>
              {recentContent.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 10 }}>
                  {recentContent.map(post => (
                    <Link key={post.id} href={`/post/${post.slug}`} style={{ textDecoration: 'none' }}>
                      <div style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 6, padding: '12px 14px', cursor: 'pointer' }}>
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 6 }}>
                          {post.content_type} · {timeAgo(post.published_at)}
                        </div>
                        <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 12, fontWeight: 500, color: '#e2e6f0', lineHeight: 1.4, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                          {post.title || post.excerpt || 'Analysis'}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>No content yet — engine is generating…</div>
              )}
            </div>
          </>
        ) : (
          /* ═══════════════════════════════════════════════════
             BASIC+ TIER: Full dashboard
             ═══════════════════════════════════════════════════ */
          <>

            {/* ── Metric Row ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 10, marginBottom: 12 }}>

              {/* Portfolio Value */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Portfolio</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: '#e2e6f0', marginBottom: 2 }}>
                  {statsLoading ? '--' : stats?.total_trades ? `${totalPnl >= 0 ? '+' : ''}$${Math.abs(totalPnl).toFixed(0)}` : '--'}
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: totalPnl >= 0 ? '#00e5a0' : '#ff3d5a' }}>
                  {statsLoading ? '' : stats ? `P&L · ${stats.total_trades} trades` : 'No trades yet'}
                </div>
              </div>

              {/* Open Positions */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Positions</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: '#e2e6f0', marginBottom: 2 }}>
                  {statsLoading ? '--' : openTrades.length}
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: openTrades.length > 0 ? '#00e5a0' : '#38405a' }}>
                  {openTrades.length > 0 ? `↑ ${openTrades.length} open trade${openTrades.length > 1 ? 's' : ''}` : 'No open trades'}
                </div>
              </div>

              {/* Open Risk */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Open Risk</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: '#e2e6f0', marginBottom: 2 }}>
                  {statsLoading ? '--' : openRiskUsd > 0 ? `$${openRiskUsd.toFixed(0)}` : '$0'}
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: openRiskUsd > 0 ? '#f0a030' : '#38405a' }}>
                  {openRiskUsd > 0 ? 'at risk across positions' : 'No risk exposure'}
                </div>
              </div>

              {/* Win Rate */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Win Rate</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: stats ? (stats.win_rate >= 0.5 ? '#00e5a0' : '#ff3d5a') : '#e2e6f0', marginBottom: 2 }}>
                  {statsLoading ? '--' : stats ? `${(stats.win_rate * 100).toFixed(0)}%` : '--'}
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>
                  {stats ? `P.F. ${stats.profit_factor.toFixed(2)}` : 'Log trades to track'}
                </div>
              </div>

              {/* Regime-aligned Setups */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Setups</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: '#e2e6f0', marginBottom: 2 }}>
                  {setups.length}
                </div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: setups.length > 0 ? '#00e5a0' : '#38405a' }}>
                  {setups.length > 0 ? `↑ ${setups.filter(s => s.direction === 'LONG').length} long · ${setups.filter(s => s.direction === 'SHORT').length} short` : 'No setups yet'}
                </div>
              </div>
            </div>

            {/* ── Main 3-col grid ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.1fr 280px', gap: 12, marginBottom: 12, alignItems: 'start' }}>

              {/* COL 1: Regime + Market snapshot */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                {/* Regime card */}
                <div style={{ background: '#10141c', border: `1px solid ${regimeStyle.border}`, borderRadius: 8, padding: '16px 20px', position: 'relative', overflow: 'hidden' }}>
                  <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 80% 60% at 80% 50%, ${regimeStyle.hex}08 0%, transparent 70%)`, pointerEvents: 'none' }} />
                  <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${regimeStyle.hex}, transparent)` }} />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5a0', display: 'inline-block', animation: 'livePulse 2s ease-in-out infinite' }} />
                      Current Market Regime
                    </div>
                    <Link href="/intelligence" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>Full Intel →</Link>
                  </div>
                  {regime ? (
                    <>
                      <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 28, letterSpacing: '2px', color: regimeStyle.text, lineHeight: 1, marginBottom: 4 }}>
                        {regime.regime_name.replace(/_/g, ' ')}
                      </div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', marginBottom: 10 }}>
                        {Math.round((regime.confidence || 0) * 100)}% confidence
                      </div>
                      <div style={{ height: 3, borderRadius: 2, background: '#1a2030' }}>
                        <div style={{ height: 3, borderRadius: 2, width: `${(regime.confidence || 0) * 100}%`, background: regimeStyle.hex, transition: 'width 1s ease' }} />
                      </div>
                      {regime.trader_action && (
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', marginTop: 10, lineHeight: 1.5 }}>
                          {regime.trader_action}
                        </div>
                      )}
                    </>
                  ) : (
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>No regime data yet — start the engine.</div>
                  )}
                </div>

                {/* Market snapshot (compact) */}
                <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
                  {[
                    { label: 'BTC', value: fmtPrice(btcPrice) },
                    { label: 'ETH', value: fmtPrice(ethPrice) },
                    { label: 'MCAP', value: fmtLarge(marketCap) },
                    { label: 'F&G', value: fearGreed != null ? String(fearGreed) : '--', sub: fearGreedLabel || '' },
                  ].map((item, i) => (
                    <div key={item.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 16px', borderBottom: i < 3 ? '1px solid #1a2030' : undefined }}>
                      <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a' }}>{item.label}</span>
                      <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 11, fontWeight: 500, color: '#e2e6f0' }}>
                        {item.value}
                        {item.sub && <span style={{ fontSize: 9, color: '#38405a', marginLeft: 6 }}>{item.sub}</span>}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Quick Tools */}
                <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 14px', borderBottom: '1px solid #1a2030' }}>
                    <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Quick Access</span>
                  </div>
                  {[
                    { href: '/tools/risk-calculator', icon: '🎯', label: 'Risk Calculator',     desc: 'Size positions & R/R' },
                    { href: '/intelligence/scanner',  icon: '🔍', label: 'Opportunity Scanner', desc: 'Ranked by score',     locked: !isPremium },
                    { href: '/intelligence',          icon: '📡', label: 'Intelligence Hub',    desc: 'Regime & correlations' },
                    { href: '/journal',               icon: '📋', label: 'Trade Journal',       desc: 'Log & track trades' },
                    { href: '/market',                icon: '📊', label: 'Market Data',         desc: 'Live prices & charts' },
                  ].map(tool => (
                    <Link key={tool.href} href={tool.href} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px', borderBottom: '1px solid #1a2030', textDecoration: 'none', transition: 'background 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                      <span style={{ fontSize: 13, opacity: 0.7 }}>{tool.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 11.5, fontWeight: 500, color: '#e2e6f0' }}>{tool.label}</div>
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>{tool.desc}</div>
                      </div>
                      {tool.locked && (
                        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase', color: '#3d7fff', border: '1px solid rgba(61,127,255,0.3)', borderRadius: 2, padding: '1px 5px', background: 'rgba(61,127,255,0.08)' }}>Premium</span>
                      )}
                    </Link>
                  ))}
                </div>
              </div>

              {/* COL 2: Open Positions + Trade Setups */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                {/* Open positions board */}
                <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Open Positions</span>
                    <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', letterSpacing: '0.5px' }}>Journal →</Link>
                  </div>
                  {statsLoading ? (
                    <div style={{ padding: '20px 14px', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>Loading positions…</div>
                  ) : openTrades.length === 0 ? (
                    <div style={{ padding: '20px 14px', textAlign: 'center' }}>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', marginBottom: 8 }}>No open trades logged yet</div>
                      <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#00e5a0', padding: '5px 12px', borderRadius: 3, textDecoration: 'none' }}>
                        Log Your First Trade →
                      </Link>
                    </div>
                  ) : (
                    openTrades.map(t => {
                      const isLong = t.direction === 'LONG';
                      const pnl = t.pnl_usd ?? null;
                      return (
                        <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderBottom: '1px solid #1a2030' }}>
                          <div style={{ width: 22, height: 22, borderRadius: 4, background: isLong ? 'rgba(0,229,160,0.12)' : 'rgba(255,61,90,0.12)', border: `1px solid ${isLong ? 'rgba(0,229,160,0.2)' : 'rgba(255,61,90,0.2)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 7, fontWeight: 700, color: isLong ? '#00e5a0' : '#ff3d5a', flexShrink: 0 }}>
                            {t.asset.slice(0, 3)}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 12, fontWeight: 600, color: '#e2e6f0' }}>
                              {t.asset} <span style={{ fontFamily: 'var(--font-bebas)', fontSize: 11, letterSpacing: '1px', color: isLong ? '#00e5a0' : '#ff3d5a', marginLeft: 4 }}>{t.direction}</span>
                            </div>
                            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>
                              Entry ${t.entry_price.toLocaleString()}
                              {t.stop_loss_price && ` · SL $${t.stop_loss_price.toLocaleString()}`}
                            </div>
                          </div>
                          {pnl !== null && (
                            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: pnl >= 0 ? '#00e5a0' : '#ff3d5a', flexShrink: 0 }}>
                              {pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Trade Setups — Premium gate */}
                <div style={{ position: 'relative', background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>AI Trade Setups</span>
                    {isPremium && (
                      <Link href="/intelligence/setups" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>All setups →</Link>
                    )}
                  </div>
                  {setups.slice(0, 3).map((setup, i) => (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 14px', borderBottom: '1px solid #1a2030' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <div style={{ width: 20, height: 20, borderRadius: 4, background: '#1a2030', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 6.5, fontWeight: 700, color: '#08090c', letterSpacing: '0.5px' }}>
                            <span style={{ color: '#788098' }}>{setup.asset.slice(0, 3)}</span>
                          </div>
                          <div>
                            <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 12, fontWeight: 600, color: '#e2e6f0' }}>{setup.asset}</div>
                            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a' }}>{setup.setup_type || 'Setup'}</div>
                          </div>
                        </div>
                        <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 12, letterSpacing: '1px', padding: '2px 7px', borderRadius: 3, background: setup.direction === 'LONG' ? 'rgba(0,229,160,0.1)' : 'rgba(255,61,90,0.1)', color: setup.direction === 'LONG' ? '#00e5a0' : '#ff3d5a' }}>
                          {setup.direction}
                        </div>
                      </div>
                      {setup.entry_zones && setup.entry_zones.length > 0 && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5 }}>
                          <div>
                            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Entry</div>
                            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>${setup.entry_zones[0].price.toLocaleString()}</div>
                          </div>
                          {setup.take_profits && setup.take_profits.length > 0 && (
                            <div>
                              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Take Profit</div>
                              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#00e5a0' }}>${setup.take_profits[0].price.toLocaleString()}</div>
                            </div>
                          )}
                          {setup.stop_loss && (
                            <div>
                              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Stop Loss</div>
                              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#ff3d5a' }}>${setup.stop_loss.price.toLocaleString()}</div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {setups.length === 0 && (
                    <div style={{ padding: '16px 14px', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
                      No setups yet — run the engine to generate AI trade setups.
                    </div>
                  )}
                  {/* Premium gate overlay */}
                  {!isPremium && <PremiumLock>{null}</PremiumLock>}
                </div>
              </div>

              {/* COL 3: Cockpit Feed */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: 480 }}>
                <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Cockpit Feed</span>
                    <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block', animation: 'livePulse 2s ease-in-out infinite' }} />
                  </div>
                  <Link href="/analysis" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>View all →</Link>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', scrollbarWidth: 'thin', scrollbarColor: '#1a2030 transparent' }}>
                  {recentContent.length > 0 ? recentContent.map(post => (
                    <Link key={post.id} href={`/post/${post.slug}`} style={{ display: 'block', padding: '9px 14px', borderBottom: '1px solid #1a2030', textDecoration: 'none', cursor: 'pointer', transition: 'background 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2, background: 'rgba(0,229,160,0.08)', color: '#00e5a0', border: '1px solid rgba(0,229,160,0.2)' }}>
                          {post.content_type}
                        </span>
                        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, color: '#38405a' }}>{timeAgo(post.published_at)}</span>
                      </div>
                      <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 11, color: '#e2e6f0', lineHeight: 1.45, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                        {post.title || post.excerpt || 'Analysis'}
                      </div>
                    </Link>
                  )) : (
                    <div style={{ padding: '16px 14px', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>No content yet…</div>
                  )}
                </div>
              </div>
            </div>

            {/* ── Portfolio + Exchange ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.1fr', gap: 12, marginBottom: 12 }}>

              {/* Portfolio stats */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Trade Statistics</span>
                  <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>Open Journal →</Link>
                </div>
                {statsLoading ? (
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>Loading stats…</div>
                ) : stats && stats.total_trades > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
                    {[
                      { l: 'Total P&L',     v: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(0)}`,   c: totalPnl >= 0 ? '#00e5a0' : '#ff3d5a' },
                      { l: 'Win Rate',      v: `${(stats.win_rate * 100).toFixed(0)}%`,                 c: stats.win_rate >= 0.5 ? '#00e5a0' : '#ff3d5a' },
                      { l: 'Profit Factor', v: stats.profit_factor.toFixed(2),                          c: stats.profit_factor >= 1.5 ? '#00e5a0' : stats.profit_factor >= 1 ? '#f0a030' : '#ff3d5a' },
                      { l: 'Trades',        v: String(stats.total_trades),                              c: '#e2e6f0' },
                    ].map(item => (
                      <div key={item.l}>
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{item.l}</div>
                        <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 20, lineHeight: 1, color: item.c }}>{item.v}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '12px 0' }}>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', marginBottom: 10 }}>No trades logged yet</div>
                    <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#00e5a0', padding: '6px 14px', borderRadius: 3, textDecoration: 'none' }}>
                      Log Your First Trade →
                    </Link>
                  </div>
                )}
              </div>

              {/* Exchange portfolio */}
              <ExchangePortfolioWidget />
            </div>

          </>
        )}

      </div>
    </CockpitShell>
  );
}
