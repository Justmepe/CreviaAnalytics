'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';

type Step = 'preview' | 'tweet' | 'form' | 'success';

const TWEET_TEXT = encodeURIComponent(
  `I just found @CreviaAnalytics 🧠

→ Live market regime detection (RISK_ON / RISK_OFF / ACCUMULATION)
→ AI-powered trade setups with entry zones & R/R ratios
→ Opportunity scanner for 16+ crypto assets
→ Risk calculator with real-time market warnings

Joining the waitlist now 👇
creviaanalytics.com/waitlist`
);

const TWEET_URL = `https://x.com/intent/post?text=${TWEET_TEXT}`;

const features = [
  {
    icon: '📡',
    title: 'Market Regime Detection',
    desc: 'Real-time detection across 6 regimes — RISK_ON, RISK_OFF, ACCUMULATION, DISTRIBUTION, ALTSEASON, and VOLATILITY_EXPANSION.',
    tag: 'Live now',
    tagColor: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  },
  {
    icon: '🎯',
    title: 'AI Trade Setups',
    desc: 'Claude AI generates entry zones, stop loss, take profits, and position sizing for BTC, ETH, SOL, and 13+ assets every cycle.',
    tag: 'Pro',
    tagColor: 'text-violet-400 border-violet-500/30 bg-violet-500/10',
  },
  {
    icon: '🔍',
    title: 'Opportunity Scanner',
    desc: 'Every tracked asset scored 0–10 across R/R ratio, regime alignment, confidence, and momentum. Best setups ranked automatically.',
    tag: 'Pro',
    tagColor: 'text-violet-400 border-violet-500/30 bg-violet-500/10',
  },
  {
    icon: '📊',
    title: 'Risk Calculator',
    desc: 'Position sizing with real-time market warnings — liquidation price, daily funding cost, regime context. Try it free below.',
    tag: 'Free preview',
    tagColor: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  },
  {
    icon: '📓',
    title: 'Trade Journal',
    desc: 'Log trades, auto-calculate P&L, track win rate and profit factor. Close positions and see your edge over time.',
    tag: 'Pro',
    tagColor: 'text-violet-400 border-violet-500/30 bg-violet-500/10',
  },
  {
    icon: '⚡',
    title: 'Breaking News Alerts',
    desc: 'RSS-powered news scanner posts to X automatically when relevance score ≥ 0.85. You never miss a market-moving event.',
    tag: 'Live now',
    tagColor: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  },
];

export default function WaitlistFlow() {
  const [step, setStep] = useState<Step>('preview');
  const [tweeted, setTweeted] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function handleOpenTweet() {
    window.open(TWEET_URL, '_blank', 'noopener,noreferrer,width=600,height=500');
    setTimeout(() => setTweeted(true), 1500); // unlock "I've shared" after brief delay
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!email) return;
    setSubmitting(true);

    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name: name || undefined, source: 'waitlist_tweet_flow' }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Something went wrong.');
        setSubmitting(false);
        return;
      }
      setStep('success');
    } catch {
      setError('Could not connect. Please try again.');
      setSubmitting(false);
    }
  }

  // ── Success ──────────────────────────────────────────────
  if (step === 'success') {
    return (
      <div className="text-center py-16">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 mb-5">
          <span className="text-3xl">✓</span>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">You&apos;re on the list!</h2>
        <p className="text-zinc-400 max-w-md mx-auto mb-8">
          We&apos;ll reach out to <span className="text-white font-medium">{email}</span> when early access opens.
          Keep an eye on your inbox.
        </p>
        <div className="flex justify-center gap-3">
          <Link
            href="/tools/risk-calculator"
            className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
          >
            Try Risk Calculator
          </Link>
          <Link
            href="/"
            className="rounded-lg border border-zinc-700 px-5 py-2.5 text-sm font-semibold text-zinc-400 hover:border-zinc-600 hover:text-white transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* ── Step indicator ─────────────────────────────────── */}
      <div className="flex items-center justify-center gap-2 mb-10">
        {(['preview', 'tweet', 'form'] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`h-7 w-7 rounded-full border text-xs font-bold flex items-center justify-center transition-all ${
              step === s
                ? 'bg-emerald-500 border-emerald-500 text-zinc-950'
                : ['preview', 'tweet', 'form'].indexOf(step) > i
                  ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-600'
            }`}>
              {['preview', 'tweet', 'form'].indexOf(step) > i ? '✓' : i + 1}
            </div>
            <span className={`text-xs hidden sm:block ${step === s ? 'text-white' : 'text-zinc-600'}`}>
              {s === 'preview' ? 'Preview' : s === 'tweet' ? 'Share' : 'Sign Up'}
            </span>
            {i < 2 && <div className="w-8 h-px bg-zinc-800 mx-1" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Preview ────────────────────────────────── */}
      {step === 'preview' && (
        <div>
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-white mb-3">Here&apos;s what&apos;s coming</h2>
            <p className="text-zinc-400 max-w-xl mx-auto">
              Crevia Analytics is a full-stack crypto intelligence platform. Early access members get Pro features free during beta.
            </p>
          </div>

          {/* Feature grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-8">
            {features.map((f) => (
              <div key={f.title} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                <div className="flex items-start justify-between mb-3">
                  <span className="text-2xl">{f.icon}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${f.tagColor}`}>
                    {f.tag}
                  </span>
                </div>
                <h3 className="font-semibold text-white mb-1 text-sm">{f.title}</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          {/* Risk calculator teaser */}
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 mb-8 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="text-xs text-blue-400 font-semibold mb-1">FREE PREVIEW — No sign-up needed</div>
              <p className="text-sm text-white font-medium">Try the Risk Calculator right now</p>
              <p className="text-xs text-zinc-500 mt-0.5">Position sizing with liquidation price, R/R, and live market regime warnings.</p>
            </div>
            <Link
              href="/tools/risk-calculator"
              target="_blank"
              className="shrink-0 rounded-lg border border-blue-500/30 px-4 py-2 text-sm font-semibold text-blue-400 hover:bg-blue-500/10 transition-colors"
            >
              Open Calculator →
            </Link>
          </div>

          <div className="text-center">
            <button
              onClick={() => setStep('tweet')}
              className="rounded-lg bg-emerald-500 px-8 py-3 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
            >
              Request Early Access →
            </button>
            <p className="text-xs text-zinc-600 mt-3">Takes 30 seconds. No credit card.</p>
          </div>
        </div>
      )}

      {/* ── Step 2: Tweet to unlock ─────────────────────────── */}
      {step === 'tweet' && (
        <div className="max-w-lg mx-auto text-center">
          <div className="text-4xl mb-4">𝕏</div>
          <h2 className="text-2xl font-bold text-white mb-3">Share to unlock access</h2>
          <p className="text-zinc-400 mb-8">
            Post the tweet below to help spread the word. Once you&apos;ve shared, continue to the sign-up form.
          </p>

          {/* Tweet preview */}
          <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-5 text-left mb-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-8 w-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-white">You</div>
              <div>
                <div className="text-sm font-semibold text-white">Your handle</div>
                <div className="text-xs text-zinc-500">@you</div>
              </div>
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{`I just found @CreviaAnalytics 🧠

→ Live market regime detection (RISK_ON / RISK_OFF / ACCUMULATION)
→ AI-powered trade setups with entry zones & R/R ratios
→ Opportunity scanner for 16+ crypto assets
→ Risk calculator with real-time market warnings

Joining the waitlist now 👇
creviaanalytics.com/waitlist`}</p>
          </div>

          <button
            onClick={handleOpenTweet}
            className="w-full rounded-lg bg-[#1d9bf0] px-6 py-3 text-sm font-semibold text-white hover:bg-[#1a8cd8] transition-colors mb-4"
          >
            Post on X →
          </button>

          {tweeted ? (
            <button
              onClick={() => setStep('form')}
              className="w-full rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
            >
              I&apos;ve shared — Continue →
            </button>
          ) : (
            <p className="text-xs text-zinc-600">Post the tweet above, then the continue button will appear.</p>
          )}

          <button
            onClick={() => setStep('preview')}
            className="mt-4 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            ← Back
          </button>
        </div>
      )}

      {/* ── Step 3: Sign-up form ────────────────────────────── */}
      {step === 'form' && (
        <div className="max-w-md mx-auto">
          <div className="text-center mb-8">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 mb-3">
              <span className="text-lg">🎉</span>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Almost there</h2>
            <p className="text-zinc-400 text-sm">Enter your details and we&apos;ll reach out when early access opens.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                Name <span className="text-zinc-600">(optional)</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Securing your spot...' : 'Secure My Early Access'}
            </button>
            <p className="text-xs text-center text-zinc-600">No spam. Unsubscribe anytime.</p>
          </form>

          <button
            onClick={() => setStep('tweet')}
            className="mt-4 text-xs text-zinc-600 hover:text-zinc-400 transition-colors block mx-auto"
          >
            ← Back
          </button>
        </div>
      )}
    </div>
  );
}
