import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'About CreviaCockpit',
  description: 'CreviaCockpit delivers real-time crypto market intelligence — covering BTC, ETH, DeFi, memecoins, on-chain whale flows, and macro cross-asset analysis.',
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">

      <h1 className="text-4xl font-bold text-white mb-4">About CreviaCockpit</h1>
      <p className="text-zinc-400 text-lg mb-12 leading-relaxed">
        Real-time crypto market intelligence for traders who want data, not noise.
      </p>

      <div className="space-y-10 text-sm leading-relaxed text-zinc-300">

        <section>
          <h2 className="text-xl font-semibold text-white mb-3">What We Do</h2>
          <p>
            CreviaCockpit is a crypto market intelligence platform that publishes five structured
            daily analyses covering major assets, DeFi, memecoins, privacy coins, and macro
            cross-asset themes. Every piece of analysis is grounded in live market data — prices,
            derivatives positioning, on-chain whale flows, and macro indicators — not opinion or
            speculation.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Our Daily Coverage</h2>
          <ul className="space-y-2">
            {[
              ['08:00 UTC', 'Morning Scan', 'Full market sweep across 16+ assets with sector breakdowns'],
              ['12:00 UTC', 'News Digest', 'Synthesised news flow — what happened and what it means for markets'],
              ['15:00 UTC', 'Whale Activity', 'On-chain large-wallet flows correlated with price and leverage data'],
              ['18:00 UTC', 'Macro Tie-In', 'DXY, gold, equities, real yields — connected to crypto positioning'],
              ['21:00 UTC', 'Evening Outlook', 'Day wrap with key levels and overnight risk framework'],
            ].map(([time, label, desc]) => (
              <li key={label} className="flex gap-3">
                <span className="text-emerald-400 font-mono text-xs mt-0.5 whitespace-nowrap">{time}</span>
                <span><strong className="text-white">{label}</strong> — {desc}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white mb-3">What We Are Not</h2>
          <p>
            We are not a financial advisor, and we do not offer trading signals or sell trade
            recommendations. Our platform helps traders make more informed decisions by providing
            structured data interpretation and market context. All analysis is for informational
            purposes only.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Intelligence Platform</h2>
          <p>
            Registered users get access to the full intelligence platform: real-time market regime
            detection, on-chain whale tracking, cross-asset correlation matrices, trade setup
            scoring, and a personal trade journal with automatic P&amp;L tracking.
          </p>
          <div className="mt-4 flex gap-4">
            <Link
              href="/waitlist"
              className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
            >
              Join Waitlist
            </Link>
            <Link
              href="/analysis"
              className="inline-flex items-center rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:border-zinc-500 transition-colors"
            >
              Browse Analysis
            </Link>
          </div>
        </section>

      </div>
    </div>
  );
}
