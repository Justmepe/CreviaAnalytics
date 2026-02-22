import { getLatestTradeSetups } from '@/lib/api';
import TradeSetupCard from '@/components/intelligence/TradeSetupCard';
import type { TradeSetup } from '@/types';
import Link from 'next/link';

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
    <main className="min-h-screen bg-zinc-950">
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Trade Setups</h1>
              <p className="text-sm text-zinc-500 mt-1">
                AI-generated trade ideas based on market regime, price action, and derivatives data
              </p>
            </div>
            <Link
              href="/intelligence"
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Back to Intelligence
            </Link>
          </div>

          {setups.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {setups.map((setup) => (
                <TradeSetupCard key={setup.id} setup={setup} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center">
              <h2 className="text-lg font-bold text-white">No Trade Setups Yet</h2>
              <p className="text-sm text-zinc-500 mt-2 max-w-md mx-auto">
                Trade setups are generated automatically during each research cycle for major assets (BTC, ETH, SOL, BNB).
                Start the engine to begin generating setups.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Disclaimer */}
      <section>
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <p className="text-xs text-zinc-600 text-center">
            Trade setups are AI-generated analysis, not financial advice. Always do your own research and manage risk appropriately.
          </p>
        </div>
      </section>
    </main>
  );
}
