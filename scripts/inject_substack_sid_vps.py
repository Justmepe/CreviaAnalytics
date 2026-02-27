#!/usr/bin/env python3
"""
Non-interactive Substack SID injection for VPS.

Usage:
    SUBSTACK_SID="s:YOUR_SID_HERE" DISPLAY=:99 python scripts/inject_substack_sid_vps.py

The script injects the SID cookie into the Playwright session and verifies
authentication by navigating to the publisher dashboard — no interactive
input required.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Load env
from dotenv import load_dotenv
load_dotenv()

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
SESSION_DIR = PROJECT_ROOT / "substack_browser_session"
SUBDOMAIN = os.getenv("SUBSTACK_SUBDOMAIN", "petergikonyo")
BASE_URL = f"https://{SUBDOMAIN}.substack.com"

def main():
    sid = os.getenv("SUBSTACK_SID", "").strip().strip('"').strip("'")
    if not sid:
        print("ERROR: SUBSTACK_SID env var not set.")
        print("Usage: SUBSTACK_SID='s:...' python scripts/inject_substack_sid_vps.py")
        sys.exit(1)

    print(f"\n{'='*70}")
    print("SUBSTACK SID INJECTION (VPS non-interactive)")
    print(f"{'='*70}")
    print(f"Subdomain:  {SUBDOMAIN}")
    print(f"Session:    {SESSION_DIR}")
    print(f"SID prefix: {sid[:25]}...")
    print()

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-gpu-sandbox",
                "--no-zygote",
            ],
        )

        # Inject SID cookie
        cookie = {
            "name": "substack.sid",
            "value": sid,
            "domain": ".substack.com",
            "path": "/",
            "expires": int(
                (datetime.now(timezone.utc) + timedelta(days=365)).timestamp()
            ),
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
        context.add_cookies([cookie])
        print("Cookie injected.")

        page = context.new_page()
        pub_url = f"{BASE_URL}/publish"
        print(f"Navigating to {pub_url} ...")
        page.goto(pub_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        url = page.url
        print(f"Final URL: {url}")

        if "sign-in" in url.lower() or "login" in url.lower():
            print("\nERROR: SID cookie rejected — redirected to sign-in.")
            print("The SID may be expired. Get a fresh one from your browser.")
            context.close()
            sys.exit(1)

        if "/publish" in url:
            print("\nSUCCESS: Publisher dashboard loaded — session authenticated.")
            context.close()
            print(f"\nSession saved to {SESSION_DIR}")
            print("Substack posting will work automatically.")
            sys.exit(0)

        print(f"\nWARNING: Unexpected URL: {url}")
        print("Session may be partially valid. Check manually.")
        context.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
