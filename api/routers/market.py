"""
Market data API router — snapshots and asset prices
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from api.database import get_db
from api.config import WEB_API_SECRET
from api.schemas.content import (
    PublishMarketSnapshotRequest, PublishAssetPriceRequest,
    MarketSnapshotResponse, AssetPriceResponse,
)
from api.services.content_service import (
    save_market_snapshot, save_asset_price,
    get_latest_snapshot, get_latest_prices,
)

router = APIRouter(prefix='/api/market', tags=['market'])


def _verify_internal(x_api_secret: str = Header(None)):
    if x_api_secret != WEB_API_SECRET:
        raise HTTPException(status_code=403, detail='Invalid API secret')


# --- Publish endpoints (engine → API) ---

@router.post('/snapshot', response_model=MarketSnapshotResponse)
def publish_snapshot(req: PublishMarketSnapshotRequest, db: Session = Depends(get_db),
                     _=Depends(_verify_internal)):
    snapshot = save_market_snapshot(
        db=db,
        btc_price=req.btc_price,
        eth_price=req.eth_price,
        total_market_cap=req.total_market_cap,
        btc_dominance=req.btc_dominance,
        fear_greed_index=req.fear_greed_index,
        fear_greed_label=req.fear_greed_label,
        total_volume_24h=req.total_volume_24h,
        raw_data=req.raw_data,
    )
    return snapshot


@router.post('/price', response_model=AssetPriceResponse)
def publish_price(req: PublishAssetPriceRequest, db: Session = Depends(get_db),
                  _=Depends(_verify_internal)):
    price = save_asset_price(
        db=db,
        ticker=req.ticker,
        price_usd=req.price_usd,
        change_24h=req.change_24h,
        change_7d=req.change_7d,
        volume_24h=req.volume_24h,
        market_cap=req.market_cap,
        raw_data=req.raw_data,
    )
    return price


# --- Read endpoints (frontend → API) ---

@router.get('/snapshot/latest', response_model=Optional[MarketSnapshotResponse])
def latest_snapshot(db: Session = Depends(get_db)):
    snapshot = get_latest_snapshot(db)
    if not snapshot:
        raise HTTPException(status_code=404, detail='No market snapshots available')
    return snapshot


@router.get('/prices', response_model=List[AssetPriceResponse])
def latest_prices(
    tickers: Optional[str] = Query(None, description='Comma-separated tickers: BTC,ETH,SOL'),
    db: Session = Depends(get_db),
):
    ticker_list = tickers.split(',') if tickers else None
    prices = get_latest_prices(db, ticker_list)
    return prices
