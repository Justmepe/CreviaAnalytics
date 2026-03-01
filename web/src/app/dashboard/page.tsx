import { Metadata } from 'next';
import DashboardClient from '@/components/dashboard/DashboardClient';
import { getCurrentRegime, getLatestTradeSetups, getLatestSnapshot, getContentFeed, getLatestPrices } from '@/lib/api';
import type { MarketRegime, TradeSetup, ContentPost } from '@/types';

export const metadata: Metadata = {
  title: 'Dashboard',
};

export const revalidate = 60;

async function fetchDashboardData() {
  const [regime, setups, snapshot, feed, prices] = await Promise.allSettled([
    getCurrentRegime(),
    getLatestTradeSetups(undefined, 5),
    getLatestSnapshot(),
    getContentFeed({ page_size: 8 }),
    getLatestPrices('BTC,ETH,SOL,XMR,BNB,AAVE'),
  ]);

  const priceArr = prices.status === 'fulfilled' ? prices.value : [];
  const priceMap = Object.fromEntries(priceArr.map(p => [p.ticker, p]));

  return {
    regime:        regime.status === 'fulfilled' ? regime.value : null,
    setups:        setups.status === 'fulfilled' ? setups.value : [],
    snapshot:      snapshot.status === 'fulfilled' ? snapshot.value : null,
    recentContent: feed.status === 'fulfilled' ? feed.value.items : [],
    assetPrices:   priceMap,
  };
}

export default async function DashboardPage() {
  const { regime, setups, snapshot, recentContent, assetPrices } = await fetchDashboardData();

  return (
    <DashboardClient
      regime={regime as MarketRegime | null}
      setups={setups as TradeSetup[]}
      recentContent={recentContent as ContentPost[]}
      btcPrice={snapshot?.btc_price ?? assetPrices['BTC']?.price_usd ?? null}
      ethPrice={snapshot?.eth_price ?? assetPrices['ETH']?.price_usd ?? null}
      solPrice={assetPrices['SOL']?.price_usd ?? null}
      xmrPrice={assetPrices['XMR']?.price_usd ?? null}
      bnbPrice={assetPrices['BNB']?.price_usd ?? null}
      aavePrice={assetPrices['AAVE']?.price_usd ?? null}
      solChange={assetPrices['SOL']?.change_24h ?? null}
      xmrChange={assetPrices['XMR']?.change_24h ?? null}
      marketCap={snapshot?.total_market_cap ?? null}
      fearGreed={snapshot?.fear_greed_index ?? null}
      fearGreedLabel={snapshot?.fear_greed_label ?? null}
    />
  );
}
