"""
Payment service — core logic for intent creation, USDC verification, and subscription activation.

USDC on Base L2:
  Contract: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
  Decimals:  6  →  parseUnits("100", 6) = 100_000_000
  NOTE: transaction.value is always 0 for ERC-20. Verify via Transfer event logs only.

Payment flow:
  1. create_payment_intent()  → returns intent with receive_address + expected_usdc_units
  2. User sends USDC on Base to receive_address
  3. verify_usdc_transfer()   → parses Transfer logs, validates from/to/amount
  4. activate_subscription()  → sets user.tier, upserts SubscriptionRecord
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.models.payment import PaymentIntent, SubscriptionRecord
from api.models.user import User

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

USDC_CONTRACT_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

TIER_CONFIG = {
    'basic':      {'usd_cents': 2000,  'usdc_units': '20000000',   'trial_days': 3},
    'pro':        {'usd_cents': 10000, 'usdc_units': '100000000',  'trial_days': 7},
    'enterprise': {'usd_cents': 20000, 'usdc_units': '200000000',  'trial_days': 14},
}

INTENT_TTL_MINUTES = 15       # Crypto intents expire after 15 minutes
NEXAPAY_TTL_MINUTES = 60      # Card intents have 1-hour window
SUBSCRIPTION_DAYS = 30        # Monthly billing cycle

# Transfer event ABI for web3.py log parsing
TRANSFER_ABI = [{
    'name': 'Transfer',
    'type': 'event',
    'anonymous': False,
    'inputs': [
        {'name': 'from',  'type': 'address', 'indexed': True},
        {'name': 'to',    'type': 'address', 'indexed': True},
        {'name': 'value', 'type': 'uint256', 'indexed': False},
    ],
}]


# ─────────────────────────────────────────────
# Intent creation
# ─────────────────────────────────────────────

def create_payment_intent(
    db: Session,
    user_id: int,
    tier: str,
    pathway: str,
    sender_address: Optional[str] = None,
) -> PaymentIntent:
    """
    Create a new payment intent.
    For MetaMask: requires sender_address, sets receive_address from PAYMENT_RECEIVE_WALLET.
    For NexaPay: sender_address optional; nexapay_order_id set later after API call.
    """
    if tier not in TIER_CONFIG:
        raise ValueError(f'Unknown tier: {tier}')

    cfg = TIER_CONFIG[tier]
    ttl = INTENT_TTL_MINUTES if pathway == 'metamask' else NEXAPAY_TTL_MINUTES

    intent = PaymentIntent(
        user_id=user_id,
        tier=tier,
        amount_usd_cents=cfg['usd_cents'],
        pathway=pathway,
        receive_address=os.getenv('PAYMENT_RECEIVE_WALLET', ''),
        expected_usdc_units=cfg['usdc_units'],
        sender_address=sender_address.lower() if sender_address else None,
        status='pending',
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl),
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return intent


# ─────────────────────────────────────────────
# USDC Transfer verification (Base L2)
# ─────────────────────────────────────────────

def verify_usdc_transfer(db: Session, intent_id: int, tx_hash: str) -> bool:
    """
    Verify a USDC Transfer event on Base L2.

    Rules:
      - intent must be pending and not expired
      - tx_hash must be unique (no double-spend)
      - Transfer.to   == PAYMENT_RECEIVE_WALLET
      - Transfer.from == intent.sender_address  (if provided)
      - Transfer.value >= intent.expected_usdc_units

    Returns True on success and activates the subscription.
    """
    intent = db.query(PaymentIntent).filter(
        PaymentIntent.id == intent_id,
        PaymentIntent.user_id != None,  # noqa: E711
    ).first()

    if not intent:
        logger.warning('verify_usdc_transfer: intent %s not found', intent_id)
        return False

    if intent.status != 'pending':
        logger.warning('verify_usdc_transfer: intent %s already %s', intent_id, intent.status)
        return False

    if datetime.now(timezone.utc) > intent.expires_at:
        intent.status = 'expired'
        db.commit()
        logger.warning('verify_usdc_transfer: intent %s expired', intent_id)
        return False

    # Idempotency: reject duplicate tx_hash
    existing = db.query(PaymentIntent).filter(
        PaymentIntent.tx_hash == tx_hash,
        PaymentIntent.status == 'paid',
    ).first()
    if existing:
        logger.warning('verify_usdc_transfer: tx_hash %s already settled (intent %s)', tx_hash, existing.id)
        return False

    # On-chain verification
    try:
        valid = _check_transfer_on_chain(tx_hash, intent)
    except Exception as e:
        logger.error('verify_usdc_transfer: on-chain check failed: %s', e)
        return False

    if not valid:
        return False

    # Mark paid and activate
    intent.tx_hash = tx_hash
    intent.status = 'paid'
    intent.paid_at = datetime.now(timezone.utc)
    db.commit()

    activate_subscription(db, intent.user_id, intent.tier, tx_hash, intent.pathway)
    return True


def _check_transfer_on_chain(tx_hash: str, intent: PaymentIntent) -> bool:
    """
    Parse USDC Transfer event logs from Base L2 to verify the transfer.
    Uses web3.py — equivalent of Viem's parseEventLogs.
    """
    try:
        from web3 import Web3
    except ImportError:
        logger.error('web3 package not installed. Run: pip install web3')
        return False

    rpc_url = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception as e:
        logger.error('_check_transfer_on_chain: receipt fetch failed: %s', e)
        return False

    if receipt is None or receipt.status != 1:
        logger.warning('_check_transfer_on_chain: tx failed or not found: %s', tx_hash)
        return False

    receive_wallet = os.getenv('PAYMENT_RECEIVE_WALLET', '').lower()
    if not receive_wallet:
        logger.error('_check_transfer_on_chain: PAYMENT_RECEIVE_WALLET not set')
        return False

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(USDC_CONTRACT_BASE),
        abi=TRANSFER_ABI,
    )

    try:
        logs = contract.events.Transfer().process_receipt(receipt)
    except Exception as e:
        logger.error('_check_transfer_on_chain: log parse error: %s', e)
        return False

    expected_amount = int(intent.expected_usdc_units)

    for log in logs:
        to_addr = log['args']['to'].lower()
        from_addr = log['args']['from'].lower()
        value = log['args']['value']

        # Must arrive at our wallet
        if to_addr != receive_wallet:
            continue

        # If we have sender on record, enforce it (MetaMask path)
        if intent.sender_address and from_addr != intent.sender_address.lower():
            continue

        # Allow overpayment, reject underpayment
        if value >= expected_amount:
            logger.info(
                '_check_transfer_on_chain: valid transfer — from=%s amount=%s tx=%s',
                from_addr, value, tx_hash,
            )
            return True

    logger.warning('_check_transfer_on_chain: no matching Transfer log in %s', tx_hash)
    return False


# ─────────────────────────────────────────────
# Subscription activation
# ─────────────────────────────────────────────

def activate_subscription(
    db: Session,
    user_id: int,
    tier: str,
    tx_hash: Optional[str],
    pathway: str,
) -> SubscriptionRecord:
    """
    Upsert a SubscriptionRecord and update User.tier.
    Idempotent: safe to call multiple times for same user.
    """
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=SUBSCRIPTION_DAYS)

    # Upsert subscription record (one row per user)
    sub = db.query(SubscriptionRecord).filter(SubscriptionRecord.user_id == user_id).first()
    if sub:
        sub.tier = tier
        sub.payment_pathway = pathway
        sub.tx_hash = tx_hash
        sub.current_period_start = now
        sub.current_period_end = period_end
        sub.is_trial = False
        sub.status = 'active'
        sub.updated_at = now
    else:
        sub = SubscriptionRecord(
            user_id=user_id,
            tier=tier,
            payment_pathway=pathway,
            tx_hash=tx_hash,
            current_period_start=now,
            current_period_end=period_end,
            is_trial=False,
            status='active',
        )
        db.add(sub)

    # Update user tier
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.tier = tier
        user.subscription_status = 'active'
        user.subscription_end = period_end

    db.commit()
    if sub.id:
        db.refresh(sub)

    logger.info('activate_subscription: user=%s tier=%s pathway=%s', user_id, tier, pathway)
    return sub


# ─────────────────────────────────────────────
# Trial activation
# ─────────────────────────────────────────────

def activate_trial(db: Session, user_id: int, tier: str) -> SubscriptionRecord:
    """
    Start a free trial for a user. No payment required.
    Prevents re-trial: raises ValueError if user has already trialed this tier.
    """
    if tier not in TIER_CONFIG:
        raise ValueError(f'Unknown tier: {tier}')

    trial_days = TIER_CONFIG[tier]['trial_days']
    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=trial_days)

    # Check for existing trial/subscription on this tier
    existing = db.query(SubscriptionRecord).filter(SubscriptionRecord.user_id == user_id).first()
    if existing and existing.tier == tier:
        raise ValueError(f'Already trialed or subscribed to {tier}')

    if existing:
        existing.tier = tier
        existing.payment_pathway = 'trial'
        existing.tx_hash = None
        existing.current_period_start = now
        existing.current_period_end = trial_end
        existing.is_trial = True
        existing.trial_ends_at = trial_end
        existing.status = 'trial'
        sub = existing
    else:
        sub = SubscriptionRecord(
            user_id=user_id,
            tier=tier,
            payment_pathway='trial',
            current_period_start=now,
            current_period_end=trial_end,
            is_trial=True,
            trial_ends_at=trial_end,
            status='trial',
        )
        db.add(sub)

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.tier = tier
        user.subscription_status = 'trial'
        user.subscription_end = trial_end

    db.commit()
    logger.info('activate_trial: user=%s tier=%s days=%s', user_id, tier, trial_days)
    return sub


# ─────────────────────────────────────────────
# NexaPay webhook HMAC validation
# ─────────────────────────────────────────────

def verify_nexapay_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Validate NexaPay webhook signature.
    Expected: HMAC-SHA256(raw_body, NEXAPAY_SECRET) == signature_header
    """
    secret = os.getenv('NEXAPAY_SECRET', '')
    if not secret:
        logger.error('NEXAPAY_SECRET not configured')
        return False

    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.lower())


# ─────────────────────────────────────────────
# Subscription expiry check (called by cron)
# ─────────────────────────────────────────────

def expire_stale_subscriptions(db: Session) -> int:
    """
    Downgrade users whose subscription/trial has ended.
    Returns count of expired subscriptions.
    """
    now = datetime.now(timezone.utc)
    expired = db.query(SubscriptionRecord).filter(
        SubscriptionRecord.status.in_(['active', 'trial']),
        SubscriptionRecord.current_period_end < now,
    ).all()

    count = 0
    for sub in expired:
        sub.status = 'expired'
        user = db.query(User).filter(User.id == sub.user_id).first()
        if user:
            user.tier = 'free'
            user.subscription_status = 'expired'
        count += 1

    if count:
        db.commit()
        logger.info('expire_stale_subscriptions: expired %d subscriptions', count)

    return count
