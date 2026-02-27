const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    next: { revalidate: 60 },
    signal: AbortSignal.timeout(8000),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

import type { ContentListResponse, ContentPost, MarketSnapshot, AssetPrice, MarketRegime, CorrelationSnapshot, TradeSetup, OpportunityScan, JournalEntry, PortfolioStats, ExchangeKey, PortfolioSummary } from '@/types';
import { getStoredToken } from './auth';

async function authFetchClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getJournalEntries(statusFilter?: string, asset?: string): Promise<JournalEntry[]> {
  const p = new URLSearchParams();
  if (statusFilter) p.set('status', statusFilter);
  if (asset) p.set('asset', asset);
  return authFetchClient<JournalEntry[]>(`/api/journal/entries?${p}`);
}

export async function createJournalEntry(data: Record<string, unknown>): Promise<JournalEntry> {
  return authFetchClient<JournalEntry>('/api/journal/entries', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function closeJournalEntry(id: number, exitPrice: number, notes?: string): Promise<JournalEntry> {
  return authFetchClient<JournalEntry>(`/api/journal/entries/${id}/close`, {
    method: 'POST',
    body: JSON.stringify({ exit_price: exitPrice, notes }),
  });
}

export async function deleteJournalEntry(id: number): Promise<void> {
  await authFetchClient<void>(`/api/journal/entries/${id}`, { method: 'DELETE' });
}

export async function getPortfolioStats(): Promise<PortfolioStats> {
  return authFetchClient<PortfolioStats>('/api/journal/portfolio');
}

export async function getContentFeed(params?: {
  content_type?: string;
  sector?: string;
  ticker?: string;
  page?: number;
  page_size?: number;
}): Promise<ContentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.content_type) searchParams.set('content_type', params.content_type);
  if (params?.sector) searchParams.set('sector', params.sector);
  if (params?.ticker) searchParams.set('ticker', params.ticker);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));

  const qs = searchParams.toString();
  return fetchAPI<ContentListResponse>(`/api/content/feed${qs ? `?${qs}` : ''}`);
}

export async function getPost(slug: string): Promise<ContentPost> {
  return fetchAPI<ContentPost>(`/api/content/post/${slug}`);
}

export async function getLatestSnapshot(): Promise<MarketSnapshot> {
  return fetchAPI<MarketSnapshot>('/api/market/snapshot/latest');
}

export async function getLatestPrices(tickers?: string): Promise<AssetPrice[]> {
  const qs = tickers ? `?tickers=${tickers}` : '';
  return fetchAPI<AssetPrice[]>(`/api/market/prices${qs}`);
}

export async function getCurrentRegime(): Promise<MarketRegime> {
  return fetchAPI<MarketRegime>('/api/intelligence/regime/current');
}

export async function getLatestCorrelations(timeframe: number = 24): Promise<CorrelationSnapshot> {
  return fetchAPI<CorrelationSnapshot>(`/api/intelligence/correlations/latest?timeframe=${timeframe}`);
}

export interface SmartMoneyScan {
  signals: Array<{
    signal_type: string;
    asset: string;
    data: Record<string, unknown> | null;
    interpretation: string | null;
    impact: string;
    confidence: string;
    timestamp: string | null;
  }>;
  signal_count: number;
  net_sentiment: string;
  aggregate_interpretation: string | null;
}

export async function getSmartMoneySignals(window: number = 6): Promise<SmartMoneyScan> {
  return fetchAPI<SmartMoneyScan>(`/api/intelligence/smart-money/signals?window=${window}`);
}

export async function getLatestOpportunities(): Promise<OpportunityScan> {
  return fetchAPI<OpportunityScan>('/api/intelligence/opportunities/latest');
}

export async function getLatestTradeSetups(asset?: string, limit: number = 10): Promise<TradeSetup[]> {
  const params = new URLSearchParams();
  if (asset) params.set('asset', asset);
  params.set('limit', String(limit));
  return fetchAPI<TradeSetup[]>(`/api/intelligence/setups/latest?${params.toString()}`);
}

export async function getHealthCheck(): Promise<{ status: string }> {
  return fetchAPI('/api/health');
}

// --- Portfolio / Exchange API Key management ---

export async function getExchangeKeys(): Promise<ExchangeKey[]> {
  return authFetchClient<ExchangeKey[]>('/api/portfolio/keys');
}

export async function addExchangeKey(data: {
  exchange: string;
  api_key: string;
  api_secret: string;
  label?: string;
}): Promise<ExchangeKey> {
  return authFetchClient<ExchangeKey>('/api/portfolio/keys', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteExchangeKey(id: number): Promise<void> {
  await authFetchClient<void>(`/api/portfolio/keys/${id}`, { method: 'DELETE' });
}

export async function syncPortfolio(): Promise<PortfolioSummary[]> {
  return authFetchClient<PortfolioSummary[]>('/api/portfolio/sync');
}

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--';
  if (price >= 1000) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (price >= 1) return `$${price.toFixed(2)}`;
  return `$${price.toFixed(4)}`;
}

export function formatLargeNumber(num: number | null | undefined): string {
  if (num == null) return '--';
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  return `$${num.toLocaleString()}`;
}

export function formatChange(change: number | null | undefined): string {
  if (change == null) return '--';
  const sign = change >= 0 ? '+' : '';
  return `${sign}${change.toFixed(2)}%`;
}

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
