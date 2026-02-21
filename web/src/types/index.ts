export interface Tweet {
  position: number;
  body: string;
}

export interface JournalEntry {
  id: number;
  asset: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number | null;
  leverage: number | null;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  risk_amount: number | null;
  status: string | null;
  outcome: string | null;
  pnl_usd: number | null;
  pnl_pct: number | null;
  rr_achieved: number | null;
  setup_type: string | null;
  regime_at_entry: string | null;
  notes: string | null;
  tags: string[] | null;
  trade_setup_id: number | null;
  entry_time: string | null;
  exit_time: string | null;
  created_at: string | null;
}

export interface PortfolioStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl_usd: number;
  avg_rr_achieved: number;
  avg_win_usd: number;
  avg_loss_usd: number;
  profit_factor: number;
  max_drawdown_usd: number;
  best_trade_usd: number;
  worst_trade_usd: number;
  active_trades: number;
}

export interface ContentPost {
  id: number;
  content_type: 'thread' | 'memo' | 'news_tweet' | 'risk_alert';
  title: string | null;
  slug: string;
  body: string;
  excerpt: string | null;
  tickers: string[] | null;
  sector: string | null;
  tier: string;
  image_url: string | null;
  published_at: string | null;
  tweets: Tweet[] | null;
  market_snapshot: Record<string, unknown> | null;
}

export interface ContentListResponse {
  items: ContentPost[];
  total: number;
  page: number;
  page_size: number;
}

export interface MarketSnapshot {
  id: number;
  btc_price: number | null;
  eth_price: number | null;
  total_market_cap: number | null;
  btc_dominance: number | null;
  fear_greed_index: number | null;
  fear_greed_label: string | null;
  total_volume_24h: number | null;
  captured_at: string | null;
}

export interface AssetPrice {
  ticker: string;
  price_usd: number | null;
  change_24h: number | null;
  change_7d: number | null;
  volume_24h: number | null;
  market_cap: number | null;
  captured_at: string | null;
}

export interface RegimeSignal {
  metric: string;
  value: number | string;
  status: string;
  contribution: number;
  matched: boolean;
}

export interface MarketRegime {
  id: number;
  regime_name: string;
  confidence: number;
  description: string | null;
  trader_action: string | null;
  expected_outcome: string | null;
  color: string | null;
  supporting_signals: RegimeSignal[] | null;
  metrics_snapshot: Record<string, unknown> | null;
  detected_at: string | null;
  historical_accuracy: number | null;
  regime_count: number | null;
  previous_regime: string | null;
}

export interface Opportunity {
  asset: string;
  direction: string;
  setup_type: string;
  confidence: number;
  score: number;
  score_breakdown: Record<string, number>;
  best_rr: number;
  recommendation: string;  // STRONG, MODERATE, WEAK, AVOID
  entry_zones: Array<{ price: number; type: string; reason: string }>;
  stop_loss: { price: number; reason: string; distance_pct?: number } | null;
  take_profits: Array<{ price: number; percentage: number; rr: number; reason: string }>;
  reasoning: string[];
  risk_factors: string[];
  regime_at_creation: string | null;
}

export interface OpportunityScan {
  id: number;
  opportunities: Opportunity[] | null;
  opportunity_count: number | null;
  best_rr: { asset: string; direction: string; rr: number } | null;
  highest_conviction: { asset: string; direction: string; confidence: number } | null;
  safest_play: { asset: string; direction: string; score: number } | null;
  regime: string | null;
  scanned_at: string | null;
}

export interface CorrelationPair {
  metric1: string;
  metric2: string;
  metric1_key?: string;
  metric2_key?: string;
  correlation: number;
  strength?: string;
  note?: string;
}

export interface TradeEntryZone {
  price: number;
  type: string;  // aggressive, conservative, patient
  reason: string;
}

export interface TradeSetup {
  id: number;
  asset: string;
  direction: 'LONG' | 'SHORT';
  setup_type: string | null;
  confidence: number | null;
  entry_zones: TradeEntryZone[] | null;
  stop_loss: { price: number; reason: string; distance_pct?: number } | null;
  take_profits: Array<{ price: number; percentage: number; rr: number; reason: string }> | null;
  reasoning: string[] | null;
  risk_factors: string[] | null;
  position_sizing: Record<string, number> | null;
  regime_at_creation: string | null;
  outcome: string | null;
  created_at: string | null;
  expires_at: string | null;
}

export interface CorrelationSnapshot {
  id: number;
  correlation_matrix: number[][] | null;
  labels: string[] | null;
  metric_keys: string[] | null;
  strongest_pairs: CorrelationPair[] | null;
  interpretation: string | null;
  timeframe_hours: number | null;
  data_points: number | null;
  captured_at: string | null;
}
