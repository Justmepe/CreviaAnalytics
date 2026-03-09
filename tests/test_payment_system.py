#!/usr/bin/env python3
"""
tests/test_payment_system.py

Verifies the payment system built on 2026-03-10:

  1.  create_payment_intent — correct fields, TTL, and tier config
  2.  create_payment_intent — unknown tier raises ValueError
  3.  _check_transfer_on_chain — valid Transfer event accepted
  4.  _check_transfer_on_chain — wrong recipient rejected
  5.  _check_transfer_on_chain — wrong sender rejected (MetaMask path)
  6.  _check_transfer_on_chain — underpayment rejected
  7.  _check_transfer_on_chain — overpayment accepted
  8.  verify_usdc_transfer — expired intent rejected
  9.  verify_usdc_transfer — duplicate tx_hash rejected
  10. verify_usdc_transfer — valid flow sets status=paid + activates subscription
  11. activate_subscription — user.tier updated + SubscriptionRecord upserted
  12. activate_subscription — idempotent re-activation
  13. activate_trial — creates trial subscription
  14. activate_trial — re-trial on same tier blocked
  15. expire_stale_subscriptions — downgrades expired users to free
  16. verify_nexapay_signature — valid HMAC accepted
  17. verify_nexapay_signature — tampered body rejected
  18. verify_nexapay_signature — missing secret falls back to False
  19. API: POST /api/payments/intent — requires auth
  20. API: POST /api/payments/trial — creates trial, updates user tier
  21. API: POST /api/payments/nexapay/webhook — valid webhook activates subscription
  22. API: POST /api/payments/nexapay/webhook — invalid signature returns 401
  23. API: GET /api/payments/subscription — returns correct subscription state

Run from project root:
    python tests/test_payment_system.py

All external dependencies (DB, web3, httpx, NexaPay API) are mocked.
"""

import sys
import os
import hashlib
import hmac as hmac_lib
import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

# ── project root on path ───────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "  ✅ PASS"
FAIL = "  ❌ FAIL"
SKIP = "  ⚠️  SKIP"
results = []


def record(name, passed, detail=""):
    icon = PASS if passed else FAIL
    print(f"{icon}  {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, passed))


def _make_db(intent=None, user=None, sub=None):
    """Build a minimal SQLAlchemy session mock."""
    db = MagicMock()
    query_chain = MagicMock()

    # Configurable returns per model
    _returns = {
        'intent': intent,
        'user': user,
        'sub': sub,
    }

    def _query(model):
        chain = MagicMock()
        name = getattr(model, '__name__', '') if hasattr(model, '__name__') else str(model)
        chain.filter.return_value = chain
        chain.first.return_value = (
            _returns['intent'] if 'PaymentIntent' in name
            else _returns['sub'] if 'SubscriptionRecord' in name
            else _returns['user'] if 'User' in name
            else None
        )
        chain.order_by.return_value = chain
        chain.limit.return_value = chain
        chain.all.return_value = []
        return chain

    db.query.side_effect = _query
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


# ══════════════════════════════════════════════════════════════
# Section 1 — payment_service unit tests
# ══════════════════════════════════════════════════════════════

print("\n─── payment_service unit tests ───────────────────────────────────────────")

# ── Test 1: create_payment_intent ─────────────────────────────────────────────

try:
    from api.services.payment_service import create_payment_intent, TIER_CONFIG

    with patch.dict(os.environ, {'PAYMENT_RECEIVE_WALLET': '0xTREASURY'}):
        db = _make_db()
        # Capture the intent passed to db.add
        added = []
        db.add.side_effect = lambda obj: added.append(obj)
        db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)

        intent = create_payment_intent(db, user_id=42, tier='pro', pathway='metamask', sender_address='0xSENDER')

        passed = (
            intent.user_id == 42 and
            intent.tier == 'pro' and
            intent.pathway == 'metamask' and
            intent.expected_usdc_units == TIER_CONFIG['pro']['usdc_units'] and
            intent.sender_address == '0xsender' and  # lowercased
            intent.receive_address == '0xTREASURY' and
            intent.status == 'pending' and
            intent.expires_at > datetime.now(timezone.utc)
        )
        record("create_payment_intent — correct fields and TTL set", passed)
except Exception as e:
    record("create_payment_intent — correct fields and TTL set", False, str(e))

# ── Test 2: unknown tier raises ValueError ────────────────────────────────────

try:
    from api.services.payment_service import create_payment_intent

    db = _make_db()
    raised = False
    try:
        create_payment_intent(db, user_id=1, tier='platinum', pathway='metamask')
    except ValueError:
        raised = True
    record("create_payment_intent — unknown tier raises ValueError", raised)
except Exception as e:
    record("create_payment_intent — unknown tier raises ValueError", False, str(e))

# ── Tests 3–7: _check_transfer_on_chain ─────────────────────────────────────

try:
    from api.services.payment_service import _check_transfer_on_chain
    from api.models.payment import PaymentIntent

    TREASURY = '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
    SENDER   = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    AMOUNT   = 100_000_000  # 100 USDC (6 decimals)

    def _make_intent(sender=SENDER, amount=str(AMOUNT)):
        i = MagicMock(spec=PaymentIntent)
        i.sender_address = sender
        i.expected_usdc_units = amount
        return i

    def _make_web3_mock(to=TREASURY, frm=SENDER, value=AMOUNT, tx_status=1):
        w3 = MagicMock()
        receipt = MagicMock()
        receipt.status = tx_status

        log = MagicMock()
        log.__getitem__ = lambda self, key: {'args': {'to': to, 'from': frm, 'value': value}}[key]
        log['args'] = {'to': to, 'from': frm, 'value': value}

        contract = MagicMock()
        contract.events.Transfer.return_value.process_receipt.return_value = [log]
        w3.eth.get_transaction_receipt.return_value = receipt
        w3.eth.contract.return_value = contract
        w3.to_checksum_address = lambda x: x
        return w3

    env = {'PAYMENT_RECEIVE_WALLET': TREASURY, 'BASE_RPC_URL': 'http://mock'}

    # Test 3: valid transfer
    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.return_value = _make_web3_mock()
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = _check_transfer_on_chain('0xTXHASH', _make_intent())
        record("_check_transfer_on_chain — valid Transfer event accepted", result is True)

    # Test 4: wrong recipient
    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.return_value = _make_web3_mock(to='0xWRONG')
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = _check_transfer_on_chain('0xTXHASH', _make_intent())
        record("_check_transfer_on_chain — wrong recipient rejected", result is False)

    # Test 5: wrong sender (MetaMask path enforces sender_address)
    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.return_value = _make_web3_mock(frm='0xOTHERSENDER')
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = _check_transfer_on_chain('0xTXHASH', _make_intent(sender=SENDER))
        record("_check_transfer_on_chain — wrong sender rejected", result is False)

    # Test 6: underpayment
    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.return_value = _make_web3_mock(value=50_000_000)  # $50 instead of $100
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = _check_transfer_on_chain('0xTXHASH', _make_intent())
        record("_check_transfer_on_chain — underpayment rejected", result is False)

    # Test 7: overpayment accepted
    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.return_value = _make_web3_mock(value=150_000_000)  # $150 for $100 tier
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = _check_transfer_on_chain('0xTXHASH', _make_intent())
        record("_check_transfer_on_chain — overpayment accepted", result is True)

except Exception as e:
    for n in range(3, 8):
        record(f"_check_transfer_on_chain — test {n}", False, str(e))

# ── Test 8: verify_usdc_transfer rejects expired intent ──────────────────────

try:
    from api.services.payment_service import verify_usdc_transfer
    from api.models.payment import PaymentIntent

    expired_intent = MagicMock(spec=PaymentIntent)
    expired_intent.status = 'pending'
    expired_intent.expires_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    expired_intent.user_id = 1

    db = _make_db(intent=expired_intent)
    result = verify_usdc_transfer(db, intent_id=1, tx_hash='0xABC')
    record("verify_usdc_transfer — expired intent rejected", result is False and expired_intent.status == 'expired')
except Exception as e:
    record("verify_usdc_transfer — expired intent rejected", False, str(e))

# ── Test 9: verify_usdc_transfer rejects duplicate tx_hash ───────────────────

try:
    from api.services.payment_service import verify_usdc_transfer
    from api.models.payment import PaymentIntent

    fresh_intent = MagicMock(spec=PaymentIntent)
    fresh_intent.status = 'pending'
    fresh_intent.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    fresh_intent.user_id = 1
    fresh_intent.sender_address = None

    # A previously paid duplicate intent
    dup_intent = MagicMock(spec=PaymentIntent)
    dup_intent.id = 99

    db = MagicMock()
    call_count = [0]

    def _query_side_effect(model):
        chain = MagicMock()
        chain.filter.return_value = chain
        call_count[0] += 1
        # First call → fresh_intent (status lookup), second call → dup_intent (duplicate check)
        chain.first.return_value = fresh_intent if call_count[0] <= 1 else dup_intent
        return chain

    db.query.side_effect = _query_side_effect
    db.commit = MagicMock()

    result = verify_usdc_transfer(db, intent_id=1, tx_hash='0xDUP')
    record("verify_usdc_transfer — duplicate tx_hash rejected", result is False)
except Exception as e:
    record("verify_usdc_transfer — duplicate tx_hash rejected", False, str(e))

# ── Test 10: verify_usdc_transfer — full valid flow ───────────────────────────

try:
    from api.services.payment_service import verify_usdc_transfer
    from api.models.payment import PaymentIntent

    TREASURY = '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
    SENDER   = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

    valid_intent = MagicMock(spec=PaymentIntent)
    valid_intent.status = 'pending'
    valid_intent.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    valid_intent.user_id = 5
    valid_intent.tier = 'basic'
    valid_intent.pathway = 'metamask'
    valid_intent.sender_address = SENDER
    valid_intent.expected_usdc_units = '20000000'

    db = MagicMock()
    call_count = [0]
    user_mock = MagicMock()
    user_mock.tier = 'free'
    sub_mock = None  # No existing subscription

    def _qs(model):
        chain = MagicMock()
        chain.filter.return_value = chain
        call_count[0] += 1
        mname = getattr(model, '__name__', '') if hasattr(model, '__name__') else str(model)
        if 'PaymentIntent' in mname:
            chain.first.return_value = valid_intent if call_count[0] == 1 else None  # No dup
        elif 'SubscriptionRecord' in mname:
            chain.first.return_value = sub_mock
        elif 'User' in mname:
            chain.first.return_value = user_mock
        else:
            chain.first.return_value = None
        return chain

    db.query.side_effect = _qs
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    env = {'PAYMENT_RECEIVE_WALLET': TREASURY, 'BASE_RPC_URL': 'http://mock'}

    def _w3_valid(*a, **kw):
        w3 = MagicMock()
        receipt = MagicMock(); receipt.status = 1
        log = MagicMock()
        log.__getitem__ = lambda s, k: {'args': {'to': TREASURY, 'from': SENDER, 'value': 20_000_000}}[k]
        log['args'] = {'to': TREASURY, 'from': SENDER, 'value': 20_000_000}
        contract = MagicMock()
        contract.events.Transfer.return_value.process_receipt.return_value = [log]
        w3.eth.get_transaction_receipt.return_value = receipt
        w3.eth.contract.return_value = contract
        w3.to_checksum_address = lambda x: x
        return w3

    with patch.dict(os.environ, env), patch('api.services.payment_service.Web3') as W3:
        W3.side_effect = _w3_valid
        W3.HTTPProvider = MagicMock()
        W3.to_checksum_address = lambda x: x
        result = verify_usdc_transfer(db, intent_id=1, tx_hash='0xVALID')

    passed = result is True and valid_intent.status == 'paid' and user_mock.tier == 'basic'
    record("verify_usdc_transfer — valid flow: status=paid + tier upgraded", passed)
except Exception as e:
    record("verify_usdc_transfer — valid flow: status=paid + tier upgraded", False, str(e))

# ── Tests 11–12: activate_subscription ────────────────────────────────────────

try:
    from api.services.payment_service import activate_subscription

    # Test 11: new subscription
    user = MagicMock(); user.tier = 'free'; user.subscription_status = 'none'
    db = _make_db(user=user, sub=None)
    created = []
    db.add.side_effect = lambda obj: created.append(obj)
    db.refresh = MagicMock()

    activate_subscription(db, user_id=1, tier='pro', tx_hash='0xABC', pathway='metamask')
    record(
        "activate_subscription — user.tier updated + SubscriptionRecord created",
        user.tier == 'pro' and user.subscription_status == 'active' and len(created) == 1,
    )

    # Test 12: idempotent re-activation (existing sub)
    from api.models.payment import SubscriptionRecord
    existing_sub = MagicMock(spec=SubscriptionRecord)
    existing_sub.tier = 'basic'; existing_sub.status = 'active'
    user2 = MagicMock(); user2.tier = 'basic'; user2.subscription_status = 'active'
    db2 = _make_db(user=user2, sub=existing_sub)
    db2.add = MagicMock()

    activate_subscription(db2, user_id=2, tier='enterprise', tx_hash='0xRENEW', pathway='nexapay')
    record(
        "activate_subscription — idempotent: existing sub updated, not duplicated",
        existing_sub.tier == 'enterprise' and not db2.add.called,
    )
except Exception as e:
    record("activate_subscription — user.tier updated + SubscriptionRecord created", False, str(e))
    record("activate_subscription — idempotent: existing sub updated, not duplicated", False, str(e))

# ── Tests 13–14: activate_trial ───────────────────────────────────────────────

try:
    from api.services.payment_service import activate_trial

    # Test 13: new trial
    user = MagicMock(); user.tier = 'free'
    db = _make_db(user=user, sub=None)
    created = []
    db.add.side_effect = lambda obj: created.append(obj)
    db.refresh = MagicMock()

    sub = activate_trial(db, user_id=1, tier='pro')
    record(
        "activate_trial — creates trial subscription",
        sub.is_trial is True and sub.status == 'trial' and user.subscription_status == 'trial' and user.tier == 'pro',
    )

    # Test 14: re-trial blocked
    from api.models.payment import SubscriptionRecord
    existing_trial = MagicMock(spec=SubscriptionRecord)
    existing_trial.tier = 'pro'
    db2 = _make_db(sub=existing_trial)
    raised = False
    try:
        activate_trial(db2, user_id=1, tier='pro')
    except ValueError:
        raised = True
    record("activate_trial — re-trial on same tier raises ValueError", raised)
except Exception as e:
    record("activate_trial — creates trial subscription", False, str(e))
    record("activate_trial — re-trial on same tier raises ValueError", False, str(e))

# ── Test 15: expire_stale_subscriptions ───────────────────────────────────────

try:
    from api.services.payment_service import expire_stale_subscriptions
    from api.models.payment import SubscriptionRecord

    expired_sub = MagicMock(spec=SubscriptionRecord)
    expired_sub.status = 'active'
    expired_sub.user_id = 7
    expired_sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)

    user = MagicMock(); user.tier = 'pro'

    db = MagicMock()
    def _qs(model):
        chain = MagicMock()
        chain.filter.return_value = chain
        mname = getattr(model, '__name__', '') if hasattr(model, '__name__') else str(model)
        chain.all.return_value = [expired_sub] if 'SubscriptionRecord' in mname else []
        chain.first.return_value = user if 'User' in mname else None
        return chain
    db.query.side_effect = _qs
    db.commit = MagicMock()

    count = expire_stale_subscriptions(db)
    record(
        "expire_stale_subscriptions — expired sub downgraded to free",
        count == 1 and expired_sub.status == 'expired' and user.tier == 'free',
    )
except Exception as e:
    record("expire_stale_subscriptions — expired sub downgraded to free", False, str(e))

# ── Tests 16–18: verify_nexapay_signature ────────────────────────────────────

try:
    from api.services.payment_service import verify_nexapay_signature

    SECRET = 'test-nexapay-secret-xyz'
    body = b'{"event":"payment.completed","txHash":"0xABC"}'
    valid_sig = hmac_lib.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {'NEXAPAY_SECRET': SECRET}):
        record("verify_nexapay_signature — valid HMAC accepted",
               verify_nexapay_signature(body, valid_sig) is True)
        record("verify_nexapay_signature — tampered body rejected",
               verify_nexapay_signature(b'tampered body', valid_sig) is False)

    with patch.dict(os.environ, {'NEXAPAY_SECRET': ''}):
        record("verify_nexapay_signature — missing secret returns False",
               verify_nexapay_signature(body, valid_sig) is False)

except Exception as e:
    for n in ['valid HMAC accepted', 'tampered body rejected', 'missing secret returns False']:
        record(f"verify_nexapay_signature — {n}", False, str(e))


# ══════════════════════════════════════════════════════════════
# Section 2 — FastAPI endpoint tests (TestClient)
# ══════════════════════════════════════════════════════════════

print("\n─── FastAPI endpoint tests ────────────────────────────────────────────────")

try:
    from fastapi.testclient import TestClient
    from api.main import app

    # Shared test client
    client = TestClient(app, raise_server_exceptions=False)

    # ── Test 19: /api/payments/intent requires auth ───────────────────────────
    try:
        resp = client.post('/api/payments/intent', json={'tier': 'pro'})
        record("API: POST /api/payments/intent — returns 401 without auth", resp.status_code == 401)
    except Exception as e:
        record("API: POST /api/payments/intent — returns 401 without auth", False, str(e))

    # ── Test 20: /api/payments/trial — creates trial ──────────────────────────
    try:
        from api.middleware.auth import create_access_token
        from api.models.user import User

        # Create a fake user and patch get_current_user + DB
        fake_user = MagicMock(spec=User)
        fake_user.id = 99
        fake_user.email = 'testpay@test.com'
        fake_user.tier = 'free'
        fake_user.subscription_status = 'none'

        token = create_access_token(99, 'testpay@test.com')
        headers = {'Authorization': f'Bearer {token}'}

        with patch('api.routers.payments.get_current_user', return_value=fake_user), \
             patch('api.routers.payments.activate_trial') as mock_trial:

            from api.models.payment import SubscriptionRecord
            fake_sub = MagicMock(spec=SubscriptionRecord)
            fake_sub.is_trial = True
            fake_sub.status = 'trial'
            fake_sub.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=7)
            mock_trial.return_value = fake_sub

            resp = client.post('/api/payments/trial', json={'tier': 'pro'}, headers=headers)
            data = resp.json()
            passed = resp.status_code == 200 and data.get('status') == 'trial_started'
            record("API: POST /api/payments/trial — 200 + trial_started status", passed,
                   f"status={resp.status_code} body={data}")
    except Exception as e:
        record("API: POST /api/payments/trial — 200 + trial_started status", False, str(e))

    # ── Test 21: /api/payments/nexapay/webhook — valid webhook ───────────────
    try:
        SECRET = 'webhook-secret-abc'
        payload = {
            'event': 'payment.completed',
            'orderId': '123',
            'txHash': '0xVALIDTX',
            'status': 'completed',
        }
        body = json.dumps(payload).encode()
        sig = hmac_lib.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

        from api.models.payment import PaymentIntent
        fake_intent = MagicMock(spec=PaymentIntent)
        fake_intent.id = 123
        fake_intent.user_id = 1
        fake_intent.tier = 'pro'
        fake_intent.status = 'pending'

        with patch.dict(os.environ, {'NEXAPAY_SECRET': SECRET}), \
             patch('api.routers.payments.activate_subscription') as mock_activate, \
             patch('api.routers.payments.get_db') as mock_get_db:

            mock_db = MagicMock()
            def _qs(model):
                chain = MagicMock()
                chain.filter.return_value = chain
                mname = getattr(model, '__name__', '') if hasattr(model, '__name__') else str(model)
                chain.first.return_value = fake_intent if 'PaymentIntent' in mname else None
                return chain
            mock_db.query.side_effect = _qs
            mock_db.commit = MagicMock()
            mock_get_db.return_value = iter([mock_db])

            resp = client.post(
                '/api/payments/nexapay/webhook',
                content=body,
                headers={'Content-Type': 'application/json', 'X-NexaPay-Signature': sig},
            )
            data = resp.json()
            passed = resp.status_code == 200 and data.get('action') == 'activated'
            record("API: POST /api/payments/nexapay/webhook — valid webhook activates subscription",
                   passed, f"status={resp.status_code} action={data.get('action')}")
    except Exception as e:
        record("API: POST /api/payments/nexapay/webhook — valid webhook activates subscription", False, str(e))

    # ── Test 22: /api/payments/nexapay/webhook — bad signature ───────────────
    try:
        bad_body = b'{"event":"payment.completed","orderId":"1","txHash":"0xX","status":"ok"}'
        with patch.dict(os.environ, {'NEXAPAY_SECRET': 'correct-secret'}):
            resp = client.post(
                '/api/payments/nexapay/webhook',
                content=bad_body,
                headers={'Content-Type': 'application/json', 'X-NexaPay-Signature': 'badsig'},
            )
            record("API: POST /api/payments/nexapay/webhook — bad signature returns 401",
                   resp.status_code == 401)
    except Exception as e:
        record("API: POST /api/payments/nexapay/webhook — bad signature returns 401", False, str(e))

    # ── Test 23: /api/payments/subscription — returns subscription state ──────
    try:
        from api.middleware.auth import create_access_token
        from api.models.user import User
        from api.models.payment import SubscriptionRecord

        fake_user = MagicMock(spec=User)
        fake_user.id = 50
        fake_user.email = 'subcheck@test.com'
        token = create_access_token(50, 'subcheck@test.com')
        headers = {'Authorization': f'Bearer {token}'}

        fake_sub = MagicMock(spec=SubscriptionRecord)
        fake_sub.tier = 'basic'
        fake_sub.status = 'active'
        fake_sub.is_trial = False
        fake_sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=25)
        fake_sub.payment_pathway = 'metamask'

        with patch('api.routers.payments.get_current_user', return_value=fake_user), \
             patch('api.routers.payments.get_db') as mock_get_db:

            mock_db = MagicMock()
            def _qs2(model):
                chain = MagicMock()
                chain.filter.return_value = chain
                mname = getattr(model, '__name__', '') if hasattr(model, '__name__') else str(model)
                chain.first.return_value = fake_sub if 'SubscriptionRecord' in mname else None
                return chain
            mock_db.query.side_effect = _qs2
            mock_get_db.return_value = iter([mock_db])

            resp = client.get('/api/payments/subscription', headers=headers)
            data = resp.json()
            passed = (
                resp.status_code == 200 and
                data.get('tier') == 'basic' and
                data.get('status') == 'active' and
                data.get('payment_pathway') == 'metamask'
            )
            record("API: GET /api/payments/subscription — returns correct state", passed,
                   f"body={data}")
    except Exception as e:
        record("API: GET /api/payments/subscription — returns correct state", False, str(e))

except ImportError as e:
    for n in range(19, 24):
        record(f"API test {n}", False, f"Import error: {e}")


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

print("\n" + "═" * 70)
passed_count = sum(1 for _, p in results if p)
total = len(results)
failed = [(name, ) for name, p in results if not p]

print(f"  Results: {passed_count}/{total} passed")
if failed:
    print(f"\n  Failed tests:")
    for (name,) in failed:
        print(f"    ✗  {name}")

print("═" * 70 + "\n")
sys.exit(0 if passed_count == total else 1)
