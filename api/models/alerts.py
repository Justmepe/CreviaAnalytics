"""
SQLAlchemy model for price alerts
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from api.database import Base


class PriceAlert(Base):
    __tablename__ = 'price_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    asset = Column(String(20), nullable=False)          # 'BTC', 'ETH', etc.
    alert_type = Column(String(30), nullable=False)     # price_above, price_below, pct_change_up, pct_change_down
    threshold_value = Column(Float, nullable=False)     # price level OR pct threshold
    frequency = Column(String(20), default='once')      # once, daily, always
    status = Column(String(20), default='active')       # active, paused, triggered
    note = Column(String(500))                          # optional user note
    last_triggered = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_price_alerts_user', 'user_id'),
        Index('idx_price_alerts_status', 'status'),
    )
