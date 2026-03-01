'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from '@/components/layout/CockpitShell';
import {
  getJournalEntries,
  getPortfolioStats,
  createJournalEntry,
  closeJournalEntry,
  deleteJournalEntry,
} from '@/lib/api';
import type { JournalEntry, PortfolioStats } from '@/types';

const outcomeColors: Record<string, string> = {
  win: 'text-emerald-400',
  loss: 'text-red-400',
  breakeven: 'text-zinc-400',
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-lg font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-zinc-600 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function JournalPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [fetching, setFetching] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [closingId, setClosingId] = useState<number | null>(null);
  const [closeExitPrice, setCloseExitPrice] = useState('');
  const [formData, setFormData] = useState({
    asset: '', direction: 'LONG', entry_price: '', quantity: '',
    leverage: '1', stop_loss_price: '', take_profit_price: '',
    risk_amount: '', setup_type: '', notes: '',
  });
  const [formError, setFormError] = useState('');
  const [formSaving, setFormSaving] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      Promise.all([getJournalEntries(), getPortfolioStats()])
        .then(([e, s]) => { setEntries(e); setStats(s); })
        .catch(() => {})
        .finally(() => setFetching(false));
    }
  }, [user]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError('');
    setFormSaving(true);
    try {
      const entry = await createJournalEntry({
        asset: formData.asset.toUpperCase(),
        direction: formData.direction,
        entry_price: parseFloat(formData.entry_price),
        quantity: formData.quantity ? parseFloat(formData.quantity) : undefined,
        leverage: parseFloat(formData.leverage || '1'),
        stop_loss_price: formData.stop_loss_price ? parseFloat(formData.stop_loss_price) : undefined,
        take_profit_price: formData.take_profit_price ? parseFloat(formData.take_profit_price) : undefined,
        risk_amount: formData.risk_amount ? parseFloat(formData.risk_amount) : undefined,
        setup_type: formData.setup_type || undefined,
        notes: formData.notes || undefined,
      });
      setEntries(prev => [entry, ...prev]);
      setShowForm(false);
      setFormData({ asset: '', direction: 'LONG', entry_price: '', quantity: '', leverage: '1', stop_loss_price: '', take_profit_price: '', risk_amount: '', setup_type: '', notes: '' });
      // Refresh stats
      const s = await getPortfolioStats();
      setStats(s);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create entry');
    } finally {
      setFormSaving(false);
    }
  }

  async function handleClose(id: number) {
    if (!closeExitPrice) return;
    try {
      const updated = await closeJournalEntry(id, parseFloat(closeExitPrice));
      setEntries(prev => prev.map(e => e.id === id ? updated : e));
      setClosingId(null);
      setCloseExitPrice('');
      const s = await getPortfolioStats();
      setStats(s);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to close trade');
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this journal entry?')) return;
    try {
      await deleteJournalEntry(id);
      setEntries(prev => prev.filter(e => e.id !== id));
      const s = await getPortfolioStats();
      setStats(s);
    } catch {}
  }

  if (loading || fetching) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Loading journal...</div>
      </div>
    );
  }

  return (
    <CockpitShell>
    <main className="min-h-screen bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Trade Journal</h1>
            <p className="text-sm text-zinc-500 mt-0.5">Track and review your trades</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
          >
            + Log Trade
          </button>
        </div>

        {/* Portfolio Stats */}
        {stats && stats.total_trades > 0 && (
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 mb-6">
            <StatCard label="Total Trades" value={String(stats.total_trades)} sub={`${stats.active_trades} open`} />
            <StatCard label="Win Rate" value={`${(stats.win_rate * 100).toFixed(0)}%`} sub={`${stats.winning_trades}W / ${stats.losing_trades}L`} />
            <StatCard label="Total P&L" value={`$${stats.total_pnl_usd.toFixed(2)}`} />
            <StatCard label="Avg R/R" value={`${stats.avg_rr_achieved.toFixed(2)}R`} />
            <StatCard label="Profit Factor" value={stats.profit_factor.toFixed(2)} />
            <StatCard label="Best Trade" value={`$${stats.best_trade_usd.toFixed(2)}`} />
            <StatCard label="Max Drawdown" value={`$${stats.max_drawdown_usd.toFixed(2)}`} />
          </div>
        )}

        {/* New Entry Form */}
        {showForm && (
          <div className="rounded-xl border border-zinc-700 bg-zinc-900/70 p-5 mb-6">
            <h2 className="text-base font-bold text-white mb-4">Log New Trade</h2>
            {formError && (
              <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
                {formError}
              </div>
            )}
            <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Asset *</label>
                <input required value={formData.asset} onChange={e => setFormData(p => ({...p, asset: e.target.value}))}
                  placeholder="BTC"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Direction *</label>
                <select value={formData.direction} onChange={e => setFormData(p => ({...p, direction: e.target.value}))}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none">
                  <option value="LONG">LONG</option>
                  <option value="SHORT">SHORT</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Entry Price *</label>
                <input required type="number" step="any" value={formData.entry_price} onChange={e => setFormData(p => ({...p, entry_price: e.target.value}))}
                  placeholder="68500"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Quantity</label>
                <input type="number" step="any" value={formData.quantity} onChange={e => setFormData(p => ({...p, quantity: e.target.value}))}
                  placeholder="0.01"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Stop Loss</label>
                <input type="number" step="any" value={formData.stop_loss_price} onChange={e => setFormData(p => ({...p, stop_loss_price: e.target.value}))}
                  placeholder="66500"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Take Profit</label>
                <input type="number" step="any" value={formData.take_profit_price} onChange={e => setFormData(p => ({...p, take_profit_price: e.target.value}))}
                  placeholder="72000"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Risk ($)</label>
                <input type="number" step="any" value={formData.risk_amount} onChange={e => setFormData(p => ({...p, risk_amount: e.target.value}))}
                  placeholder="100"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Setup Type</label>
                <input value={formData.setup_type} onChange={e => setFormData(p => ({...p, setup_type: e.target.value}))}
                  placeholder="Breakout, Range Low..."
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="sm:col-span-2 lg:col-span-4">
                <label className="block text-xs text-zinc-500 mb-1">Notes</label>
                <input value={formData.notes} onChange={e => setFormData(p => ({...p, notes: e.target.value}))}
                  placeholder="Why you took this trade..."
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="sm:col-span-2 lg:col-span-4 flex gap-2">
                <button type="submit" disabled={formSaving}
                  className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors">
                  {formSaving ? 'Saving...' : 'Log Trade'}
                </button>
                <button type="button" onClick={() => setShowForm(false)}
                  className="rounded-lg border border-zinc-700 px-5 py-2 text-sm text-zinc-400 hover:bg-zinc-800 transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Entries List */}
        {entries.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-10 text-center">
            <h2 className="text-lg font-bold text-white mb-2">No trades logged yet</h2>
            <p className="text-sm text-zinc-500">Click &quot;Log Trade&quot; to start tracking your trades against the AI setups.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map((entry) => (
              <div key={entry.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`font-bold text-sm ${entry.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {entry.direction}
                    </span>
                    <span className="font-bold text-white">{entry.asset}</span>
                    {entry.setup_type && <span className="text-xs text-zinc-500">{entry.setup_type}</span>}
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      entry.status === 'open' ? 'bg-blue-500/10 text-blue-400' :
                      entry.status === 'closed' ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-800 text-zinc-600'
                    }`}>
                      {entry.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    {entry.pnl_usd != null && (
                      <div className="text-right">
                        <div className={`text-sm font-bold ${entry.pnl_usd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {entry.pnl_usd >= 0 ? '+' : ''}${entry.pnl_usd.toFixed(2)}
                        </div>
                        {entry.rr_achieved != null && (
                          <div className="text-xs text-zinc-500">{entry.rr_achieved.toFixed(2)}R</div>
                        )}
                      </div>
                    )}
                    <div className="text-right text-sm">
                      <div className="text-white font-mono">${entry.entry_price.toLocaleString()}</div>
                      {entry.exit_price && (
                        <div className="text-zinc-500 font-mono text-xs">→ ${entry.exit_price.toLocaleString()}</div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {entry.status === 'open' && (
                        closingId === entry.id ? (
                          <div className="flex gap-1">
                            <input
                              type="number" step="any" value={closeExitPrice}
                              onChange={e => setCloseExitPrice(e.target.value)}
                              placeholder="Exit price"
                              className="w-28 rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-white focus:outline-none"
                            />
                            <button onClick={() => handleClose(entry.id)} className="text-xs text-emerald-400 hover:text-emerald-300">✓</button>
                            <button onClick={() => setClosingId(null)} className="text-xs text-zinc-500 hover:text-zinc-400">✕</button>
                          </div>
                        ) : (
                          <button onClick={() => setClosingId(entry.id)} className="text-xs text-zinc-400 hover:text-white">Close</button>
                        )
                      )}
                      <button onClick={() => handleDelete(entry.id)} className="text-xs text-zinc-600 hover:text-red-400">Delete</button>
                    </div>
                  </div>
                </div>
                {entry.notes && (
                  <p className="text-xs text-zinc-500 mt-2 truncate">{entry.notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
    </CockpitShell>
  );
}
