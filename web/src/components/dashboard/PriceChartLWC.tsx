'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CandlestickSeries, LineStyle } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, UTCTimestamp } from 'lightweight-charts';
import { getKlines } from '@/lib/api';
import type { KlineBar } from '@/lib/api';
import type { TradeSetup, MarketRegime } from '@/types';

// ── Types ────────────────────────────────────────────────────────────────────

type ChartAsset = 'BTC' | 'ETH' | 'SOL' | 'XMR';
type TF = '4H' | '1D' | '1W';

const TF_MAP: Record<TF, string> = { '4H': '4h', '1D': '1d', '1W': '1w' };
const TF_LIMIT: Record<TF, number> = { '4H': 120, '1D': 90, '1W': 52 };

const ASSET_BG: Record<ChartAsset, string> = {
  BTC: 'linear-gradient(135deg,#f7931a,#e8720c)',
  ETH: 'linear-gradient(135deg,#627eea,#3b5ede)',
  SOL: 'linear-gradient(135deg,#9945ff,#14f195)',
  XMR: 'linear-gradient(135deg,#ff6600,#cc4400)',
};

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
  if (p >= 1)     return `$${p.toFixed(2)}`;
  return `$${p.toFixed(4)}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  btcPrice: number | null;
  ethPrice: number | null;
  solPrice: number | null;
  xmrPrice: number | null;
  setups: TradeSetup[];
  regime: MarketRegime | null;
}

export default function PriceChartLWC({ btcPrice, ethPrice, solPrice, xmrPrice, setups, regime }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const seriesRef    = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const priceLineRefs = useRef<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>[]>([]);

  const [asset, setAsset]   = useState<ChartAsset>('BTC');
  const [tf, setTf]         = useState<TF>('4H');
  const [bars, setBars]     = useState<KlineBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(false);

  const currentPrice: Record<ChartAsset, number | null> = {
    BTC: btcPrice, ETH: ethPrice, SOL: solPrice, XMR: xmrPrice,
  };
  const livePrice = currentPrice[asset];

  // Active setup for this asset
  const activeSetup = setups.find(s => s.asset.toUpperCase().startsWith(asset));
  const tp    = activeSetup?.take_profits?.[0]?.price ?? null;
  const entry = activeSetup?.entry_zones?.[0]?.price ?? null;
  const sl    = activeSetup?.stop_loss?.price ?? null;

  const regColor = regime ? (REGIME_COLORS[regime.regime_name] ?? '#00e5a0') : '#00e5a0';
  const isDown   = regime?.regime_name?.match(/RISK_OFF|DISTRIBUTION/) != null;

  // Compute 24h change from first vs last close in the bar array (daily chart) or use live bar
  const changePct = bars.length >= 2
    ? ((bars[bars.length - 1].close / bars[bars.length - 2].close - 1) * 100)
    : null;

  // ── Fetch klines ──────────────────────────────────────────────────────────
  const fetchBars = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await getKlines(asset, TF_MAP[tf], TF_LIMIT[tf]);
      setBars(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [asset, tf]);

  useEffect(() => { fetchBars(); }, [fetchBars]);

  // Poll every 30 seconds to keep the last candle fresh
  useEffect(() => {
    const id = setInterval(fetchBars, 30_000);
    return () => clearInterval(id);
  }, [fetchBars]);

  // ── Build / update chart ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    // Create chart on first render
    if (!chartRef.current) {
      chartRef.current = createChart(containerRef.current, {
        layout: {
          background: { color: 'transparent' },
          textColor:  'rgba(120,128,152,0.9)',
          fontFamily: "'DM Mono', monospace",
          fontSize:   10,
        },
        grid: {
          vertLines: { color: 'rgba(26,32,48,0.6)' },
          horzLines: { color: 'rgba(26,32,48,0.6)' },
        },
        crosshair: {
          vertLine: { color: 'rgba(120,128,152,0.4)', width: 1, style: LineStyle.Dashed },
          horzLine: { color: 'rgba(120,128,152,0.4)', width: 1, style: LineStyle.Dashed },
        },
        rightPriceScale: {
          borderColor: 'rgba(26,32,48,0.6)',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: 'rgba(26,32,48,0.6)',
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: true,
        handleScale:  true,
      });

      seriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
        upColor:        '#00e5a0',
        downColor:      '#ff3d5a',
        borderUpColor:  '#00e5a0',
        borderDownColor:'#ff3d5a',
        wickUpColor:    'rgba(0,229,160,0.5)',
        wickDownColor:  'rgba(255,61,90,0.5)',
      });
    }

    // Feed data
    const lwcData: CandlestickData[] = bars.map(b => ({
      time:  b.time as UTCTimestamp,
      open:  b.open,
      high:  b.high,
      low:   b.low,
      close: b.close,
    }));
    seriesRef.current!.setData(lwcData);

    // Remove old price lines
    priceLineRefs.current.forEach(pl => seriesRef.current!.removePriceLine(pl));
    priceLineRefs.current = [];

    // Add TP / Entry / SL price lines
    if (tp) {
      priceLineRefs.current.push(seriesRef.current!.createPriceLine({
        price: tp, color: 'rgba(0,229,160,0.7)', lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'TP',
      }));
    }
    if (entry) {
      priceLineRefs.current.push(seriesRef.current!.createPriceLine({
        price: entry, color: 'rgba(120,128,152,0.5)', lineWidth: 1,
        lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: 'Entry',
      }));
    }
    if (sl) {
      priceLineRefs.current.push(seriesRef.current!.createPriceLine({
        price: sl, color: 'rgba(255,61,90,0.7)', lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'SL',
      }));
    }

    chartRef.current!.timeScale().fitContent();
  }, [bars, tp, entry, sl]);

  // ── Resize observer ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || !chartRef.current) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      chartRef.current?.resize(width, height);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      chartRef.current?.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, []);

  // ── Reset chart when asset/tf changes (need fresh series) ─────────────────
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current  = null;
      seriesRef.current = null;
      priceLineRefs.current = [];
    }
  }, [asset, tf]);

  // ── UI helpers ────────────────────────────────────────────────────────────
  const tabBtn = (key: string, active: boolean, onClick: () => void, extraStyle?: React.CSSProperties) => (
    <button
      key={key}
      onClick={onClick}
      style={{
        fontFamily: "'DM Mono', monospace",
        fontSize: 8.5, letterSpacing: '0.5px',
        textTransform: 'uppercase' as const,
        padding: '3px 8px', borderRadius: 3,
        cursor: 'pointer', transition: 'all 0.15s',
        border: '1px solid #1a2030',
        background: active ? '#151a26' : 'none',
        color: active ? '#e2e6f0' : '#38405a',
        ...extraStyle,
      }}
    >
      {key}
    </button>
  );

  const ASSET_TABS: ChartAsset[] = ['BTC', 'ETH', 'SOL', 'XMR'];
  const TF_TABS: TF[] = ['4H', '1D', '1W'];

  return (
    <div style={{ background: '#10141c', border: '1px solid #1a2030', borderRadius: 8, overflow: 'hidden' }}>
      {/* ── Header ── */}
      <div style={{ padding: '9px 14px', borderBottom: '1px solid #1a2030', display: 'flex', flexWrap: 'wrap' as const, gap: 7, alignItems: 'center' }}>
        {/* Asset info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{ width: 24, height: 24, borderRadius: 4, background: ASSET_BG[asset], display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'DM Mono', monospace", fontSize: 7, fontWeight: 700, color: '#070809', flexShrink: 0 }}>
            {asset}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 9.5, letterSpacing: '1.2px', textTransform: 'uppercase', color: '#788098' }}>{asset} / USDT</span>
              {livePrice && (
                <span style={{ fontFamily: 'var(--font-bebas)', fontSize: 19, color: '#e2e6f0', lineHeight: 1 }}>
                  {fmtPrice(livePrice)}
                </span>
              )}
              {changePct !== null && (
                <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 9.5, color: changePct >= 0 ? '#00e5a0' : '#ff3d5a' }}>
                  {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                </span>
              )}
            </div>
            {regime && (
              <div style={{ marginTop: 2 }}>
                <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: regColor, background: `${regColor}12`, border: `1px solid ${regColor}33`, padding: '1px 6px', borderRadius: 2, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                  <span style={{ width: 4, height: 4, borderRadius: '50%', background: regColor, display: 'inline-block' }} />
                  {regime.regime_name.replace(/_/g, ' ')} · {Math.round((regime.confidence || 0) * 100)}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 3, marginLeft: 'auto' }}>
          {ASSET_TABS.map(k => tabBtn(k, asset === k, () => setAsset(k)))}
          <div style={{ width: 1, height: 13, background: '#1a2030', margin: '0 3px' }} />
          {TF_TABS.map(t => tabBtn(t, tf === t, () => setTf(t), { border: 'none', background: tf === t ? 'rgba(0,229,160,0.08)' : 'none', color: tf === t ? '#00e5a0' : '#38405a' }))}
        </div>
      </div>

      {/* ── Chart area ── */}
      <div style={{ position: 'relative', height: 220 }}>
        {/* Regime tint overlay */}
        <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(180deg, ${isDown ? 'rgba(255,61,90,.04)' : 'rgba(0,229,160,.04)'} 0%, transparent 60%)`, pointerEvents: 'none', zIndex: 0 }} />

        {/* Chart container — LWC mounts here */}
        <div ref={containerRef} style={{ position: 'absolute', inset: 0, zIndex: 1 }} />

        {/* Loading state */}
        {loading && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(16,20,28,0.7)' }}>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: '#38405a', letterSpacing: '1px' }}>LOADING KLINES…</span>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: '#ff3d5a' }}>Chart data unavailable</span>
            <button onClick={fetchBars} style={{ fontFamily: "'DM Mono', monospace", fontSize: 9, padding: '4px 10px', borderRadius: 3, border: '1px solid #1a2030', background: 'none', color: '#788098', cursor: 'pointer' }}>Retry</button>
          </div>
        )}
      </div>

      {/* ── Stats bar ── */}
      {bars.length > 0 && (() => {
        const last = bars[bars.length - 1];
        const dayHigh = Math.max(...bars.slice(-24).map(b => b.high));
        const dayLow  = Math.min(...bars.slice(-24).map(b => b.low));
        const dayVol  = bars.slice(-24).reduce((s, b) => s + b.volume * b.close, 0);
        const fmtVol = dayVol >= 1e9 ? `$${(dayVol/1e9).toFixed(1)}B` : dayVol >= 1e6 ? `$${(dayVol/1e6).toFixed(0)}M` : `$${dayVol.toFixed(0)}`;
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', borderTop: '1px solid #1a2030' }}>
            {[
              { label: '24h Volume', value: fmtVol },
              { label: '24h High',   value: fmtPrice(dayHigh), color: '#00e5a0' },
              { label: '24h Low',    value: fmtPrice(dayLow),  color: '#ff3d5a' },
              { label: 'Last Close', value: fmtPrice(last.close) },
            ].map((s, i) => (
              <div key={s.label} style={{ padding: '7px 13px', borderRight: i < 3 ? '1px solid #1a2030' : undefined }}>
                <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 7.5, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#38405a', marginBottom: 2 }}>{s.label}</div>
                <div style={{ fontFamily: 'var(--font-bebas)', fontSize: 15, color: s.color || '#e2e6f0', lineHeight: 1 }}>{s.value}</div>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
