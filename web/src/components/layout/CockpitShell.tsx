'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useMarketPrices } from '@/context/MarketPricesContext';
import { useMarketStream } from '@/hooks/useMarketStream';

// ── Tier metadata ────────────────────────────────────────────────────────────
const TIER_META: Record<string, { icon: string; label: string; color: string; bg: string; border: string; subtext: string }> = {
  free:       { icon: '○',  label: 'Free',     color: '#788098', bg: 'rgba(30,35,50,0.5)',        border: '#222c42',                 subtext: 'Join waitlist to upgrade' },
  basic:      { icon: '⬡',  label: 'Basic',    color: '#00e5a0', bg: 'rgba(0,229,160,0.08)',      border: 'rgba(0,229,160,0.2)',      subtext: 'Active plan' },
  pro:        { icon: '⚡', label: 'Premium',  color: '#3d7fff', bg: 'rgba(61,127,255,0.08)',     border: 'rgba(61,127,255,0.2)',     subtext: 'Active plan' },
  enterprise: { icon: '◈',  label: 'Premium+', color: '#9b7cf4', bg: 'rgba(155,124,244,0.08)',   border: 'rgba(155,124,244,0.2)',    subtext: 'Active plan' },
};

// ── Navigation ───────────────────────────────────────────────────────────────
const NAV_SECTIONS = [
  {
    section: 'Command Centre',
    items: [
      { href: '/dashboard',             icon: '⬡',  label: 'Dashboard',           live: true  },
      { href: '/intelligence',          icon: '📡', label: 'Intelligence',         live: false },
      { href: '/analysis',              icon: '📰', label: 'Analysis',             live: false },
      { href: '/market',                icon: '📊', label: 'Market',               live: false },
    ],
  },
  {
    section: 'Trading Tools',
    items: [
      { href: '/intelligence/setups',   icon: '⚡', label: 'Trade Setups',         live: true  },
      { href: '/tools/risk-calculator', icon: '🎯', label: 'Risk Calculator',      live: false },
      { href: '/intelligence/scanner',  icon: '🔍', label: 'Opportunity Scanner',  live: false },
    ],
  },
  {
    section: 'Intelligence',
    items: [
      { href: '/whale-tracker',         icon: '🐋', label: 'Whale Tracker',        live: true  },
      { href: '/alerts',                icon: '🔔', label: 'My Alerts',            live: false },
    ],
  },
  {
    section: 'Account',
    items: [
      { href: '/account',               icon: '⚙',  label: 'Settings',            live: false },
      { href: '/billing',               icon: '💳', label: 'Billing',              live: false },
    ],
  },
];

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
function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// ── CockpitShell ─────────────────────────────────────────────────────────────
export default function CockpitShell({ children }: { children: React.ReactNode }) {
  const pathname   = usePathname();
  const router     = useRouter();
  const { user, logout } = useAuth();
  const { ticks, wsStatus } = useMarketPrices();
  const { snapshot } = useMarketStream();
  const [utcTime, setUtcTime] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // UTC clock — updates every 30s (low cost)
  useEffect(() => {
    function tick() {
      const d  = new Date();
      const hh = String(d.getUTCHours()).padStart(2, '0');
      const mm = String(d.getUTCMinutes()).padStart(2, '0');
      setUtcTime(`${hh}:${mm} UTC`);
    }
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  const tier     = user?.tier ?? 'free';
  const meta     = TIER_META[tier] ?? TIER_META.free;
  const isLive   = wsStatus === 'live';
  const btcPrice = ticks['BTC']?.price ?? snapshot?.btc_price ?? null;
  const ethPrice = ticks['ETH']?.price ?? snapshot?.eth_price ?? null;
  const btcChg   = ticks['BTC']?.change ?? null;
  const userName = user ? (user.name || user.email.split('@')[0]) : 'User';
  const initials = userName.slice(0, 2).toUpperCase();

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      background: '#070809',
    }}>

      {/* ── SIDEBAR ── */}
      <aside style={{
        width: 220,
        height: '100vh',
        background: '#0c0e12',
        borderRight: '1px solid #1a2030',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        zIndex: 20,
      }}
        className="cockpit-sidebar"
      >
        {/* Logo */}
        <Link
          href="/dashboard"
          style={{
            height: 52,
            display: 'flex',
            alignItems: 'center',
            gap: 9,
            padding: '0 16px',
            borderBottom: '1px solid #1a2030',
            textDecoration: 'none',
            flexShrink: 0,
          }}
        >
          <div style={{
            width: 26, height: 26, borderRadius: 6,
            background: 'linear-gradient(135deg, #00e5a0, #0090ff)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--font-bebas)', fontSize: 11, color: '#070809',
            letterSpacing: '0.5px',
          }}>CC</div>
          <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: '#e2e6f0' }}>
            Crevia<span style={{ color: '#00e5a0' }}>Cockpit</span>
          </span>
        </Link>

        {/* Tier badge */}
        <div
          style={{
            margin: '12px 14px 4px',
            padding: '8px 12px',
            borderRadius: 5,
            background: meta.bg,
            border: `1px solid ${meta.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            cursor: 'pointer',
            transition: 'opacity 0.2s',
          }}
          onClick={() => router.push('/billing')}
        >
          <span style={{ fontSize: 15 }}>{meta.icon}</span>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10, fontWeight: 500,
              letterSpacing: '0.8px', textTransform: 'uppercase',
              color: meta.color,
            }}>{meta.label}</div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 8.5,
              color: tier === 'free' ? '#f0a030' : '#38405a',
              marginTop: 1,
            }}>{meta.subtext}</div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {NAV_SECTIONS.map(({ section, items }) => (
            <div key={section}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 8.5, letterSpacing: '1.5px',
                textTransform: 'uppercase', color: '#38405a',
                padding: '12px 16px 5px',
              }}>{section}</div>

              {items.map(item => {
                // Active: exact match or prefix (but /intelligence should not activate /intelligence/setups)
                const isActive = pathname === item.href ||
                  (item.href.length > 1 && pathname.startsWith(item.href + '/') && item.href !== '/intelligence');

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 16px',
                      textDecoration: 'none',
                      borderLeft: `2px solid ${isActive ? '#00e5a0' : 'transparent'}`,
                      background: isActive ? '#10141c' : 'transparent',
                      transition: 'background 0.15s',
                    }}
                    onClick={() => setMobileNavOpen(false)}
                    className="cockpit-nav-item"
                  >
                    <span style={{
                      fontSize: 14,
                      opacity: isActive ? 1 : 0.4,
                      width: 18, textAlign: 'center', flexShrink: 0,
                      transition: 'opacity 0.15s',
                    }}>{item.icon}</span>
                    <span style={{
                      fontSize: 12.5,
                      color: isActive ? '#e2e6f0' : '#788098',
                      flex: 1,
                      transition: 'color 0.15s',
                    }}>{item.label}</span>
                    {item.live && (
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 8, letterSpacing: '0.5px',
                        textTransform: 'uppercase',
                        padding: '1px 5px', borderRadius: 2,
                        background: 'rgba(0,229,160,0.08)',
                        color: '#00e5a0',
                        border: '1px solid rgba(0,229,160,0.2)',
                        display: 'flex', alignItems: 'center', gap: 3,
                      }}>
                        <span style={{
                          width: 4, height: 4, borderRadius: '50%',
                          background: '#00e5a0', display: 'inline-block',
                          animation: 'livePulse 2s ease-in-out infinite',
                        }} />
                        Live
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User row */}
        <div style={{ borderTop: '1px solid #1a2030', padding: '12px 14px' }}>
          <div
            style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '4px 2px', cursor: 'pointer' }}
            onClick={() => router.push('/account')}
          >
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'linear-gradient(135deg, #3d7fff, #0050cc)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'var(--font-mono)', fontSize: 9, color: '#fff', flexShrink: 0,
            }}>{initials}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 500, color: '#e2e6f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{userName}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, color: '#38405a', marginTop: 1 }}>
                {meta.label} plan
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); logout(); }}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: 8, color: '#38405a',
                background: 'none', border: 'none', cursor: 'pointer',
                letterSpacing: '0.5px', flexShrink: 0, padding: '4px',
              }}
              title="Sign out"
            >↪</button>
          </div>
        </div>
      </aside>

      {/* ── MAIN AREA ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

        {/* Topbar */}
        <div style={{
          height: 52,
          borderBottom: '1px solid #1a2030',
          background: 'rgba(7,8,9,0.9)',
          backdropFilter: 'blur(20px)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          flexShrink: 0,
          gap: 12,
        }}>
          {/* Left: clock + greeting */}
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, overflow: 'hidden' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#38405a', flexShrink: 0 }}>{utcTime}</span>
            <span style={{ color: '#38405a', fontSize: 10, flexShrink: 0 }}>·</span>
            <span style={{ fontSize: 13, fontWeight: 500, color: '#e2e6f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {getGreeting()}, {userName.split(' ')[0]}.
            </span>
          </div>

          {/* Right: market tickers */}
          <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
            {/* Live pill */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '0 11px', height: 52 }}>
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: isLive ? '#00e5a0' : '#38405a',
                display: 'inline-block',
                animation: isLive ? 'livePulse 2s ease-in-out infinite' : 'none',
              }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: isLive ? '#00e5a0' : '#38405a', letterSpacing: '1px', textTransform: 'uppercase' }}>
                {isLive ? 'Live' : 'Offline'}
              </span>
            </div>

            {btcPrice != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px', borderLeft: '1px solid #1a2030', height: 52 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', textTransform: 'uppercase' }}>BTC</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>{fmtPrice(btcPrice)}</span>
                {btcChg != null && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: btcChg >= 0 ? '#00e5a0' : '#ff3d5a' }}>
                    {btcChg >= 0 ? '+' : ''}{btcChg.toFixed(2)}%
                  </span>
                )}
              </div>
            )}

            {ethPrice != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px', borderLeft: '1px solid #1a2030', height: 52 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', textTransform: 'uppercase' }}>ETH</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>{fmtPrice(ethPrice)}</span>
              </div>
            )}

            {snapshot?.total_market_cap != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px', borderLeft: '1px solid #1a2030', height: 52 }}
                className="hide-mobile">
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, color: '#38405a', textTransform: 'uppercase' }}>MCAP</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>{fmtLarge(snapshot.total_market_cap)}</span>
              </div>
            )}
          </div>

          {/* Action icons */}
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <Link href="/alerts" style={{
              width: 32, height: 32, borderRadius: 5,
              background: '#10141c', border: '1px solid #1a2030',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, textDecoration: 'none', flexShrink: 0,
            }}>🔔</Link>
            <Link href="/account" style={{
              width: 32, height: 32, borderRadius: 5,
              background: '#10141c', border: '1px solid #1a2030',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, textDecoration: 'none', flexShrink: 0,
            }}>⚙</Link>
          </div>
        </div>

        {/* Content scroll area */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          scrollbarWidth: 'thin',
          scrollbarColor: '#1a2030 transparent',
        }}>
          {children}
        </div>
      </div>

      <style>{`
        .cockpit-nav-item:hover {
          background: #10141c !important;
        }
        .cockpit-nav-item:hover span:first-child {
          opacity: 0.8 !important;
        }
        .cockpit-nav-item:hover span:nth-child(2) {
          color: #b0b8cc !important;
        }
        @media (max-width: 768px) {
          .cockpit-sidebar {
            display: none;
          }
          .hide-mobile {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
