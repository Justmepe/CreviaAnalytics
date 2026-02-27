'use client';

import { useMarketPrices } from '@/context/MarketPricesContext';
import { formatPrice } from '@/lib/api';

const HERO_ASSETS = [
  { ticker: 'BTC', name: 'Bitcoin',   grad: 'linear-gradient(135deg,#f7931a,#e07c10)', textColor: '#08090c' },
  { ticker: 'ETH', name: 'Ethereum',  grad: 'linear-gradient(135deg,#627eea,#4f67c8)', textColor: '#fff'    },
  { ticker: 'SOL', name: 'Solana',    grad: 'linear-gradient(135deg,#9945ff,#14f195)', textColor: '#fff'    },
  { ticker: 'BNB', name: 'BNB Chain', grad: 'linear-gradient(135deg,#f3ba2f,#d4a228)', textColor: '#08090c' },
];

export default function HeroPricePanel() {
  const { ticks } = useMarketPrices();

  return (
    <div style={{ background: '#111520', border: '1px solid #1c2235', borderRadius: 8, overflow: 'hidden' }}>
      {HERO_ASSETS.map((asset, i) => {
        const tick = ticks[asset.ticker];
        const price = tick?.price ?? null;
        const change = tick?.change ?? null;
        const isUp = (change ?? 0) >= 0;

        return (
          <div
            key={asset.ticker}
            style={{
              display: 'grid',
              gridTemplateColumns: '32px 1fr auto auto',
              alignItems: 'center',
              gap: 10,
              padding: '10px 16px',
              borderBottom: i < HERO_ASSETS.length - 1 ? '1px solid #1c2235' : undefined,
            }}
          >
            {/* Avatar */}
            <div style={{
              width: 30, height: 30, borderRadius: 7,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 500,
              color: asset.textColor, background: asset.grad,
            }}>
              {asset.ticker.slice(0, 3)}
            </div>

            {/* Name */}
            <div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, fontWeight: 500, color: '#dfe3f0' }}>
                {asset.name}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#3d4562' }}>
                {asset.ticker}
              </div>
            </div>

            {/* Price */}
            <div className="font-mono-cc" style={{ fontSize: 12, fontWeight: 500, color: '#dfe3f0', textAlign: 'right' }}>
              {price != null ? formatPrice(price) : '--'}
            </div>

            {/* Change */}
            <div className="font-mono-cc" style={{ fontSize: 10, textAlign: 'right', color: isUp ? '#00d68f' : '#f03e5a', minWidth: 52 }}>
              {change != null ? `${isUp ? '+' : ''}${change.toFixed(2)}%` : '--'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
