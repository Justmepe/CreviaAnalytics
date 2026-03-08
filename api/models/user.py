"""
SQLAlchemy models for users, subscriptions, and API usage
"""

import secrets
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from api.database import Base


class ExchangeApiKey(Base):
    __tablename__ = 'exchange_api_keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exchange = Column(String(20), nullable=False)  # 'binance', 'bybit', 'okx'
    label = Column(String(100))  # optional user-defined label
    api_key_enc = Column(String(512), nullable=False)    # encrypted
    api_secret_enc = Column(String(512), nullable=False)  # encrypted
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_exchange_keys_user', 'user_id'),
    )


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255))
    name = Column(String(255))
    avatar_url = Column(String(500))

    # OAuth
    provider = Column(String(50))  # google, twitter, email
    provider_id = Column(String(255))

    # Subscription
    tier = Column(String(20), default='free')  # free, basic, pro (Premium), enterprise (Premium+)
    stripe_customer_id = Column(String(255))
    subscription_status = Column(String(20), default='none')  # active, canceled, past_due, none
    subscription_end = Column(DateTime(timezone=True))

    # API Access
    api_key = Column(String(64), unique=True)
    api_calls_today = Column(Integer, default=0)
    api_calls_month = Column(Integer, default=0)

    # Discord alert webhook
    discord_webhook_url = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def generate_api_key(self):
        self.api_key = secrets.token_hex(32)
        return self.api_key


class ApiUsage(Base):
    __tablename__ = 'api_usage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    endpoint = Column(String(255))
    method = Column(String(10))
    status_code = Column(Integer)
    called_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_api_usage_user', 'user_id', called_at.desc()),
    )


class EmailSubscription(Base):
    __tablename__ = 'email_subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    frequency = Column(String(20), default='daily')  # daily, weekly
    sectors = Column(ARRAY(String(50)))  # ['majors', 'defi'] or NULL for all
    is_active = Column(Boolean, default=True)
    unsubscribe_token = Column(String(64), unique=True, default=lambda: secrets.token_hex(32))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
