"""
SQLAlchemy models for content storage
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from api.database import Base


class ContentPost(Base):
    __tablename__ = 'content_posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String(20), nullable=False, index=True)  # thread, memo, news_tweet, risk_alert
    title = Column(String(500))
    slug = Column(String(500), unique=True, nullable=False, index=True)
    body = Column(Text, nullable=False)
    body_html = Column(Text)
    excerpt = Column(Text)

    # Asset/sector reference
    tickers = Column(ARRAY(String(20)))
    sector = Column(String(50), index=True)  # majors, memecoins, privacy, defi, global

    # Market data snapshot at time of generation
    market_snapshot = Column(JSONB)

    # Access control
    tier = Column(String(20), default='free', index=True)  # free, pro, enterprise
    is_published = Column(Boolean, default=True)

    # Image
    image_url = Column(String(1000))

    # Metadata
    generated_by = Column(String(50), default='claude')
    source_file = Column(String(500))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tweets = relationship('ThreadTweet', back_populates='post', cascade='all, delete-orphan',
                          order_by='ThreadTweet.position')

    __table_args__ = (
        Index('idx_content_published_desc', published_at.desc()),
    )


class ThreadTweet(Base):
    __tablename__ = 'thread_tweets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('content_posts.id', ondelete='CASCADE'), nullable=False)
    position = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship('ContentPost', back_populates='tweets')


class MarketSnapshot(Base):
    __tablename__ = 'market_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    btc_price = Column(Float)
    eth_price = Column(Float)
    total_market_cap = Column(Float)
    btc_dominance = Column(Float)
    fear_greed_index = Column(Integer)
    fear_greed_label = Column(String(30))
    total_volume_24h = Column(Float)
    raw_data = Column(JSONB)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AssetPrice(Base):
    __tablename__ = 'asset_prices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    price_usd = Column(Float)
    change_24h = Column(Float)
    change_7d = Column(Float)
    volume_24h = Column(Float)
    market_cap = Column(Float)
    raw_data = Column(JSONB)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_asset_prices_ticker_time', 'ticker', captured_at.desc()),
    )


class MetricTimeSeries(Base):
    """Stores individual metric data points for historical trend analysis and correlation calculations."""
    __tablename__ = 'metric_timeseries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    metadata_ = Column('metadata', JSONB)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_metric_ts', 'metric_name', 'captured_at'),
    )


class SmartMoneySignal(Base):
    """Stores smart money signals detected by the tracker."""
    __tablename__ = 'smart_money_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_type = Column(String(50), nullable=False, index=True)
    asset = Column(String(10), nullable=False)
    data = Column(JSONB)
    interpretation = Column(Text)
    impact = Column(String(20))  # bullish, bearish, neutral
    confidence = Column(String(20))  # high, medium, low
    net_sentiment = Column(String(30))  # Overall sentiment at scan time
    aggregate_interpretation = Column(Text)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CorrelationSnapshot(Base):
    """Stores correlation matrix snapshots from the correlation engine."""
    __tablename__ = 'correlation_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_matrix = Column(JSONB)         # 2D list of floats
    labels = Column(JSONB)                     # Metric labels
    metric_keys = Column(JSONB)                # Metric internal names
    strongest_pairs = Column(JSONB)            # Top correlated pairs with notes
    interpretation = Column(Text)              # Summary interpretation text
    timeframe_hours = Column(Integer, default=24)
    data_points = Column(Integer)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class RegimeSnapshot(Base):
    """Stores market regime detection results for the intelligence dashboard."""
    __tablename__ = 'regime_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    regime_name = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    description = Column(Text)
    trader_action = Column(Text)
    expected_outcome = Column(Text)
    color = Column(String(20), default='zinc')
    supporting_signals = Column(JSONB)
    metrics_snapshot = Column(JSONB)
    historical_accuracy = Column(Float)
    regime_count = Column(Integer)
    previous_regime = Column(String(50))
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class TradeSetup(Base):
    """Stores AI-generated trade setups from the trade setup generator."""
    __tablename__ = 'trade_setups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # LONG, SHORT
    setup_type = Column(String(100))
    confidence = Column(Float)
    entry_zones = Column(JSONB)       # [{price, type, reason}]
    stop_loss = Column(JSONB)         # {price, reason, distance_pct}
    take_profits = Column(JSONB)      # [{price, percentage, rr, reason}]
    reasoning = Column(JSONB)         # [str]
    risk_factors = Column(JSONB)      # [str]
    position_sizing = Column(JSONB)   # {risk_100, risk_200, risk_500}
    regime_at_creation = Column(String(50))
    outcome = Column(String(20), default='pending')  # pending, hit_tp, hit_sl, invalidated
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_setup_asset_time', 'asset', created_at.desc()),
    )


class OpportunityScan(Base):
    """Stores ranked opportunity scan results."""
    __tablename__ = 'opportunity_scans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunities = Column(JSONB)          # Full ranked list
    opportunity_count = Column(Integer)
    best_rr = Column(JSONB)                # {asset, direction, rr}
    highest_conviction = Column(JSONB)     # {asset, direction, confidence}
    safest_play = Column(JSONB)            # {asset, direction, score}
    regime = Column(String(50))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ContentTracker(Base):
    """Tracks every piece of content generated to prevent duplicates across restarts."""
    __tablename__ = 'content_tracker'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    content_type = Column(String(20), nullable=False, index=True)  # thread, memo, news_tweet
    ticker = Column(String(50), index=True)
    sector = Column(String(50))

    # Channel tracking — what was posted where
    x_tweet_id = Column(String(50))
    x_thread_url = Column(String(500))
    discord_sent = Column(Boolean, default=False)
    web_slug = Column(String(500))
    substack_note_id = Column(String(100))

    # Link back to content_posts if published to web
    content_post_id = Column(Integer, ForeignKey('content_posts.id', ondelete='SET NULL'), nullable=True)

    # Source / debug info
    source_file = Column(String(500))
    body_preview = Column(String(300))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    posted_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_tracker_ticker_type', 'ticker', 'content_type'),
    )
