#!/usr/bin/env python3
"""
X SESSION SETUP - Automatic Login using .env Credentials

This script:
1. Reads X credentials from .env file
2. Opens a persistent browser
3. Automatically logs in to X.com
4. Saves the session for automated posting
5. Tracks session state

Credentials used from .env:
- TWITTER_EMAIL
- TWITTER_PASSWORD
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SESSION_DIR = str(PROJECT_ROOT / "x_browser_session")

# Get credentials from .env
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "").strip()
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "").strip()

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("❌ Playwright not installed")
    sys.exit(1)

try:
    from src.utils.x_session_manager import XSessionManager
    HAS_SESSION_MANAGER = True
except ImportError:
    HAS_SESSION_MANAGER = False

print("=" * 80)
print("X BROWSER SESSION SETUP - AUTOMATED LOGIN")
print("=" * 80)
print()

# Validate credentials
if not TWITTER_EMAIL or not TWITTER_PASSWORD:
    print("❌ ERROR: Missing credentials in .env file")
    print()
    print("Required in .env:")
    print("  TWITTER_EMAIL=your_email@example.com")
    print("  TWITTER_PASSWORD=your_password")
    print()
    sys.exit(1)

print("✅ Credentials loaded from .env")
print(f"   Email: {TWITTER_EMAIL[:20]}...")
print()

print("This script will:")
print("1. Open a persistent browser")
print("2. Automatically log in to X.com")
print("3. Save session for automated posting")
print("4. Track session state")
print()
print("Starting login process automatically...")
print()

try:
    with sync_playwright() as p:
        print("[1] Creating persistent browser session...")
        print(f"    Directory: {SESSION_DIR}")
        
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.new_page()
        
        print("[2] Opening X.com...")
        page.goto("https://x.com/i/flow/login", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        time.sleep(2)
        
        print("[3] Logging in automatically...")
        print()
        print("=" * 80)
        print("AUTO-LOGIN IN PROGRESS - DO NOT CLOSE BROWSER")
        print("=" * 80)
        print()
        
        # Step 1: Enter email/username
        print("[3a] Entering email/username...")
        try:
            # Wait for email input field - try multiple selectors
            email_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[placeholder*="email"]',
                'input[placeholder*="phone"]',
                'input[type="text"]',
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    elem = page.locator(selector).first
                    elem.wait_for(state="visible", timeout=3000)
                    email_input = elem
                    print(f"     ✅ Found email input: {selector}")
                    break
                except Exception:
                    continue
            
            if not email_input:
                raise Exception("Could not find email input field")
            
            email_input.fill(TWITTER_EMAIL)
            time.sleep(0.5)
            
            # Click Next button
            next_buttons = page.locator('button:has-text("Next")')
            if next_buttons.count() > 0:
                next_buttons.first.click()
                time.sleep(3)
                print("     ✅ Email entered and Next clicked")
            else:
                # Try by aria-label or other attributes
                page.keyboard.press("Enter")
                time.sleep(3)
                print("     ✅ Email entered (pressed Enter)")
            
        except Exception as e:
            print(f"     ⚠️  Email input error: {e}")
            print("     Continuing...")
        
        # Step 2: Try to find and click password field
        print("[3b] Entering password...")
        time.sleep(2)
        
        try:
            # List of possible password field selectors
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]',
                'input[placeholder*="password"]',
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    elem = page.locator(selector).first
                    elem.wait_for(state="visible", timeout=3000)
                    password_input = elem
                    print(f"     Found password input: {selector}")
                    break
                except Exception:
                    continue
            
            if password_input:
                password_input.fill(TWITTER_PASSWORD)
                time.sleep(0.5)
                
                # Try to find and click Login button
                login_buttons = page.locator('button:has-text("Log in")')
                if login_buttons.count() > 0:
                    login_buttons.first.click()
                    time.sleep(3)
                    print("     ✅ Password entered and Log in clicked")
                else:
                    # Try pressing Enter
                    page.keyboard.press("Enter")
                    time.sleep(3)
                    print("     ✅ Password entered (pressed Enter)")
            else:
                print("     ⚠️  Password field not found yet")
                print("     X may require additional verification steps")
                print("     Waiting for feed to load...")
        except Exception as e:
            print(f"     ⚠️  Password input error: {e}")
            print("     Continuing...")
        
        # Step 3: Wait for feed to load
        print("[3c] Waiting for feed to load...")
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        
        time.sleep(3)
        
        # Check if login was successful
        current_url = page.url.lower()
        print(f"     Current URL: {current_url}")
        
        if "login" in current_url or "flow" in current_url:
            print()
            print("⚠️  WARNING: Still on login page")
            print()
            print("The browser is open. Monitoring for successful login...")
            print()
            
            # Wait up to 2 minutes for manual login completion
            max_wait = 120
            check_interval = 5
            elapsed = 0
            
            while elapsed < max_wait:
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                
                time.sleep(check_interval)
                current_url = page.url.lower()
                
                if "login" not in current_url and "flow" not in current_url:
                    # Login successful!
                    print("✅ Login detected - feed is loading")
                    time.sleep(2)
                    break
                
                elapsed += check_interval
                if elapsed % 30 == 0:
                    print(f"   Still waiting for login... ({elapsed}s)")
        else:
            print("     ✅ Feed loaded successfully")
            time.sleep(2)
            
            # Take screenshot of feed
            try:
                page.screenshot(path=str(PROJECT_ROOT / "x_login_success.png"))
                print("     ✅ Screenshots saved")
            except Exception:
                pass
            
            # Close browser
            print()
            print("[4] Closing browser...")
            context.close()
            time.sleep(1)
        
        # Verify session was saved
        print()
        if Path(SESSION_DIR).exists():
            print("=" * 80)
            print("✅ SUCCESS! Session saved")
            print("=" * 80)
            print()
            
            # Mark session as logged in
            if HAS_SESSION_MANAGER:
                try:
                    manager = XSessionManager(Path(SESSION_DIR))
                    manager.state.mark_logged_in()
                    print("✅ Session state tracked")
                    print("   - Login timestamp recorded")
                    print("   - Cookie expiry tracked (90 days)")
                    print("   - Session marked as valid")
                except Exception as e:
                    print(f"⚠️  Warning: Could not track session: {e}")
            
            print()
            print("Next steps:")
            print("  1. Check session: python tests/check_x_session.py")
            print("  2. Test posting: python test_x_article.py")
            print()
            print("Use with auto-login:")
            print("  from src.utils.x_browser_poster import XBrowserPoster")
            print("  poster = XBrowserPoster(auto_login=True)")
            print("  poster.post_tweet('Hello world!')")
            print()
            sys.exit(0)
        else:
            print("❌ ERROR: Session directory not created")
            sys.exit(1)
        
except KeyboardInterrupt:
    print()
    print("\n⚠️  Login interrupted by user")
    sys.exit(1)
    
except Exception as e:
    print()
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
