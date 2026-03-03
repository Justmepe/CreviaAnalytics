'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import type { ContentPost } from '@/types';

// Tier ordering: free=0, basic=1, pro=2, enterprise=3
const TIER_LEVEL: Record<string, number> = { free: 0, basic: 1, pro: 2, enterprise: 3 };

const TIER_LABEL: Record<string, string> = {
  enterprise: 'Premium+',
  pro: 'Premium',
  basic: 'Basic',
};

interface Props {
  post: ContentPost;
  /** Time-based effective tier returned by the API */
  effectiveTier: string;
  /** Full body renderer — receives the unlocked content */
  children: React.ReactNode;
}

export default function PostBodyGate({ post, effectiveTier, children }: Props) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="mt-8 rounded-xl animate-pulse" style={{ border: '1px solid #1c2235', background: '#111520', height: 240 }} />
    );
  }

  const userLevel = user ? (TIER_LEVEL[user.tier] ?? 0) : 0;
  const requiredLevel = TIER_LEVEL[effectiveTier] ?? 0;

  // Free-tier content — always visible
  if (requiredLevel === 0) return <>{children}</>;

  // User has sufficient tier — show full content
  if (userLevel >= requiredLevel) return <>{children}</>;

  // --- LOCKED: show excerpt preview + upgrade wall ---
  const excerpt = post.excerpt || post.body?.slice(0, 300) || '';

  return (
    <div className="mt-8 relative">
      {/* Blurred excerpt preview */}
      <div
        className="rounded-xl overflow-hidden"
        style={{ border: '1px solid #1c2235', background: '#0d1117', position: 'relative' }}
      >
        <div
          style={{
            padding: '24px 28px',
            filter: 'blur(3px)',
            userSelect: 'none',
            pointerEvents: 'none',
            maskImage: 'linear-gradient(to bottom, black 30%, transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, black 30%, transparent 100%)',
          }}
        >
          <p style={{ color: '#8b95b0', fontSize: 14, lineHeight: 1.8, fontWeight: 300 }}>
            {excerpt}
          </p>
        </div>

        {/* Lock overlay */}
        <div
          style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            gap: 16,
            background: 'linear-gradient(to bottom, rgba(8,9,12,0) 0%, rgba(8,9,12,0.92) 45%)',
          }}
        >
          {/* Lock icon */}
          <div
            style={{
              width: 48, height: 48, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#111520', border: '1px solid #242c42',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7a839e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-syne)', fontSize: 16, fontWeight: 600, color: '#dfe3f0', marginBottom: 6 }}>
              {TIER_LABEL[effectiveTier] ?? 'Pro'} Access Required
            </div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#7a839e', letterSpacing: '0.3px', lineHeight: 1.6, maxWidth: 260 }}>
              This analysis is live — {TIER_LABEL[effectiveTier] ?? 'Premium'} subscribers read it first.
              Free access opens in {effectiveTier === 'enterprise' ? '1 hour' : '6 hours'}.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <Link
              href="/waitlist"
              style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.8px',
                textTransform: 'uppercase', fontWeight: 500,
                background: '#f0a030', color: '#08090c',
                padding: '8px 20px', borderRadius: 4,
                textDecoration: 'none',
              }}
            >
              Upgrade to {TIER_LABEL[effectiveTier] ?? 'Premium'} →
            </Link>
            {!user && (
              <Link
                href="/auth/login"
                style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.5px',
                  textTransform: 'uppercase', color: '#7a839e',
                  border: '1px solid #242c42', padding: '8px 16px', borderRadius: 4,
                  textDecoration: 'none',
                }}
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
