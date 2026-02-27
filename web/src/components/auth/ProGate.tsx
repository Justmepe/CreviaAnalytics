'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

interface ProGateProps {
  children: React.ReactNode;
  minTier?: 'basic' | 'pro' | 'enterprise';
  featureName?: string;
  /** Optional blurred ghost rows shown behind the lock overlay */
  ghostRows?: React.ReactNode;
}

// free=0, basic=1, pro=2 (Premium), enterprise=3 (Premium+)
const tierLevels: Record<string, number> = { free: 0, basic: 1, pro: 2, enterprise: 3 };

const UPGRADE_LABEL: Record<string, string> = {
  basic: 'Upgrade to Basic',
  pro: 'Upgrade to Premium',
  enterprise: 'Upgrade to Premium+',
};

export default function ProGate({
  children,
  minTier = 'pro',
  featureName = 'this feature',
  ghostRows,
}: ProGateProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div
        className="rounded-md p-6 animate-pulse"
        style={{ border: '1px solid #1c2235', background: '#111520' }}
      >
        <div className="h-4 w-32 rounded mb-3" style={{ background: '#161b28' }} />
        <div className="h-3 w-48 rounded" style={{ background: '#161b28' }} />
      </div>
    );
  }

  const userLevel = user ? (tierLevels[user.tier] ?? 0) : 0;
  const requiredLevel = tierLevels[minTier] ?? 1;

  if (userLevel >= requiredLevel) return <>{children}</>;

  return (
    <div className="relative rounded-md overflow-hidden" style={{ border: '1px solid #1c2235' }}>
      {/* Blurred ghost rows — real data shape visible behind lock */}
      <div style={{ filter: 'blur(3.5px)', userSelect: 'none', pointerEvents: 'none' }}>
        {ghostRows ?? children}
      </div>

      {/* Lock overlay */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center gap-2.5"
        style={{ background: 'rgba(8,9,12,0.65)', backdropFilter: 'blur(1px)', zIndex: 10 }}
      >
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center"
          style={{ background: '#111520', border: '1px solid #242c42' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7a839e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>

        <div className="font-syne text-[13px] font-semibold" style={{ color: '#dfe3f0' }}>
          {minTier === 'basic' ? 'Basic Plan Required' : minTier === 'enterprise' ? 'Premium+ Required' : 'Premium Required'}
        </div>

        <p
          className="font-mono-cc text-[10px] text-center max-w-[220px] leading-relaxed"
          style={{ color: '#7a839e', letterSpacing: '0.3px' }}
        >
          {featureName} requires the {minTier === 'basic' ? 'Basic' : minTier === 'enterprise' ? 'Premium+' : 'Premium'} plan.
        </p>

        <div className="flex gap-2 mt-1">
          <Link
            href="/waitlist"
            className="font-mono-cc text-[10px] uppercase tracking-[0.5px] px-4 py-1.5 rounded transition-opacity hover:opacity-85"
            style={{ background: '#f0a030', color: '#08090c', fontWeight: 500 }}
          >
            {UPGRADE_LABEL[minTier]} →
          </Link>
          {!user && (
            <Link
              href="/auth/login"
              className="font-mono-cc text-[10px] uppercase tracking-[0.5px] px-4 py-1.5 rounded transition-colors"
              style={{ color: '#7a839e', border: '1px solid #242c42', textDecoration: 'none' }}
            >
              Sign In
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
