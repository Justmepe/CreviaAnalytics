#!/usr/bin/env python3
"""
Import CreviaCockpit X session via auth_token cookie.

Injects the auth_token cookie into a new persistent browser context,
navigates to x.com/home to verify, then saves the session.

Usage:
    DISPLAY=:99 python scripts/import_cockpit_session.py
"""
import sys
import os
import time
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SESSION_DIR = PROJECT_ROOT / "x_browser_session_cockpit"

# Auth cookies for CreviaCockpit (@CreviaCockpit)
AUTH_TOKEN = "5c1ac55f7f550a855c76da44ad3bdaac4e256574"
ATT_TOKEN = "1-g8NmnpCLKfvebAvfm3DYSgN0yk9YdDqFTiSsrGIN"
KDT_TOKEN = "ieJv6G9w1WPSfk9do8B4okidgGJDPrTl1oKQ98WZ"

# Additional session cookies
EXTRA_COOKIES = [
    {"name": "ct0", "value": "c2fd6ceb22f3b2c39bfb5ade39e8cf07b11401f59f0dad3f1d4cf3537b8a112d9b18f57daa414986ccc9663e08c356dad3d907da06b33e1c0862f922d97ffbae5ab78af6f7a0b4cea387eb4b67240b76"},
    {"name": "twid", "value": "u%3D2025543739783913472"},
    {"name": "lang", "value": "en", "httpOnly": False},
    {"name": "guest_id", "value": "v1%3A177182397416971508", "httpOnly": False},
    {"name": "personalization_id", "value": "v1_sE3/BfdFPh9c+wy47OpeKQ==", "httpOnly": False},
    {"name": "__cuid", "value": "054b1b52e4e24cb9b40c0a3ab63c50bb", "httpOnly": False},
]

if platform.system() == "Linux":
    os.environ.setdefault("DISPLAY", ":99")

print("=" * 60)
print("CreviaCockpit Session Import")
print("=" * 60)
print(f"Session dir: {SESSION_DIR}")
print(f"Auth token:  {AUTH_TOKEN[:8]}...{AUTH_TOKEN[-4:]}")
print()

SESSION_DIR.mkdir(exist_ok=True)

try:
    try:
        from patchright.sync_api import sync_playwright
        print("[i] Using patchright")
    except ImportError:
        from playwright.sync_api import sync_playwright
        print("[i] Using playwright")

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
        elif platform.system() == "Linux":
            import shutil
            return shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
        return None

    chrome_path = find_chrome()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            executable_path=chrome_path,
            viewport={"width": 1280, "height": 900},
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=NetworkServiceSandbox,EncryptedClientHello,DnsOverHttpsUpgrade",
                "--disable-quic",
                "--no-zygote",
                "--disable-gpu",
                "--disable-gpu-sandbox",
            ],
        )

        page = context.new_page()

        # Set the auth_token cookie on x.com before navigating
        print("Injecting auth_token cookie...")
        # Build full cookie list
        cookies = [
            {
                "name": "auth_token",
                "value": AUTH_TOKEN,
                "domain": ".x.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
            {
                "name": "att",
                "value": ATT_TOKEN,
                "domain": ".x.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
            {
                "name": "kdt",
                "value": KDT_TOKEN,
                "domain": ".x.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
            # Also set on twitter.com domain (redirects)
            {
                "name": "auth_token",
                "value": AUTH_TOKEN,
                "domain": ".twitter.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
            {
                "name": "att",
                "value": ATT_TOKEN,
                "domain": ".twitter.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
            {
                "name": "kdt",
                "value": KDT_TOKEN,
                "domain": ".twitter.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
            },
        ]

        # Add extra session cookies (ct0, twid, lang, etc.) on both domains
        for domain in [".x.com", ".twitter.com"]:
            for c in EXTRA_COOKIES:
                cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": c.get("httpOnly", True),
                    "sameSite": "None",
                })

        context.add_cookies(cookies)
        print(f"Injected {len(cookies)} cookies.")

        # Navigate to X home
        print("Navigating to x.com/home...")
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        url = page.url
        print(f"Current URL: {url}")

        if "login" in url.lower() or "flow" in url.lower():
            print()
            print("ERROR: Redirected to login page — token may be expired or invalid.")
            context.close()
            sys.exit(1)

        # Verify we're logged in as CreviaCockpit
        try:
            # Look for username in page
            page.wait_for_selector('[data-testid="SideNav_AccountSwitcher_Button"]', timeout=10000)
            account_info = page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').inner_text()
            print(f"Logged in as: {account_info.strip()[:80]}")
        except Exception:
            print("(Could not read account name — but not on login page, looks OK)")

        print()
        print("Session valid! Saving context...")
        context.close()

    print()
    print("=" * 60)
    print("SUCCESS: CreviaCockpit session saved")
    print("=" * 60)
    print(f"Session location: {SESSION_DIR}")
    print()
    print("Next: restart crevia-engine to activate @CreviaCockpit posting")
    print("  pm2 restart ecosystem.config.cjs --only crevia-engine --update-env")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
