"""
Journal Service — CRUD + portfolio aggregation for trade journal
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from api.models.journal import JournalEntry, PortfolioSnapshot


# ─── Journal Entries ────────────────────────────────────────────────────────

def create_journal_entry(db: Session, user_id: int, data: dict) -> JournalEntry:
    entry = JournalEntry(
        user_id=user_id,
        trade_setup_id=data.get('trade_setup_id'),
        asset=data.get('asset', ''),
        direction=data.get('direction', 'LONG'),
        entry_price=data.get('entry_price', 0),
        quantity=data.get('quantity'),
        leverage=data.get('leverage', 1.0),
        stop_loss_price=data.get('stop_loss_price'),
        take_profit_price=data.get('take_profit_price'),
        risk_amount=data.get('risk_amount'),
        setup_type=data.get('setup_type'),
        regime_at_entry=data.get('regime_at_entry'),
        notes=data.get('notes'),
        tags=data.get('tags', []),
        entry_time=data.get('entry_time') or datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_journal_entries(
    db: Session,
    user_id: int,
    status: Optional[str] = None,
    asset: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[JournalEntry]:
    query = db.query(JournalEntry).filter(JournalEntry.user_id == user_id)
    if status:
        query = query.filter(JournalEntry.status == status)
    if asset:
        query = query.filter(JournalEntry.asset == asset)
    return (query
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all())


def get_journal_entry(db: Session, user_id: int, entry_id: int) -> Optional[JournalEntry]:
    return (db.query(JournalEntry)
            .filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
            .first())


def close_journal_entry(db: Session, user_id: int, entry_id: int, data: dict) -> Optional[JournalEntry]:
    """Close a trade with exit price and compute P&L."""
    entry = get_journal_entry(db, user_id, entry_id)
    if not entry or entry.status != 'open':
        return None

    exit_price = data.get('exit_price', 0)
    entry.exit_price = exit_price
    entry.status = 'closed'
    entry.exit_time = data.get('exit_time') or datetime.now(timezone.utc)
    entry.notes = data.get('notes', entry.notes)

    # Compute P&L
    if entry.entry_price and exit_price and entry.quantity:
        if entry.direction == 'LONG':
            raw_pnl = (exit_price - entry.entry_price) * entry.quantity * (entry.leverage or 1.0)
        else:
            raw_pnl = (entry.entry_price - exit_price) * entry.quantity * (entry.leverage or 1.0)

        entry.pnl_usd = round(raw_pnl, 2)
        entry.pnl_pct = round((exit_price - entry.entry_price) / entry.entry_price * 100 *
                               (1 if entry.direction == 'LONG' else -1), 2)

        # Outcome
        if entry.pnl_usd > 0:
            entry.outcome = 'win'
        elif entry.pnl_usd < 0:
            entry.outcome = 'loss'
        else:
            entry.outcome = 'breakeven'

        # R/R achieved
        if entry.risk_amount and entry.risk_amount > 0:
            entry.rr_achieved = round(entry.pnl_usd / entry.risk_amount, 2)

    db.commit()
    db.refresh(entry)
    return entry


def delete_journal_entry(db: Session, user_id: int, entry_id: int) -> bool:
    entry = get_journal_entry(db, user_id, entry_id)
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


# ─── Portfolio Aggregation ───────────────────────────────────────────────────

def compute_portfolio_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """Compute live portfolio statistics from all journal entries."""
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user_id).all()

    closed = [e for e in entries if e.status == 'closed']
    open_trades = [e for e in entries if e.status == 'open']

    total = len(closed)
    wins = [e for e in closed if e.outcome == 'win']
    losses = [e for e in closed if e.outcome == 'loss']

    win_rate = len(wins) / total if total > 0 else 0
    total_pnl = sum(e.pnl_usd or 0 for e in closed)

    avg_win = sum(e.pnl_usd for e in wins) / len(wins) if wins else 0
    avg_loss = sum(e.pnl_usd for e in losses) / len(losses) if losses else 0
    gross_profit = sum(e.pnl_usd for e in wins)
    gross_loss = abs(sum(e.pnl_usd for e in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit or 0)

    rr_values = [e.rr_achieved for e in closed if e.rr_achieved is not None]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0

    pnl_values = [e.pnl_usd for e in closed if e.pnl_usd is not None]
    best = max(pnl_values) if pnl_values else 0
    worst = min(pnl_values) if pnl_values else 0

    # Drawdown: maximum peak-to-trough decline in cumulative P&L
    max_drawdown = 0
    if pnl_values:
        cumulative = 0
        peak = 0
        for pnl in pnl_values:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_drawdown:
                max_drawdown = dd

    return {
        'total_trades': total,
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': round(win_rate, 4),
        'total_pnl_usd': round(total_pnl, 2),
        'avg_rr_achieved': round(avg_rr, 2),
        'avg_win_usd': round(avg_win, 2),
        'avg_loss_usd': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown_usd': round(max_drawdown, 2),
        'best_trade_usd': round(best, 2),
        'worst_trade_usd': round(worst, 2),
        'active_trades': len(open_trades),
    }
