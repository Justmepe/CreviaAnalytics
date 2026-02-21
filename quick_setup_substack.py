#!/usr/bin/env python3
"""
Quick Substack Session Setup - Direct SID Injection
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Fix Windows encoding for emojis
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed")
    exit(1)

from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = Path(__file__).parent
SESSION_DIR = PROJECT_ROOT / "substack_browser_session"
SUBDOMAIN = os.getenv('SUBSTACK_SUBDOMAIN', 'petergikonyo')
BASE_URL = f"https://{SUBDOMAIN}.substack.com"

# Your SID cookie
SID_COOKIE = "s:AY8ilhDKvYqCehwPwwaL98uBZ5rjxm6s.emczc37J2OnU+AWl01an8mMtFsH7QAShOWdYy9HGyrk"

def setup():
    print("🚀 Setting up Substack session with SID cookie...")
    print(f"   Subdomain: {SUBDOMAIN}")
    print(f"   Session dir: {SESSION_DIR}")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Inject SID cookie
        cookie = {
            'name': 'substack.sid',
            'value': SID_COOKIE,
            'domain': '.substack.com',
            'path': '/',
            'expires': int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp()),
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        }

        context.add_cookies([cookie])

        page = context.new_page()
        print(f"📄 Navigating to {BASE_URL}/publish...")
        page.goto(f"{BASE_URL}/publish", wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(3000)

        print(f"   Current URL: {page.url}")

        if '/publish' in page.url:
            print("✅ Authentication successful!")
            print("   Press Enter to save session...")
            input()
            context.close()
            print("💾 Session saved!")
            return True
        else:
            print("❌ Authentication failed")
            context.close()
            return False

if __name__ == "__main__":
    success = setup()
    if success:
        print("\n✅ Done! You can now run: python main.py")
    else:
        print("\n❌ Setup failed")
