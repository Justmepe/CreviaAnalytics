#!/usr/bin/env python3
"""
Quick Substack Session Setup Using Existing SID Cookie

Instead of manual browser login, this script directly injects your
existing Substack SID cookie into the Playwright session.

Usage:
    python setup_substack_with_sid.py

The SID cookie is read from environment variable SUBSTACK_SID
or you can paste it when prompted.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright")
    print("   Then: playwright install chromium")
    exit(1)

from dotenv import load_dotenv

load_dotenv()

# Configuration
PROJECT_ROOT = Path(__file__).parent
SESSION_DIR = PROJECT_ROOT / "substack_browser_session"
SUBDOMAIN = os.getenv('SUBSTACK_SUBDOMAIN', 'petergikonyo')
BASE_URL = f"https://{SUBDOMAIN}.substack.com"


def setup_session_with_sid(sid_cookie: str):
    """
    Create Playwright session with existing SID cookie.

    Args:
        sid_cookie: The substack.sid cookie value (e.g., s:ABC123...)
    """

    print("\n" + "="*80)
    print("SUBSTACK SESSION SETUP - Using Existing SID Cookie")
    print("="*80 + "\n")

    print(f"Subdomain: {SUBDOMAIN}")
    print(f"Base URL: {BASE_URL}")
    print(f"Session directory: {SESSION_DIR}")
    print(f"SID cookie: {sid_cookie[:20]}..." if len(sid_cookie) > 20 else sid_cookie)
    print()

    # Create session directory
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # Launch browser with persistent context
    print("🚀 Launching Playwright browser...")
    with sync_playwright() as p:
        # Create persistent context (this is what stores the session)
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,  # Show browser so you can verify
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create cookie object
        # The SID cookie should be set for .substack.com domain
        cookie = {
            'name': 'substack.sid',
            'value': sid_cookie,
            'domain': '.substack.com',
            'path': '/',
            'expires': int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp()),
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        }

        print("🍪 Injecting SID cookie into browser session...")
        context.add_cookies([cookie])

        # Navigate to publisher dashboard to verify session
        page = context.new_page()
        print(f"📄 Navigating to {BASE_URL}/publish...")

        try:
            page.goto(f"{BASE_URL}/publish", wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)  # Wait for any redirects

            # Check if we're authenticated (should see "Create new" button)
            current_url = page.url
            print(f"   Current URL: {current_url}")

            if '/publish' in current_url:
                print("✅ Successfully authenticated!")
                print("   You should see the Substack publisher dashboard")
                print()
                print("⚠️  IMPORTANT: Verify you can see:")
                print("   - 'Create new' button in the top right")
                print("   - Your Substack publication dashboard")
                print()
                print("   If you see the dashboard, press Enter to save session...")
                print("   If you see a login page, the SID cookie may be expired.")
                input()

                print("\n💾 Saving session to disk...")
                context.close()

                print("✅ Session saved successfully!")
                print(f"   Location: {SESSION_DIR}")
                print()
                print("✅ You can now run main.py - Substack posting will work automatically!")
                return True
            else:
                print("❌ Authentication failed - redirected to login page")
                print("   The SID cookie may be expired or invalid")
                print("   Please run setup_substack_session.py for manual login instead")
                context.close()
                return False

        except Exception as e:
            print(f"❌ Error during verification: {e}")
            context.close()
            return False


def main():
    """Main entry point"""

    # Try to get SID from environment
    sid = os.getenv('SUBSTACK_SID', '')

    # If not in env, prompt user
    if not sid:
        print("\n" + "="*80)
        print("SUBSTACK SID COOKIE")
        print("="*80)
        print()
        print("Please paste your Substack SID cookie value below.")
        print("It should look like: s:AY8ilhDKvYqCehwPwwaL98uBZ5rjxm6s.emczc37J2OnU+AWl01an8mMtFsH7QAShOWdYy9HGyrk")
        print()
        print("You can find this in your browser's developer tools:")
        print("  1. Open substack.com while logged in")
        print("  2. Press F12 (developer tools)")
        print("  3. Go to Application > Cookies > https://substack.com")
        print("  4. Find 'substack.sid' and copy its value")
        print()
        sid = input("Paste SID cookie value: ").strip()

    if not sid:
        print("❌ No SID cookie provided")
        return

    # Clean up the SID (remove any quotes or whitespace)
    sid = sid.strip().strip('"').strip("'")

    # Validate it looks like a session ID
    if not sid.startswith('s:'):
        print("⚠️  Warning: SID cookie should start with 's:'")
        print(f"   You provided: {sid[:50]}...")
        confirm = input("   Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return

    # Setup session
    success = setup_session_with_sid(sid)

    if success:
        print("\n" + "="*80)
        print("✅ SETUP COMPLETE")
        print("="*80)
        print()
        print("Next steps:")
        print("  1. The browser should show your Substack dashboard")
        print("  2. Session is saved and will be reused automatically")
        print("  3. Run: python main.py")
        print()
        print("Substack posting will work for:")
        print("  - Articles (long-form)")
        print("  - Notes (short posts)")
        print("  - Chat threads")
        print()
    else:
        print("\n" + "="*80)
        print("❌ SETUP FAILED")
        print("="*80)
        print()
        print("The SID cookie appears to be invalid or expired.")
        print()
        print("Alternative: Run manual login setup")
        print("  python setup_substack_session.py")
        print()


if __name__ == "__main__":
    main()
