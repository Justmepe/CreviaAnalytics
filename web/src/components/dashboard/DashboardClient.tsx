'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getPortfolioStats, getJournalEntries } from '@/lib/api';
import type { PortfolioStats, JournalEntry, MarketRegime, TradeSetup } from '@/types';

interface DashboardClientProps {
  regime: MarketRegime | null;
  setups: TradeSetup[];
  btcPrice: number | null;
  ethPrice: number | null;
  marketCap: number | null;
  fearGreed: number | null;
  fearGreedLabel: string | null;
}

const regimeColors: Record<string, { text: string; bg: string; border: string }> = {
  RISK_ON: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  ACCUMULATION: { text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  ALTSEASON_CONFIRMED: { text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
  NEUTRAL: { text: 'text-zinc-400', bg: 'bg-zinc-800/50', border: 'border-zinc-700' },
  DISTRIBUTION: { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  RISK_OFF: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  VOLATILITY_EXPANSION: { text: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
};

function formatPrice(p: number | null): string {
  if (!p) return '--';
  if (p >= 1000) return `$${p.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  return `$${p.toFixed(2)}`;
}

function formatLarge(n: number | null): string {
  if (!n) return '--';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  return `$${n.toLocaleString()}`;
}

export default function DashboardClient({
  regime, setups, btcPrice, ethPrice, marketCap, fearGreed, fearGreedLabel
}: DashboardClientProps) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [openTrades, setOpenTrades] = useState<JournalEntry[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/auth/login');
    }
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
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Loading dashboard...</div>
      </div>
    );
  }

  if (!user) return null;

  const regimeStyle = regime
    ? regimeColors[regime.regime_name] || regimeColors.NEUTRAL
    : regimeColors.NEUTRAL;

  const isPro = user.tier === 'pro' || user.tier === 'enterprise';
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <main className="min-h-screen bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">
              {greeting}, {user.name || user.email.split('@')[0]}
            </h1>
            <p className="text-sm text-zinc-500 mt-0.5">
              Here&apos;s your market intelligence overview
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-1 rounded-full border font-semibold ${
              user.tier === 'pro' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
              user.tier === 'enterprise' ? 'bg-violet-500/10 text-violet-400 border-violet-500/30' :
              'bg-zinc-800 text-zinc-400 border-zinc-700'
            }`}>
              {user.tier.toUpperCase()}
            </span>
            <button onClick={logout} className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
              Sign out
            </button>
          </div>
        </div>

        {/* ── Row 1: Market Snapshot + Regime ── */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-4">
          {/* BTC */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500 mb-1">Bitcoin</div>
            <div className="text-2xl font-bold font-mono text-white">{formatPrice(btcPrice)}</div>
          </div>
          {/* ETH */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500 mb-1">Ethereum</div>
            <div className="text-2xl font-bold font-mono text-white">{formatPrice(ethPrice)}</div>
          </div>
          {/* Market Cap */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500 mb-1">Total Market Cap</div>
            <div className="text-2xl font-bold font-mono text-white">{formatLarge(marketCap)}</div>
          </div>
          {/* Fear & Greed */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500 mb-1">Fear & Greed</div>
            <div className={`text-2xl font-bold font-mono ${
              fearGreed != null
                ? fearGreed >= 75 ? 'text-red-400' : fearGreed >= 55 ? 'text-yellow-400'
                : fearGreed <= 25 ? 'text-emerald-400' : fearGreed <= 45 ? 'text-blue-400'
                : 'text-zinc-300'
              : 'text-zinc-500'
            }`}>
              {fearGreed ?? '--'}
              <span className="text-sm font-normal ml-2 text-zinc-500">{fearGreedLabel}</span>
            </div>
          </div>
        </div>

        {/* ── Row 2: Regime + Portfolio Stats ── */}
        <div className="grid gap-4 lg:grid-cols-2 mb-4">

          {/* Regime Card */}
          <div className={`rounded-xl border ${regimeStyle.border} ${regimeStyle.bg} p-5`}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-zinc-400">Current Market Regime</h2>
              <Link href="/intelligence" className="text-xs text-zinc-500 hover:text-zinc-300">
                Full Intelligence →
              </Link>
            </div>
            {regime ? (
              <>
                <div className={`text-2xl font-black ${regimeStyle.text} mb-1`}>
                  {regime.regime_name.replace(/_/g, ' ')}
                </div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${regimeStyle.bg.replace('/10', '')}`}
                      style={{ width: `${(regime.confidence || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-400">{Math.round((regime.confidence || 0) * 100)}% confidence</span>
                </div>
                <p className="text-sm text-zinc-400">{regime.description}</p>
                {regime.trader_action && (
                  <p className="text-xs text-zinc-500 mt-2 italic">{regime.trader_action}</p>
                )}
              </>
            ) : (
              <div className="text-sm text-zinc-500">No regime data yet — start the engine to detect market regime.</div>
            )}
          </div>

          {/* Portfolio Stats */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-zinc-400">Your Portfolio</h2>
              <Link href="/journal" className="text-xs text-zinc-500 hover:text-zinc-300">
                Open Journal →
              </Link>
            </div>

            {statsLoading ? (
              <div className="text-sm text-zinc-600 animate-pulse">Loading stats...</div>
            ) : stats && stats.total_trades > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-zinc-500">Total P&L</div>
                  <div className={`text-xl font-bold ${stats.total_pnl_usd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {stats.total_pnl_usd >= 0 ? '+' : ''}${stats.total_pnl_usd.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500">Win Rate</div>
                  <div className={`text-xl font-bold ${stats.win_rate >= 0.5 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(stats.win_rate * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500">Trades</div>
                  <div className="text-lg font-bold text-white">
                    {stats.total_trades}
                    <span className="text-xs text-zinc-500 ml-1">({stats.active_trades} open)</span>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500">Profit Factor</div>
                  <div className={`text-lg font-bold ${stats.profit_factor >= 1.5 ? 'text-emerald-400' : stats.profit_factor >= 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {stats.profit_factor.toFixed(2)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-zinc-500 mb-3">No trades logged yet.</p>
                <Link href="/journal" className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors">
                  Log Your First Trade
                </Link>
              </div>
            )}

            {/* Open trades preview */}
            {openTrades.length > 0 && (
              <div className="mt-3 border-t border-zinc-800 pt-3">
                <div className="text-xs text-zinc-500 mb-2">{openTrades.length} open trade{openTrades.length > 1 ? 's' : ''}</div>
                {openTrades.slice(0, 2).map(t => (
                  <div key={t.id} className="flex items-center justify-between text-xs mb-1">
                    <span className={t.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}>{t.direction}</span>
                    <span className="text-white font-medium">{t.asset}</span>
                    <span className="text-zinc-500 font-mono">${t.entry_price.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Row 3: Latest Trade Setups + Quick Tools ── */}
        <div className="grid gap-4 lg:grid-cols-3 mb-4">

          {/* Trade Setups */}
          <div className="lg:col-span-2 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-zinc-400">Latest Trade Setups</h2>
              <Link href="/intelligence/setups" className="text-xs text-zinc-500 hover:text-zinc-300">
                All Setups →
              </Link>
            </div>

            {!isPro ? (
              <div className="rounded-lg border border-dashed border-zinc-700 p-4 text-center">
                <p className="text-xs text-zinc-500 mb-2">AI trade setups are available on Pro</p>
                <Link href="/pricing" className="text-xs text-emerald-400 hover:text-emerald-300">Upgrade →</Link>
              </div>
            ) : setups.length > 0 ? (
              <div className="space-y-2">
                {setups.slice(0, 3).map((setup, i) => (
                  <div key={i} className={`flex items-center justify-between rounded-lg p-3 border ${
                    setup.direction === 'LONG' ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'
                  }`}>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-bold ${setup.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {setup.direction}
                      </span>
                      <span className="font-bold text-white">{setup.asset}</span>
                      {setup.setup_type && <span className="text-xs text-zinc-500">{setup.setup_type}</span>}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-zinc-500">
                      {setup.entry_zones && setup.entry_zones.length > 0 && (
                        <span>Entry: ${setup.entry_zones[0].price.toLocaleString()}</span>
                      )}
                      <span className="text-zinc-600">{Math.round((setup.confidence || 0) * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No setups generated yet. Run the engine to generate AI trade setups.</p>
            )}
          </div>

          {/* Quick Tools */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-zinc-400 px-1">Quick Access</h2>
            {[
              { href: '/tools/risk-calculator', label: 'Risk Calculator', desc: 'Position sizing & R/R' },
              { href: '/intelligence/scanner', label: 'Opportunity Scanner', desc: 'Ranked setups by score', pro: true },
              { href: '/intelligence', label: 'Intelligence Hub', desc: 'Regime, correlations, signals' },
              { href: '/journal', label: 'Trade Journal', desc: 'Log & track your trades' },
              { href: '/market', label: 'Market Data', desc: 'Prices & snapshots' },
            ].map(tool => (
              <Link
                key={tool.href}
                href={tool.href}
                className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 p-3 hover:border-zinc-700 hover:bg-zinc-800/50 transition-all group"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white group-hover:text-emerald-400 transition-colors">
                      {tool.label}
                    </span>
                    {tool.pro && !isPro && (
                      <span className="text-xs text-emerald-500 border border-emerald-500/30 rounded px-1">PRO</span>
                    )}
                  </div>
                  <div className="text-xs text-zinc-600">{tool.desc}</div>
                </div>
                <span className="text-zinc-600 group-hover:text-zinc-400 transition-colors">→</span>
              </Link>
            ))}
          </div>
        </div>

        {/* ── Row 4: Daily Scan / Analysis feed ── */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-zinc-400">Daily Analysis Feed</h2>
            <Link href="/analysis" className="text-xs text-zinc-500 hover:text-zinc-300">
              All Analysis →
            </Link>
          </div>
          <p className="text-xs text-zinc-600">
            Latest memos, threads, and market analysis generated by the engine appear here.
            Visit <Link href="/analysis" className="text-zinc-400 hover:text-white underline">Analysis</Link> for the full feed.
          </p>
        </div>

      </div>
    </main>
  );
}
