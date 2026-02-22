import { Metadata } from 'next';
import WaitlistFlow from '@/components/WaitlistFlow';

export const metadata: Metadata = {
  title: 'Early Access | CreviaCockpit',
  description: 'Join the waitlist for CreviaCockpit — live market regime detection, AI trade setups, and opportunity scanner for 16+ crypto assets.',
  openGraph: {
    title: 'CreviaCockpit — Early Access',
    description: 'Live regime detection, AI trade setups, opportunity scanner, risk calculator. Join the waitlist.',
    type: 'website',
  },
};

export default function WaitlistPage() {
  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-zinc-800">
        <div className="absolute inset-0 bg-linear-to-br from-emerald-950/20 via-zinc-950 to-zinc-950" />
        <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-emerald-500/5 blur-3xl" />

        <div className="relative mx-auto max-w-3xl px-4 pt-16 pb-8 sm:px-6 sm:pt-20 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-400 mb-5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Limited early access
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl mb-4">
            Crypto intelligence,{' '}
            <span className="text-emerald-400">actually actionable</span>
          </h1>
          <p className="text-lg text-zinc-400 max-w-xl mx-auto">
            Live regime detection, AI trade setups, and an opportunity scanner for 16+ assets.
            Early access members get Pro features free during beta.
          </p>
        </div>
      </section>

      {/* Multi-step flow */}
      <section className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
        <WaitlistFlow />
      </section>
    </div>
  );
}
