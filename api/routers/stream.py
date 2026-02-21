"""
Real-time streaming endpoint via Server-Sent Events (SSE)
Pushes live market data, regime changes, and smart money signals to the frontend.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.database import get_db
from api.services.content_service import (
    get_current_regime,
    get_latest_snapshot,
    get_smart_money_signals,
    get_latest_opportunity_scan,
)

router = APIRouter(prefix='/api/stream', tags=['stream'])

PING_INTERVAL = 15  # seconds between keep-alive pings
DATA_INTERVAL = 60  # seconds between data pushes


async def event_generator(db: Session) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events with live market data."""

    async def send_event(event_type: str, data: dict) -> str:
        payload = json.dumps(data, default=str)
        return f"event: {event_type}\ndata: {payload}\n\n"

    # Send initial snapshot immediately
    try:
        snapshot = get_latest_snapshot(db)
        if snapshot:
            yield await send_event('snapshot', {
                'btc_price': snapshot.btc_price,
                'eth_price': snapshot.eth_price,
                'total_market_cap': snapshot.total_market_cap,
                'btc_dominance': snapshot.btc_dominance,
                'fear_greed_index': snapshot.fear_greed_index,
                'fear_greed_label': snapshot.fear_greed_label,
                'captured_at': snapshot.captured_at.isoformat() if snapshot.captured_at else None,
            })
    except Exception:
        pass

    # Send initial regime
    try:
        regime = get_current_regime(db)
        if regime:
            yield await send_event('regime', {
                'regime_name': regime.regime_name,
                'confidence': regime.confidence,
                'description': regime.description,
                'color': regime.color,
            })
    except Exception:
        pass

    tick = 0
    while True:
        await asyncio.sleep(PING_INTERVAL)
        tick += 1

        # Keep-alive ping every PING_INTERVAL seconds
        yield f"event: ping\ndata: {json.dumps({'t': datetime.now(timezone.utc).isoformat()})}\n\n"

        # Full data push every DATA_INTERVAL seconds
        if tick % (DATA_INTERVAL // PING_INTERVAL) == 0:
            try:
                snapshot = get_latest_snapshot(db)
                if snapshot:
                    yield await send_event('snapshot', {
                        'btc_price': snapshot.btc_price,
                        'eth_price': snapshot.eth_price,
                        'total_market_cap': snapshot.total_market_cap,
                        'btc_dominance': snapshot.btc_dominance,
                        'fear_greed_index': snapshot.fear_greed_index,
                        'fear_greed_label': snapshot.fear_greed_label,
                        'captured_at': snapshot.captured_at.isoformat() if snapshot.captured_at else None,
                    })
            except Exception:
                pass

            try:
                regime = get_current_regime(db)
                if regime:
                    yield await send_event('regime', {
                        'regime_name': regime.regime_name,
                        'confidence': regime.confidence,
                        'description': regime.description,
                        'color': regime.color,
                    })
            except Exception:
                pass


@router.get('/market')
async def market_stream(db: Session = Depends(get_db)):
    """
    Server-Sent Events stream for live market data.
    Events: snapshot, regime, ping
    """
    return StreamingResponse(
        event_generator(db),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
