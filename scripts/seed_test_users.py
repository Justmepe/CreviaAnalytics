#!/usr/bin/env python3
"""
Seed test users — one per subscription tier.

Run from the project root:
    python scripts/seed_test_users.py

Credentials (all tiers):
    test.free@crevia.io        / TestCrevia1!  — Free
    test.basic@crevia.io       / TestCrevia1!  — Basic   (Observer  $20/mo)
    test.premium@crevia.io     / TestCrevia1!  — Premium (Pilot    $100/mo)
    test.premium+@crevia.io    / TestCrevia1!  — Premium+ (Command $200/mo)
"""

import sys
import os

# Allow running from project root or scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.database import SessionLocal, create_tables
from api.models.user import User
from api.middleware.auth import hash_password

PASSWORD = 'TestCrevia1!'

TEST_USERS = [
    {
        'email': 'test.free@crevia.io',
        'name': 'Test Free',
        'tier': 'free',
        'subscription_status': 'none',
    },
    {
        'email': 'test.basic@crevia.io',
        'name': 'Test Basic',
        'tier': 'basic',
        'subscription_status': 'active',
    },
    {
        'email': 'test.premium@crevia.io',
        'name': 'Test Premium',
        'tier': 'pro',
        'subscription_status': 'active',
    },
    {
        'email': 'test.premium_plus@crevia.io',
        'name': 'Test Premium+',
        'tier': 'enterprise',
        'subscription_status': 'active',
    },
]


def seed():
    create_tables()
    db = SessionLocal()

    try:
        pw_hash = hash_password(PASSWORD)
        created = 0
        updated = 0

        for spec in TEST_USERS:
            existing = db.query(User).filter(User.email == spec['email']).first()

            if existing:
                # Update tier/status in case it changed
                existing.tier = spec['tier']
                existing.subscription_status = spec['subscription_status']
                existing.name = spec['name']
                existing.password_hash = pw_hash
                updated += 1
                print(f"  ↺  Updated  {spec['email']}  →  tier={spec['tier']}")
            else:
                user = User(
                    email=spec['email'],
                    name=spec['name'],
                    password_hash=pw_hash,
                    provider='email',
                    tier=spec['tier'],
                    subscription_status=spec['subscription_status'],
                )
                db.add(user)
                created += 1
                print(f"  ✓  Created  {spec['email']}  →  tier={spec['tier']}")

        db.commit()
        print(f"\nDone — {created} created, {updated} updated.")
        print(f"\nLogin with password: {PASSWORD}")
        print("\nTest accounts:")
        for u in TEST_USERS:
            print(f"  {u['tier']:12}  {u['email']}")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("Seeding test users...\n")
    seed()
