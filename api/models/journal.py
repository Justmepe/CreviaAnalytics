"""
SQLAlchemy models for Trade Journal & Portfolio tracking
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from api.database import Base


class JournalEntry(Base):
    """A manually-logged or AI-setup-linked trade."""
    __tablename__ = 'journal_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    trade_setup_id = Column(Integer, ForeignKey('trade_setups.id', ondelete='SET NULL'), nullable=True)

    # Trade details
    asset = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)   # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Float)
    leverage = Column(Float, default=1.0)

    # Risk management
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    risk_amount = Column(Float)                       # In USD

    # Status & outcome
    status = Column(String(20), default='open')       # open, closed, cancelled
    outcome = Column(String(20))                      # win, loss, breakeven
    pnl_usd = Column(Float)
    pnl_pct = Column(Float)
    rr_achieved = Column(Float)                       # Actual R:R achieved

    # Context
    setup_type = Column(String(100))
    regime_at_entry = Column(String(50))
    notes = Column(Text)
    tags = Column(JSONB, default=list)                # ['breakout', 'news_event', ...]
    screenshots = Column(JSONB, default=list)         # URLs

    # Timestamps
    entry_time = Column(DateTime(timezone=True))
    exit_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_journal_user_asset', 'user_id', 'asset'),
        Index('idx_journal_user_status', 'user_id', 'status'),
    )


class PortfolioSnapshot(Base):
    """Daily portfolio performance snapshot for a user."""
    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Overall stats at snapshot time
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float)                          # 0.0 - 1.0
    total_pnl_usd = Column(Float, default=0)
    avg_rr_achieved = Column(Float)
    avg_win_usd = Column(Float)
    avg_loss_usd = Column(Float)
    profit_factor = Column(Float)                     # Gross profit / Gross loss
    max_drawdown_usd = Column(Float)
    best_trade_usd = Column(Float)
    worst_trade_usd = Column(Float)
    active_trades = Column(Integer, default=0)

    snapshotted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
