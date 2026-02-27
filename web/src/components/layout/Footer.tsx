'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const COCKPIT_PATHS = [
  '/dashboard', '/whale-tracker', '/alerts', '/billing', '/journal', '/account',
];

export default function Footer() {
  const pathname = usePathname();
  const { user } = useAuth();

  if (user && COCKPIT_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return null;
  }
  return (
    <footer className="border-t border-zinc-800 bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center">
              <Image
                src="/logo2.png"
                alt="CreviaCockpit"
                width={376}
                height={450}
                className="h-20 w-auto object-contain"
              />
            </div>
            <p className="mt-3 text-sm text-zinc-500">
              Professional crypto market analysis. Real-time insights for 16+ assets across majors, DeFi, privacy, and memecoins.
            </p>
          </div>

          {/* Research */}
          <div>
            <h4 className="text-sm font-semibold text-white">Research</h4>
            <ul className="mt-3 space-y-2">
              <li><Link href="/analysis" className="text-sm text-zinc-500 hover:text-emerald-400">Analysis Feed</Link></li>
              <li><Link href="/analysis?type=thread" className="text-sm text-zinc-500 hover:text-emerald-400">Market Threads</Link></li>
              <li><Link href="/analysis?type=memo" className="text-sm text-zinc-500 hover:text-emerald-400">Market Memos</Link></li>
            </ul>
          </div>

          {/* Markets */}
          <div>
            <h4 className="text-sm font-semibold text-white">Markets</h4>
            <ul className="mt-3 space-y-2">
              <li><Link href="/market" className="text-sm text-zinc-500 hover:text-emerald-400">Dashboard</Link></li>
              <li><Link href="/asset/BTC" className="text-sm text-zinc-500 hover:text-emerald-400">Bitcoin</Link></li>
              <li><Link href="/asset/ETH" className="text-sm text-zinc-500 hover:text-emerald-400">Ethereum</Link></li>
              <li><Link href="/asset/SOL" className="text-sm text-zinc-500 hover:text-emerald-400">Solana</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-sm font-semibold text-white">Company</h4>
            <ul className="mt-3 space-y-2">
              <li><Link href="/pricing" className="text-sm text-zinc-500 hover:text-emerald-400">Pricing</Link></li>
              <li><a href="https://x.com" target="_blank" rel="noopener" className="text-sm text-zinc-500 hover:text-emerald-400">X / Twitter</a></li>
              <li><a href="https://discord.gg" target="_blank" rel="noopener" className="text-sm text-zinc-500 hover:text-emerald-400">Discord</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-zinc-800 pt-6 text-center text-sm text-zinc-600">
          &copy; {new Date().getFullYear()} CreviaCockpit. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
