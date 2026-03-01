import { getLatestOpportunities } from '@/lib/api';
import OpportunityCard from '@/components/intelligence/OpportunityCard';
import type { OpportunityScan } from '@/types';
import Link from 'next/link';
import AuthShell from '@/components/layout/AuthShell';
import ProGate from '@/components/auth/ProGate';

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
    <AuthShell requireAuth>
      <main style={{ background: '#08090c', minHeight: '100vh' }}>
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-bebas tracking-[2px] text-[26px]" style={{ color: '#e8eaf0' }}>Opportunity Scanner</h1>
              <p className="font-mono-cc text-[11px] mt-1" style={{ color: '#3d4562' }}>
                Assets ranked by composite score: confidence, R/R, regime alignment, and volume
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

          <ProGate featureName="Opportunity Scanner" minTier="pro">
            <>
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
                <div className="rounded-[6px] p-8 text-center" style={{ border: '1px solid #1c2235', background: '#111520' }}>
                  <h2 className="font-syne text-base font-bold" style={{ color: '#e8eaf0' }}>No Opportunities Scanned Yet</h2>
                  <p className="font-mono-cc text-[11px] mt-2" style={{ color: '#3d4562' }}>
                    The scanner runs after trade setups are generated each cycle.
                  </p>
                </div>
              )}

              {scan?.regime && (
                <p className="font-mono-cc text-[10px] text-center mt-6" style={{ color: '#2a3050' }}>
                  Scanned under <span style={{ color: '#3d4562' }}>{scan.regime.replace('_', ' ')}</span> regime
                  {scan.scanned_at && (
                    <> · Last scan: {new Date(scan.scanned_at).toLocaleString()}</>
                  )}
                </p>
              )}
            </>
          </ProGate>

        </div>
      </main>
    </AuthShell>
  );
}
