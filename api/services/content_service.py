"""
Content service — slug generation, tier logic, storage operations
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from api.models.content import ContentPost, ThreadTweet, MarketSnapshot, AssetPrice, RegimeSnapshot, MetricTimeSeries, CorrelationSnapshot, SmartMoneySignal, TradeSetup, OpportunityScan
from api.config import ENTERPRISE_WINDOW, PRO_WINDOW


def _is_price_data_line(line: str) -> bool:
    """Return True if the line looks like a raw price-data dump."""
    l = line.lower()
    if l.startswith('prices:') or l.startswith('price:'):
        return True
    # Pattern: "TICKER: $123.45 | ..." or "TICKER: $123.45,"
    if re.match(r'^[A-Z]{2,6}:\s*\$[\d,]+', line) and ('|' in line or ',' in line):
        return True
    return False


def _extract_title(body: str, ticker: str) -> str:
    """Extract a clean headline from memo/article body, skipping price-dump lines."""
    for line in body.split('\n')[:15]:
        line = line.strip()
        if not line:
            continue
        # Markdown header — strip leading # characters
        if line.startswith('#'):
            cleaned = line.lstrip('#').strip()
            if cleaned and not _is_price_data_line(cleaned):
                return cleaned[:200]
            continue
        # Skip raw price-data lines
        if _is_price_data_line(line):
            continue
        # First meaningful non-price line is the title
        return line[:200]
    return f'{ticker} Market Analysis'


def generate_slug(content_type: str, ticker: str, title: Optional[str] = None) -> str:
    """Generate a URL-friendly slug for a content post."""
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    base = f"{ticker.lower()}-{content_type}-{date_str}"

    if title:
        # Extract first 5 meaningful words from title
        words = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower()).split()
        meaningful = [w for w in words if len(w) > 2][:5]
        if meaningful:
            base += '-' + '-'.join(meaningful)

    # Ensure uniqueness by appending timestamp suffix
    suffix = datetime.now(timezone.utc).strftime('%H%M%S')
    return f"{base}-{suffix}"


def get_content_tier(published_at: datetime) -> str:
    """Determine access tier based on content age."""
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age = now - published_at
    if age > timedelta(seconds=PRO_WINDOW):
        return 'free'
    elif age > timedelta(seconds=ENTERPRISE_WINDOW):
        return 'pro'
    else:
        return 'enterprise'


def create_thread_post(db: Session, tweets: List[str], tweet_count: int,
                       tickers: List[str], sector: str,
                       image_url: Optional[str] = None,
                       market_snapshot: Optional[dict] = None,
                       source_file: Optional[str] = None) -> ContentPost:
    """Store a thread as a ContentPost with associated ThreadTweets."""
    title = tweets[0][:200] if tweets else 'Market Analysis Thread'
    body = '\n\n---\n\n'.join(tweets)
    excerpt = tweets[0][:160] if tweets else ''

    post = ContentPost(
        content_type='thread',
        title=title,
        slug=generate_slug('thread', tickers[0] if tickers else 'crypto', title),
        body=body,
        excerpt=excerpt,
        tickers=tickers,
        sector=sector,
        tier='free',
        image_url=image_url,
        market_snapshot=market_snapshot,
        source_file=source_file,
    )
    db.add(post)
    db.flush()  # Get the post.id

    for i, tweet_text in enumerate(tweets, 1):
        tweet = ThreadTweet(post_id=post.id, position=i, body=tweet_text)
        db.add(tweet)

    db.commit()
    db.refresh(post)
    return post


def create_memo_post(db: Session, ticker: str, body: str,
                     current_price: Optional[float] = None,
                     sector: Optional[str] = None,
                     tickers: Optional[List[str]] = None,
                     image_url: Optional[str] = None,
                     market_snapshot: Optional[dict] = None,
                     source_file: Optional[str] = None) -> ContentPost:
    """Store a market memo as a ContentPost."""
    title = _extract_title(body, ticker)
    excerpt = body[:160].replace('\n', ' ')

    # Determine sector from ticker if not provided
    if not sector:
        sector_map = {
            # Majors (large-caps)
            'BTC': 'majors', 'ETH': 'majors', 'XRP': 'majors', 'SOL': 'majors',
            'BNB': 'majors', 'AVAX': 'majors', 'SUI': 'majors', 'LINK': 'majors',
            # Memecoins
            'DOGE': 'memecoins', 'SHIB': 'memecoins', 'PEPE': 'memecoins', 'FLOKI': 'memecoins',
            # Privacy
            'XMR': 'privacy', 'ZEC': 'privacy', 'DASH': 'privacy', 'SCRT': 'privacy',
            # DeFi
            'AAVE': 'defi', 'UNI': 'defi', 'CRV': 'defi', 'LDO': 'defi',
            # Commodities / tokenized stocks
            'XAU': 'commodities', 'TSLA': 'commodities',
        }
        sector = sector_map.get(ticker, 'global')

    snapshot = market_snapshot or {}
    if current_price is not None:
        snapshot['price_at_generation'] = current_price

    post = ContentPost(
        content_type='memo',
        title=title,
        slug=generate_slug('memo', ticker, title),
        body=body,
        excerpt=excerpt,
        tickers=tickers or [ticker],
        sector=sector,
        tier='free',
        image_url=image_url,
        market_snapshot=snapshot,
        source_file=source_file,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def create_article_post(db: Session, title: str, body: str,
                        sector: str = 'global',
                        tickers: Optional[List[str]] = None,
                        image_url: Optional[str] = None,
                        market_snapshot: Optional[dict] = None,
                        source_file: Optional[str] = None) -> ContentPost:
    """Store a long-form newsletter article as a ContentPost (content_type='article')."""
    excerpt = body[:200].replace('\n', ' ').strip()
    post = ContentPost(
        content_type='article',
        title=title[:200],
        slug=generate_slug('article', tickers[0] if tickers else 'market', title),
        body=body,
        excerpt=excerpt,
        tickers=tickers or ['BTC', 'ETH'],
        sector=sector,
        tier='enterprise',  # First hour: Enterprise only
        image_url=image_url,
        market_snapshot=market_snapshot,
        source_file=source_file,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def create_news_tweet_post(db: Session, ticker: str, body: str,
                           current_price: Optional[float] = None,
                           sector: Optional[str] = None,
                           tickers: Optional[List[str]] = None) -> ContentPost:
    """Store a news tweet as a ContentPost."""
    title = body[:200]
    excerpt = body[:160]

    if not sector:
        sector_map = {
            # Majors (large-caps)
            'BTC': 'majors', 'ETH': 'majors', 'XRP': 'majors', 'SOL': 'majors',
            'BNB': 'majors', 'AVAX': 'majors', 'SUI': 'majors', 'LINK': 'majors',
            # Memecoins
            'DOGE': 'memecoins', 'SHIB': 'memecoins', 'PEPE': 'memecoins', 'FLOKI': 'memecoins',
            # Privacy
            'XMR': 'privacy', 'ZEC': 'privacy', 'DASH': 'privacy', 'SCRT': 'privacy',
            # DeFi
            'AAVE': 'defi', 'UNI': 'defi', 'CRV': 'defi', 'LDO': 'defi',
            # Commodities / tokenized stocks
            'XAU': 'commodities', 'TSLA': 'commodities',
        }
        sector = sector_map.get(ticker, 'global')

    snapshot = {}
    if current_price is not None:
        snapshot['price_at_generation'] = current_price

    post = ContentPost(
        content_type='news_tweet',
        title=title,
        slug=generate_slug('news', ticker, title),
        body=body,
        excerpt=excerpt,
        tickers=tickers or [ticker],
        sector=sector,
        tier='free',
        market_snapshot=snapshot if snapshot else None,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def save_market_snapshot(db: Session, btc_price: float = None, eth_price: float = None,
                         total_market_cap: float = None, btc_dominance: float = None,
                         fear_greed_index: int = None, fear_greed_label: str = None,
                         total_volume_24h: float = None,
                         raw_data: dict = None) -> MarketSnapshot:
    """Store a market snapshot for the dashboard."""
    snapshot = MarketSnapshot(
        btc_price=btc_price,
        eth_price=eth_price,
        total_market_cap=total_market_cap,
        btc_dominance=btc_dominance,
        fear_greed_index=fear_greed_index,
        fear_greed_label=fear_greed_label,
        total_volume_24h=total_volume_24h,
        raw_data=raw_data,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_asset_price(db: Session, ticker: str, price_usd: float,
                     change_24h: float = None, change_7d: float = None,
                     volume_24h: float = None, market_cap: float = None,
                     raw_data: dict = None) -> AssetPrice:
    """Store an asset price point."""
    price = AssetPrice(
        ticker=ticker,
        price_usd=price_usd,
        change_24h=change_24h,
        change_7d=change_7d,
        volume_24h=volume_24h,
        market_cap=market_cap,
        raw_data=raw_data,
    )
    db.add(price)
    db.commit()
    db.refresh(price)
    return price


def get_content_feed(db: Session, content_type: Optional[str] = None,
                     sector: Optional[str] = None, ticker: Optional[str] = None,
                     page: int = 1, page_size: int = 20):
    """Get paginated content feed with optional filters."""
    query = (db.query(ContentPost)
               .filter(ContentPost.is_published == True)
               # Never surface error posts — engine failures must not reach the feed
               .filter(~ContentPost.title.ilike('Error%'))
               .filter(~ContentPost.title.ilike('Error generating%')))

    if content_type:
        query = query.filter(ContentPost.content_type == content_type)
    if sector:
        query = query.filter(ContentPost.sector == sector)
    if ticker:
        query = query.filter(ContentPost.tickers.any(ticker))

    total = query.count()
    items = (query
             .order_by(ContentPost.published_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all())

    return items, total


def get_content_by_slug(db: Session, slug: str) -> Optional[ContentPost]:
    """Get a single content post by its slug. Returns None for error posts."""
    post = db.query(ContentPost).filter(ContentPost.slug == slug).first()
    if post and post.title and post.title.lower().startswith('error'):
        return None
    return post


def get_latest_snapshot(db: Session) -> Optional[MarketSnapshot]:
    """Get the most recent market snapshot."""
    return (db.query(MarketSnapshot)
            .order_by(MarketSnapshot.captured_at.desc())
            .first())


def save_regime_snapshot(db: Session, regime_name: str, confidence: float,
                         description: str = None, trader_action: str = None,
                         expected_outcome: str = None, color: str = 'zinc',
                         supporting_signals: list = None,
                         metrics_snapshot: dict = None,
                         historical_accuracy: float = None,
                         regime_count: int = None,
                         previous_regime: str = None) -> RegimeSnapshot:
    """Store a regime detection result."""
    snapshot = RegimeSnapshot(
        regime_name=regime_name,
        confidence=confidence,
        description=description,
        trader_action=trader_action,
        expected_outcome=expected_outcome,
        color=color,
        supporting_signals=supporting_signals,
        metrics_snapshot=metrics_snapshot,
        historical_accuracy=historical_accuracy,
        regime_count=regime_count,
        previous_regime=previous_regime,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_current_regime(db: Session) -> Optional[RegimeSnapshot]:
    """Get the most recent regime snapshot."""
    return (db.query(RegimeSnapshot)
            .order_by(RegimeSnapshot.detected_at.desc())
            .first())


def get_latest_prices(db: Session, tickers: Optional[List[str]] = None):
    """Get the latest price for each tracked asset."""
    from sqlalchemy import func as sa_func, distinct

    subq = (db.query(
                AssetPrice.ticker,
                sa_func.max(AssetPrice.captured_at).label('latest')
            )
            .group_by(AssetPrice.ticker))

    if tickers:
        subq = subq.filter(AssetPrice.ticker.in_(tickers))

    subq = subq.subquery()

    return (db.query(AssetPrice)
            .join(subq, (AssetPrice.ticker == subq.c.ticker) &
                        (AssetPrice.captured_at == subq.c.latest))
            .all())


# --- Metric Time-Series ---

def save_metric_timeseries(db: Session, metrics: list) -> int:
    """Bulk insert metric data points. Each item: {'metric_name': str, 'value': float}.
    Returns the number of points saved."""
    objects = []
    for m in metrics:
        if m.get('value') is not None:
            objects.append(MetricTimeSeries(
                metric_name=m['metric_name'],
                value=float(m['value']),
            ))
    if objects:
        db.bulk_save_objects(objects)
        db.commit()
    return len(objects)


def get_metric_history(db: Session, metric_name: str, hours_back: int = 24) -> list:
    """Get historical values for a metric within the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    return (db.query(MetricTimeSeries)
            .filter(MetricTimeSeries.metric_name == metric_name,
                    MetricTimeSeries.captured_at >= cutoff)
            .order_by(MetricTimeSeries.captured_at.asc())
            .all())


def get_metric_trend(db: Session, metric_name: str, period_hours: int = 24) -> dict:
    """Calculate trend direction for a metric over the given period.
    Returns: {'direction': 'increasing'|'decreasing'|'flat', 'change_pct': float,
              'current_value': float|None, 'previous_value': float|None}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)

    # Get the latest value
    latest = (db.query(MetricTimeSeries)
              .filter(MetricTimeSeries.metric_name == metric_name)
              .order_by(MetricTimeSeries.captured_at.desc())
              .first())

    # Get the earliest value in the period
    earliest = (db.query(MetricTimeSeries)
                .filter(MetricTimeSeries.metric_name == metric_name,
                        MetricTimeSeries.captured_at >= cutoff)
                .order_by(MetricTimeSeries.captured_at.asc())
                .first())

    if not latest or not earliest or earliest.value == 0:
        return {
            'direction': 'flat',
            'change_pct': 0.0,
            'current_value': latest.value if latest else None,
            'previous_value': earliest.value if earliest else None,
        }

    change_pct = ((latest.value - earliest.value) / abs(earliest.value)) * 100

    if change_pct > 2.0:
        direction = 'increasing'
    elif change_pct < -2.0:
        direction = 'decreasing'
    else:
        direction = 'flat'

    return {
        'direction': direction,
        'change_pct': round(change_pct, 2),
        'current_value': latest.value,
        'previous_value': earliest.value,
    }


def get_regime_history(db: Session, limit: int = 20) -> list:
    """Get recent regime snapshots for history tracking."""
    return (db.query(RegimeSnapshot)
            .order_by(RegimeSnapshot.detected_at.desc())
            .limit(limit)
            .all())


def count_regime_occurrences(db: Session, regime_name: str) -> int:
    """Count how many times a specific regime has been detected."""
    return db.query(RegimeSnapshot).filter(RegimeSnapshot.regime_name == regime_name).count()


# --- Correlation Matrix ---

def save_correlation_snapshot(db: Session, correlation_data: dict) -> CorrelationSnapshot:
    """Store a correlation matrix snapshot."""
    snapshot = CorrelationSnapshot(
        correlation_matrix=correlation_data.get('matrix'),
        labels=correlation_data.get('labels'),
        metric_keys=correlation_data.get('metric_keys'),
        strongest_pairs=correlation_data.get('strongest_pairs'),
        interpretation=correlation_data.get('interpretation'),
        timeframe_hours=correlation_data.get('period_hours', 24),
        data_points=correlation_data.get('data_points', 0),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_latest_correlation(db: Session, timeframe_hours: int = 24) -> Optional[CorrelationSnapshot]:
    """Get the most recent correlation snapshot for a given timeframe."""
    query = db.query(CorrelationSnapshot)
    if timeframe_hours:
        query = query.filter(CorrelationSnapshot.timeframe_hours == timeframe_hours)
    return query.order_by(CorrelationSnapshot.captured_at.desc()).first()


# --- Smart Money Signals ---

def save_smart_money_signals(db: Session, signals: list, net_sentiment: str,
                              aggregate_interpretation: str = None) -> int:
    """Bulk insert smart money signals. Returns count saved."""
    objects = []
    for s in signals:
        objects.append(SmartMoneySignal(
            signal_type=s.get('signal_type', ''),
            asset=s.get('asset', ''),
            data=s.get('data'),
            interpretation=s.get('interpretation'),
            impact=s.get('impact', 'neutral'),
            confidence=s.get('confidence', 'low'),
            net_sentiment=net_sentiment,
            aggregate_interpretation=aggregate_interpretation,
        ))
    if objects:
        db.bulk_save_objects(objects)
        db.commit()
    return len(objects)


def get_smart_money_signals(db: Session, hours_back: int = 6, limit: int = 20) -> list:
    """Get recent smart money signals within the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    return (db.query(SmartMoneySignal)
            .filter(SmartMoneySignal.captured_at >= cutoff)
            .order_by(SmartMoneySignal.captured_at.desc())
            .limit(limit)
            .all())


# --- Trade Setups ---

def save_trade_setup(db: Session, setup_data: dict) -> TradeSetup:
    """Store a trade setup generated by the AI engine."""
    setup = TradeSetup(
        asset=setup_data.get('asset', ''),
        direction=setup_data.get('direction', 'LONG'),
        setup_type=setup_data.get('setup_type'),
        confidence=setup_data.get('confidence'),
        entry_zones=setup_data.get('entry_zones'),
        stop_loss=setup_data.get('stop_loss'),
        take_profits=setup_data.get('take_profits'),
        reasoning=setup_data.get('reasoning'),
        risk_factors=setup_data.get('risk_factors'),
        position_sizing=setup_data.get('position_sizing'),
        regime_at_creation=setup_data.get('regime_at_creation'),
    )
    db.add(setup)
    db.commit()
    db.refresh(setup)
    return setup


def get_latest_trade_setups(db: Session, asset: Optional[str] = None,
                             limit: int = 10) -> list:
    """Get recent trade setups, optionally filtered by asset."""
    query = db.query(TradeSetup).filter(TradeSetup.outcome == 'pending')
    if asset:
        query = query.filter(TradeSetup.asset == asset)
    return (query
            .order_by(TradeSetup.created_at.desc())
            .limit(limit)
            .all())


def get_trade_setup_by_id(db: Session, setup_id: int) -> Optional[TradeSetup]:
    """Get a specific trade setup by ID."""
    return db.query(TradeSetup).filter(TradeSetup.id == setup_id).first()


# --- Opportunity Scans ---

def save_opportunity_scan(db: Session, scan_data: dict) -> OpportunityScan:
    """Store an opportunity scan result."""
    scan = OpportunityScan(
        opportunities=scan_data.get('opportunities'),
        opportunity_count=scan_data.get('opportunity_count', 0),
        best_rr=scan_data.get('best_rr'),
        highest_conviction=scan_data.get('highest_conviction'),
        safest_play=scan_data.get('safest_play'),
        regime=scan_data.get('regime'),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def get_latest_opportunity_scan(db: Session) -> Optional[OpportunityScan]:
    """Get the most recent opportunity scan."""
    return (db.query(OpportunityScan)
            .order_by(OpportunityScan.scanned_at.desc())
            .first())
