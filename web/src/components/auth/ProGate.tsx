'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

interface ProGateProps {
  /** Component rendered when user has the required tier */
  children: React.ReactNode;
  /** Minimum tier required: 'pro' | 'enterprise' */
  minTier?: 'pro' | 'enterprise';
  /** Feature name shown in the upgrade prompt */
  featureName?: string;
}

const tierLevels: Record<string, number> = { free: 0, pro: 1, enterprise: 2 };

export default function ProGate({
  children,
  minTier = 'pro',
  featureName = 'this feature',
}: ProGateProps) {
  const { user, loading } = useAuth();

  // Show a loading skeleton while auth resolves
  if (loading) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-6 animate-pulse">
        <div className="h-4 w-32 bg-zinc-800 rounded mb-3" />
        <div className="h-3 w-48 bg-zinc-800 rounded" />
      </div>
    );
  }

  const userLevel = user ? (tierLevels[user.tier] ?? 0) : 0;
  const requiredLevel = tierLevels[minTier] ?? 1;

  if (userLevel >= requiredLevel) {
    return <>{children}</>;
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-6 text-center">
      <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-3">
        <svg className="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
      <h3 className="text-sm font-bold text-white mb-1">
        {minTier.charAt(0).toUpperCase() + minTier.slice(1)} Required
      </h3>
      <p className="text-xs text-zinc-500 mb-4 max-w-xs mx-auto">
        {featureName} is available on the {minTier} plan and above.
      </p>
      {user ? (
        <Link
          href="/pricing"
          className="inline-block rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
        >
          Upgrade to {minTier.charAt(0).toUpperCase() + minTier.slice(1)}
        </Link>
      ) : (
        <div className="flex gap-2 justify-center">
          <Link
            href="/auth/register"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
          >
            Create Account
          </Link>
          <Link
            href="/auth/login"
            className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            Sign In
          </Link>
        </div>
      )}
    </div>
  );
}
