"""
Admin inbox — queued content tasks from the engine for manual Claude writing
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

from api.database import Base


class AdminInboxItem(Base):
    __tablename__ = 'admin_inbox'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_type = Column(String(50), nullable=False)   # morning_scan, breaking_news, mid_day, closing_bell
    headline = Column(String(300))                   # short description shown in the card
    raw_data = Column(JSON)                          # structured analysis data from engine
    suggested_prompt = Column(Text)                  # pre-filled Claude prompt
    status = Column(String(20), default='pending')   # pending | done | dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
