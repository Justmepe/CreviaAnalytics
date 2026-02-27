'use client';

/**
 * MarketPricesContext — ONE price source for the entire app.
 *
 * Opens TWO Binance WebSocket connections:
 *   1. Spot  (stream.binance.com)  — all regular crypto pairs
 *   2. Futures (fstream.binance.com) — XAU/USDT (gold) and other perp-only pairs
 *
 * All components subscribe via useMarketPrices() — guaranteed identical prices
 * across LiveMarketBar, MarketLiveClient, HeroPricePanel, RiskCalculator, etc.
 */

import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react';

/* ── Types ──────────────────────────────────────────────────────── */

export interface PriceTick {
  price: number;
  change: number; // 24h %
}

export type WsStatus = 'connecting' | 'live' | 'offline';

interface MarketPricesContextType {
  ticks: Record<string, PriceTick>;
  wsStatus: WsStatus;
}

/* ── Stream maps ────────────────────────────────────────────────── */

/** Spot market streams (stream.binance.com) */
const SPOT_STREAMS: Record<string, string> = {
  BTC:  'btcusdt@ticker',
  ETH:  'ethusdt@ticker',
  XRP:  'xrpusdt@ticker',
  SOL:  'solusdt@ticker',
  BNB:  'bnbusdt@ticker',
  AVAX: 'avaxusdt@ticker',
  SUI:  'suiusdt@ticker',
  LINK: 'linkusdt@ticker',
  AAVE: 'aaveusdt@ticker',
  UNI:  'uniusdt@ticker',
  CRV:  'crvusdt@ticker',
  LDO:  'ldousdt@ticker',
  XMR:  'xmrusdt@ticker',
  ZEC:  'zecusdt@ticker',
  DASH: 'dashusdt@ticker',
  SCRT: 'scrtusdt@ticker',
  DOGE: 'dogeusdt@ticker',
  SHIB: 'shibusdt@ticker',
  PEPE: 'pepeusdt@ticker',
  FLOKI:'flokiusdt@ticker',
};

/** Futures (perpetual) streams (fstream.binance.com) */
const FUTURES_STREAMS: Record<string, string> = {
  XAU:  'xauusdt@ticker',   // Gold perpetual — only on futures
  TSLA: 'tslausdt@ticker',  // Tesla tokenized stock — only on futures
};

// Unified export used by other components (MarketLiveClient sectors etc.)
export const ALL_TICKER_STREAMS: Record<string, string> = {
  ...SPOT_STREAMS,
  ...FUTURES_STREAMS,
};

// Reverse maps: stream name → ticker symbol
const SPOT_REVERSE = Object.fromEntries(
  Object.entries(SPOT_STREAMS).map(([t, s]) => [s, t])
);
const FUTURES_REVERSE = Object.fromEntries(
  Object.entries(FUTURES_STREAMS).map(([t, s]) => [s, t])
);

const SPOT_URL    = `wss://stream.binance.com:9443/stream?streams=${Object.values(SPOT_STREAMS).join('/')}`;
const FUTURES_URL = `wss://fstream.binance.com/stream?streams=${Object.values(FUTURES_STREAMS).join('/')}`;

/* ── Context ────────────────────────────────────────────────────── */

const MarketPricesContext = createContext<MarketPricesContextType>({
  ticks: {},
  wsStatus: 'connecting',
});

/* ── Provider ───────────────────────────────────────────────────── */

interface ProviderProps {
  children: ReactNode;
  initialPrices?: Array<{
    ticker: string;
    price_usd: number | null;
    change_24h: number | null;
  }>;
}

export function MarketPricesProvider({ children, initialPrices = [] }: ProviderProps) {
  const [ticks, setTicks] = useState<Record<string, PriceTick>>(() => {
    const m: Record<string, PriceTick> = {};
    for (const p of initialPrices) {
      if (p.price_usd != null) {
        m[p.ticker] = { price: p.price_usd, change: p.change_24h ?? 0 };
      }
    }
    return m;
  });

  const [spotStatus,    setSpotStatus]    = useState<WsStatus>('connecting');
  const [futuresStatus, setFuturesStatus] = useState<WsStatus>('connecting');

  // Combined status: "live" if at least spot is live
  const wsStatus: WsStatus =
    spotStatus === 'live' ? 'live' :
    spotStatus === 'connecting' || futuresStatus === 'connecting' ? 'connecting' :
    'offline';

  const spotRef    = useRef<WebSocket | null>(null);
  const futuresRef = useRef<WebSocket | null>(null);
  const spotRetry    = useRef<ReturnType<typeof setTimeout> | null>(null);
  const futuresRetry = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  function buildConnection(
    url: string,
    reverseMap: Record<string, string>,
    setStatus: (s: WsStatus) => void,
    wsRefLocal: React.MutableRefObject<WebSocket | null>,
    retryRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>,
  ) {
    if (!mountedRef.current) return;
    setStatus('connecting');

    const ws = new WebSocket(url);
    wsRefLocal.current = ws;

    ws.onopen = () => {
      if (mountedRef.current) setStatus('live');
    };

    ws.onmessage = (evt) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(evt.data as string) as {
          stream: string;
          data: { c: string; P: string };
        };
        const ticker = reverseMap[msg.stream];
        if (!ticker) return;
        const price = parseFloat(msg.data.c);
        const change = parseFloat(msg.data.P);
        if (!isNaN(price) && !isNaN(change)) {
          setTicks((prev) => ({ ...prev, [ticker]: { price, change } }));
        }
      } catch { /* ignore */ }
    };

    ws.onerror = () => {
      if (mountedRef.current) setStatus('offline');
    };

    ws.onclose = () => {
      if (mountedRef.current) {
        setStatus('offline');
        retryRef.current = setTimeout(
          () => buildConnection(url, reverseMap, setStatus, wsRefLocal, retryRef),
          5000,
        );
      }
    };
  }

  useEffect(() => {
    mountedRef.current = true;

    buildConnection(SPOT_URL,    SPOT_REVERSE,    setSpotStatus,    spotRef,    spotRetry);
    buildConnection(FUTURES_URL, FUTURES_REVERSE, setFuturesStatus, futuresRef, futuresRetry);

    return () => {
      mountedRef.current = false;
      if (spotRetry.current)    clearTimeout(spotRetry.current);
      if (futuresRetry.current) clearTimeout(futuresRetry.current);
      spotRef.current?.close();
      futuresRef.current?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MarketPricesContext.Provider value={{ ticks, wsStatus }}>
      {children}
    </MarketPricesContext.Provider>
  );
}

/* ── Hook ───────────────────────────────────────────────────────── */

export function useMarketPrices(): MarketPricesContextType {
  return useContext(MarketPricesContext);
}
