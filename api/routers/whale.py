"""
Whale API Router

REST endpoints for whale intelligence data.
All data is served from the WhaleAnalyzer engine that runs as a background
thread in api/main.py, refreshing every 5 minutes via DataAggregator.

Tier gates:
  pro        → sentiment, cascade-risk, flow-chart
  enterprise → recent transactions (requires ETHERSCAN_API_KEY)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.middleware.auth import require_tier

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/whale', tags=['whale'])

# ---------------------------------------------------------------------------
# Shared engine — set once at FastAPI startup via set_whale_engine()
# ---------------------------------------------------------------------------

_engine = None   # WhaleAnalyzer instance


def set_whale_engine(engine) -> None:
    """Called from api/main.py on_startup to inject the live engine."""
    global _engine
    _engine = engine
    logger.info('WhaleAnalyzer engine registered with router')


def get_whale_engine():
    """Return the live WhaleAnalyzer engine (or None if not yet started)."""
    return _engine


def _get_engine():
    if _engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                'code': 'ENGINE_NOT_READY',
                'message': 'Whale engine is initialising — try again in 30 seconds.',
            },
        )
    return _engine


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SentimentResponse(BaseModel):
    asset: str
    score: float
    label: str
    confidence: int
    key_signal: str
    window_hours: int
    components: Dict[str, Any]
    computed_at: str


class CascadeWarningItem(BaseModel):
    asset: str
    risk_level: str
    confidence: int
    estimated_usd_at_risk: float
    liq_wall_price: Optional[float]
    current_price: Optional[float]
    price_distance_pct: Optional[float]
    direction: str
    key_signals: List[str]
    human_summary: str
    expires_at: str
    created_at: str


class CascadeRiskResponse(BaseModel):
    warnings: List[CascadeWarningItem]
    checked_at: str


class FlowDataPoint(BaseModel):
    timestamp: str
    net_flow_usd: float
    deposit_usd: float
    withdrawal_usd: float
    transaction_count: int


class FlowChartResponse(BaseModel):
    asset: str
    data: List[Dict]
    summary: Dict


class RecentResponse(BaseModel):
    transactions: List[Dict]
    total_usd_moved: float
    generated_at: str
    _note: Optional[str] = None


# ---------------------------------------------------------------------------
# Supported assets & windows
# ---------------------------------------------------------------------------

SUPPORTED_ASSETS = {'BTC', 'ETH', 'SOL'}
VALID_WINDOWS    = {1, 4, 12, 24}


def _assert_asset(asset: str) -> str:
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=404,
            detail={'code': 'ASSET_NOT_FOUND', 'message': f'Unsupported asset: {asset}'},
        )
    return asset


# ---------------------------------------------------------------------------
# GET /api/whale/sentiment/{asset}  — pro
# ---------------------------------------------------------------------------

@router.get('/sentiment/{asset}', response_model=SentimentResponse)
def get_whale_sentiment(
    asset: str,
    window_hours: int = Query(default=4, ge=1, le=24),
    _user=Depends(require_tier('pro')),
):
    asset  = _assert_asset(asset)
    engine = _get_engine()

    sentiment = engine.get_sentiment(asset)
    if sentiment is None:
        # Engine hasn't computed yet — trigger on demand (blocks briefly)
        try:
            engine._refresh_asset(asset)
            sentiment = engine.get_sentiment(asset)
        except Exception as e:
            logger.error('On-demand sentiment refresh failed for %s: %s', asset, e)

    if sentiment is None:
        raise HTTPException(
            status_code=503,
            detail={'code': 'DATA_UNAVAILABLE',
                    'message': 'Sentiment data not yet available — engine is warming up.'},
        )

    return sentiment.to_dict()


# ---------------------------------------------------------------------------
# GET /api/whale/cascade-risk  — pro
# ---------------------------------------------------------------------------

@router.get('/cascade-risk', response_model=CascadeRiskResponse)
def get_cascade_risk(
    asset: str = Query(default='all'),
    _user=Depends(require_tier('pro')),
):
    engine   = _get_engine()
    if asset != 'all':
        asset = _assert_asset(asset)

    warnings = engine.get_cascade_warnings(asset=asset)
    return {
        'warnings': [w.to_dict() for w in warnings],
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /api/whale/flow-chart/{asset}  — pro
# ---------------------------------------------------------------------------

@router.get('/flow-chart/{asset}', response_model=FlowChartResponse)
def get_flow_chart(
    asset: str,
    _user=Depends(require_tier('pro')),
):
    asset  = _assert_asset(asset)
    engine = _get_engine()

    chart = engine.get_flow_chart(asset)
    if chart is None:
        # Return empty chart — will populate after first Glassnode call
        empty_points = [
            {
                'timestamp': (
                    datetime.now(timezone.utc).replace(
                        minute=0, second=0, microsecond=0
                    ).isoformat()
                ),
                'net_flow_usd': 0.0,
                'deposit_usd': 0.0,
                'withdrawal_usd': 0.0,
                'transaction_count': 0,
            }
        ]
        return {
            'asset': asset,
            'data': empty_points,
            'summary': {'net_24h_usd': 0.0, 'bias': 'NEUTRAL', 'largest_single': 0.0},
        }

    return chart


# ---------------------------------------------------------------------------
# GET /api/whale/recent  — enterprise (requires ETHERSCAN_API_KEY)
# ---------------------------------------------------------------------------

@router.get('/recent', response_model=RecentResponse)
def get_recent_transactions(
    limit: int  = Query(default=20, ge=1, le=100),
    chain: str  = Query(default='all'),
    asset: str  = Query(default=None),
    flow_type: str = Query(default='all'),
    _user=Depends(require_tier('enterprise')),
):
    engine = _get_engine()
    result = engine.get_recent_transactions(
        limit=limit, chain=chain, asset=asset, flow_type=flow_type
    )
    return result
