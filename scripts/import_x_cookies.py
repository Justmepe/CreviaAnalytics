"""
Run this on the VPS after uploading x_cookies.json.
Imports X cookies into the patchright browser session.
Usage: python scripts/import_x_cookies.py
"""
import json, os, sys

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', 'x_cookies.json')
SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'x_browser_session')

if not os.path.exists(COOKIES_FILE):
    print(f"ERROR: {COOKIES_FILE} not found. Run export_x_cookies.py first.")
    sys.exit(1)

with open(COOKIES_FILE) as f:
    cookies = json.load(f)

print(f"Loaded {len(cookies)} cookies from file")

try:
    from patchright.sync_api import sync_playwright
    print("Using patchright")
except ImportError:
    from playwright.sync_api import sync_playwright
    print("Using playwright")

os.environ.setdefault('DISPLAY', ':99')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
        ],
        ignore_default_args=['--enable-automation'],
    )

    # Import cookies
    ctx.add_cookies(cookies)
    print(f"Imported {len(cookies)} cookies into session")

    # Verify by navigating to X home
    page = ctx.new_page()
    page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
    url = page.url
    print(f"Navigation result: {url}")

    if 'home' in url:
        print("\nSUCCESS: Logged in to X! Session saved.")
    elif 'login' in url:
        print("\nFAILED: Redirected to login page. Cookies may be expired.")
    else:
        print(f"\nUnknown state: {url}")

    ctx.close()
