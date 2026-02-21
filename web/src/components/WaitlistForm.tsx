'use client';

import { useState, FormEvent } from 'react';

interface WaitlistFormProps {
  source?: string;
  compact?: boolean;           // compact=true for inline hero variant
}

export default function WaitlistForm({ source = 'landing', compact = false }: WaitlistFormProps) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email) return;
    setStatus('loading');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/waitlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name: name || undefined, source }),
      });

      const data = await res.json();

      if (!res.ok) {
        setMessage(data.detail || 'Something went wrong.');
        setStatus('error');
        return;
      }

      setMessage(data.message);
      setStatus('success');
    } catch {
      setMessage('Could not connect. Please try again.');
      setStatus('error');
    }
  }

  if (status === 'success') {
    return (
      <div className={`rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-6 py-5 text-center ${compact ? 'max-w-md' : ''}`}>
        <div className="text-2xl mb-2">✓</div>
        <p className="font-semibold text-emerald-400">You&apos;re on the list!</p>
        <p className="text-sm text-zinc-400 mt-1">{message}</p>
      </div>
    );
  }

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 max-w-md">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="your@email.com"
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <button
          type="submit"
          disabled={status === 'loading'}
          className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {status === 'loading' ? 'Joining...' : 'Join Waitlist'}
        </button>
        {status === 'error' && (
          <p className="text-xs text-red-400 mt-1 w-full">{message}</p>
        )}
      </form>
    );
  }

  // Full variant (for /waitlist page)
  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-full max-w-md mx-auto">
      {status === 'error' && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {message}
        </div>
      )}
      <div>
        <label className="block text-sm font-medium text-zinc-300 mb-1.5">Name <span className="text-zinc-600">(optional)</span></label>
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
        disabled={status === 'loading'}
        className="w-full rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors"
      >
        {status === 'loading' ? 'Joining...' : 'Request Early Access'}
      </button>
      <p className="text-xs text-center text-zinc-600">No spam. Unsubscribe anytime.</p>
    </form>
  );
}
