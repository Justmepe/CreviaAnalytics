#!/usr/bin/env python3
"""
SUBSTACK SESSION SETUP - Manual Login Once, Save for Automation

Similar to setup_x_session.py: opens a browser, you log in manually,
session is saved to substack_browser_session/ for automated posting.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

SESSION_DIR = "substack_browser_session"

print("=" * 80)
print("SUBSTACK BROWSER SESSION SETUP")
print("=" * 80)
print()
print("This script will:")
print("1. Open a persistent browser")
print("2. You log in manually to Substack")
print("3. Session is saved for automated posting")
print()
print("IMPORTANT:")
print("- Log in to your Substack account normally")
print("- Use email: petergikonyo025@gmail.com")
print("- After login, you should see your Substack feed/notes")
print("- Once logged in, press Enter in this terminal to save & close")
print()

input("Press Enter to start...")
print()

try:
    with sync_playwright() as p:
        print(f"[1] Creating persistent browser session at: {SESSION_DIR}")
        print()

        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        print("[2] Opening Substack...")
        page.goto("https://substack.com")
        time.sleep(2)

        print("[3] Please log in using the browser window")
        print()
        print("=" * 80)
        print("LOG IN TO SUBSTACK IN THE BROWSER WINDOW")
        print("=" * 80)
        print()
        print("Steps:")
        print("  1. Click 'Sign in'")
        print("  2. Choose 'Sign in with password'")
        print("  3. Enter your email and password")
        print("  4. Complete any CAPTCHA if shown")
        print("  5. Verify you can see your feed/dashboard")
        print()
        print("Once you're logged in and can see your Substack feed,")
        print("come back here and press Enter.")
        print()
        print("=" * 80)
        print()

        input("Press Enter once you've logged in successfully...")

        # Verify session works by navigating to notes
        print()
        print("[4] Verifying session...")
        page.goto("https://substack.com/notes")
        time.sleep(3)

        url = page.url
        if "notes" in url.lower():
            print("   Session verified - Notes page accessible")
        else:
            print(f"   Warning: Redirected to {url} (session might not be saved)")

        context.close()

        if Path(SESSION_DIR).exists():
            print()
            print("=" * 80)
            print(f"SUCCESS! Session saved to: {SESSION_DIR}")
            print("=" * 80)
            print()
            print("You can now use automated posting via the main pipeline.")
            print()
            sys.exit(0)
        else:
            print("ERROR: Session directory not created")
            sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
