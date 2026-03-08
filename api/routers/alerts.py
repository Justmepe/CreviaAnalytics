"""
Price Alerts API — CRUD + Discord webhook management
"""

from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware.auth import get_current_user
from api.models.alerts import PriceAlert
from api.models.user import User

router = APIRouter(prefix='/api/alerts', tags=['alerts'])

_VALID_TYPES = {'price_above', 'price_below', 'pct_change_up', 'pct_change_down'}
_VALID_FREQ   = {'once', 'daily', 'always'}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateAlertRequest(BaseModel):
    asset: str
    alert_type: str
    threshold_value: float
    frequency: str = 'once'
    note: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    asset: str
    alert_type: str
    threshold_value: float
    frequency: str
    status: str
    note: Optional[str]
    last_triggered: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookSaveRequest(BaseModel):
    webhook_url: str


class WebhookStatusResponse(BaseModel):
    has_webhook: bool
    masked_url: Optional[str]


# ---------------------------------------------------------------------------
# Alert CRUD
# ---------------------------------------------------------------------------

@router.get('', response_model=List[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(PriceAlert)
        .filter(PriceAlert.user_id == user.id)
        .order_by(PriceAlert.created_at.desc())
        .all()
    )


@router.post('', response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    req: CreateAlertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if req.alert_type not in _VALID_TYPES:
        raise HTTPException(400, f'Invalid alert_type. Valid: {_VALID_TYPES}')
    if req.frequency not in _VALID_FREQ:
        raise HTTPException(400, f'Invalid frequency. Valid: {_VALID_FREQ}')

    alert = PriceAlert(
        user_id         = user.id,
        asset           = req.asset.upper().replace('USDT', ''),
        alert_type      = req.alert_type,
        threshold_value = req.threshold_value,
        frequency       = req.frequency,
        note            = req.note,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete('/{alert_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = (
        db.query(PriceAlert)
        .filter(PriceAlert.id == alert_id, PriceAlert.user_id == user.id)
        .first()
    )
    if not alert:
        raise HTTPException(404, 'Alert not found')
    db.delete(alert)
    db.commit()


@router.put('/{alert_id}/toggle', response_model=AlertResponse)
def toggle_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle between active and paused."""
    alert = (
        db.query(PriceAlert)
        .filter(PriceAlert.id == alert_id, PriceAlert.user_id == user.id)
        .first()
    )
    if not alert:
        raise HTTPException(404, 'Alert not found')
    alert.status = 'paused' if alert.status == 'active' else 'active'
    db.commit()
    db.refresh(alert)
    return alert


# ---------------------------------------------------------------------------
# Discord webhook management
# ---------------------------------------------------------------------------

@router.get('/webhook', response_model=WebhookStatusResponse)
def get_webhook(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    u: User = db.query(User).filter(User.id == user.id).first()
    has = bool(u.discord_webhook_url)
    masked = None
    if has:
        url = u.discord_webhook_url
        masked = url[:40] + '...' + url[-8:] if len(url) > 48 else url
    return {'has_webhook': has, 'masked_url': masked}


@router.post('/webhook')
def save_webhook(
    req: WebhookSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if 'discord.com/api/webhooks/' not in req.webhook_url:
        raise HTTPException(400, 'Must be a valid Discord webhook URL')
    u: User = db.query(User).filter(User.id == user.id).first()
    u.discord_webhook_url = req.webhook_url
    db.commit()
    return {'message': 'Webhook saved'}


@router.post('/webhook/test')
async def test_webhook(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    u: User = db.query(User).filter(User.id == user.id).first()
    if not u.discord_webhook_url:
        raise HTTPException(400, 'No webhook URL configured')

    payload = {
        'embeds': [{
            'title': '✅ Webhook Connected',
            'description': (
                'Your Discord webhook is connected to **Crevia Analytics**. '
                "You'll receive alerts here when your conditions are met."
            ),
            'color': 0x00D4AA,
            'footer': {'text': 'Crevia Analytics · creviacockpit.com'},
        }]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(u.discord_webhook_url, json=payload)

    if resp.status_code not in (200, 204):
        raise HTTPException(400, f'Webhook test failed (HTTP {resp.status_code}) — check URL')
    return {'message': 'Test message sent to Discord'}
