import { Metadata } from 'next';
import DashboardClient from '@/components/dashboard/DashboardClient';
import { getCurrentRegime, getLatestTradeSetups, getLatestSnapshot } from '@/lib/api';
import type { MarketRegime, TradeSetup } from '@/types';

export const metadata: Metadata = {
  title: 'Dashboard',
};

export const revalidate = 60;

async function fetchDashboardData() {
  const [regime, setups, snapshot] = await Promise.allSettled([
    getCurrentRegime(),
    getLatestTradeSetups(undefined, 5),
    getLatestSnapshot(),
  ]);

  return {
    regime: regime.status === 'fulfilled' ? regime.value : null,
    setups: setups.status === 'fulfilled' ? setups.value : [],
    snapshot: snapshot.status === 'fulfilled' ? snapshot.value : null,
  };
}

export default async function DashboardPage() {
  const { regime, setups, snapshot } = await fetchDashboardData();

  return (
    <DashboardClient
      regime={regime as MarketRegime | null}
      setups={setups as TradeSetup[]}
      btcPrice={snapshot?.btc_price ?? null}
      ethPrice={snapshot?.eth_price ?? null}
      marketCap={snapshot?.total_market_cap ?? null}
      fearGreed={snapshot?.fear_greed_index ?? null}
      fearGreedLabel={snapshot?.fear_greed_label ?? null}
    />
  );
}
