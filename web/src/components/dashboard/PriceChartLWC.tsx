'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CandlestickSeries, LineStyle } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, UTCTimestamp } from 'lightweight-charts';
import { getKlines } from '@/lib/api';
import type { KlineBar } from '@/lib/api';
import type { TradeSetup, MarketRegime } from '@/types';

// ── Asset catalog — all Binance USDT pairs we can chart ──────────────────────

interface AssetMeta {
  ticker: string;
  name: string;
  pair: string;            // Binance USDT pair
  gradient: string;
  category: 'Major' | 'DeFi' | 'Privacy' | 'Meme' | 'Other';
}

const ASSET_CATALOG: AssetMeta[] = [
  { ticker: 'BTC',   name: 'Bitcoin',      pair: 'BTCUSDT',   gradient: 'linear-gradient(135deg,#f7931a,#e8720c)', category: 'Major'   },
  { ticker: 'ETH',   name: 'Ethereum',     pair: 'ETHUSDT',   gradient: 'linear-gradient(135deg,#627eea,#3b5ede)', category: 'Major'   },
  { ticker: 'BNB',   name: 'BNB',          pair: 'BNBUSDT',   gradient: 'linear-gradient(135deg,#f3ba2f,#d09c20)', category: 'Major'   },
  { ticker: 'SOL',   name: 'Solana',       pair: 'SOLUSDT',   gradient: 'linear-gradient(135deg,#9945ff,#14f195)', category: 'Major'   },
  { ticker: 'AAVE',  name: 'Aave',         pair: 'AAVEUSDT',  gradient: 'linear-gradient(135deg,#b6509e,#2ebac6)', category: 'DeFi'    },
  { ticker: 'UNI',   name: 'Uniswap',      pair: 'UNIUSDT',   gradient: 'linear-gradient(135deg,#ff007a,#b50059)', category: 'DeFi'    },
  { ticker: 'CRV',   name: 'Curve',        pair: 'CRVUSDT',   gradient: 'linear-gradient(135deg,#40b0a6,#2a7a77)', category: 'DeFi'    },
  { ticker: 'LDO',   name: 'Lido DAO',     pair: 'LDOUSDT',   gradient: 'linear-gradient(135deg,#00a3ff,#0070cc)', category: 'DeFi'    },
  { ticker: 'LINK',  name: 'Chainlink',    pair: 'LINKUSDT',  gradient: 'linear-gradient(135deg,#2a5ada,#1a3ab0)', category: 'DeFi'    },
  { ticker: 'MKR',   name: 'Maker',        pair: 'MKRUSDT',   gradient: 'linear-gradient(135deg,#1aab9b,#0e7a6d)', category: 'DeFi'    },
  { ticker: 'XMR',   name: 'Monero',       pair: 'XMRUSDT',   gradient: 'linear-gradient(135deg,#ff6600,#cc4400)', category: 'Privacy' },
  { ticker: 'ZEC',   name: 'Zcash',        pair: 'ZECUSDT',   gradient: 'linear-gradient(135deg,#f4b728,#c8911a)', category: 'Privacy' },
  { ticker: 'DASH',  name: 'Dash',         pair: 'DASHUSDT',  gradient: 'linear-gradient(135deg,#008de4,#0066aa)', category: 'Privacy' },
  { ticker: 'DOGE',  name: 'Dogecoin',     pair: 'DOGEUSDT',  gradient: 'linear-gradient(135deg,#c2a633,#9a8228)', category: 'Meme'    },
  { ticker: 'SHIB',  name: 'Shiba Inu',    pair: 'SHIBUSDT',  gradient: 'linear-gradient(135deg,#ff3d00,#cc2200)', category: 'Meme'    },
  { ticker: 'PEPE',  name: 'Pepe',         pair: 'PEPEUSDT',  gradient: 'linear-gradient(135deg,#00aa44,#007722)', category: 'Meme'    },
  { ticker: 'FLOKI', name: 'Floki',        pair: 'FLOKIUSDT', gradient: 'linear-gradient(135deg,#f4b728,#b07c00)', category: 'Meme'    },
  { ticker: 'DOT',   name: 'Polkadot',     pair: 'DOTUSDT',   gradient: 'linear-gradient(135deg,#e6007a,#a00055)', category: 'Other'   },
  { ticker: 'ADA',   name: 'Cardano',      pair: 'ADAUSDT',   gradient: 'linear-gradient(135deg,#0033ad,#002280)', category: 'Other'   },
  { ticker: 'AVAX',  name: 'Avalanche',    pair: 'AVAXUSDT',  gradient: 'linear-gradient(135deg,#e84142,#b02020)', category: 'Other'   },
  { ticker: 'ATOM',  name: 'Cosmos',       pair: 'ATOMUSDT',  gradient: 'linear-gradient(135deg,#2e3148,#6f7390)', category: 'Other'   },
  { ticker: 'SUI',   name: 'Sui',          pair: 'SUIUSDT',   gradient: 'linear-gradient(135deg,#4ca3ff,#1a6dcc)', category: 'Other'   },
];

// ── Timeframes ────────────────────────────────────────────────────────────────

type TF = '1H' | '4H' | '1D' | '1W';
const TF_MAP:   Record<TF, string> = { '1H': '1h', '4H': '4h', '1D': '1d', '1W': '1w' };
const TF_LIMIT: Record<TF, number> = { '1H': 200,  '4H': 200,  '1D': 180,  '1W': 104  };

// ── Regime colours ────────────────────────────────────────────────────────────

const REGIME_COLORS: Record<string, string> = {
  RISK_OFF:             '#ff3d5a',
  DISTRIBUTION:         '#ff6b35',
  RISK_ON:              '#00e5a0',
  ACCUMULATION:         '#00e5a0',
  VOLATILITY_EXPANSION: '#f59e0b',
  NEUTRAL:              '#788098',
};

function fmtPrice(p: number): string {
  if (p >= 10000) return `$${p.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  if (p >= 1000)  return `$${p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (p >= 1)     return `$${p.toFixed(3)}`;
  return `$${p.toFixed(6)}`;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  btcPrice: number | null;
  ethPrice: number | null;
  solPrice: number | null;
  xmrPrice: number | null;
  setups: TradeSetup[];
  regime: MarketRegime | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function PriceChartLWC({ btcPrice, ethPrice, solPrice, xmrPrice, setups, regime }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const seriesRef    = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const plRefs       = useRef<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>[]>([]);
  const roRef        = useRef<ResizeObserver | null>(null);

  const [assetIdx, setAssetIdx] = useState(0);           // index into ASSET_CATALOG
  const [tf, setTf]             = useState<TF>('4H');
  const [bars, setBars]         = useState<KlineBar[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(false);
  const [dropOpen, setDropOpen] = useState(false);
  const [search, setSearch]     = useState('');

  const meta = ASSET_CATALOG[assetIdx];

  // Seed live price for the 4 prop-driven assets
  const livePrices: Record<string, number | null> = {
    BTC: btcPrice, ETH: ethPrice, SOL: solPrice, XMR: xmrPrice,
  };

  // Last close from bar data, or fall back to prop price
  const lastBar   = bars.at(-1);
  const prevBar   = bars.at(-2);
  const livePrice = lastBar?.close ?? livePrices[meta.ticker] ?? null;
  const changePct = lastBar && prevBar
    ? ((lastBar.close / prevBar.close - 1) * 100)
    : null;

  // Active setup for this asset
  const activeSetup = setups.find(s => s.asset.toUpperCase().startsWith(meta.ticker));
  const tp    = activeSetup?.take_profits?.[0]?.price ?? null;
  const entry = activeSetup?.entry_zones?.[0]?.price ?? null;
  const sl    = activeSetup?.stop_loss?.price ?? null;

  const regColor = regime ? (REGIME_COLORS[regime.regime_name] ?? '#00e5a0') : '#00e5a0';
  const isDown   = /RISK_OFF|DISTRIBUTION/.test(regime?.regime_name ?? '');

  // ── Filtered asset list for dropdown ──────────────────────────────────────
  const filtered = ASSET_CATALOG.filter(a =>
    search === '' ||
    a.ticker.toLowerCase().includes(search.toLowerCase()) ||
    a.name.toLowerCase().includes(search.toLowerCase())
  );

  // ── Fetch klines ──────────────────────────────────────────────────────────
  const fetchBars = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await getKlines(meta.pair, TF_MAP[tf], TF_LIMIT[tf]);
      setBars(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [meta.pair, tf]);

  useEffect(() => { fetchBars(); }, [fetchBars]);

  // Auto-refresh every 30 s to keep last candle live
  useEffect(() => {
    const id = setInterval(fetchBars, 30_000);
    return () => clearInterval(id);
  }, [fetchBars]);

  // ── Destroy + recreate chart on asset/tf switch ────────────────────────────
  useEffect(() => {
    if (chartRef.current) {
      roRef.current?.disconnect();
      chartRef.current.remove();
      chartRef.current  = null;
      seriesRef.current = null;
      plRefs.current    = [];
    }
  }, [assetIdx, tf]);

  // ── Build chart once bars are ready ──────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;
    if (chartRef.current) return;  // already built for this render cycle

    const container = containerRef.current;

    chartRef.current = createChart(container, {
      width:  container.clientWidth,
      height: container.clientHeight || 230,
      layout: {
        background:  { color: 'transparent' },
        textColor:   'rgba(120,128,152,0.85)',
        fontFamily:  "'DM Mono', monospace",
        fontSize:    10,
      },
      grid: {
        vertLines: { color: 'rgba(26,32,48,0.5)' },
        horzLines: { color: 'rgba(26,32,48,0.5)' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: 'rgba(120,128,152,0.35)', width: 1, style: LineStyle.Dashed },
        horzLine: { color: 'rgba(120,128,152,0.35)', width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: {
        borderColor:  'rgba(26,32,48,0.6)',
        scaleMargins: { top: 0.08, bottom: 0.08 },
        textColor:    'rgba(120,128,152,0.85)',
      },
      timeScale: {
        borderColor:      'rgba(26,32,48,0.6)',
        timeVisible:      true,
        secondsVisible:   false,
        tickMarkFormatter: undefined,   // let LWC auto-format from real timestamps
        fixRightEdge:     true,
        fixLeftEdge:      false,
        rightBarStaysOnScroll: true,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale:  { mouseWheel: true, pinch: true },
    });

    seriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
      upColor:         '#00e5a0',
      downColor:       '#ff3d5a',
      borderUpColor:   '#00e5a0',
      borderDownColor: '#ff3d5a',
      wickUpColor:     'rgba(0,229,160,0.55)',
      wickDownColor:   'rgba(255,61,90,0.55)',
    });

    // Feed real OHLCV data
    const lwcData: CandlestickData[] = bars.map(b => ({
      time:  b.time as UTCTimestamp,
      open:  b.open,
      high:  b.high,
      low:   b.low,
      close: b.close,
    }));
    seriesRef.current.setData(lwcData);

    // TP / Entry / SL lines
    if (tp) {
      plRefs.current.push(seriesRef.current.createPriceLine({
        price: tp, color: 'rgba(0,229,160,0.75)', lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'TP',
      }));
    }
    if (entry) {
      plRefs.current.push(seriesRef.current.createPriceLine({
        price: entry, color: 'rgba(120,128,152,0.55)', lineWidth: 1,
        lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: 'Entry',
      }));
    }
    if (sl) {
      plRefs.current.push(seriesRef.current.createPriceLine({
        price: sl, color: 'rgba(255,61,90,0.75)', lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'SL',
      }));
    }

    chartRef.current.timeScale().fitContent();

    // Responsive resize
    roRef.current = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      chartRef.current?.resize(width, height);
    });
    roRef.current.observe(container);
  }, [bars, tp, entry, sl]);

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      roRef.current?.disconnect();
      chartRef.current?.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, []);

  // ── Derived stats from bar data ───────────────────────────────────────────
  const recentBars = tf === '1H' ? bars.slice(-24) : tf === '4H' ? bars.slice(-6) : bars.slice(-1);
  const dayHigh    = recentBars.length ? Math.max(...recentBars.map(b => b.high))    : null;
  const dayLow     = recentBars.length ? Math.min(...recentBars.map(b => b.low))     : null;
  const dayVol     = recentBars.reduce((s, b) => s + b.volume * b.close, 0);
  const fmtVol     = dayVol >= 1e9 ? `$${(dayVol/1e9).toFixed(1)}B`
                   : dayVol >= 1e6 ? `$${(dayVol/1e6).toFixed(0)}M`
                   : dayVol > 0    ? `$${dayVol.toFixed(0)}`
                   : '--';

  // ── Tab button ────────────────────────────────────────────────────────────
  const tfBtn = (t: TF) => (
    <button
      key={t}
      onClick={() => setTf(t)}
      style={{
        fontFamily: "'DM Mono', monospace", fontSize: 8.5,
        letterSpacing: '0.4px', textTransform: 'uppercase' as const,
        padding: '3px 8px', borderRadius: 3, cursor: 'pointer',
        border: 'none', transition: 'all 0.15s',
        background: tf === t ? 'rgba(0,229,160,0.1)' : 'none',
        color:      tf === t ? '#00e5a0'              : '#38405a',
      }}
    >
      {t}
    </button>
  );

  // Group for dropdown rendering
  const categories: AssetMeta['category'][] = ['Major', 'DeFi', 'Privacy', 'Meme', 'Other'];

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden', position: 'relative' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ padding: '9px 14px', borderBottom: '1px solid #1a2030', display: 'flex', flexWrap: 'wrap' as const, gap: 6, alignItems: 'center' }}>

        {/* Asset selector button */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => { setDropOpen(o => !o); setSearch(''); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              background: '#151a26', border: '1px solid #1a2030',
              borderRadius: 5, padding: '4px 9px 4px 6px', cursor: 'pointer',
            }}
          >
            <div style={{ width: 22, height: 22, borderRadius: 4, background: meta.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'DM Mono', monospace", fontSize: 6.5, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
              {meta.ticker.slice(0, 4)}
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 9.5, fontWeight: 600, color: '#e2e6f0', letterSpacing: '0.5px' }}>{meta.ticker} / USDT</div>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 7.5, color: '#38405a' }}>{meta.name}</div>
            </div>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 8, color: '#38405a', marginLeft: 3 }}>▾</span>
          </button>

          {/* Dropdown panel */}
          {dropOpen && (
            <div
              style={{
                position: 'absolute', top: '100%', left: 0, zIndex: 100, marginTop: 4,
                background: '#0d1119', border: '1px solid #1a2030', borderRadius: 6,
                width: 220, maxHeight: 320, overflowY: 'auto',
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              }}
            >
              {/* Search */}
              <div style={{ padding: '7px 9px', borderBottom: '1px solid #1a2030', position: 'sticky', top: 0, background: '#0d1119', zIndex: 1 }}>
                <input
                  autoFocus
                  placeholder="Search asset…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{
                    width: '100%', background: '#10141c', border: '1px solid #1a2030',
                    borderRadius: 3, padding: '4px 8px', color: '#e2e6f0',
                    fontFamily: "'DM Mono', monospace", fontSize: 10, outline: 'none',
                    boxSizing: 'border-box' as const,
                  }}
                />
              </div>

              {/* Grouped list */}
              {(search !== '' ? [{ cat: null as AssetMeta['category'] | null, items: filtered }] : categories.map(cat => ({ cat, items: ASSET_CATALOG.filter(a => a.category === cat) }))).map(group => (
                <div key={group.cat ?? 'results'}>
                  {group.cat && (
                    <div style={{ padding: '5px 10px 2px', fontFamily: "'DM Mono', monospace", fontSize: 7, letterSpacing: '1px', textTransform: 'uppercase', color: '#38405a' }}>
                      {group.cat}
                    </div>
                  )}
                  {group.items.map((a, i) => {
                    const idx = ASSET_CATALOG.indexOf(a);
                    return (
                      <button
                        key={a.ticker}
                        onClick={() => { setAssetIdx(idx); setDropOpen(false); setSearch(''); }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                          padding: '6px 10px', border: 'none', cursor: 'pointer',
                          background: idx === assetIdx ? 'rgba(0,229,160,0.05)' : i % 2 === 0 ? 'transparent' : 'rgba(26,32,48,0.2)',
                          textAlign: 'left' as const,
                          borderLeft: idx === assetIdx ? '2px solid #00e5a0' : '2px solid transparent',
                        }}
                      >
                        <div style={{ width: 20, height: 20, borderRadius: 3, background: a.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'DM Mono', monospace", fontSize: 5.5, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
                          {a.ticker.slice(0, 4)}
                        </div>
                        <div>
                          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 9.5, color: '#e2e6f0' }}>{a.ticker}</div>
                          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 7, color: '#38405a' }}>{a.name}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live price + change */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          {livePrice && (
            <span style={{ fontFamily: 'var(--font-bebas)', fontSize: 20, color: '#e2e6f0', lineHeight: 1 }}>
              {fmtPrice(livePrice)}
            </span>
          )}
          {changePct !== null && (
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 9.5, color: changePct >= 0 ? '#00e5a0' : '#ff3d5a' }}>
              {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
            </span>
          )}
        </div>

        {/* Regime pill */}
        {regime && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: "'DM Mono', monospace", fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase' as const, color: regColor, background: `${regColor}12`, border: `1px solid ${regColor}33`, padding: '2px 7px', borderRadius: 2 }}>
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: regColor, display: 'inline-block', flexShrink: 0 }} />
            {regime.regime_name.replace(/_/g, ' ')} · {Math.round((regime.confidence || 0) * 100)}%
          </div>
        )}

        {/* TF tabs — pushed right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 1, marginLeft: 'auto' }}>
          {(['1H', '4H', '1D', '1W'] as TF[]).map(tfBtn)}
        </div>
      </div>

      {/* ── Chart area ─────────────────────────────────────────────────────── */}
      <div style={{ position: 'relative', height: 230 }}>
        {/* Regime tint */}
        <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(180deg, ${isDown ? 'rgba(255,61,90,.035)' : 'rgba(0,229,160,.035)'} 0%, transparent 55%)`, pointerEvents: 'none', zIndex: 0 }} />

        {/* LWC mount point */}
        <div ref={containerRef} style={{ position: 'absolute', inset: 0, zIndex: 1 }} />

        {/* Loading */}
        {loading && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(16,20,28,0.7)', backdropFilter: 'blur(2px)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 20, height: 20, border: '2px solid #1a2030', borderTopColor: '#00e5a0', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 9, color: '#38405a', letterSpacing: '1px' }}>LOADING {meta.ticker} {tf}</span>
            </div>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: '#ff3d5a' }}>Failed to load {meta.ticker} klines</span>
            <button onClick={fetchBars} style={{ fontFamily: "'DM Mono', monospace", fontSize: 9, padding: '4px 12px', borderRadius: 3, border: '1px solid #1a2030', background: '#151a26', color: '#788098', cursor: 'pointer' }}>Retry</button>
          </div>
        )}

        {/* Spinner keyframe — injected inline */}
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>

      {/* ── Stats bar ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', borderTop: '1px solid #1a2030' }}>
        {[
          { label: '24h Volume', value: fmtVol },
          { label: '24h High',   value: dayHigh ? fmtPrice(dayHigh) : '--', color: '#00e5a0' },
          { label: '24h Low',    value: dayLow  ? fmtPrice(dayLow)  : '--', color: '#ff3d5a' },
          { label: 'Candles',    value: bars.length > 0 ? `${bars.length} × ${tf}` : '--' },
        ].map((s, i) => (
          <div key={s.label} style={{ padding: '7px 12px', borderRight: i < 3 ? '1px solid #1a2030' : undefined }}>
            <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 7, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 2 }}>{s.label}</div>
            <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 14, color: s.color || '#e2e6f0', lineHeight: 1 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* ── Click-away close for dropdown ──────────────────────────────────── */}
      {dropOpen && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 99 }}
          onClick={() => setDropOpen(false)}
        />
      )}
    </div>
  );
}
