'use client';

import { useEffect, useState, useRef } from 'react';

export interface StreamSnapshot {
  btc_price: number | null;
  eth_price: number | null;
  total_market_cap: number | null;
  btc_dominance: number | null;
  fear_greed_index: number | null;
  fear_greed_label: string | null;
  captured_at: string | null;
}

export interface StreamRegime {
  regime_name: string;
  confidence: number;
  description: string | null;
  color: string | null;
}

interface UseMarketStreamReturn {
  snapshot: StreamSnapshot | null;
  regime: StreamRegime | null;
  connected: boolean;
  lastPing: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useMarketStream(): UseMarketStreamReturn {
  const [snapshot, setSnapshot] = useState<StreamSnapshot | null>(null);
  const [regime, setRegime] = useState<StreamRegime | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastPing, setLastPing] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    function connect() {
      if (esRef.current) {
        esRef.current.close();
      }

      const es = new EventSource(`${API_BASE}/api/stream/market`);
      esRef.current = es;

      es.addEventListener('open', () => setConnected(true));

      es.addEventListener('snapshot', (e) => {
        try {
          const data = JSON.parse(e.data);
          setSnapshot(data);
        } catch {}
      });

      es.addEventListener('regime', (e) => {
        try {
          const data = JSON.parse(e.data);
          setRegime(data);
        } catch {}
      });

      es.addEventListener('ping', (e) => {
        try {
          const data = JSON.parse(e.data);
          setLastPing(data.t);
        } catch {}
      });

      es.addEventListener('error', () => {
        setConnected(false);
        es.close();
        // Reconnect after 10s
        setTimeout(connect, 10000);
      });
    }

    connect();

    return () => {
      esRef.current?.close();
    };
  }, []);

  return { snapshot, regime, connected, lastPing };
}
