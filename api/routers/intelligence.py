"""
Intelligence API router — regime detection, metrics time-series, and market intelligence
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from api.database import get_db
from api.config import WEB_API_SECRET
from api.schemas.content import (
    PublishRegimeRequest, RegimeResponse,
    PublishMetricsRequest, MetricHistoryResponse, MetricHistoryPoint, MetricTrendResponse,
    PublishCorrelationRequest, CorrelationResponse,
    PublishSmartMoneyRequest, SmartMoneyScanResponse, SmartMoneySignalItem,
    PublishTradeSetupRequest, TradeSetupResponse,
    PublishOpportunityScanRequest, OpportunityScanResponse,
)
from api.services.content_service import (
    save_regime_snapshot, get_current_regime, get_regime_history, count_regime_occurrences,
    save_metric_timeseries, get_metric_history, get_metric_trend,
    save_correlation_snapshot, get_latest_correlation,
    save_smart_money_signals, get_smart_money_signals,
    get_latest_snapshot,
    save_trade_setup, get_latest_trade_setups,
    save_opportunity_scan, get_latest_opportunity_scan,
)

router = APIRouter(prefix='/api/intelligence', tags=['intelligence'])


def _verify_internal(x_api_secret: str = Header(None)):
    if x_api_secret != WEB_API_SECRET:
        raise HTTPException(status_code=403, detail='Invalid API secret')


# --- Regime endpoints ---

@router.post('/regime', response_model=RegimeResponse)
def publish_regime(req: PublishRegimeRequest, db: Session = Depends(get_db),
                   _=Depends(_verify_internal)):
    """Store a regime detection result from the Python engine."""
    snapshot = save_regime_snapshot(
        db=db,
        regime_name=req.regime_name,
        confidence=req.confidence,
        description=req.description,
        trader_action=req.trader_action,
        expected_outcome=req.expected_outcome,
        color=req.color,
        supporting_signals=req.supporting_signals,
        metrics_snapshot=req.metrics_snapshot,
        historical_accuracy=req.historical_accuracy,
        regime_count=req.regime_count,
        previous_regime=req.previous_regime,
    )
    return snapshot


@router.get('/regime/current', response_model=Optional[RegimeResponse])
def current_regime(db: Session = Depends(get_db)):
    """Get the most recent regime detection result."""
    regime = get_current_regime(db)
    if not regime:
        raise HTTPException(status_code=404, detail='No regime data available yet')
    return regime


@router.get('/regime/history', response_model=List[RegimeResponse])
def regime_history(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    """Get recent regime detection history."""
    return get_regime_history(db, limit=limit)


# --- Metrics time-series endpoints ---

@router.post('/metrics')
def publish_metrics(req: PublishMetricsRequest, db: Session = Depends(get_db),
                    _=Depends(_verify_internal)):
    """Bulk publish metric data points from the engine each cycle."""
    metrics = [{'metric_name': m.metric_name, 'value': m.value} for m in req.metrics]
    count = save_metric_timeseries(db, metrics)
    return {'saved': count}


@router.get('/metrics/history', response_model=MetricHistoryResponse)
def metrics_history(metric: str = Query(..., description='Metric name'),
                    hours: int = Query(24, le=168, description='Hours to look back'),
                    db: Session = Depends(get_db)):
    """Get historical values for a metric within the last N hours."""
    points = get_metric_history(db, metric, hours)
    return MetricHistoryResponse(
        metric_name=metric,
        points=[MetricHistoryPoint(value=p.value, captured_at=p.captured_at) for p in points],
        count=len(points),
    )


@router.get('/metrics/trend', response_model=MetricTrendResponse)
def metrics_trend(metric: str = Query(..., description='Metric name'),
                  period: int = Query(24, le=168, description='Period in hours'),
                  db: Session = Depends(get_db)):
    """Get trend direction for a metric over the given period."""
    trend = get_metric_trend(db, metric, period)
    return MetricTrendResponse(
        metric_name=metric,
        direction=trend['direction'],
        change_pct=trend['change_pct'],
        period_hours=period,
        current_value=trend['current_value'],
        previous_value=trend['previous_value'],
    )


# --- Correlation matrix endpoints ---

@router.post('/correlations', response_model=CorrelationResponse)
def publish_correlations(req: PublishCorrelationRequest, db: Session = Depends(get_db),
                         _=Depends(_verify_internal)):
    """Store a correlation matrix snapshot from the engine."""
    data = req.model_dump()
    data['period_hours'] = data.pop('timeframe_hours', 24)
    snapshot = save_correlation_snapshot(db, data)
    return snapshot


@router.get('/correlations/latest', response_model=Optional[CorrelationResponse])
def latest_correlations(timeframe: int = Query(24, le=168, description='Timeframe in hours'),
                        db: Session = Depends(get_db)):
    """Get the most recent correlation matrix snapshot."""
    corr = get_latest_correlation(db, timeframe)
    if not corr:
        raise HTTPException(status_code=404, detail='No correlation data available yet')
    return corr


# --- Smart Money endpoints ---

@router.post('/smart-money')
def publish_smart_money(req: PublishSmartMoneyRequest, db: Session = Depends(get_db),
                        _=Depends(_verify_internal)):
    """Store smart money signals from the engine."""
    signals = [s.model_dump() for s in req.signals]
    count = save_smart_money_signals(db, signals, req.net_sentiment, req.aggregate_interpretation)
    return {'saved': count, 'net_sentiment': req.net_sentiment}


@router.get('/smart-money/signals')
def smart_money_signals(window: int = Query(6, le=48, description='Hours to look back'),
                        db: Session = Depends(get_db)):
    """Get recent smart money signals."""
    signals = get_smart_money_signals(db, hours_back=window)
    if not signals:
        return {
            'signals': [],
            'signal_count': 0,
            'net_sentiment': 'NEUTRAL',
            'aggregate_interpretation': 'No signals in the given window.',
        }

    # Build response from latest signals
    signal_items = []
    net_sentiment = 'NEUTRAL'
    interpretation = None
    for s in signals:
        signal_items.append({
            'signal_type': s.signal_type,
            'asset': s.asset,
            'data': s.data,
            'interpretation': s.interpretation,
            'impact': s.impact,
            'confidence': s.confidence,
            'timestamp': s.captured_at.isoformat() if s.captured_at else None,
        })
        if s.net_sentiment:
            net_sentiment = s.net_sentiment
        if s.aggregate_interpretation and not interpretation:
            interpretation = s.aggregate_interpretation

    return {
        'signals': signal_items,
        'signal_count': len(signal_items),
        'net_sentiment': net_sentiment,
        'aggregate_interpretation': interpretation,
    }


# --- Market Context endpoint (for Risk Calculator) ---

@router.get('/market-context')
def market_context(db: Session = Depends(get_db)):
    """Aggregate current market context for the risk calculator.
    Returns regime, funding rates, liquidations, and volatility assessment."""
    regime = get_current_regime(db)
    snapshot = get_latest_snapshot(db)

    # Build context from latest data
    context = {
        'regime': None,
        'funding_rate': None,
        'liquidations_24h': None,
        'volatility': 'normal',
        'fear_greed': None,
    }

    if regime:
        context['regime'] = {
            'name': regime.regime_name,
            'confidence': regime.confidence,
            'color': regime.color,
            'trader_action': regime.trader_action,
        }

    if snapshot:
        context['fear_greed'] = snapshot.fear_greed_index

    # Get latest metrics for funding and liquidations
    for metric_name in ['btc_funding_rate', 'total_liquidations_24h']:
        trend = get_metric_trend(db, metric_name, 24)
        if trend.get('current_value') is not None:
            if metric_name == 'btc_funding_rate':
                context['funding_rate'] = trend['current_value']
            elif metric_name == 'total_liquidations_24h':
                context['liquidations_24h'] = trend['current_value']

    # Assess volatility from liquidations
    liq = context.get('liquidations_24h')
    if liq is not None:
        if liq > 200_000_000:
            context['volatility'] = 'extreme'
        elif liq > 100_000_000:
            context['volatility'] = 'elevated'
        elif liq > 50_000_000:
            context['volatility'] = 'moderate'

    return context


# --- Trade Setup endpoints ---

@router.post('/setups', response_model=TradeSetupResponse)
def publish_trade_setup(req: PublishTradeSetupRequest, db: Session = Depends(get_db),
                        _=Depends(_verify_internal)):
    """Store an AI-generated trade setup from the engine."""
    setup = save_trade_setup(db, req.model_dump())
    return setup


@router.get('/setups/latest', response_model=List[TradeSetupResponse])
def latest_trade_setups(asset: Optional[str] = Query(None, description='Filter by asset ticker'),
                        limit: int = Query(10, le=50, description='Max results'),
                        db: Session = Depends(get_db)):
    """Get the most recent active trade setups."""
    return get_latest_trade_setups(db, asset=asset, limit=limit)


# --- Opportunity Scanner endpoints ---

@router.post('/opportunities', response_model=OpportunityScanResponse)
def publish_opportunities(req: PublishOpportunityScanRequest, db: Session = Depends(get_db),
                          _=Depends(_verify_internal)):
    """Store an opportunity scan result from the engine."""
    scan = save_opportunity_scan(db, req.model_dump())
    return scan


@router.get('/opportunities/latest', response_model=Optional[OpportunityScanResponse])
def latest_opportunities(db: Session = Depends(get_db)):
    """Get the most recent opportunity scan."""
    scan = get_latest_opportunity_scan(db)
    if not scan:
        raise HTTPException(status_code=404, detail='No opportunity scan available yet')
    return scan
