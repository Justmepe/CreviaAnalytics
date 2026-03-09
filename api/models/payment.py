"""
Payment models — PaymentIntent and SubscriptionRecord

PaymentIntent: 15-min TTL correlation record linking a user to an expected USDC transfer.
SubscriptionRecord: Active subscription state per user (one row per user, upserted on payment).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func

from api.database import Base


class PaymentIntent(Base):
    __tablename__ = 'payment_intents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # What they're buying
    tier = Column(String(20), nullable=False)           # basic / pro / enterprise
    amount_usd_cents = Column(Integer, nullable=False)  # 2000 / 10000 / 20000
    pathway = Column(String(20), nullable=False)        # metamask / nexapay / fiat_bridge / trial

    # Crypto correlation (MetaMask pathway)
    receive_address = Column(String(42))                # Our treasury wallet on Base
    expected_usdc_units = Column(String(30))            # raw USDC units (6 decimals), e.g. "100000000"
    sender_address = Column(String(42))                 # User's wallet — matched against Transfer.from

    # Settlement
    tx_hash = Column(String(66))                        # USDC Transfer tx hash (set on settlement)
    block_number = Column(Integer)

    # NexaPay specific
    nexapay_order_id = Column(String(100))
    nexapay_status = Column(String(50))

    # Status machine: pending → paid | expired | failed
    status = Column(String(20), default='pending', nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Prevent double-settlement of the same on-chain tx
        UniqueConstraint('tx_hash', name='uq_payment_intent_tx_hash'),
        Index('idx_payment_intents_user', 'user_id'),
        Index('idx_payment_intents_status', 'status'),
    )


class SubscriptionRecord(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # One active subscription row per user
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)

    tier = Column(String(20), nullable=False)           # basic / pro / enterprise
    payment_pathway = Column(String(20))                # how they paid last
    tx_hash = Column(String(66))                        # settlement tx for last payment

    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))  # +30 days from paid_at

    # Trial tracking
    is_trial = Column(Boolean, default=False)
    trial_ends_at = Column(DateTime(timezone=True))

    auto_renew = Column(Boolean, default=False)         # manual renewal only for v1
    status = Column(String(20), default='active')       # active / canceled / expired / trial

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_subscriptions_user', 'user_id'),
        Index('idx_subscriptions_status', 'status'),
    )
