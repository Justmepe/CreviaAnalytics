#!/usr/bin/env python3
"""
X Browser Login — CreviaCockpit Account

Opens Chrome browser to log in to CreviaCockpit manually.
Session saved to x_browser_session_cockpit/ for dual-account posting.

Run once on VPS:
  DISPLAY=:99 python setup_x_session_cockpit.py
"""

import sys
import time
import platform
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SESSION_DIR = PROJECT_ROOT / "x_browser_session_cockpit"

print("\n" + "=" * 80)
print("X BROWSER LOGIN — CreviaCockpit")
print("=" * 80 + "\n")
print(f"Session directory: {SESSION_DIR}")
print()

SESSION_DIR.mkdir(exist_ok=True)

try:
    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        from playwright.sync_api import sync_playwright

    def find_chrome():
        if platform.system() == "Windows":
            paths = [
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
                Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
            ]
            for p in paths:
                if p.exists():
                    return str(p)
        elif platform.system() == "Darwin":
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif platform.system() == "Linux":
            import shutil
            return shutil.which("google-chrome") or shutil.which("chromium")
        return None

    if platform.system() == "Linux":
        os.environ.setdefault('DISPLAY', ':99')

    print("Opening Chrome browser for CreviaCockpit login...")
    print()

    with sync_playwright() as p:
        chrome_path = find_chrome()
        context = p.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            executable_path=chrome_path,
            viewport={"width": 1280, "height": 900},
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-zygote',
                '--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade',
                '--disable-quic',
            ],
        )

        page = context.new_page()

        print("=" * 80)
        print("BROWSER OPENED — LOG IN AS CreviaCockpit")
        print("=" * 80)
        print()
        print("Credentials:")
        print("  Email:    creohub.io@gmail.com")
        print("  Username: CreviaCockpit")
        print("  Password: (check TWITTER_PASSWORD_2 in .env)")
        print()
        print("Complete 2FA if prompted, then wait until you see the X feed.")
        print("Close the browser window when done.")
        print("=" * 80)
        print()

        page.goto("https://x.com/login", timeout=30000)

        try:
            page.wait_for_url("**/home**", timeout=300000)
            print("Logged in — session saved.")
        except Exception:
            pass

        context.close()

    print()
    print("=" * 80)
    print("LOGIN COMPLETE")
    print("=" * 80)
    print()
    print(f"CreviaCockpit session saved to: {SESSION_DIR}")
    print()
    print("The engine will now post breaking news to CreviaCockpit automatically.")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
