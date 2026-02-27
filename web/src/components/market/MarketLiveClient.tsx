'use client';

import type { MarketSnapshot } from '@/types';
import { formatPrice, formatLargeNumber } from '@/lib/api';
import { useMarketPrices } from '@/context/MarketPricesContext';

/* ── Static config ──────────────────────────────────────────────── */

const avatarGrads: Record<string, string> = {
  BTC:  'linear-gradient(135deg,#f7931a,#e87d16)',
  ETH:  'linear-gradient(135deg,#627eea,#4f67c8)',
  XRP:  'linear-gradient(135deg,#346aa9,#1e4a80)',
  SOL:  'linear-gradient(135deg,#9945ff,#14f195)',
  BNB:  'linear-gradient(135deg,#f3ba2f,#d4a228)',
  AVAX: 'linear-gradient(135deg,#e84142,#b52e2f)',
  SUI:  'linear-gradient(135deg,#4da2ff,#2578d8)',
  LINK: 'linear-gradient(135deg,#2a5ada,#1a3aaa)',
  DOGE: 'linear-gradient(135deg,#c2a633,#a08a29)',
  SHIB: 'linear-gradient(135deg,#e8542a,#c43e1e)',
  PEPE: 'linear-gradient(135deg,#4caf50,#2e7d32)',
  FLOKI:'linear-gradient(135deg,#ff9800,#e65100)',
  XMR:  'linear-gradient(135deg,#f26822,#c85416)',
  ZEC:  'linear-gradient(135deg,#ecb244,#c4912e)',
  DASH: 'linear-gradient(135deg,#008de4,#006bb5)',
  SCRT: 'linear-gradient(135deg,#312154,#1e1e2e)',
  AAVE: 'linear-gradient(135deg,#b6509e,#8b3d7a)',
  UNI:  'linear-gradient(135deg,#ff007a,#c8005e)',
  CRV:  'linear-gradient(135deg,#3a82b5,#2a6288)',
  LDO:  'linear-gradient(135deg,#77d1f3,#45a8c8)',
  XAU:  'linear-gradient(135deg,#ffd700,#b8960a)',
  TSLA: 'linear-gradient(135deg,#cc0000,#990000)',
};

const coinFullNames: Record<string, string> = {
  BTC:  'Bitcoin',   ETH:  'Ethereum',  XRP:  'Ripple',    SOL:  'Solana',
  BNB:  'BNB Chain', AVAX: 'Avalanche', SUI:  'Sui',        LINK: 'Chainlink',
  DOGE: 'Dogecoin',  SHIB: 'Shiba Inu', PEPE: 'Pepe',       FLOKI:'Floki',
  XMR:  'Monero',    ZEC:  'Zcash',     DASH: 'Dash',        SCRT: 'Secret',
  AAVE: 'Aave',      UNI:  'Uniswap',   CRV:  'Curve',       LDO:  'Lido',
  XAU:  'Gold',      TSLA: 'Tesla',
};

// White text on dark avatars, dark text on bright avatars
const lightTextTickers = new Set(['ETH','SOL','XRP','AVAX','SUI','LINK','XMR','ZEC','DASH','SCRT','AAVE','UNI','CRV','LDO','TSLA']);

const sectors: Array<{ title: string; tickers: string[] }> = [
  { title: 'Majors',       tickers: ['BTC','ETH','XRP','SOL'] },
  { title: 'Altcoins',     tickers: ['BNB','AVAX','SUI','LINK'] },
  { title: 'DeFi',         tickers: ['AAVE','UNI','CRV','LDO'] },
  { title: 'Privacy',      tickers: ['XMR','ZEC','DASH','SCRT'] },
  { title: 'Memecoins',    tickers: ['DOGE','SHIB','PEPE','FLOKI'] },
  { title: 'Commodities',  tickers: ['XAU','TSLA'] },
];

/* ── Sparkline ──────────────────────────────────────────────────── */

function sparklinePath(change: number): string {
  return change >= 0
    ? '0,24 20,22 40,20 60,18 80,14 100,10 120,8 140,6'
    : '0,8 20,10 40,12 60,14 80,18 100,22 120,24 140,26';
}

/* ── Props ──────────────────────────────────────────────────────── */

interface Props {
  snapshot: MarketSnapshot | null;
}

/* ── Component ──────────────────────────────────────────────────── */

export default function MarketLiveClient({ snapshot }: Props) {
  // All prices from the shared app-wide WebSocket — same source as LiveMarketBar
  const { ticks, wsStatus } = useMarketPrices();

  /* Derived stat card values */
  const btcPrice = ticks['BTC']?.price ?? snapshot?.btc_price ?? null;
  const ethPrice = ticks['ETH']?.price ?? snapshot?.eth_price ?? null;

  const fgIndex = snapshot?.fear_greed_index;
  const fgLabel = snapshot?.fear_greed_label ?? 'N/A';
  const fgColor =
    fgIndex == null ? '#3d4562' :
    fgIndex < 25    ? '#f03e5a' :
    fgIndex < 45    ? '#f0a030' :
    fgIndex < 55    ? '#7a839e' :
    fgIndex < 75    ? '#4a8cf0' :
    '#00d68f';

  const statCards = [
    { label: 'BTC Price',  value: formatPrice(btcPrice) },
    { label: 'ETH Price',  value: formatPrice(ethPrice) },
    { label: 'Market Cap', value: formatLargeNumber(snapshot?.total_market_cap) },
    { label: '24h Volume', value: formatLargeNumber(snapshot?.total_volume_24h) },
    { label: 'BTC Dom.',   value: snapshot?.btc_dominance ? `${snapshot.btc_dominance.toFixed(1)}%` : '--' },
  ];

  const wsDotColor =
    wsStatus === 'live'       ? '#00d68f' :
    wsStatus === 'connecting' ? '#f0a030' : '#f03e5a';

  const wsLabel =
    wsStatus === 'live'       ? 'WebSocket · Live' :
    wsStatus === 'connecting' ? 'Connecting…' :
    'Offline · Retrying';

  return (
    <>
      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-3">
        {statCards.map((s) => (
          <div
            key={s.label}
            style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '14px 16px' }}
          >
            <div className="font-mono-cc text-[9px] tracking-[1px] uppercase" style={{ color: '#3d4562', marginBottom: 8 }}>
              {s.label}
            </div>
            <div className="font-syne text-[18px] font-bold" style={{ color: '#dfe3f0', lineHeight: 1 }}>
              {s.value}
            </div>
          </div>
        ))}

        {/* Fear & Greed */}
        <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 6, padding: '14px 16px' }}>
          <div className="font-mono-cc text-[9px] tracking-[1px] uppercase" style={{ color: '#3d4562', marginBottom: 8 }}>
            Fear &amp; Greed
          </div>
          <div className="font-syne text-[18px] font-bold" style={{ color: fgColor, lineHeight: 1 }}>
            {fgIndex ?? '--'}
          </div>
          <div className="font-mono-cc text-[10px] mt-1" style={{ color: fgColor }}>
            {fgLabel}
          </div>
        </div>
      </div>

      {/* WS status badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 28 }}>
        <span
          style={{
            width: 5, height: 5, borderRadius: '50%',
            background: wsDotColor,
            display: 'inline-block',
            animation: wsStatus === 'live' ? 'livePulse 2s ease-in-out infinite' : 'none',
          }}
        />
        <span
          className="font-mono-cc"
          style={{ fontSize: 9, color: '#3d4562', letterSpacing: '0.5px', textTransform: 'uppercase' }}
        >
          {wsLabel}
        </span>
      </div>

      {/* ── Sector Coin Rails ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        {sectors.map((sector) => {
          const sectorTicks = sector.tickers
            .map((t) => ({ ticker: t, tick: ticks[t] }))
            .filter((x): x is { ticker: string; tick: { price: number; change: number } } => x.tick != null);

          if (sectorTicks.length === 0) return null;

          const changes = sectorTicks.map(({ tick }) => tick.change);
          const avg = changes.reduce((s, c) => s + c, 0) / changes.length;
          const avgUp = avg >= 0;

          return (
            <div key={sector.title}>
              {/* Sector header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span className="font-syne" style={{ fontSize: 14, fontWeight: 700, color: '#dfe3f0' }}>
                  {sector.title}
                </span>
                <span className="font-mono-cc" style={{ fontSize: 10, color: avgUp ? '#00d68f' : '#f03e5a' }}>
                  {avgUp ? '+' : ''}{avg.toFixed(1)}% avg
                </span>
              </div>

              {/* Coin rail */}
              <div className="coin-rail">
                {sectorTicks.map(({ ticker, tick }) => {
                  const isUp = tick.change >= 0;
                  const changeStr = `${isUp ? '+' : ''}${tick.change.toFixed(2)}%`;
                  const grad = avatarGrads[ticker] ?? 'linear-gradient(135deg,#161b28,#242c42)';
                  const avatarTextColor = lightTextTickers.has(ticker) ? '#f0f2ff' : '#08090c';

                  return (
                    <div
                      key={ticker}
                      style={{
                        width: 160, flexShrink: 0,
                        background: '#111520', border: '1px solid #1c2235', borderRadius: 6,
                        padding: '14px 14px 12px', display: 'flex', flexDirection: 'column', gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{
                          width: 32, height: 32, borderRadius: 8, background: grad, flexShrink: 0,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 500, color: avatarTextColor,
                        }}>
                          {ticker.length <= 3 ? ticker : ticker.slice(0, 3)}
                        </div>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.5px',
                          padding: '2px 6px', borderRadius: 3,
                          background: isUp ? 'rgba(0,214,143,0.1)' : 'rgba(240,62,90,0.1)',
                          color: isUp ? '#00d68f' : '#f03e5a',
                        }}>
                          {changeStr}
                        </span>
                      </div>

                      <div>
                        <div style={{ fontFamily: 'var(--font-syne)', fontSize: 13, fontWeight: 600, color: '#dfe3f0' }}>
                          {ticker}
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#3d4562' }}>
                          {coinFullNames[ticker] ?? ticker}
                        </div>
                      </div>

                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 500, color: '#dfe3f0' }}>
                        {formatPrice(tick.price)}
                      </div>

                      <svg width="100%" height="32" viewBox="0 0 140 32" preserveAspectRatio="none">
                        <polyline
                          points={sparklinePath(tick.change)}
                          fill="none"
                          stroke={isUp ? '#00d68f' : '#f03e5a'}
                          strokeWidth="1.5"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
