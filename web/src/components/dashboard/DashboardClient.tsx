'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getPortfolioStats, getJournalEntries, syncPortfolio, timeAgo, getCurrentRegime, getLatestTradeSetups, getContentFeed } from '@/lib/api';
import type {
  PortfolioStats, JournalEntry, MarketRegime, TradeSetup,
  ContentPost, PortfolioSummary, RegimeSignal,
} from '@/types';
import CockpitShell from '@/components/layout/CockpitShell';
import PriceChartLWC from '@/components/dashboard/PriceChartLWC';

interface DashboardClientProps {
  regime: MarketRegime | null;
  setups: TradeSetup[];
  recentContent: ContentPost[];
  btcPrice: number | null;
  ethPrice: number | null;
  solPrice: number | null;
  xmrPrice: number | null;
  bnbPrice: number | null;
  aavePrice: number | null;
  solChange: number | null;
  xmrChange: number | null;
  marketCap: number | null;
  fearGreed: number | null;
  fearGreedLabel: string | null;
}

// ── Tier system ───────────────────────────────────────────────────────────────
const TIER_LEVEL: Record<string, number> = { free: 0, basic: 1, pro: 2, enterprise: 3 };

// ── Regime colours ────────────────────────────────────────────────────────────
const REGIME_COLORS: Record<string, { text: string; bg: string; border: string; hex: string }> = {
  RISK_ON:              { text: '#00e5a0', bg: 'rgba(0,229,160,0.07)',   border: 'rgba(0,229,160,0.2)',   hex: '#00e5a0' },
  ACCUMULATION:         { text: '#00e5a0', bg: 'rgba(0,229,160,0.07)',   border: 'rgba(0,229,160,0.2)',   hex: '#00e5a0' },
  ALTSEASON_CONFIRMED:  { text: '#f0a030', bg: 'rgba(240,160,48,0.07)',  border: 'rgba(240,160,48,0.2)',  hex: '#f0a030' },
  NEUTRAL:              { text: '#788098', bg: 'rgba(30,35,50,0.5)',     border: '#1a2030',               hex: '#788098' },
  DISTRIBUTION:         { text: '#f0a030', bg: 'rgba(240,160,48,0.07)',  border: 'rgba(240,160,48,0.2)',  hex: '#f0a030' },
  RISK_OFF:             { text: '#ff3d5a', bg: 'rgba(255,61,90,0.07)',   border: 'rgba(255,61,90,0.2)',   hex: '#ff3d5a' },
  VOLATILITY_EXPANSION: { text: '#9b7cf4', bg: 'rgba(155,124,244,0.07)', border: 'rgba(155,124,244,0.2)', hex: '#9b7cf4' },
};

// ── Asset gradients ───────────────────────────────────────────────────────────
const ASSET_BG: Record<string, string> = {
  BTC:  'linear-gradient(135deg,#f7931a,#e07c10)',
  ETH:  'linear-gradient(135deg,#627eea,#4f67c8)',
  SOL:  'linear-gradient(135deg,#9945ff,#14f195)',
  BNB:  'linear-gradient(135deg,#f3ba2f,#d4a228)',
  AAVE: 'linear-gradient(135deg,#2ebac6,#1a9aaa)',
  XMR:  'linear-gradient(135deg,#f06020,#c84010)',
  DOGE: 'linear-gradient(135deg,#c2a633,#a88b28)',
  DEFAULT: 'linear-gradient(135deg,#3d7fff,#0050cc)',
};
function assetBg(sym: string): string {
  const key = Object.keys(ASSET_BG).find(k => sym.startsWith(k));
  return key ? ASSET_BG[key] : ASSET_BG.DEFAULT;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtPrice(p: number | null): string {
  if (!p) return '--';
  return p >= 1000
    ? `$${p.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
    : `$${p.toFixed(2)}`;
}
function fmtLarge(n: number | null): string {
  if (!n) return '--';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(1)}B`;
  return `$${n.toLocaleString()}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// TierLock
// ─────────────────────────────────────────────────────────────────────────────
function TierLock({ children, title, minTierLabel = 'Basic' }: {
  children: React.ReactNode; title?: string; minTierLabel?: string;
}) {
  return (
    <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', border: '1px solid #1a2030' }}>
      <div style={{ filter: 'blur(4px)', userSelect: 'none', pointerEvents: 'none', opacity: 0.35 }}>{children}</div>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(7,8,9,0.78)', backdropFilter: 'blur(2px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, zIndex: 10 }}>
        <div style={{ fontSize: 22, opacity: 0.6 }}>⬡</div>
        {title && <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#788098', textAlign: 'center', padding: '0 20px' }}>{title}</div>}
        <Link href="/waitlist" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#f0a030', padding: '6px 16px', borderRadius: 3, fontWeight: 500, textDecoration: 'none' }}>
          Unlock with {minTierLabel} →
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PremiumLock
// ─────────────────────────────────────────────────────────────────────────────
function PremiumLock() {
  return (
    <div style={{ position: 'absolute', inset: 0, backdropFilter: 'blur(4px)', background: 'rgba(7,8,9,0.78)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, zIndex: 10, borderRadius: 8 }}>
      <div style={{ fontSize: 20 }}>⚡</div>
      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '0.5px', textTransform: 'uppercase', color: '#788098' }}>Premium Feature</div>
      <Link href="/waitlist" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#f0a030', padding: '5px 14px', borderRadius: 3, fontWeight: 500, textDecoration: 'none' }}>
        Upgrade to Premium →
      </Link>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// F&G Gauge
// ─────────────────────────────────────────────────────────────────────────────
function FGGauge({ value, label }: { value: number | null; label: string | null }) {
  const v = value ?? 50;
  const arcLen = 125.66;
  const dashOffset = arcLen * (1 - v / 100);
  const angle = Math.PI * (1 - v / 100);
  const nLen = 34;
  const nx = 50 + nLen * Math.cos(angle);
  const ny = 50 - nLen * Math.sin(angle);
  const gaugeColor = v <= 25 ? '#ff3d5a' : v <= 45 ? '#f0a030' : v <= 55 ? '#e8d020' : '#00e5a0';

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: 14, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a' }}>Fear &amp; Greed</div>
      <svg viewBox="0 0 100 55" width={96} height={52}>
        <defs>
          <linearGradient id="fgg" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#ff3d5a" />
            <stop offset="40%"  stopColor="#f0a030" />
            <stop offset="70%"  stopColor="#e8d020" />
            <stop offset="100%" stopColor="#00e5a0" />
          </linearGradient>
        </defs>
        <path d="M10,50 A40,40 0 0,1 90,50" stroke="#1a2030"    strokeWidth="8" fill="none" strokeLinecap="round" />
        <path d="M10,50 A40,40 0 0,1 90,50" stroke="url(#fgg)" strokeWidth="8" fill="none" strokeLinecap="round" strokeDasharray={arcLen} strokeDashoffset={dashOffset} />
        <line x1="50" y1="50" x2={nx.toFixed(1)} y2={ny.toFixed(1)} stroke="#788098" strokeWidth="2" strokeLinecap="round" />
        <circle cx="50" cy="50" r="3.5" fill="#0c0e12" stroke="#1a2030" strokeWidth="2" />
      </svg>
      <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 38, lineHeight: 1, color: gaugeColor }}>{value ?? '--'}</div>
      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: gaugeColor, letterSpacing: '0.8px', textTransform: 'uppercase' }}>{label || 'Neutral'}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Regime Hero
// ─────────────────────────────────────────────────────────────────────────────
function RegimeHero({ regime, fearGreed, fearGreedLabel }: {
  regime: MarketRegime | null; fearGreed: number | null; fearGreedLabel: string | null;
}) {
  const rs = regime ? (REGIME_COLORS[regime.regime_name] || REGIME_COLORS.NEUTRAL) : REGIME_COLORS.NEUTRAL;

  const rawBars: RegimeSignal[] = regime?.supporting_signals?.slice(0, 4) ?? [];
  // Normalize bar widths: largest contribution = 100%, color from matched boolean
  const maxContrib = rawBars.length ? Math.max(...rawBars.map(s => s.contribution)) : 1;
  const bars = rawBars.length >= 1
    ? rawBars.map(s => ({
        label: s.metric.length > 26 ? s.metric.slice(0, 24) + '…' : s.metric,
        pct: Math.round((s.contribution / maxContrib) * 100),
        matched: s.matched,
      }))
    : [
        { label: 'Exchange Netflow', pct: 72, matched: true },
        { label: 'Funding Rate',     pct: 61, matched: true },
        { label: 'OI Trend',         pct: 55, matched: false },
        { label: 'Stablecoin Supply',pct: 83, matched: true },
      ];

  const bias = regime?.regime_name?.match(/RISK_ON|ACCUMULATION/) ? 'Long-favoured'
    : regime?.regime_name?.match(/RISK_OFF/) ? 'Short-favoured' : 'Neutral bias';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: 12, marginBottom: 12 }}>
      {/* Left: regime card */}
      <div style={{ background: '#10141c', border: `1px solid ${rs.border}`, borderRadius: 8, padding: '16px 20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 80% 60% at 80% 50%, ${rs.hex}08 0%, transparent 70%)`, pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg,transparent,${rs.hex},transparent)` }} />

        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
              Current Market Regime
            </div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, letterSpacing: '2px', color: rs.text, lineHeight: 1 }}>
              {regime ? regime.regime_name.replace(/_/g, ' ') : 'NO DATA'}
            </div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', marginTop: 3 }}>
              {regime
                ? `${Math.round((regime.confidence || 0) * 100)}% confidence${regime.historical_accuracy ? ` · ${Math.round(regime.historical_accuracy * 100)}% accuracy` : ''}`
                : 'Engine not running — start main.py'}
            </div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 16 }}>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '5px 12px', borderRadius: 3, background: rs.bg, color: rs.text, border: `1px solid ${rs.border}`, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              ✓ {bias}
            </div>
            {regime?.detected_at && (
              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', marginTop: 5, display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
                <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#38405a', display: 'inline-block' }} />
                {timeAgo(regime.detected_at)}
              </div>
            )}
          </div>
        </div>

        {/* Factor bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {bars.map((b, i) => {
            const barCol = b.matched ? '#00e5a0' : '#ff3d5a';
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a', width: 108, flexShrink: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{b.label}</span>
                <div style={{ flex: 1, height: 3, background: '#1a2030', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 2, background: barCol, width: `${b.pct}%`, transition: 'width 1s ease' }} />
                </div>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#788098', width: 28, textAlign: 'right', flexShrink: 0 }}>{b.pct}%</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right: F&G gauge */}
      <FGGauge value={fearGreed} label={fearGreedLabel} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Live Signals (COL 1, full height)
// ─────────────────────────────────────────────────────────────────────────────
function LiveSignals({ regime, setups, content }: {
  regime: MarketRegime | null; setups: TradeSetup[]; content: ContentPost[];
}) {
  type Sig = { icon: string; ck: string; title: string; desc: string; time: string };
  const sigs: Sig[] = [];

  if (regime) {
    sigs.push({
      icon: '📡', ck: 'g',
      title: `${regime.regime_name.replace(/_/g, ' ')} confirmed at ${Math.round((regime.confidence || 0) * 100)}%`,
      desc: regime.trader_action || regime.description || 'Monitor for regime-aligned setups',
      time: regime.detected_at ? timeAgo(regime.detected_at) : 'now',
    });
  }
  setups.slice(0, 3).forEach(s => {
    const rr = s.take_profits?.[0]?.rr;
    const entry = s.entry_zones?.[0]?.price;
    sigs.push({
      icon: '⚡', ck: 'a',
      title: `${s.asset} ${s.direction} setup${rr ? ` — ${rr.toFixed(1)}R` : ''}`,
      desc: `Entry ${entry ? fmtPrice(entry) : 'at market'}${s.stop_loss ? ` · SL ${fmtPrice(s.stop_loss.price)}` : ''}`,
      time: s.created_at ? timeAgo(s.created_at) : 'recent',
    });
  });
  content.slice(0, 5).forEach(p => {
    const icon = p.content_type === 'risk_alert' ? '⚠' : p.content_type === 'thread' ? '📊' : '↗';
    const ck   = p.content_type === 'risk_alert' ? 'r' : p.content_type === 'news_tweet' ? 'b' : 'g';
    sigs.push({
      icon, ck,
      title: p.title || p.excerpt?.slice(0, 70) || 'Market update',
      desc:  p.tickers?.length ? `${p.tickers.slice(0, 3).join(', ')} — ${p.excerpt?.slice(0, 80) || ''}` : (p.excerpt?.slice(0, 80) || ''),
      time:  p.published_at ? timeAgo(p.published_at) : '',
    });
  });
  if (!sigs.length) {
    sigs.push({ icon: '📡', ck: 'b', title: 'Cockpit scanning markets…', desc: 'Signals appear here as the engine generates intelligence', time: 'now' });
  }

  const BG:  Record<string, string> = { g: 'rgba(0,229,160,0.08)', b: 'rgba(61,127,255,0.08)', a: 'rgba(240,160,48,0.08)', r: 'rgba(255,61,90,0.08)' };
  const BRD: Record<string, string> = { g: 'rgba(0,229,160,0.15)', b: 'rgba(61,127,255,0.15)', a: 'rgba(240,160,48,0.15)', r: 'rgba(255,61,90,0.15)' };

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column', gridRow: '1 / 3' }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Live Signals</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase', background: 'rgba(0,229,160,0.08)', color: '#00e5a0', border: '1px solid rgba(0,229,160,0.2)', padding: '2px 6px', borderRadius: 2 }}>
          <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
          Real-time
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', scrollbarWidth: 'thin', scrollbarColor: '#1a2030 transparent' }}>
        {sigs.map((sig, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '9px 14px', borderBottom: '1px solid #1a2030', cursor: 'pointer', transition: 'background 0.15s' }}
            onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
            <div style={{ width: 24, height: 24, borderRadius: 5, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, marginTop: 1, background: BG[sig.ck], border: `1px solid ${BRD[sig.ck]}` }}>
              {sig.icon}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11.5, fontWeight: 500, color: '#e2e6f0', marginBottom: 1, lineHeight: 1.3 }}>{sig.title}</div>
              <div style={{ fontSize: 10.5, color: '#38405a', lineHeight: 1.4, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const }}>{sig.desc}</div>
            </div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', flexShrink: 0, marginTop: 1 }}>{sig.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Active Setups (COL 2 ROW 1)
// ─────────────────────────────────────────────────────────────────────────────
function ActiveSetups({ setups, isPremium }: { setups: TradeSetup[]; isPremium: boolean }) {
  return (
    <div style={{ position: 'relative', background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Active Trade Setups</span>
        <Link href="/intelligence/setups" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', textTransform: 'uppercase', letterSpacing: '0.8px' }}>View all →</Link>
      </div>

      {setups.length === 0 ? (
        <div style={{ padding: '20px 14px', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
          No setups yet — engine generates them each cycle.
        </div>
      ) : (
        setups.slice(0, 3).map((s, i) => {
          const isLong = s.direction === 'LONG';
          const entry  = s.entry_zones?.[0]?.price;
          const tp     = s.take_profits?.[0]?.price;
          const sl     = s.stop_loss?.price;
          const rr     = s.take_profits?.[0]?.rr;
          return (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 14px', borderBottom: '1px solid #1a2030', cursor: 'pointer', transition: 'background 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <div style={{ width: 20, height: 20, borderRadius: 4, background: assetBg(s.asset), display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 6.5, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
                    {s.asset.slice(0, 3)}
                  </div>
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: '#e2e6f0' }}>{s.asset}</div>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a' }}>{s.setup_type || 'Setup'}</div>
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 12, letterSpacing: '1px', padding: '2px 7px', borderRadius: 3, background: isLong ? 'rgba(0,229,160,0.1)' : 'rgba(255,61,90,0.1)', color: isLong ? '#00e5a0' : '#ff3d5a' }}>
                  {s.direction}
                </div>
              </div>

              {entry && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5 }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Entry</div>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>{fmtPrice(entry)}</div>
                  </div>
                  {tp && (
                    <div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Take Profit</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#00e5a0' }}>{fmtPrice(tp)}</div>
                    </div>
                  )}
                  {sl && (
                    <div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>Stop Loss</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#ff3d5a' }}>{fmtPrice(sl)}</div>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                {rr && (
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, background: 'rgba(240,160,48,0.08)', color: '#f0a030', border: '1px solid rgba(240,160,48,0.2)', padding: '2px 7px', borderRadius: 3 }}>
                    {rr.toFixed(1)}R
                  </span>
                )}
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a', display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
                  {s.created_at ? timeAgo(s.created_at) : 'New'}
                </span>
              </div>
            </div>
          );
        })
      )}

      {!isPremium && <PremiumLock />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Price Chart (COL 2 ROW 2) — delegates to PriceChartLWC (Lightweight Charts + real Binance klines)
// ─────────────────────────────────────────────────────────────────────────────
function PriceChart({ btcPrice, ethPrice, solPrice, xmrPrice, setups, regime }: {
  btcPrice: number | null; ethPrice: number | null;
  solPrice: number | null; xmrPrice: number | null;
  setups: TradeSetup[]; regime: MarketRegime | null;
}) {
  return <PriceChartLWC btcPrice={btcPrice} ethPrice={ethPrice} solPrice={solPrice} xmrPrice={xmrPrice} setups={setups} regime={regime} />;
}

// ─────────────────────────────────────────────────────────────────────────────
// Whale Activity (COL 3 ROW 1)
// ─────────────────────────────────────────────────────────────────────────────
const WHALE_DATA = [
  { asset: 'ETH', bg: ASSET_BG.ETH, dir: 'Outflow', isOut: true,  desc: '42,000 ETH left Binance',  sub: '→ unknown cold wallet',         amount: '$86.4M', time: '9m ago',  bar: 88,  barCol: '#00e5a0' },
  { asset: 'BTC', bg: ASSET_BG.BTC, dir: 'Inflow',  isOut: false, desc: '4,200 BTC to Binance',      sub: 'Watch for sell pressure',        amount: '$283M',  time: '26m ago', bar: 100, barCol: '#ff3d5a' },
  { asset: 'SOL', bg: ASSET_BG.SOL, dir: 'Inflow',  isOut: false, desc: '9,800 SOL to OKX',          sub: 'Potential distribution signal',  amount: '$856K',  time: '41m ago', bar: 42,  barCol: '#ff3d5a' },
  { asset: 'BTC', bg: ASSET_BG.BTC, dir: 'Outflow', isOut: true,  desc: '2,100 BTC left Kraken',     sub: '→ self-custody, accumulation',   amount: '$141M',  time: '58m ago', bar: 60,  barCol: '#00e5a0' },
];

function WhaleActivity({ isBasicPlus }: { isBasicPlus: boolean }) {
  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Whale Activity</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase', background: 'rgba(0,229,160,0.08)', color: '#00e5a0', border: '1px solid rgba(0,229,160,0.2)', padding: '2px 6px', borderRadius: 2 }}>
          <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
          Live
        </span>
      </div>

      {isBasicPlus ? (
        <>
          {WHALE_DATA.map((w, i) => (
            <div key={i} style={{ padding: '9px 14px', borderBottom: '1px solid #1a2030', cursor: 'pointer', transition: 'background 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 18, height: 18, borderRadius: 4, background: w.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 6, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
                    {w.asset}
                  </div>
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: '#e2e6f0' }}>{w.asset}</span>
                </div>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '0.5px', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2, background: w.isOut ? 'rgba(0,229,160,0.08)' : 'rgba(255,61,90,0.08)', color: w.isOut ? '#00e5a0' : '#ff3d5a', border: `1px solid ${w.isOut ? 'rgba(0,229,160,0.2)' : 'rgba(255,61,90,0.2)'}` }}>
                  {w.dir}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10.5, color: '#38405a', lineHeight: 1.4 }}>{w.desc}</div>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, color: '#38405a' }}>{w.sub}</div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 8 }}>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: w.isOut ? '#00e5a0' : '#ff3d5a' }}>{w.amount}</div>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#38405a', marginTop: 3 }}>{w.time}</div>
                </div>
              </div>
              <div style={{ height: 2, background: '#1a2030', borderRadius: 1, marginTop: 5, overflow: 'hidden' }}>
                <div style={{ height: '100%', borderRadius: 1, background: w.barCol, width: `${w.bar}%`, transition: 'width 1.2s ease' }} />
              </div>
            </div>
          ))}
          <div style={{ padding: '8px 14px', borderTop: '1px solid #1a2030' }}>
            <Link href="/whale-tracker" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
              onMouseEnter={e => (e.currentTarget.style.color = '#00e5a0')}
              onMouseLeave={e => (e.currentTarget.style.color = '#38405a')}>
              View full whale dashboard →
            </Link>
          </div>
        </>
      ) : (
        <TierLock title="Whale activity · Basic or higher" minTierLabel="Basic">
          <div style={{ padding: 14 }}>
            {WHALE_DATA.slice(0, 2).map((w, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #1a2030' }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>{w.desc}</div>
              </div>
            ))}
          </div>
        </TierLock>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Cockpit Feed Panel (COL 3 ROW 2)
// ─────────────────────────────────────────────────────────────────────────────
const FEED_META: Record<string, { label: string; color: string; bg: string; border: string; leftBorder: string }> = {
  thread:     { label: '📊 Thread',  color: '#788098', bg: 'rgba(30,35,50,.5)',     border: '#1a2030',               leftBorder: '#38405a' },
  memo:       { label: '📋 Memo',    color: '#788098', bg: 'rgba(30,35,50,.5)',     border: '#1a2030',               leftBorder: '#38405a' },
  news_tweet: { label: '📡 Alert',   color: '#3d7fff', bg: 'rgba(61,127,255,.08)', border: 'rgba(61,127,255,.2)',  leftBorder: '#3d7fff' },
  risk_alert: { label: '🔔 Risk',    color: '#f0a030', bg: 'rgba(240,160,48,.08)', border: 'rgba(240,160,48,.2)',  leftBorder: '#f0a030' },
};

function CockpitFeedPanel({ content }: { content: ContentPost[] }) {
  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: 320 }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Cockpit Feed</span>
          <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
        </div>
        <Link href="/analysis" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>View all →</Link>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', scrollbarWidth: 'thin', scrollbarColor: '#1a2030 transparent' }}>
        {content.length > 0 ? content.map(post => {
          const meta = FEED_META[post.content_type] || FEED_META.thread;
          return (
            <Link key={post.id} href={`/post/${post.slug}`} style={{ display: 'block', padding: '8px 12px 8px 14px', borderBottom: '1px solid #1a2030', textDecoration: 'none', cursor: 'pointer', transition: 'background 0.15s', borderLeft: `2px solid ${meta.leftBorder}40` }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 2, background: meta.bg, color: meta.color, border: `1px solid ${meta.border}` }}>{meta.label}</span>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, color: '#38405a' }}>{post.published_at ? timeAgo(post.published_at) : ''}</span>
              </div>
              <div style={{ fontSize: 11, color: '#e2e6f0', lineHeight: 1.45, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const }}>
                {post.title || post.excerpt || 'Market analysis'}
              </div>
              {post.tickers && post.tickers.length > 0 && (
                <div style={{ display: 'flex', gap: 3, marginTop: 4 }}>
                  {post.tickers.slice(0, 3).map(t => (
                    <span key={t} style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, padding: '1px 5px', borderRadius: 2, background: '#0c0e12', border: '1px solid #1a2030', color: '#38405a' }}>{t}</span>
                  ))}
                </div>
              )}
            </Link>
          );
        }) : (
          <div style={{ padding: '16px 14px', fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>No content yet…</div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Watchlist + Alerts (bottom COL 1, tabbed)
// ─────────────────────────────────────────────────────────────────────────────
function WatchlistAlerts({ btcPrice, ethPrice, solPrice, xmrPrice, aavePrice, solChange, xmrChange, regime, setups }: {
  btcPrice: number | null; ethPrice: number | null;
  solPrice: number | null; xmrPrice: number | null; aavePrice: number | null;
  solChange: number | null; xmrChange: number | null;
  regime: MarketRegime | null; setups: TradeSetup[];
}) {
  const [tab, setTab] = useState<'wl' | 'al'>('wl');
  const btc  = btcPrice  || 67468;
  const eth  = ethPrice  || 2033;
  const sol  = solPrice  || 87.4;
  const xmr  = xmrPrice  || 347.8;
  const aave = aavePrice || 116.2;

  const fmtChg = (c: number | null, fallback: string) =>
    c != null ? `${c >= 0 ? '+' : ''}${c.toFixed(2)}%` : fallback;

  // Sparkline points: trending up or down based on real 24h change
  const upPts  = '0,15 6,12 12,13 20,8 28,6 35,3 42,1';
  const dnPts  = '0,3 6,5 12,4 20,7 28,10 35,13 42,15';
  const solUp  = (solChange ?? 1) >= 0;
  const xmrUp  = (xmrChange ?? 1) >= 0;

  const WATCH = [
    { sym: 'BTC',  bg: ASSET_BG.BTC,  price: fmtPrice(btc),   pts: upPts, up: true,   chg: '+4.57%'               },
    { sym: 'ETH',  bg: ASSET_BG.ETH,  price: fmtPrice(eth),   pts: upPts, up: true,   chg: '+7.17%'               },
    { sym: 'SOL',  bg: ASSET_BG.SOL,  price: fmtPrice(sol),   pts: solUp ? upPts : dnPts, up: solUp, chg: fmtChg(solChange, '+9.41%') },
    { sym: 'AAVE', bg: ASSET_BG.AAVE, price: fmtPrice(aave),  pts: upPts, up: true,   chg: '+8.89%'               },
    { sym: 'XMR',  bg: ASSET_BG.XMR,  price: fmtPrice(xmr),   pts: xmrUp ? upPts : dnPts, up: xmrUp, chg: fmtChg(xmrChange, '+1.92%') },
  ];

  const ALERTS = [
    { active: true,  title: 'ETH · Price Alert',      sub: 'Above $2,000 · Triggered 12m ago',                            badge: 'Triggered', bCol: '#00e5a0', bBg: 'rgba(0,229,160,.08)',   bBrd: 'rgba(0,229,160,.2)'   },
    { active: false, title: 'BTC · Resistance Break',  sub: 'Above $70,000 · Watching',                                    badge: 'Watching',  bCol: '#f0a030', bBg: 'rgba(240,160,48,.08)', bBrd: 'rgba(240,160,48,.2)' },
    { active: false, title: 'Regime Change',            sub: `Any shift · ${regime?.regime_name?.replace(/_/g, ' ') || 'Unknown'}`, badge: 'Active', bCol: '#f0a030', bBg: 'rgba(240,160,48,.08)', bBrd: 'rgba(240,160,48,.2)' },
    ...(setups[0] ? [{ active: true, title: `${setups[0].asset} Setup Alert`, sub: `${setups[0].direction} · ${setups[0].entry_zones?.[0]?.price ? fmtPrice(setups[0].entry_zones[0].price) : 'at market'}`, badge: 'New', bCol: '#ff3d5a', bBg: 'rgba(255,61,90,.08)', bBrd: 'rgba(255,61,90,.2)' }] : []),
  ];

  const tabStyle = (active: boolean): React.CSSProperties => ({
    flex: 1, padding: '9px 14px',
    fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase',
    color: active ? '#e2e6f0' : '#38405a', background: 'none', border: 'none',
    borderBottom: `2px solid ${active ? '#00e5a0' : 'transparent'}`,
    cursor: 'pointer', transition: 'all 0.15s', marginBottom: -1,
  });

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: 0, borderBottom: '1px solid #1a2030', display: 'flex' }}>
        <button onClick={() => setTab('wl')} style={tabStyle(tab === 'wl')}>Watchlist</button>
        <button onClick={() => setTab('al')} style={{ ...tabStyle(tab === 'al'), display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          Alerts
          <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, background: 'rgba(255,61,90,0.08)', color: '#ff3d5a', border: '1px solid rgba(255,61,90,0.2)', padding: '1px 5px', borderRadius: 2 }}>2</span>
        </button>
      </div>

      {tab === 'wl' ? (
        <div>
          {WATCH.map((w, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 13px', borderBottom: '1px solid #1a2030', cursor: 'pointer', transition: 'background 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ width: 22, height: 22, borderRadius: 4, background: w.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 7, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
                {w.sym.slice(0, 3)}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0' }}>{w.sym}</div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, color: '#788098', marginTop: 1 }}>{w.price}</div>
              </div>
              <svg width="42" height="18" viewBox="0 0 42 18" style={{ flexShrink: 0 }}>
                <polyline points={w.pts} fill="none" stroke={w.up ? '#00e5a0' : '#ff3d5a'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, fontWeight: 500, color: w.up ? '#00e5a0' : '#ff3d5a', minWidth: 46, textAlign: 'right', flexShrink: 0 }}>{w.chg}</div>
            </div>
          ))}
        </div>
      ) : (
        <div>
          {ALERTS.map((a, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '7px 13px', borderBottom: '1px solid #1a2030', cursor: 'pointer', transition: 'background 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#151a26')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: a.active ? '#00e5a0' : '#38405a', flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: '#e2e6f0' }}>{a.title}</div>
                <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a', marginTop: 1 }}>{a.sub}</div>
              </div>
              <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.5px', textTransform: 'uppercase', padding: '2px 5px', borderRadius: 2, color: a.bCol, background: a.bBg, border: `1px solid ${a.bBrd}`, flexShrink: 0 }}>{a.badge}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Quick Risk (bottom COL 2)
// ─────────────────────────────────────────────────────────────────────────────
function QuickRisk({ btcPrice }: { btcPrice: number | null }) {
  const base = Math.round(btcPrice || 67468);
  const [acct, setAcct]   = useState('10000');
  const [risk, setRisk]   = useState('1');
  const [entry, setEntry] = useState(String(base));
  const [sl, setSl]       = useState(String(Math.round(base * 0.963)));

  const maxRisk = parseFloat(acct) * parseFloat(risk) / 100 || 0;
  const diff    = Math.abs(parseFloat(entry) - parseFloat(sl)) || 1;
  const pos     = maxRisk / diff;

  const fmtR = (v: number) => isFinite(v) ? `$${v.toFixed(0)}` : '--';
  const fmtP = (v: number) => isFinite(v) ? (v < 1 ? `${v.toFixed(4)} units` : `${v.toFixed(2)} units`) : '--';

  const wrapStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 3 };
  const inpStyle:  React.CSSProperties = { background: 'none', border: 'none', outline: 'none', fontFamily: 'var(--font-dm-mono)', fontSize: 10.5, fontWeight: 500, color: '#e2e6f0', padding: '5px 5px 5px 0', width: '100%' };
  const pfxStyle:  React.CSSProperties = { fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', padding: '0 4px 0 7px' };

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '11px 14px', borderBottom: '1px solid #1a2030', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Quick Risk</span>
        <Link href="/tools/risk-calculator" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', textTransform: 'uppercase', letterSpacing: '0.8px' }}>Full calc →</Link>
      </div>
      <div style={{ padding: '11px 13px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 9 }}>
          {[
            { label: 'Account', pfx: '$', val: acct, set: setAcct, sfx: '' },
            { label: 'Risk %',  pfx: '',  val: risk,  set: setRisk,  sfx: '%', step: '0.1' },
            { label: 'Entry',   pfx: '$', val: entry, set: setEntry, sfx: '' },
            { label: 'Stop Loss', pfx: '$', val: sl,  set: setSl,   sfx: '' },
          ].map(f => (
            <div key={f.label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a' }}>{f.label}</div>
              <div style={wrapStyle}>
                {f.pfx && <span style={pfxStyle}>{f.pfx}</span>}
                <input type="number" value={f.val} step={f.step} onChange={e => f.set(e.target.value)} style={{ ...inpStyle, paddingLeft: f.pfx ? 0 : 8 }} />
                {f.sfx && <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, color: '#38405a', paddingRight: 6 }}>{f.sfx}</span>}
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 3, padding: '8px 10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 2 }}>Max Risk</div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 17, lineHeight: 1, color: '#ff3d5a' }}>{fmtR(maxRisk)}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 2 }}>Position Size</div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 17, lineHeight: 1, color: '#e2e6f0' }}>{fmtP(pos)}</div>
          </div>
        </div>

        <Link href="/tools/risk-calculator" style={{ display: 'block', padding: 7, fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#070809', background: '#00e5a0', borderRadius: 3, textAlign: 'center', textDecoration: 'none', fontWeight: 500 }}>
          Open Full Calculator →
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Exchange Portfolio Widget
// ─────────────────────────────────────────────────────────────────────────────
const EXCHANGE_ICON:  Record<string, string> = { binance: 'B', bybit: 'Y', okx: 'O' };
const EXCHANGE_COLOR: Record<string, string> = { binance: '#f3ba2f', bybit: '#f0a030', okx: '#3d7fff' };

function ExchangePortfolioWidget() {
  const [summaries, setSummaries] = useState<PortfolioSummary[] | null>(null);
  const [syncing, setSyncing]     = useState(false);
  const [error, setError]         = useState('');

  const doSync = useCallback(async () => {
    setSyncing(true); setError('');
    try { setSummaries(await syncPortfolio()); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : 'Sync failed'); }
    finally { setSyncing(false); }
  }, []);

  const totalUSD = summaries?.reduce((acc, s) => acc + s.total_usd, 0) ?? 0;

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>Exchange Portfolio</div>
          {summaries && totalUSD > 0 && (
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 28, color: '#e2e6f0', lineHeight: 1 }}>
              ${totalUSD.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', marginLeft: 6, fontWeight: 300 }}>USD</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link href="/account" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none', letterSpacing: '0.5px' }}>Manage keys →</Link>
          <button onClick={doSync} disabled={syncing} style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', background: '#151a26', border: '1px solid #1a2030', borderRadius: 4, color: '#788098', padding: '5px 12px', cursor: 'pointer', opacity: syncing ? 0.5 : 1 }}>
            {syncing ? 'Syncing…' : '↻ Sync'}
          </button>
        </div>
      </div>
      {error && <div style={{ fontSize: 11, color: '#ff3d5a', marginBottom: 10 }}>{error}</div>}
      {summaries === null ? (
        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
          Connect your exchange to see live balances.{' '}
          <Link href="/account" style={{ color: '#00e5a0', textDecoration: 'none' }}>Add API keys →</Link>
        </div>
      ) : summaries.length === 0 ? (
        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
          No exchanges connected.{' '}
          <Link href="/account" style={{ color: '#00e5a0', textDecoration: 'none' }}>Connect Exchange →</Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {summaries.map(s => (
            <div key={s.key_id}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 20, height: 20, borderRadius: 4, background: '#1a2030', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 8, fontWeight: 700, color: EXCHANGE_COLOR[s.exchange] || '#788098' }}>
                  {EXCHANGE_ICON[s.exchange] || s.exchange[0].toUpperCase()}
                </div>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: '#e2e6f0', textTransform: 'capitalize' }}>{s.exchange}</span>
                {s.label && <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>— {s.label}</span>}
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-dm-mono)', fontSize: 10, fontWeight: 500, color: '#e2e6f0' }}>${s.total_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
              {s.error ? (
                <div style={{ fontSize: 10, color: '#ff3d5a', paddingLeft: 28 }}>{s.error}</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5, paddingLeft: 28 }}>
                  {s.holdings.slice(0, 6).map(h => (
                    <div key={h.asset} style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 4, padding: '6px 8px' }}>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, fontWeight: 700, color: '#e2e6f0' }}>{h.asset}</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#38405a' }}>{h.total < 0.01 ? h.total.toFixed(6) : h.total.toFixed(4)}</div>
                      <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#788098', marginTop: 2 }}>${h.usd_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Free Dashboard
// ─────────────────────────────────────────────────────────────────────────────
function FreeDashboard({ fearGreed, fearGreedLabel, recentContent, btcPrice, ethPrice, marketCap }: {
  fearGreed: number | null; fearGreedLabel: string | null;
  recentContent: ContentPost[]; btcPrice: number | null; ethPrice: number | null; marketCap: number | null;
}) {
  return (
    <>
      {/* Upgrade banner */}
      <div style={{ background: 'rgba(240,160,48,0.07)', border: '1px solid rgba(240,160,48,0.2)', borderRadius: 8, padding: '16px 20px', marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 18, color: '#f0a030', marginBottom: 3, letterSpacing: '1px' }}>Unlock your full trading cockpit</div>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', letterSpacing: '0.3px' }}>Regime detection · Trade setups · Risk calculator · Portfolio tracking · Whale intel</div>
        </div>
        <Link href="/waitlist" style={{ flexShrink: 0, marginLeft: 20, fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#f0a030', padding: '7px 16px', borderRadius: 3, fontWeight: 500, textDecoration: 'none' }}>
          Join Waitlist →
        </Link>
      </div>

      {/* Market snapshot */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 16 }}>
        {[
          { label: 'BTC Price',  value: fmtPrice(btcPrice) },
          { label: 'ETH Price',  value: fmtPrice(ethPrice) },
          { label: 'Market Cap', value: fmtLarge(marketCap) },
          { label: 'Fear & Greed', value: fearGreed != null ? String(fearGreed) : '--', sub: fearGreedLabel || '', color: fearGreed != null && fearGreed <= 25 ? '#ff3d5a' : fearGreed != null && fearGreed >= 75 ? '#00e5a0' : '#e2e6f0' },
        ].map(item => (
          <div key={item.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px' }}>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: (item as { color?: string }).color || '#e2e6f0', marginBottom: 2 }}>{item.value}</div>
            {(item as { sub?: string }).sub && <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>{(item as { sub: string }).sub}</div>}
          </div>
        ))}
      </div>

      {/* Locked previews */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <TierLock title="Market Regime · Confidence · Intelligence">
          <div style={{ background: '#10141c', padding: 20, borderRadius: 8 }}>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 32, color: '#00e5a0' }}>ACCUMULATION</div>
            <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098', marginTop: 4 }}>80% confidence · 4 confirming factors</div>
            <div style={{ height: 3, borderRadius: 2, background: '#1a2030', marginTop: 12 }}>
              <div style={{ height: 3, borderRadius: 2, width: '80%', background: '#00e5a0' }} />
            </div>
          </div>
        </TierLock>
        <TierLock title="Trade Setups · Entry · TP · SL · R/R">
          <div style={{ background: '#10141c', padding: 20, borderRadius: 8 }}>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 18, color: '#e2e6f0', marginBottom: 8 }}>BTC LONG · 2.8R</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              {[['Entry', '$66,800', '#e2e6f0'], ['TP', '$72,500', '#00e5a0'], ['SL', '$64,200', '#ff3d5a']].map(([l, v, c]) => (
                <div key={l}>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#38405a', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{l}</div>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 11, fontWeight: 500, color: c as string }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </TierLock>
      </div>

      {/* F&G gauge (visible for free) */}
      <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 12, marginBottom: 16 }}>
        <FGGauge value={fearGreed} label={fearGreedLabel} />
        <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px' }}>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', marginBottom: 8 }}>What you get with Basic+</div>
          {['Full market regime detection with confidence scores', 'AI-generated trade setups with entry · TP · SL · R/R', 'Live price chart with candlestick view', 'Whale activity tracker (real-time flows)', 'Risk calculator: size positions automatically', 'Trade journal: track P&L, win rate, drawdown'].map(feat => (
            <div key={feat} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
              <span style={{ color: '#00e5a0', flexShrink: 0, marginTop: 1 }}>✓</span>
              <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, color: '#788098' }}>{feat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Cockpit feed */}
      <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Cockpit Feed</span>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5a0', display: 'inline-block' }} />
          </div>
          <Link href="/analysis" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>View all →</Link>
        </div>
        {recentContent.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: 10 }}>
            {recentContent.map(post => (
              <Link key={post.id} href={`/post/${post.slug}`} style={{ textDecoration: 'none' }}>
                <div style={{ background: '#0c0e12', border: '1px solid #1a2030', borderRadius: 6, padding: '12px 14px', cursor: 'pointer' }}>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 6 }}>
                    {post.content_type} · {post.published_at ? timeAgo(post.published_at) : ''}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: '#e2e6f0', lineHeight: 1.4, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const }}>
                    {post.title || post.excerpt || 'Analysis'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>No content yet — engine is generating…</div>
        )}
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Dashboard
// ─────────────────────────────────────────────────────────────────────────────
export default function DashboardClient({
  regime, setups, recentContent,
  btcPrice, ethPrice, solPrice, xmrPrice, bnbPrice: _bnbPrice, aavePrice, solChange, xmrChange,
  marketCap, fearGreed, fearGreedLabel,
}: DashboardClientProps) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats]           = useState<PortfolioStats | null>(null);
  const [openTrades, setOpenTrades]  = useState<JournalEntry[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  // Live-refreshing server data (regime, setups, feed) — initialised from SSR props
  const [liveRegime,  setLiveRegime]  = useState<MarketRegime | null>(regime);
  const [liveSetups,  setLiveSetups]  = useState<TradeSetup[]>(setups);
  const [liveContent, setLiveContent] = useState<ContentPost[]>(recentContent);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace('/auth/login');
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      Promise.all([
        getPortfolioStats().catch(() => null),
        getJournalEntries('open').catch(() => []),
      ]).then(([s, trades]) => {
        setStats(s); setOpenTrades(trades);
      }).finally(() => setStatsLoading(false));
    }
  }, [user]);

  // Poll regime + setups + feed every 60 s
  useEffect(() => {
    const refresh = async () => {
      const [r, s, c] = await Promise.allSettled([
        getCurrentRegime(),
        getLatestTradeSetups(undefined, 5),
        getContentFeed({ page_size: 8 }),
      ]);
      if (r.status === 'fulfilled') setLiveRegime(r.value);
      if (s.status === 'fulfilled') setLiveSetups(s.value);
      if (c.status === 'fulfilled') setLiveContent(c.value.items);
      setLastRefresh(new Date());
    };
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, []);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#070809', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 11, color: '#38405a', letterSpacing: '1px' }}>LOADING COCKPIT…</div>
      </div>
    );
  }
  if (!user) return null;

  const tierLevel  = TIER_LEVEL[user.tier] ?? 0;
  const isFree     = tierLevel === 0;
  const isBasicPlus = tierLevel >= 1;
  const isPremium  = tierLevel >= 2;

  const totalPnl = stats?.total_pnl_usd ?? 0;
  const openRisk = openTrades.reduce((acc, t) => {
    if (t.stop_loss_price && t.entry_price && t.quantity)
      return acc + Math.abs(t.entry_price - t.stop_loss_price) * t.quantity;
    return acc;
  }, 0);

  return (
    <CockpitShell>
      {/* ── Responsive grid CSS ── */}
      <style>{`
        .dash-metrics { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:12px; }
        .dash-main    { display:grid; grid-template-columns:1fr 1.1fr 280px; grid-template-rows:auto auto; gap:12px; margin-bottom:12px; align-items:start; }
        .dash-bottom  { display:grid; grid-template-columns:1fr 1.1fr 280px; gap:12px; margin-bottom:12px; }
        .dash-port    { display:grid; grid-template-columns:1fr 1.1fr; gap:12px; }
        .dash-row-span { grid-row:1/3; }
        @media (max-width:1100px) {
          .dash-metrics { grid-template-columns:repeat(3,1fr); }
          .dash-main    { grid-template-columns:1fr 1fr; grid-template-rows:auto auto auto; }
          .dash-bottom  { grid-template-columns:1fr 1fr; }
          .dash-port    { grid-template-columns:1fr; }
          .dash-row-span { grid-row:auto; }
        }
        @media (max-width:680px) {
          .dash-metrics { grid-template-columns:repeat(2,1fr); }
          .dash-main    { grid-template-columns:1fr; }
          .dash-bottom  { grid-template-columns:1fr; }
          .dash-port    { grid-template-columns:1fr; }
        }
      `}</style>

      <div style={{ padding: '14px 16px' }}>

        {isFree ? (
          <FreeDashboard fearGreed={fearGreed} fearGreedLabel={fearGreedLabel} recentContent={liveContent} btcPrice={btcPrice} ethPrice={ethPrice} marketCap={marketCap} />

        ) : (
          <>
            {/* ── Regime Hero ── */}
            <RegimeHero regime={liveRegime} fearGreed={fearGreed} fearGreedLabel={fearGreedLabel} />

            {/* ── 5-Metric Row ── */}
            <div className="dash-metrics">
              {[
                { label: 'Portfolio P&L',    value: statsLoading ? '--' : stats ? `${totalPnl >= 0 ? '+' : ''}$${Math.abs(totalPnl).toFixed(0)}` : '--', sub: stats ? `${stats.total_trades} trades` : 'Log trades to start', color: totalPnl >= 0 ? '#00e5a0' : '#ff3d5a' },
                { label: 'Open Positions',   value: statsLoading ? '--' : String(openTrades.length), sub: openTrades.length > 0 ? `↑ ${openTrades.length} active` : 'No open trades', color: openTrades.length > 0 ? '#00e5a0' : '#38405a' },
                { label: 'Open Risk',        value: statsLoading ? '--' : openRisk > 0 ? `$${openRisk.toFixed(0)}` : '$0', sub: openRisk > 0 ? 'at risk in open trades' : 'No risk exposure', color: openRisk > 0 ? '#f0a030' : '#38405a' },
                { label: 'Win Rate',         value: statsLoading ? '--' : stats ? `${(stats.win_rate * 100).toFixed(0)}%` : '--', sub: stats ? `P.F. ${stats.profit_factor.toFixed(2)}` : 'Log trades to track', color: stats ? (stats.win_rate >= 0.5 ? '#00e5a0' : '#ff3d5a') : '#e2e6f0' },
                { label: 'Signals Today',    value: String(liveSetups.length), sub: liveSetups.length > 0 ? `↑ ${liveSetups.filter(s => s.direction === 'LONG').length}L · ${liveSetups.filter(s => s.direction === 'SHORT').length}S` : 'No setups yet', color: liveSetups.length > 0 ? '#00e5a0' : '#38405a' },
              ].map(m => (
                <div key={m.label} style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 6, padding: '11px 13px', transition: 'border-color 0.2s' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = '#222c42')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = '#1a2030')}>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{m.label}</div>
                  <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 21, lineHeight: 1, color: m.color, marginBottom: 2 }}>{m.value}</div>
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a' }}>{m.sub}</div>
                </div>
              ))}
            </div>

            {/* ── Main 3-col Grid ── */}
            <div className="dash-main">

              {/* COL 1: Live Signals (full height on desktop) */}
              <LiveSignals regime={liveRegime} setups={liveSetups} content={liveContent} />

              {/* COL 2 ROW 1: Active Setups */}
              <ActiveSetups setups={liveSetups} isPremium={isPremium} />

              {/* COL 3 ROW 1: Whale Activity */}
              <WhaleActivity isBasicPlus={isBasicPlus} />

              {/* COL 2 ROW 2: Price Chart */}
              <PriceChart btcPrice={btcPrice} ethPrice={ethPrice} solPrice={solPrice} xmrPrice={xmrPrice} setups={liveSetups} regime={liveRegime} />

              {/* COL 3 ROW 2: Cockpit Feed */}
              <CockpitFeedPanel content={liveContent} />
            </div>

            {/* ── Bottom Row ── */}
            <div className="dash-bottom">
              <WatchlistAlerts btcPrice={btcPrice} ethPrice={ethPrice} solPrice={solPrice} xmrPrice={xmrPrice} aavePrice={aavePrice} solChange={solChange} xmrChange={xmrChange} regime={liveRegime} setups={liveSetups} />
              <QuickRisk btcPrice={btcPrice} />
              <div />
            </div>

            {/* ── Portfolio + Exchange ── */}
            <div className="dash-port">

              {/* Trade Statistics */}
              <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, padding: '16px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#788098' }}>Trade Statistics</span>
                  <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', textDecoration: 'none' }}>Open Journal →</Link>
                </div>
                {statsLoading ? (
                  <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>Loading stats…</div>
                ) : stats && stats.total_trades > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
                    {[
                      { l: 'Total P&L',     v: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(0)}`,   c: totalPnl >= 0 ? '#00e5a0' : '#ff3d5a' },
                      { l: 'Win Rate',      v: `${(stats.win_rate * 100).toFixed(0)}%`,                 c: stats.win_rate >= 0.5 ? '#00e5a0' : '#ff3d5a' },
                      { l: 'Profit Factor', v: stats.profit_factor.toFixed(2),                          c: stats.profit_factor >= 1.5 ? '#00e5a0' : stats.profit_factor >= 1 ? '#f0a030' : '#ff3d5a' },
                      { l: 'Trades',        v: String(stats.total_trades),                              c: '#e2e6f0' },
                    ].map(item => (
                      <div key={item.l}>
                        <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 4 }}>{item.l}</div>
                        <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 20, lineHeight: 1, color: item.c }}>{item.v}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '12px 0' }}>
                    <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', marginBottom: 10 }}>No trades logged yet</div>
                    <Link href="/journal" style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#08090c', background: '#00e5a0', padding: '6px 14px', borderRadius: 3, textDecoration: 'none' }}>
                      Log Your First Trade →
                    </Link>
                  </div>
                )}
              </div>

              <ExchangePortfolioWidget />
            </div>

            {/* ── Last refresh indicator ── */}
            {lastRefresh && (
              <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
                <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#252d40', letterSpacing: '0.5px' }}>
                  ↺ live · updated {timeAgo(lastRefresh.toISOString())}
                </span>
              </div>
            )}
          </>
        )}

      </div>
    </CockpitShell>
  );
}
