'use client';

import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const tierBadge: Record<string, { label: string; color: string }> = {
  free: { label: 'Free', color: 'text-zinc-400 bg-zinc-800 border-zinc-700' },
  pro: { label: 'Pro', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  enterprise: { label: 'Enterprise', color: 'text-violet-400 bg-violet-500/10 border-violet-500/30' },
};

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
