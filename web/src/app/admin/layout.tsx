'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('crevia_access_token');
    if (!token) { router.replace('/auth/login'); return; }

    fetch(`${API}/api/admin/posts?limit=1`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => {
        if (r.status === 403 || r.status === 401) { router.replace('/'); return; }
        setChecking(false);
      })
      .catch(() => { router.replace('/'); });
  }, [router]);

  if (checking) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: '#0d1117', color: '#8b949e',
        fontFamily: 'monospace',
      }}>
        Verifying access…
      </div>
    );
  }

  return <>{children}</>;
}
