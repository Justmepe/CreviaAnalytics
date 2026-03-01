import { getLatestTradeSetups } from '@/lib/api';
import TradeSetupCard from '@/components/intelligence/TradeSetupCard';
import type { TradeSetup } from '@/types';
import Link from 'next/link';
import AuthShell from '@/components/layout/AuthShell';
import ProGate from '@/components/auth/ProGate';

export const revalidate = 60;

export const metadata = {
  title: 'Trade Setups | CreviaCockpit',
  description: 'AI-generated trade setups with entry zones, stop losses, and take profit targets.',
};

export default async function TradeSetupsPage() {
  let setups: TradeSetup[] = [];

  try {
    setups = await getLatestTradeSetups(undefined, 20);
  } catch {
    // No setups available yet
  }

  return (
    <AuthShell requireAuth>
    <main style={{ background: '#08090c', minHeight: '100vh' }}>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-bebas tracking-[2px] text-[26px]" style={{ color: '#e8eaf0' }}>Trade Setups</h1>
            <p className="font-mono-cc text-[11px] mt-1" style={{ color: '#3d4562' }}>
              Regime-aware ideas based on market conditions, price action, and derivatives data
            </p>
          </div>
          <Link
            href="/intelligence"
            className="font-mono-cc text-[11px] uppercase tracking-[0.5px] transition-colors hover:text-[#00d68f]"
            style={{ color: '#6b7494', textDecoration: 'none' }}
          >
            ← Back to Intelligence
          </Link>
        </div>

        <ProGate featureName="AI Trade Setups" minTier="pro">
          {setups.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {setups.map((setup) => (
                <TradeSetupCard key={setup.id} setup={setup} />
              ))}
            </div>
          ) : (
            <div className="rounded-[6px] p-8 text-center" style={{ border: '1px solid #1c2235', background: '#111520' }}>
              <h2 className="font-syne text-base font-bold" style={{ color: '#e8eaf0' }}>No Trade Setups Yet</h2>
              <p className="font-mono-cc text-[11px] mt-2" style={{ color: '#3d4562' }}>
                Trade setups generate automatically each research cycle for all tracked assets.
              </p>
            </div>
          )}
        </ProGate>

        <p className="font-mono-cc text-[10px] text-center mt-6" style={{ color: '#2a3050' }}>
          Trade setups are intelligence output, not financial advice. Always manage your own risk.
        </p>
      </div>
    </main>
    </AuthShell>
  );
}
