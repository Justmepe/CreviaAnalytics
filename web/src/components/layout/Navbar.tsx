'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

// Paths where the cockpit shell (sidebar layout) takes over — hide public Navbar
const COCKPIT_PATHS = [
  '/dashboard', '/whale-tracker', '/alerts', '/billing', '/journal', '/account',
  '/intelligence', '/intelligence/setups', '/intelligence/scanner', '/market', '/analysis',
];

const publicNavLinks = [
  { href: '/', label: 'Home' },
  { href: '/news', label: 'News' },
  { href: '/analysis', label: 'Feed' },
  { href: '/market', label: 'Market' },
  { href: '/intelligence', label: 'Intelligence' },
  { href: '/tools/risk-calculator', label: 'Risk Calc' },
  { href: '/pricing', label: 'Pricing' },
];

const authedNavLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/news', label: 'News' },
  { href: '/analysis', label: 'Feed' },
  { href: '/market', label: 'Market' },
  { href: '/intelligence', label: 'Intelligence' },
  { href: '/tools/risk-calculator', label: 'Risk Calc' },
  { href: '/journal', label: 'Journal' },
];

const tierColors: Record<string, string> = {
  pro: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  enterprise: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  free: 'bg-zinc-700/50 text-zinc-400 border-zinc-600/30',
};

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const navLinks = user ? authedNavLinks : publicNavLinks;

  // Hide public Navbar when user is in their cockpit
  if (user && COCKPIT_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return null;
  }

  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/logo.png"
            alt="CreviaCockpit"
            width={200}
            height={167}
            className="h-9 w-auto rounded-lg object-contain"
            priority
          />
          <span className="text-lg font-semibold text-white hidden sm:block">
            Crevia<span className="text-emerald-400">Cockpit</span>
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Desktop CTA / User Menu */}
        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-zinc-800 transition-colors"
              >
                <div className="h-7 w-7 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-xs font-bold text-emerald-400">
                  {(user.name || user.email).charAt(0).toUpperCase()}
                </div>
                <div className="text-left">
                  <div className="text-xs text-white font-medium">{user.name || user.email.split('@')[0]}</div>
                  <div className={`text-xs px-1.5 py-0.5 rounded border text-center ${tierColors[user.tier] || tierColors.free}`}>
                    {user.tier.toUpperCase()}
                  </div>
                </div>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-1 w-44 rounded-xl border border-zinc-700 bg-zinc-900 shadow-xl py-1">
                  <div className="px-3 py-2 border-b border-zinc-800">
                    <div className="text-xs text-zinc-400 truncate">{user.email}</div>
                  </div>
                  <Link
                    href="/dashboard"
                    onClick={() => setUserMenuOpen(false)}
                    className="block px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
                  >
                    Dashboard
                  </Link>
                  {user.tier === 'free' && (
                    <Link
                      href="/waitlist"
                      onClick={() => setUserMenuOpen(false)}
                      className="block px-3 py-2 text-sm text-emerald-400 hover:bg-zinc-800"
                    >
                      Upgrade to Pro
                    </Link>
                  )}
                  <button
                    onClick={() => { logout(); setUserMenuOpen(false); }}
                    className="w-full text-left px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="text-sm font-medium text-zinc-400 hover:text-white transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/waitlist"
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-400"
              >
                Join Waitlist
              </Link>
            </>
          )}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 md:hidden"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {mobileOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <nav className="border-t border-zinc-800 px-4 py-3 md:hidden">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white"
            >
              {link.label}
            </Link>
          ))}
          {user ? (
            <>
              <div className="mt-2 px-3 py-2 border-t border-zinc-800">
                <div className="text-xs text-zinc-400">{user.email}</div>
                <div className="text-xs text-zinc-500 capitalize">{user.tier} plan</div>
              </div>
              <button
                onClick={() => { logout(); setMobileOpen(false); }}
                className="mt-1 w-full text-left rounded-lg px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800"
              >
                Sign Out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/auth/login"
                onClick={() => setMobileOpen(false)}
                className="mt-2 block rounded-lg px-3 py-2 text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white"
              >
                Sign In
              </Link>
              <Link
                href="/waitlist"
                onClick={() => setMobileOpen(false)}
                className="mt-1 block rounded-lg bg-emerald-500 px-3 py-2 text-center text-sm font-semibold text-zinc-950"
              >
                Join Waitlist
              </Link>
            </>
          )}
        </nav>
      )}
    </header>
  );
}
