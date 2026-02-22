"""
Portfolio router — exchange API key management and portfolio sync.
API keys are symmetrically encrypted at rest using the JWT_SECRET-derived Fernet key.
"""

import base64
import hashlib
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.config import JWT_SECRET
from api.database import get_db
from api.middleware.auth import get_current_user
from api.models.user import User, ExchangeApiKey
from api.services.exchange_client import (
    fetch_binance_portfolio,
    fetch_bybit_portfolio,
    enrich_with_usd_values,
)

router = APIRouter(prefix='/api/portfolio', tags=['portfolio'])

# --- Encryption helpers ---

def _fernet() -> Fernet:
    """Derive a Fernet key from JWT_SECRET (deterministic, no extra env var)."""
    raw = hashlib.sha256(JWT_SECRET.encode()).digest()  # 32 bytes
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise HTTPException(status_code=500, detail="Failed to decrypt exchange key")


# --- Schemas ---

class AddKeyRequest(BaseModel):
    exchange: str          # 'binance' | 'bybit' | 'okx'
    api_key: str
    api_secret: str
    label: Optional[str] = None


class ExchangeKeyResponse(BaseModel):
    id: int
    exchange: str
    label: Optional[str]
    api_key_masked: str    # show only first 6 + last 4 chars
    is_active: bool
    last_synced: Optional[str]
    created_at: str


class PortfolioHolding(BaseModel):
    asset: str
    free: float
    locked: float
    total: float
    price_usd: float
    usd_value: float


class PortfolioSummary(BaseModel):
    exchange: str
    key_id: int
    label: Optional[str]
    total_usd: float
    holdings: list[PortfolioHolding]
    synced_at: str
    error: Optional[str] = None


# --- Helper ---

def _mask(key: str) -> str:
    if len(key) <= 10:
        return "****"
    return key[:6] + "..." + key[-4:]


def _to_response(k: ExchangeApiKey) -> ExchangeKeyResponse:
    raw_key = decrypt(k.api_key_enc)
    return ExchangeKeyResponse(
        id=k.id,
        exchange=k.exchange,
        label=k.label,
        api_key_masked=_mask(raw_key),
        is_active=k.is_active,
        last_synced=k.last_synced.isoformat() if k.last_synced else None,
        created_at=k.created_at.isoformat() if k.created_at else "",
    )


# --- Endpoints ---

@router.get('/keys', response_model=list[ExchangeKeyResponse])
def list_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all exchange API keys saved by the current user (secrets never returned)."""
    keys = db.query(ExchangeApiKey).filter(
        ExchangeApiKey.user_id == user.id,
        ExchangeApiKey.is_active == True,
    ).order_by(ExchangeApiKey.created_at.desc()).all()
    return [_to_response(k) for k in keys]


@router.post('/keys', response_model=ExchangeKeyResponse, status_code=201)
def add_key(
    req: AddKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a new exchange API key pair (encrypted at rest)."""
    SUPPORTED = {"binance", "bybit", "okx"}
    if req.exchange.lower() not in SUPPORTED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Exchange must be one of: {', '.join(SUPPORTED)}",
        )

    # Prevent duplicate exchange entries per user
    existing = db.query(ExchangeApiKey).filter(
        ExchangeApiKey.user_id == user.id,
        ExchangeApiKey.exchange == req.exchange.lower(),
        ExchangeApiKey.is_active == True,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have an active {req.exchange} key. Delete it first.",
        )

    key = ExchangeApiKey(
        user_id=user.id,
        exchange=req.exchange.lower(),
        label=req.label,
        api_key_enc=encrypt(req.api_key.strip()),
        api_secret_enc=encrypt(req.api_secret.strip()),
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return _to_response(key)


@router.delete('/keys/{key_id}', status_code=204)
def delete_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an exchange API key (marks inactive, does not delete row)."""
    key = db.query(ExchangeApiKey).filter(
        ExchangeApiKey.id == key_id,
        ExchangeApiKey.user_id == user.id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    db.commit()


@router.get('/sync', response_model=list[PortfolioSummary])
async def sync_portfolio(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch live portfolio balances from all connected exchanges.
    Returns enriched balances with USD values.
    """
    keys = db.query(ExchangeApiKey).filter(
        ExchangeApiKey.user_id == user.id,
        ExchangeApiKey.is_active == True,
    ).all()

    if not keys:
        return []

    results: list[PortfolioSummary] = []

    for key in keys:
        api_key = decrypt(key.api_key_enc)
        api_secret = decrypt(key.api_secret_enc)
        now = datetime.now(timezone.utc)

        try:
            if key.exchange == "binance":
                raw = await fetch_binance_portfolio(api_key, api_secret)
            elif key.exchange == "bybit":
                raw = await fetch_bybit_portfolio(api_key, api_secret)
            else:
                results.append(PortfolioSummary(
                    exchange=key.exchange,
                    key_id=key.id,
                    label=key.label,
                    total_usd=0,
                    holdings=[],
                    synced_at=now.isoformat(),
                    error=f"Exchange '{key.exchange}' sync not yet implemented",
                ))
                continue

            enriched = await enrich_with_usd_values(raw)
            total_usd = sum(h["usd_value"] for h in enriched)

            holdings = [
                PortfolioHolding(
                    asset=h["asset"],
                    free=h["free"],
                    locked=h["locked"],
                    total=h["total"],
                    price_usd=h["price_usd"],
                    usd_value=h["usd_value"],
                )
                for h in enriched
            ]

            # Update last_synced timestamp
            key.last_synced = now
            db.commit()

            results.append(PortfolioSummary(
                exchange=key.exchange,
                key_id=key.id,
                label=key.label,
                total_usd=round(total_usd, 2),
                holdings=holdings,
                synced_at=now.isoformat(),
            ))

        except Exception as e:
            results.append(PortfolioSummary(
                exchange=key.exchange,
                key_id=key.id,
                label=key.label,
                total_usd=0,
                holdings=[],
                synced_at=now.isoformat(),
                error=str(e),
            ))

    return results
