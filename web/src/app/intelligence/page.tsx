import { getCurrentRegime, getLatestCorrelations, getSmartMoneySignals, getLatestTradeSetups, getLatestOpportunities } from '@/lib/api';
import type { SmartMoneyScan } from '@/lib/api';
import MarketRegimeIndicator from '@/components/intelligence/MarketRegimeIndicator';
import CorrelationMatrix from '@/components/intelligence/CorrelationMatrix';
import SmartMoneyTracker from '@/components/intelligence/SmartMoneyTracker';
import TradeSetupCard from '@/components/intelligence/TradeSetupCard';
import OpportunityCard from '@/components/intelligence/OpportunityCard';
import ProGate from '@/components/auth/ProGate';
import type { MarketRegime, CorrelationSnapshot, TradeSetup, OpportunityScan } from '@/types';
import Link from 'next/link';

export const revalidate = 60;

export const metadata = {
  title: 'Intelligence | CreviaCockpit',
  description: 'Market regime detection, correlation analysis, smart money tracking, and trading intelligence.',
};

export default async function IntelligencePage() {
  let regime: MarketRegime | null = null;
  let correlations: CorrelationSnapshot | null = null;
  let smartMoney: SmartMoneyScan | null = null;
  let tradeSetups: TradeSetup[] = [];
  let opportunities: OpportunityScan | null = null;

  try {
    regime = await getCurrentRegime();
  } catch {
    // No regime data yet
  }

  try {
    correlations = await getLatestCorrelations(24);
  } catch {
    // No correlation data yet
  }

  try {
    smartMoney = await getSmartMoneySignals(6);
  } catch {
    // No smart money data yet
  }

  try {
    tradeSetups = await getLatestTradeSetups(undefined, 4);
  } catch {
    // No trade setups yet
  }

  try {
    opportunities = await getLatestOpportunities();
  } catch {
    // No opportunities yet
  }

  const topOpportunities = opportunities?.opportunities?.slice(0, 3) ?? [];

  return (
    <main className="min-h-screen bg-zinc-950">
      {/* Regime Indicator */}
      {regime ? (
        <MarketRegimeIndicator regime={regime} />
      ) : (
        <section className="border-b border-zinc-800">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="text-lg font-bold text-white">Market Regime</h2>
              <p className="text-sm text-zinc-500 mt-2">
                No regime data available yet. Start the engine to begin detecting market regimes.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Correlation Matrix + Smart Money — side by side on desktop */}
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Correlation Matrix */}
            {correlations ? (
              <CorrelationMatrix data={correlations} />
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
                <h3 className="text-lg font-bold text-white">Correlation Matrix</h3>
                <p className="text-sm text-zinc-500 mt-2">
                  No correlation data available yet. The engine needs to collect historical metrics first.
                </p>
              </div>
            )}

            {/* Smart Money Tracker */}
            {smartMoney && smartMoney.signal_count > 0 ? (
              <SmartMoneyTracker data={smartMoney} />
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
                <h3 className="text-lg font-bold text-white">Smart Money Activity</h3>
                <p className="text-sm text-zinc-500 mt-2">
                  No smart money signals detected yet. Signals appear when funding rates, liquidations, or capital flows become notable.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Top Opportunities */}
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Top Opportunities</h2>
            <Link
              href="/intelligence/scanner"
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Full Scanner
            </Link>
          </div>

          <ProGate featureName="Opportunity Scanner" minTier="pro">
            {topOpportunities.length > 0 ? (
              <div className="grid gap-4 lg:grid-cols-3">
                {topOpportunities.map((opp, i) => (
                  <OpportunityCard key={`${opp.asset}-${opp.direction}`} opportunity={opp} rank={i + 1} />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/30 p-6">
                <h3 className="text-sm font-bold text-zinc-400">Opportunity Scanner</h3>
                <p className="text-xs text-zinc-600 mt-1">
                  No opportunities scanned yet. The scanner ranks assets after trade setups are generated.
                </p>
              </div>
            )}
          </ProGate>
        </div>
      </section>

      {/* Trade Setups Preview */}
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Latest Trade Setups</h2>
            <Link
              href="/intelligence/setups"
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              View All
            </Link>
          </div>

          <ProGate featureName="AI Trade Setups" minTier="pro">
            {tradeSetups.length > 0 ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {tradeSetups.map((setup) => (
                  <TradeSetupCard key={setup.id} setup={setup} />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/30 p-6">
                <h3 className="text-sm font-bold text-zinc-400">Trade Setups</h3>
                <p className="text-xs text-zinc-600 mt-1">
                  No setups generated yet. The engine generates AI-powered trade setups for major assets each cycle.
                </p>
              </div>
            )}
          </ProGate>
        </div>
      </section>
    </main>
  );
}
