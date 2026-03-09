"""
Payments router — USDC subscription payments on Base L2

Endpoints:
  POST /api/payments/intent               Create MetaMask payment intent
  GET  /api/payments/status/{intent_id}   Poll intent status
  POST /api/payments/verify               Submit tx_hash for on-chain verification
  POST /api/payments/nexapay/create       Create NexaPay card order
  POST /api/payments/nexapay/webhook      NexaPay settlement webhook (HMAC)
  POST /api/payments/trial                Start a free trial
  GET  /api/payments/subscription         Current subscription details
  POST /api/payments/cancel               Cancel auto-renewal
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware.auth import get_current_user
from api.models.payment import PaymentIntent, SubscriptionRecord
from api.models.user import User
from api.services.payment_service import (
    TIER_CONFIG,
    activate_subscription,
    activate_trial,
    create_payment_intent,
    expire_stale_subscriptions,
    verify_nexapay_signature,
    verify_usdc_transfer,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/payments', tags=['payments'])


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class IntentRequest(BaseModel):
    tier: str
    sender_address: Optional[str] = None   # User's wallet (required for MetaMask pathway)


class IntentResponse(BaseModel):
    intent_id: int
    tier: str
    receive_address: str
    expected_usdc_units: str
    amount_usd_cents: int
    expires_at: str
    chain_id: int = 8453                    # Base mainnet


class VerifyRequest(BaseModel):
    intent_id: int
    tx_hash: str


class TrialRequest(BaseModel):
    tier: str


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    is_trial: bool
    current_period_end: Optional[str]
    payment_pathway: Optional[str]


class NexaPayCreateRequest(BaseModel):
    tier: str


class NexaPayCreateResponse(BaseModel):
    intent_id: int
    redirect_url: str
    order_id: str


# ─────────────────────────────────────────────
# MetaMask / direct USDC pathway
# ─────────────────────────────────────────────

@router.post('/intent', response_model=IntentResponse)
async def create_intent(
    req: IntentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a MetaMask payment intent. Returns receive_address + expected USDC amount."""
    if req.tier not in TIER_CONFIG:
        raise HTTPException(status_code=400, detail=f'Unknown tier: {req.tier}. Valid: basic, pro, enterprise')

    receive_wallet = os.getenv('PAYMENT_RECEIVE_WALLET', '')
    if not receive_wallet:
        raise HTTPException(status_code=503, detail='Payment system not configured')

    intent = create_payment_intent(
        db=db,
        user_id=user.id,
        tier=req.tier,
        pathway='metamask',
        sender_address=req.sender_address,
    )

    return IntentResponse(
        intent_id=intent.id,
        tier=intent.tier,
        receive_address=intent.receive_address,
        expected_usdc_units=intent.expected_usdc_units,
        amount_usd_cents=intent.amount_usd_cents,
        expires_at=intent.expires_at.isoformat(),
    )


@router.get('/status/{intent_id}')
async def get_intent_status(
    intent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll payment intent status. Frontend polls every 5s after sending USDC."""
    intent = db.query(PaymentIntent).filter(
        PaymentIntent.id == intent_id,
        PaymentIntent.user_id == user.id,
    ).first()

    if not intent:
        raise HTTPException(status_code=404, detail='Intent not found')

    # Auto-expire check
    if intent.status == 'pending' and datetime.now(timezone.utc) > intent.expires_at:
        intent.status = 'expired'
        db.commit()

    return {
        'intent_id': intent.id,
        'status': intent.status,
        'tier': intent.tier,
        'tx_hash': intent.tx_hash,
        'paid_at': intent.paid_at.isoformat() if intent.paid_at else None,
    }


@router.post('/verify')
async def verify_payment(
    req: VerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a tx_hash for on-chain verification.
    Called by the frontend after MetaMask transaction confirms.
    """
    # Verify ownership
    intent = db.query(PaymentIntent).filter(
        PaymentIntent.id == req.intent_id,
        PaymentIntent.user_id == user.id,
    ).first()
    if not intent:
        raise HTTPException(status_code=404, detail='Intent not found')

    success = verify_usdc_transfer(db, req.intent_id, req.tx_hash)
    if not success:
        raise HTTPException(
            status_code=400,
            detail='Payment verification failed. Check the tx hash and try again.',
        )

    # Return updated user tier
    db.refresh(user)
    return {
        'status': 'paid',
        'tier': intent.tier,
        'tx_hash': req.tx_hash,
        'message': f'Subscription activated: {intent.tier}',
    }


# ─────────────────────────────────────────────
# NexaPay card pathway
# ─────────────────────────────────────────────

@router.post('/nexapay/create', response_model=NexaPayCreateResponse)
async def nexapay_create_order(
    req: NexaPayCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a NexaPay order. Returns redirect_url to hosted payment page.
    NexaPay will call our webhook when USDC settles.
    """
    if req.tier not in TIER_CONFIG:
        raise HTTPException(status_code=400, detail=f'Unknown tier: {req.tier}')

    nexapay_key = os.getenv('NEXAPAY_API_KEY', '')
    nexapay_merchant = os.getenv('NEXAPAY_MERCHANT_ID', '')
    receive_wallet = os.getenv('PAYMENT_RECEIVE_WALLET', '')

    if not nexapay_key:
        raise HTTPException(status_code=503, detail='NexaPay not configured')

    # Create a pending intent first (to get an ID for order reference)
    intent = create_payment_intent(
        db=db,
        user_id=user.id,
        tier=req.tier,
        pathway='nexapay',
    )

    cfg = TIER_CONFIG[req.tier]
    amount_usd = cfg['usd_cents'] / 100  # e.g. 100.00

    # Call NexaPay API
    payload = {
        'merchantId': nexapay_merchant,
        'orderId': str(intent.id),
        'amount': str(amount_usd),
        'currency': 'USD',
        'cryptoCurrency': 'USDC',
        'network': 'base',
        'walletAddress': receive_wallet,
        'redirectUrl': f'{os.getenv("WEB_API_URL", "")}/billing?payment=complete',
        'webhookUrl': f'{os.getenv("WEB_API_URL", "")}/api/payments/nexapay/webhook',
        'metadata': {
            'user_id': user.id,
            'tier': req.tier,
            'intent_id': intent.id,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                'https://api.nexapay.io/v1/orders',
                json=payload,
                headers={'Authorization': f'Bearer {nexapay_key}'},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error('NexaPay order creation failed: %s', e)
        raise HTTPException(status_code=502, detail='NexaPay order creation failed')
    except Exception as e:
        logger.error('NexaPay API error: %s', e)
        raise HTTPException(status_code=502, detail='Payment gateway unavailable')

    # Save NexaPay order reference
    order_id = data.get('orderId', str(intent.id))
    intent.nexapay_order_id = order_id
    db.commit()

    return NexaPayCreateResponse(
        intent_id=intent.id,
        redirect_url=data.get('paymentUrl', ''),
        order_id=order_id,
    )


@router.post('/nexapay/webhook', status_code=200)
async def nexapay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    NexaPay settlement webhook.
    Validates HMAC-SHA256 signature then activates subscription.
    """
    raw_body = await request.body()
    signature = request.headers.get('X-NexaPay-Signature', '')

    if not verify_nexapay_signature(raw_body, signature):
        logger.warning('nexapay_webhook: invalid signature')
        raise HTTPException(status_code=401, detail='Invalid webhook signature')

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON payload')

    event_type = payload.get('event')
    if event_type != 'payment.completed':
        # Acknowledge other events without action
        return {'status': 'ok', 'action': 'ignored'}

    order_id = payload.get('orderId')
    tx_hash = payload.get('txHash')
    nexapay_status = payload.get('status')

    if not order_id or not tx_hash:
        raise HTTPException(status_code=400, detail='Missing orderId or txHash')

    # Find intent by NexaPay order ID or by ID if numeric
    intent = None
    if order_id.isdigit():
        intent = db.query(PaymentIntent).filter(PaymentIntent.id == int(order_id)).first()
    if not intent:
        intent = db.query(PaymentIntent).filter(PaymentIntent.nexapay_order_id == order_id).first()

    if not intent:
        logger.error('nexapay_webhook: intent not found for orderId=%s', order_id)
        raise HTTPException(status_code=404, detail='Intent not found')

    # Idempotency — already processed
    if intent.status == 'paid':
        return {'status': 'ok', 'action': 'already_processed'}

    if intent.status != 'pending':
        return {'status': 'ok', 'action': 'intent_not_pending'}

    # Check tx_hash uniqueness
    duplicate = db.query(PaymentIntent).filter(
        PaymentIntent.tx_hash == tx_hash,
        PaymentIntent.status == 'paid',
    ).first()
    if duplicate:
        logger.warning('nexapay_webhook: duplicate tx_hash %s', tx_hash)
        return {'status': 'ok', 'action': 'duplicate_tx'}

    # Settle
    intent.tx_hash = tx_hash
    intent.nexapay_status = nexapay_status
    intent.status = 'paid'
    intent.paid_at = datetime.now(timezone.utc)
    db.commit()

    activate_subscription(db, intent.user_id, intent.tier, tx_hash, 'nexapay')
    logger.info('nexapay_webhook: activated %s for user %s tx=%s', intent.tier, intent.user_id, tx_hash)

    return {'status': 'ok', 'action': 'activated'}


# ─────────────────────────────────────────────
# Trial pathway
# ─────────────────────────────────────────────

@router.post('/trial')
async def start_trial(
    req: TrialRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a free trial. No payment required. One trial per tier per user."""
    if req.tier not in TIER_CONFIG:
        raise HTTPException(status_code=400, detail=f'Unknown tier: {req.tier}')

    try:
        sub = activate_trial(db, user.id, req.tier)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        'status': 'trial_started',
        'tier': req.tier,
        'trial_ends': sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        'trial_days': TIER_CONFIG[req.tier]['trial_days'],
    }


# ─────────────────────────────────────────────
# Subscription status
# ─────────────────────────────────────────────

@router.get('/subscription', response_model=SubscriptionResponse)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's subscription state."""
    sub = db.query(SubscriptionRecord).filter(SubscriptionRecord.user_id == user.id).first()

    if not sub:
        return SubscriptionResponse(
            tier='free',
            status='none',
            is_trial=False,
            current_period_end=None,
            payment_pathway=None,
        )

    return SubscriptionResponse(
        tier=sub.tier,
        status=sub.status,
        is_trial=sub.is_trial,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        payment_pathway=sub.payment_pathway,
    )


@router.get('/history')
async def get_payment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return recent payment intents for the user."""
    intents = (
        db.query(PaymentIntent)
        .filter(
            PaymentIntent.user_id == user.id,
            PaymentIntent.status == 'paid',
        )
        .order_by(PaymentIntent.paid_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            'id': i.id,
            'tier': i.tier,
            'amount_usd': i.amount_usd_cents / 100,
            'pathway': i.pathway,
            'tx_hash': i.tx_hash,
            'paid_at': i.paid_at.isoformat() if i.paid_at else None,
        }
        for i in intents
    ]


@router.post('/cancel')
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel auto-renewal. Subscription remains active until current_period_end."""
    sub = db.query(SubscriptionRecord).filter(SubscriptionRecord.user_id == user.id).first()
    if not sub or sub.status not in ('active', 'trial'):
        raise HTTPException(status_code=404, detail='No active subscription')

    sub.auto_renew = False
    sub.status = 'canceled'
    user.subscription_status = 'canceled'
    db.commit()

    return {
        'status': 'canceled',
        'active_until': sub.current_period_end.isoformat() if sub.current_period_end else None,
        'message': 'Subscription will not renew. Access continues until period end.',
    }


# ─────────────────────────────────────────────
# Internal: subscription expiry cron
# ─────────────────────────────────────────────

@router.post('/internal/expire', include_in_schema=False)
async def run_expiry(
    request: Request,
    db: Session = Depends(get_db),
):
    """Internal endpoint for cron-triggered subscription expiry. Secret-gated."""
    secret = request.headers.get('X-Api-Secret', '')
    if secret != os.getenv('WEB_API_SECRET', ''):
        raise HTTPException(status_code=401, detail='Unauthorized')

    count = expire_stale_subscriptions(db)
    return {'expired_count': count}
