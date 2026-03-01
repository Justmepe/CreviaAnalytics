"""
Market data API router — snapshots and asset prices
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List
import httpx

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


_SYMBOL_MAP = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'SOL': 'SOLUSDT',
    'XMR': 'XMRUSDT',
    'BNB': 'BNBUSDT',
    'AAVE': 'AAVEUSDT',
    'DOGE': 'DOGEUSDT',
    'UNI': 'UNIUSDT',
}

@router.get('/klines')
def get_klines(
    symbol: str = Query('BTCUSDT', description='Binance pair, e.g. BTCUSDT or BTC'),
    interval: str = Query('4h', description='Binance interval: 1h, 4h, 1d, 1w'),
    limit: int = Query(100, ge=10, le=500),
):
    """Proxy Binance klines (OHLCV) for chart rendering. symbol accepts ticker (BTC) or pair (BTCUSDT)."""
    pair = _SYMBOL_MAP.get(symbol.upper(), symbol.upper())
    url = f'https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit={limit}'
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(url)
            r.raise_for_status()
            raw = r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Binance klines unavailable: {exc}')

    # Binance kline: [open_time_ms, open, high, low, close, volume, ...]
    candles = [
        {
            'time': int(k[0] // 1000),  # Unix seconds (LWC expects this)
            'open':   float(k[1]),
            'high':   float(k[2]),
            'low':    float(k[3]),
            'close':  float(k[4]),
            'volume': float(k[5]),
        }
        for k in raw
    ]
    return candles
