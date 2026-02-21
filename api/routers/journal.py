"""
Trade Journal API router — CRUD for journal entries + portfolio stats
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from api.database import get_db
from api.middleware.auth import get_current_user
from api.models.user import User
from api.models.journal import JournalEntry
from api.services.journal_service import (
    create_journal_entry,
    get_journal_entries,
    get_journal_entry,
    close_journal_entry,
    delete_journal_entry,
    compute_portfolio_stats,
)

router = APIRouter(prefix='/api/journal', tags=['journal'])


# --- Schemas ---

class CreateEntryRequest(BaseModel):
    asset: str
    direction: str  # LONG, SHORT
    entry_price: float
    quantity: Optional[float] = None
    leverage: float = 1.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    risk_amount: Optional[float] = None
    trade_setup_id: Optional[int] = None
    setup_type: Optional[str] = None
    regime_at_entry: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = []
    entry_time: Optional[datetime] = None

class CloseEntryRequest(BaseModel):
    exit_price: float
    exit_time: Optional[datetime] = None
    notes: Optional[str] = None

class JournalEntryResponse(BaseModel):
    id: int
    asset: str
    direction: str
    entry_price: float
    exit_price: Optional[float]
    quantity: Optional[float]
    leverage: Optional[float]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    risk_amount: Optional[float]
    status: Optional[str]
    outcome: Optional[str]
    pnl_usd: Optional[float]
    pnl_pct: Optional[float]
    rr_achieved: Optional[float]
    setup_type: Optional[str]
    regime_at_entry: Optional[str]
    notes: Optional[str]
    tags: Optional[List[str]]
    trade_setup_id: Optional[int]
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class PortfolioStatsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_usd: float
    avg_rr_achieved: float
    avg_win_usd: float
    avg_loss_usd: float
    profit_factor: float
    max_drawdown_usd: float
    best_trade_usd: float
    worst_trade_usd: float
    active_trades: int


# --- Endpoints ---

@router.post('/entries', response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    req: CreateEntryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Log a new trade entry."""
    entry = create_journal_entry(db, user.id, req.model_dump())
    return entry


@router.get('/entries', response_model=List[JournalEntryResponse])
def list_entries(
    status_filter: Optional[str] = Query(None, alias='status'),
    asset: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the authenticated user's journal entries."""
    return get_journal_entries(db, user.id, status=status_filter, asset=asset, limit=limit, offset=offset)


@router.get('/entries/{entry_id}', response_model=JournalEntryResponse)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific journal entry."""
    entry = get_journal_entry(db, user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail='Entry not found')
    return entry


@router.post('/entries/{entry_id}/close', response_model=JournalEntryResponse)
def close_entry(
    entry_id: int,
    req: CloseEntryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Close a trade and compute final P&L."""
    entry = close_journal_entry(db, user.id, entry_id, req.model_dump())
    if not entry:
        raise HTTPException(status_code=404, detail='Entry not found or already closed')
    return entry


@router.delete('/entries/{entry_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a journal entry."""
    deleted = delete_journal_entry(db, user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Entry not found')


@router.get('/portfolio', response_model=PortfolioStatsResponse)
def portfolio_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get aggregated portfolio statistics for the authenticated user."""
    return compute_portfolio_stats(db, user.id)
