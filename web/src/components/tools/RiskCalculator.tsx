'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

interface MarketContext {
  regime: { name: string; confidence: number; color: string; trader_action: string } | null;
  funding_rate: number | null;
  liquidations_24h: number | null;
  volatility: string;
  fear_greed: number | null;
}

interface CalcResult {
  positionSize: number;
  riskReward: number;
  maxLoss: number;
  potentialGain: number;
  notionalValue: number;
  liquidationPrice: number | null;
  dailyFundingCost: number | null;
}

interface Warning {
  severity: 'high' | 'medium' | 'low';
  message: string;
  suggestion: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'rc_used';

function WaitlistGate({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-xl bg-zinc-950/90 backdrop-blur-sm p-6 text-center">
      <div className="max-w-xs">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 mx-auto">
          <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-white mb-2">Unlock Unlimited Access</h3>
        <p className="text-sm text-zinc-400 mb-5">
          You&apos;ve used your free calculation. Join the waitlist to get unlimited risk calculations,
          real-time market context warnings, and Pro access during beta.
        </p>
        <div className="flex flex-col gap-2">
          <Link
            href="/waitlist"
            className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors"
          >
            Join Waitlist — It&apos;s Free →
          </Link>
          <Link
            href="/auth/login"
            className="rounded-lg border border-zinc-700 px-5 py-2.5 text-sm font-medium text-zinc-400 hover:border-zinc-600 hover:text-white transition-colors"
          >
            Already have access? Sign in
          </Link>
          <button
            onClick={onDismiss}
            className="mt-1 text-xs text-zinc-600 hover:text-zinc-500 transition-colors"
          >
            Continue without saving results
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RiskCalculator() {
  const [entry, setEntry] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [leverage, setLeverage] = useState('1');
  const [riskAmount, setRiskAmount] = useState('100');
  const [direction, setDirection] = useState<'long' | 'short'>('long');

  const [result, setResult] = useState<CalcResult | null>(null);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [context, setContext] = useState<MarketContext | null>(null);
  const [showGate, setShowGate] = useState(false);

  // Check localStorage on mount — gate only shows on return visits, not mid-session
  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) === '1') {
      setShowGate(true);
    }
  }, []);

  // Fetch market context on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/intelligence/market-context`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setContext(data); })
      .catch(() => {});
  }, []);

  const calculate = useCallback(() => {
    const e = parseFloat(entry);
    const sl = parseFloat(stopLoss);
    const tp = parseFloat(takeProfit);
    const lev = parseFloat(leverage) || 1;
    const risk = parseFloat(riskAmount) || 100;

    if (!e || !sl || !tp || e <= 0 || sl <= 0 || tp <= 0) {
      setResult(null);
      return;
    }

    // Position size based on capital × leverage (margin-based approach)
    const stopDistance = Math.abs(e - sl);
    if (stopDistance === 0) return;

    const notional = risk * lev;               // total position value in USD
    const positionSize = notional / e;          // units of asset controlled
    const profitDistance = direction === 'long' ? tp - e : e - tp;
    const rr = profitDistance / stopDistance;
    const maxLoss = positionSize * stopDistance; // P&L at stop (can exceed margin if wide stop)
    const potentialGain = positionSize * profitDistance; // P&L at TP

    // Liquidation price (simplified for perpetual futures)
    let liqPrice: number | null = null;
    if (lev > 1) {
      const maintenanceMargin = 0.005; // 0.5% typical
      if (direction === 'long') {
        liqPrice = e * (1 - (1 / lev) + maintenanceMargin);
      } else {
        liqPrice = e * (1 + (1 / lev) - maintenanceMargin);
      }
    }

    // Daily funding cost
    let dailyFunding: number | null = null;
    if (context?.funding_rate != null && lev > 1) {
      // Funding paid 3x/day on most exchanges
      dailyFunding = Math.abs(context.funding_rate) * notional * 3;
    }

    setResult({
      positionSize: Math.round(positionSize * 10000) / 10000,
      riskReward: Math.round(rr * 100) / 100,
      maxLoss: Math.round(maxLoss * 100) / 100,
      potentialGain: Math.round(potentialGain * 100) / 100,
      notionalValue: Math.round(notional * 100) / 100,
      liquidationPrice: liqPrice ? Math.round(liqPrice * 100) / 100 : null,
      dailyFundingCost: dailyFunding ? Math.round(dailyFunding * 100) / 100 : null,
    });

    // Mark as used after first calculation — gate will appear on their NEXT visit
    localStorage.setItem(STORAGE_KEY, '1');

    // Generate warnings based on market context
    const w: Warning[] = [];

    if (context) {
      if (context.volatility === 'extreme' || context.volatility === 'elevated') {
        w.push({
          severity: 'high',
          message: `Volatility is ${context.volatility} — wider stops recommended`,
          suggestion: `Increase stop distance by 15% or reduce leverage to ${Math.max(1, Math.floor(lev / 2))}x`,
        });
      }

      if (context.funding_rate != null && Math.abs(context.funding_rate) > 0.0005 && lev > 1) {
        const dailyCost = Math.abs(context.funding_rate) * notional * 3;
        w.push({
          severity: dailyCost > risk * 0.1 ? 'high' : 'medium',
          message: `Funding rate at ${(context.funding_rate * 100).toFixed(4)}% — costs $${dailyCost.toFixed(2)}/day`,
          suggestion: 'Consider spot trade or short-term swing only',
        });
      }

      if (context.regime) {
        const riskOffRegimes = ['RISK_OFF', 'DISTRIBUTION', 'VOLATILITY_EXPANSION'];
        if (riskOffRegimes.includes(context.regime.name) && direction === 'long') {
          w.push({
            severity: 'medium',
            message: `Market in ${context.regime.name.replace('_', ' ')} regime`,
            suggestion: context.regime.trader_action || 'Consider reducing position size by 30-50%',
          });
        }
      }

      if (context.fear_greed != null) {
        if (context.fear_greed > 80 && direction === 'long') {
          w.push({
            severity: 'medium',
            message: `Extreme greed (${context.fear_greed}) — reversal risk elevated`,
            suggestion: 'Tighten stops or reduce position size',
          });
        } else if (context.fear_greed < 20 && direction === 'short') {
          w.push({
            severity: 'medium',
            message: `Extreme fear (${context.fear_greed}) — bounce risk elevated`,
            suggestion: 'Tighten stops or reduce position size',
          });
        }
      }
    }

    if (lev > 10) {
      w.push({
        severity: 'high',
        message: `High leverage (${lev}x) significantly increases liquidation risk`,
        suggestion: 'Consider reducing leverage to 5-10x',
      });
    }

    setWarnings(w);
  }, [entry, stopLoss, takeProfit, leverage, riskAmount, direction, context]);

  // Auto-calculate when inputs change
  useEffect(() => {
    calculate();
  }, [calculate]);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Input Panel */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-6">
        <h3 className="text-lg font-bold text-white mb-4">Position Calculator</h3>

        {/* Direction Toggle */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setDirection('long')}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              direction === 'long'
                ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30'
                : 'bg-zinc-800 text-zinc-400 hover:text-zinc-300'
            }`}
          >
            Long
          </button>
          <button
            onClick={() => setDirection('short')}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              direction === 'short'
                ? 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30'
                : 'bg-zinc-800 text-zinc-400 hover:text-zinc-300'
            }`}
          >
            Short
          </button>
        </div>

        <div className="space-y-3">
          {[
            { label: 'Entry Price', value: entry, set: setEntry, prefix: '$' },
            { label: 'Stop Loss', value: stopLoss, set: setStopLoss, prefix: '$' },
            { label: 'Take Profit', value: takeProfit, set: setTakeProfit, prefix: '$' },
            { label: 'Leverage', value: leverage, set: setLeverage, suffix: 'x' },
            { label: 'Capital (Margin)', value: riskAmount, set: setRiskAmount, prefix: '$' },
          ].map((field) => (
            <div key={field.label}>
              <label className="block text-xs text-zinc-500 mb-1">{field.label}</label>
              <div className="relative">
                {field.prefix && (
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-zinc-600">
                    {field.prefix}
                  </span>
                )}
                <input
                  type="number"
                  value={field.value}
                  onChange={(e) => field.set(e.target.value)}
                  className={`w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white placeholder-zinc-600 focus:border-emerald-500 focus:outline-none ${
                    field.prefix ? 'pl-7' : ''
                  }`}
                  placeholder="0.00"
                />
                {field.suffix && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-zinc-600">
                    {field.suffix}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Market Context Badge */}
        {context?.regime && (
          <div className="mt-4 rounded-lg bg-zinc-800/60 p-3">
            <p className="text-xs text-zinc-500 mb-1">Current Market Regime</p>
            <p className="text-sm font-medium text-zinc-300">
              {context.regime.name.replace(/_/g, ' ')} ({Math.round(context.regime.confidence * 100)}%)
            </p>
          </div>
        )}
      </div>

      {/* Results Panel */}
      <div className="space-y-4">
        {/* Calculation Results */}
        {result && (
          <div className="relative rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-6 overflow-hidden">
            {showGate && (
              <WaitlistGate onDismiss={() => setShowGate(false)} />
            )}
            <h3 className="text-lg font-bold text-white mb-4">Results</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Position Size', value: `${result.positionSize}` },
                { label: 'Risk/Reward', value: `${result.riskReward}:1`, highlight: result.riskReward >= 2 },
                { label: 'Loss at Stop', value: `$${result.maxLoss}`, negative: true },
                { label: 'Gain at Target', value: `$${result.potentialGain}`, positive: true },
                { label: 'Notional Value', value: `$${result.notionalValue.toLocaleString()}` },
                ...(result.liquidationPrice ? [{ label: 'Liquidation Price', value: `$${result.liquidationPrice.toLocaleString()}`, negative: true }] : []),
                ...(result.dailyFundingCost ? [{ label: 'Daily Funding Cost', value: `$${result.dailyFundingCost}` }] : []),
              ].map((item) => (
                <div key={item.label} className="rounded-lg bg-zinc-800/60 p-3">
                  <p className="text-xs text-zinc-500">{item.label}</p>
                  <p className={`text-lg font-bold ${
                    'positive' in item && item.positive ? 'text-emerald-400' :
                    'negative' in item && item.negative ? 'text-red-400' :
                    'highlight' in item && item.highlight ? 'text-emerald-400' :
                    'text-zinc-200'
                  }`}>
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Market Warnings */}
        {warnings.length > 0 && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-6">
            <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-3">
              Market Condition Warnings
            </h3>
            <div className="space-y-2">
              {warnings.map((w, i) => (
                <div
                  key={i}
                  className={`rounded-lg p-3 ${
                    w.severity === 'high'
                      ? 'bg-red-500/10 border border-red-500/20'
                      : w.severity === 'medium'
                      ? 'bg-yellow-500/10 border border-yellow-500/20'
                      : 'bg-zinc-800/60'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold uppercase ${
                      w.severity === 'high' ? 'text-red-400' :
                      w.severity === 'medium' ? 'text-yellow-400' :
                      'text-zinc-400'
                    }`}>
                      {w.severity}
                    </span>
                    <span className="text-sm text-zinc-300">{w.message}</span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1 ml-10">{w.suggestion}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {!result && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 text-center">
            <p className="text-sm text-zinc-500">
              Enter entry price, stop loss, and take profit to calculate.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
