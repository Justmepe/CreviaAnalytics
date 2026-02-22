import { getLatestOpportunities } from '@/lib/api';
import OpportunityCard from '@/components/intelligence/OpportunityCard';
import type { OpportunityScan } from '@/types';
import Link from 'next/link';

export const revalidate = 60;

export const metadata = {
  title: 'Opportunity Scanner | CreviaCockpit',
  description: 'Multi-asset opportunity ranking by composite score, R/R ratio, and regime alignment.',
};

export default async function ScannerPage() {
  let scan: OpportunityScan | null = null;

  try {
    scan = await getLatestOpportunities();
  } catch {
    // No scan available yet
  }

  const opportunities = scan?.opportunities ?? [];

  return (
    <main className="min-h-screen bg-zinc-950">
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Opportunity Scanner</h1>
              <p className="text-sm text-zinc-500 mt-1">
                Assets ranked by composite score: confidence, R/R, regime alignment, and volume
              </p>
            </div>
            <Link
              href="/intelligence"
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Back to Intelligence
            </Link>
          </div>

          {/* Summary picks */}
          {scan && (scan.best_rr || scan.highest_conviction || scan.safest_play) && (
            <div className="grid gap-3 sm:grid-cols-3 mb-6">
              {scan.best_rr && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <div className="text-xs text-emerald-500 font-semibold uppercase tracking-wide">Best R/R</div>
                  <div className="mt-1">
                    <span className={`font-bold ${scan.best_rr.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {scan.best_rr.direction}
                    </span>{' '}
                    <span className="font-bold text-white">{scan.best_rr.asset}</span>
                    <span className="text-sm text-zinc-400 ml-2">{scan.best_rr.rr.toFixed(1)}:1</span>
                  </div>
                </div>
              )}
              {scan.highest_conviction && (
                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
                  <div className="text-xs text-blue-500 font-semibold uppercase tracking-wide">Highest Conviction</div>
                  <div className="mt-1">
                    <span className={`font-bold ${scan.highest_conviction.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {scan.highest_conviction.direction}
                    </span>{' '}
                    <span className="font-bold text-white">{scan.highest_conviction.asset}</span>
                    <span className="text-sm text-zinc-400 ml-2">{Math.round(scan.highest_conviction.confidence * 100)}%</span>
                  </div>
                </div>
              )}
              {scan.safest_play && (
                <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-4">
                  <div className="text-xs text-violet-500 font-semibold uppercase tracking-wide">Safest Play</div>
                  <div className="mt-1">
                    <span className={`font-bold ${scan.safest_play.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {scan.safest_play.direction}
                    </span>{' '}
                    <span className="font-bold text-white">{scan.safest_play.asset}</span>
                    <span className="text-sm text-zinc-400 ml-2">Score: {scan.safest_play.score.toFixed(1)}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Ranked opportunities */}
          {opportunities.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {opportunities.map((opp, i) => (
                <OpportunityCard key={`${opp.asset}-${opp.direction}`} opportunity={opp} rank={i + 1} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center">
              <h2 className="text-lg font-bold text-white">No Opportunities Scanned Yet</h2>
              <p className="text-sm text-zinc-500 mt-2 max-w-md mx-auto">
                The scanner runs after trade setups are generated. Start the engine to begin scanning opportunities.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Regime context */}
      {scan?.regime && (
        <section>
          <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
            <p className="text-xs text-zinc-600 text-center">
              Scanned under <span className="text-zinc-400">{scan.regime.replace('_', ' ')}</span> regime
              {scan.scanned_at && (
                <> &middot; Last scan: {new Date(scan.scanned_at).toLocaleString()}</>
              )}
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
