'use client';

/**
 * AuthShell — conditionally wraps content in CockpitShell.
 *
 * - Logged-in user  → renders children inside CockpitShell (sidebar visible)
 * - Public visitor  → renders children as-is (public page, no sidebar)
 * - requireAuth=true → redirects to /auth/login if not authenticated
 *
 * Use this on pages that are public but should show the cockpit sidebar
 * when the user is already logged in (Intelligence, Market, Analysis, etc.)
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CockpitShell from './CockpitShell';

interface AuthShellProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export default function AuthShell({ children, requireAuth = false }: AuthShellProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && requireAuth && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, requireAuth, router]);

  if (loading) {
    if (requireAuth) {
      return (
        <div style={{
          minHeight: '100vh', background: '#08090c',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ color: '#3d4562', fontSize: 12, fontFamily: 'monospace' }}>Loading…</div>
        </div>
      );
    }
    // Public page: render content immediately (no auth flash)
    return <>{children}</>;
  }

  if (!user) {
    if (requireAuth) return null; // redirect in-flight
    return <>{children}</>;      // public page, no sidebar
  }

  return <CockpitShell>{children}</CockpitShell>;
}
