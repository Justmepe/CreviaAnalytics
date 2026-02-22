'use client';

import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import { getExchangeKeys, addExchangeKey, deleteExchangeKey } from '@/lib/api';
import type { ExchangeKey } from '@/types';

const tierBadge: Record<string, { label: string; color: string }> = {
  free: { label: 'Free', color: 'text-zinc-400 bg-zinc-800 border-zinc-700' },
  pro: { label: 'Pro', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  enterprise: { label: 'Enterprise', color: 'text-violet-400 bg-violet-500/10 border-violet-500/30' },
};

const EXCHANGE_LABELS: Record<string, string> = {
  binance: 'Binance',
  bybit: 'Bybit',
  okx: 'OKX',
};

function ExchangeKeyManager() {
  const [keys, setKeys] = useState<ExchangeKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    exchange: 'binance',
    api_key: '',
    api_secret: '',
    label: '',
  });

  const load = useCallback(async () => {
    try {
      const data = await getExchangeKeys();
      setKeys(data);
    } catch {
      // no-op — user might not have any keys yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!form.api_key.trim() || !form.api_secret.trim()) {
      setError('API key and secret are required.');
      return;
    }
    setSubmitting(true);
    try {
      await addExchangeKey({
        exchange: form.exchange,
        api_key: form.api_key.trim(),
        api_secret: form.api_secret.trim(),
        label: form.label.trim() || undefined,
      });
      setForm({ exchange: 'binance', api_key: '', api_secret: '', label: '' });
      setShowForm(false);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save key');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number, exchange: string) {
    if (!confirm(`Remove ${EXCHANGE_LABELS[exchange] || exchange} API key?`)) return;
    try {
      await deleteExchangeKey(id);
      setKeys(prev => prev.filter(k => k.id !== id));
    } catch {
      // Silently ignore — UI stays the same
    }
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-white">Exchange Connections</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Read-only API keys — syncs your portfolio balances. Keys are encrypted at rest.
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 transition-colors"
          >
            + Connect Exchange
          </button>
        )}
      </div>

      {/* Connected keys list */}
      {loading ? (
        <div className="text-xs text-zinc-600 py-2">Loading...</div>
      ) : keys.length === 0 && !showForm ? (
        <div className="rounded-lg border border-dashed border-zinc-700 p-4 text-center">
          <p className="text-sm text-zinc-500">No exchanges connected yet.</p>
          <p className="text-xs text-zinc-600 mt-1">Connect Binance or Bybit to sync your portfolio.</p>
        </div>
      ) : (
        <div className="space-y-2 mb-4">
          {keys.map(key => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-lg bg-zinc-800/50 border border-zinc-700/50 px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <div className="h-7 w-7 rounded-md bg-zinc-700 flex items-center justify-center text-xs font-bold text-zinc-300">
                  {(EXCHANGE_LABELS[key.exchange] || key.exchange).charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="text-sm font-medium text-white">
                    {EXCHANGE_LABELS[key.exchange] || key.exchange}
                    {key.label && <span className="text-zinc-500 font-normal ml-1.5">— {key.label}</span>}
                  </div>
                  <div className="text-xs text-zinc-500 font-mono">{key.api_key_masked}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {key.last_synced && (
                  <span className="text-xs text-zinc-600 hidden sm:block">
                    Synced {new Date(key.last_synced).toLocaleDateString()}
                  </span>
                )}
                <button
                  onClick={() => handleDelete(key.id, key.exchange)}
                  className="text-xs text-red-400/70 hover:text-red-400 transition-colors"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add key form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="border border-zinc-700/50 rounded-lg p-4 mt-2 space-y-3">
          <div className="text-sm font-semibold text-white mb-1">Connect Exchange</div>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-400">
              {error}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Exchange</label>
              <select
                value={form.exchange}
                onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))}
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
              >
                <option value="binance">Binance</option>
                <option value="bybit">Bybit</option>
                <option value="okx">OKX</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Label (optional)</label>
              <input
                type="text"
                placeholder="e.g. Main spot account"
                value={form.label}
                onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-1 block">API Key</label>
            <input
              type="text"
              placeholder="Paste your read-only API key"
              value={form.api_key}
              onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
              required
              autoComplete="off"
              className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white font-mono placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-1 block">API Secret</label>
            <input
              type="password"
              placeholder="Paste your API secret"
              value={form.api_secret}
              onChange={e => setForm(f => ({ ...f, api_secret: e.target.value }))}
              required
              autoComplete="new-password"
              className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white font-mono placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 px-3 py-2 text-xs text-amber-400/80">
            Use <strong>read-only</strong> API keys with <strong>no withdrawal permissions</strong>. We only read your balance — never trade or move funds.
          </div>

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Saving...' : 'Connect Exchange'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setError(''); }}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function AccountPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Loading...</div>
      </div>
    );
  }

  if (!user) return null;

  const badge = tierBadge[user.tier] || tierBadge.free;

  return (
    <main className="min-h-screen bg-zinc-950">
      <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <h1 className="text-2xl font-bold text-white mb-6">Account</h1>

        {/* Profile card */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 mb-4">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-14 w-14 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-xl font-bold text-emerald-400">
              {(user.name || user.email).charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="text-lg font-semibold text-white">{user.name || 'Anonymous'}</div>
              <div className="text-sm text-zinc-400">{user.email}</div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-zinc-800/50 p-3">
              <div className="text-xs text-zinc-500 mb-1">Subscription</div>
              <span className={`inline-block text-sm font-semibold px-2 py-0.5 rounded border ${badge.color}`}>
                {badge.label}
              </span>
            </div>
            <div className="rounded-lg bg-zinc-800/50 p-3">
              <div className="text-xs text-zinc-500 mb-1">Status</div>
              <div className={`text-sm font-semibold ${user.subscription_status === 'active' ? 'text-emerald-400' : 'text-zinc-400'}`}>
                {user.subscription_status === 'active' ? 'Active' : user.subscription_status === 'none' ? 'No subscription' : user.subscription_status}
              </div>
            </div>
          </div>
        </div>

        {/* Exchange API Key Manager */}
        <ExchangeKeyManager />

        {/* Upgrade CTA for free users */}
        {user.tier === 'free' && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 mb-4">
            <h2 className="text-base font-bold text-white mb-1">Upgrade to Pro</h2>
            <p className="text-sm text-zinc-400 mb-4">
              Get access to AI trade setups, opportunity scanner, and priority content delivery.
            </p>
            <Link
              href="/pricing"
              className="inline-block rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
            >
              View Pro Plans
            </Link>
          </div>
        )}

        {/* Sign out */}
        <button
          onClick={() => { logout(); router.push('/'); }}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          Sign Out
        </button>
      </div>
    </main>
  );
}
