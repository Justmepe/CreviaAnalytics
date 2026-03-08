"""
Pydantic schemas for content API requests and responses
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# --- Publish requests (from engine → API) ---

class PublishThreadRequest(BaseModel):
    tweets: List[str]
    tweet_count: int
    tickers: List[str] = ['BTC', 'ETH']
    sector: str = 'global'
    image_url: Optional[str] = None
    market_snapshot: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None


class PublishMemoRequest(BaseModel):
    ticker: str
    body: str
    current_price: Optional[float] = None
    sector: Optional[str] = None
    tickers: List[str] = []
    image_url: Optional[str] = None
    market_snapshot: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None


class PublishArticleRequest(BaseModel):
    title: str
    body: str
    sector: str = 'global'
    tickers: List[str] = ['BTC', 'ETH']
    image_url: Optional[str] = None
    market_snapshot: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None


class PublishNewsTweetRequest(BaseModel):
    ticker: str
    body: str
    title: Optional[str] = None
    current_price: Optional[float] = None
    sector: Optional[str] = None
    tickers: List[str] = []
    image_url: Optional[str] = None
    market_snapshot: Optional[Dict[str, Any]] = None


class PublishMarketSnapshotRequest(BaseModel):
    btc_price: Optional[float] = None
    eth_price: Optional[float] = None
    total_market_cap: Optional[float] = None
    btc_dominance: Optional[float] = None
    fear_greed_index: Optional[int] = None
    fear_greed_label: Optional[str] = None
    total_volume_24h: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class PublishAssetPriceRequest(BaseModel):
    ticker: str
    price_usd: float
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


# --- Read responses (API → frontend) ---

class TweetResponse(BaseModel):
    position: int
    body: str

    class Config:
        from_attributes = True


class ContentPostResponse(BaseModel):
    id: int
    content_type: str
    title: Optional[str]
    slug: str
    body: str
    excerpt: Optional[str]
    tickers: Optional[List[str]]
    sector: Optional[str]
    tier: str
    image_url: Optional[str]
    published_at: Optional[datetime]
    tweets: Optional[List[TweetResponse]] = None
    market_snapshot: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ContentListResponse(BaseModel):
    items: List[ContentPostResponse]
    total: int
    page: int
    page_size: int


class MarketSnapshotResponse(BaseModel):
    id: int
    btc_price: Optional[float]
    eth_price: Optional[float]
    total_market_cap: Optional[float]
    btc_dominance: Optional[float]
    fear_greed_index: Optional[int]
    fear_greed_label: Optional[str]
    total_volume_24h: Optional[float]
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


class AssetPriceResponse(BaseModel):
    ticker: str
    price_usd: Optional[float]
    change_24h: Optional[float]
    change_7d: Optional[float]
    volume_24h: Optional[float]
    market_cap: Optional[float]
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Regime / Intelligence ---

class PublishRegimeRequest(BaseModel):
    regime_name: str
    confidence: float
    description: Optional[str] = None
    trader_action: Optional[str] = None
    expected_outcome: Optional[str] = None
    color: Optional[str] = 'zinc'
    supporting_signals: Optional[List[Dict[str, Any]]] = None
    metrics_snapshot: Optional[Dict[str, Any]] = None
    historical_accuracy: Optional[float] = None
    regime_count: Optional[int] = None
    previous_regime: Optional[str] = None


class RegimeResponse(BaseModel):
    id: int
    regime_name: str
    confidence: float
    description: Optional[str]
    trader_action: Optional[str]
    expected_outcome: Optional[str]
    color: Optional[str]
    supporting_signals: Optional[List[Dict[str, Any]]]
    metrics_snapshot: Optional[Dict[str, Any]]
    historical_accuracy: Optional[float]
    regime_count: Optional[int]
    previous_regime: Optional[str]
    detected_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Metrics Time-Series ---

class MetricDataPoint(BaseModel):
    metric_name: str
    value: float

class PublishMetricsRequest(BaseModel):
    metrics: List[MetricDataPoint]

class MetricHistoryPoint(BaseModel):
    value: float
    captured_at: datetime

    class Config:
        from_attributes = True

class MetricHistoryResponse(BaseModel):
    metric_name: str
    points: List[MetricHistoryPoint]
    count: int

class MetricTrendResponse(BaseModel):
    metric_name: str
    direction: str  # 'increasing', 'decreasing', 'flat'
    change_pct: float
    period_hours: int
    current_value: Optional[float]
    previous_value: Optional[float]


# --- Smart Money ---

class SmartMoneySignalItem(BaseModel):
    signal_type: str
    asset: str
    data: Optional[Dict[str, Any]] = None
    interpretation: Optional[str] = None
    impact: str  # bullish, bearish, neutral
    confidence: str  # high, medium, low
    timestamp: Optional[str] = None

class PublishSmartMoneyRequest(BaseModel):
    signals: List[SmartMoneySignalItem]
    net_sentiment: str
    aggregate_interpretation: Optional[str] = None

class SmartMoneyScanResponse(BaseModel):
    signals: List[SmartMoneySignalItem]
    signal_count: int
    net_sentiment: str
    aggregate_interpretation: Optional[str]
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Correlation Matrix ---

class CorrelationPair(BaseModel):
    metric1: str
    metric2: str
    metric1_key: Optional[str] = None
    metric2_key: Optional[str] = None
    correlation: float
    strength: Optional[str] = None
    note: Optional[str] = None

class PublishCorrelationRequest(BaseModel):
    correlation_matrix: List[List[float]]
    labels: List[str]
    metric_keys: List[str] = []
    strongest_pairs: List[CorrelationPair] = []
    interpretation: Optional[str] = None
    timeframe_hours: int = 24
    data_points: int = 0

class CorrelationResponse(BaseModel):
    id: int
    correlation_matrix: Optional[List[List[float]]]
    labels: Optional[List[str]]
    metric_keys: Optional[List[str]]
    strongest_pairs: Optional[List[Dict[str, Any]]]
    interpretation: Optional[str]
    timeframe_hours: Optional[int]
    data_points: Optional[int]
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Trade Setups ---

class PublishTradeSetupRequest(BaseModel):
    asset: str
    direction: str  # LONG, SHORT
    setup_type: Optional[str] = None
    confidence: float = 0.5
    entry_zones: List[Dict[str, Any]] = []
    stop_loss: Optional[Dict[str, Any]] = None
    take_profits: List[Dict[str, Any]] = []
    reasoning: List[str] = []
    risk_factors: List[str] = []
    position_sizing: Optional[Dict[str, Any]] = None
    regime_at_creation: Optional[str] = None
    generated_at: Optional[str] = None

class TradeSetupResponse(BaseModel):
    id: int
    asset: str
    direction: str
    setup_type: Optional[str]
    confidence: Optional[float]
    entry_zones: Optional[List[Dict[str, Any]]]
    stop_loss: Optional[Dict[str, Any]]
    take_profits: Optional[List[Dict[str, Any]]]
    reasoning: Optional[List[str]]
    risk_factors: Optional[List[str]]
    position_sizing: Optional[Dict[str, Any]]
    regime_at_creation: Optional[str]
    outcome: Optional[str]
    created_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Opportunity Scanner ---

class PublishOpportunityScanRequest(BaseModel):
    opportunities: List[Dict[str, Any]]
    opportunity_count: int = 0
    best_rr: Optional[Dict[str, Any]] = None
    highest_conviction: Optional[Dict[str, Any]] = None
    safest_play: Optional[Dict[str, Any]] = None
    regime: Optional[str] = None
    scanned_at: Optional[str] = None

class OpportunityScanResponse(BaseModel):
    id: int
    opportunities: Optional[List[Dict[str, Any]]]
    opportunity_count: Optional[int]
    best_rr: Optional[Dict[str, Any]]
    highest_conviction: Optional[Dict[str, Any]]
    safest_play: Optional[Dict[str, Any]]
    regime: Optional[str]
    scanned_at: Optional[datetime]

    class Config:
        from_attributes = True
