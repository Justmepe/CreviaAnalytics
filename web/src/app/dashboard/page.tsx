import { Metadata } from 'next';
import DashboardClient from '@/components/dashboard/DashboardClient';
import { getCurrentRegime, getLatestTradeSetups, getLatestSnapshot, getContentFeed } from '@/lib/api';
import type { MarketRegime, TradeSetup, ContentPost } from '@/types';

export const metadata: Metadata = {
  title: 'Dashboard',
};

export const revalidate = 60;

async function fetchDashboardData() {
  const [regime, setups, snapshot, feed] = await Promise.allSettled([
    getCurrentRegime(),
    getLatestTradeSetups(undefined, 5),
    getLatestSnapshot(),
    getContentFeed({ page_size: 6 }),
  ]);

  return {
    regime: regime.status === 'fulfilled' ? regime.value : null,
    setups: setups.status === 'fulfilled' ? setups.value : [],
    snapshot: snapshot.status === 'fulfilled' ? snapshot.value : null,
    recentContent: feed.status === 'fulfilled' ? feed.value.items : [],
  };
}

export default async function DashboardPage() {
  const { regime, setups, snapshot, recentContent } = await fetchDashboardData();

  return (
    <DashboardClient
      regime={regime as MarketRegime | null}
      setups={setups as TradeSetup[]}
      recentContent={recentContent as ContentPost[]}
      btcPrice={snapshot?.btc_price ?? null}
      ethPrice={snapshot?.eth_price ?? null}
      marketCap={snapshot?.total_market_cap ?? null}
      fearGreed={snapshot?.fear_greed_index ?? null}
      fearGreedLabel={snapshot?.fear_greed_label ?? null}
    />
  );
}
