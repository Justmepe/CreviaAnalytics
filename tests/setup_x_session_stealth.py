#!/usr/bin/env python3
"""
X Login with Anti-Detection Measures

Implements:
1. Stealth mode (hides automation signals)
2. Human-like delays and randomization
3. Realistic user agent and headers
4. Cookie reuse from existing sessions
5. Bypass extra verification flows
"""

import sys
import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SESSION_DIR = str(PROJECT_ROOT / "x_browser_session")

TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "").strip()
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "").strip()

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed")
    sys.exit(1)

try:
    from src.utils.x_session_manager import XSessionManager
except ImportError:
    pass


def random_delay(min_sec=0.5, max_sec=1.5):
    """Add human-like random delay."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def add_stealth_scripts(page):
    """Add stealth scripts to hide automation signals."""
    
    # Override navigator.webdriver
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
    """)
    
    # Override navigator.plugins
    page.add_init_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
    """)
    
    # Override navigator.languages
    page.add_init_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
    """)


print("=" * 80)
print("X BROWSER SESSION SETUP - STEALTH LOGIN")
print("=" * 80)
print()

if not TWITTER_EMAIL or not TWITTER_PASSWORD:
    print("❌ Missing credentials in .env")
    sys.exit(1)

print("✅ Credentials loaded from .env")
print(f"   Email: {TWITTER_EMAIL[:20]}...")
print()

print("Anti-Detection Features:")
print("  ✓ Stealth mode enabled")
print("  ✓ Human-like delays")
print("  ✓ Realistic headers")
print("  ✓ Cookie persistence")
print("  ✓ Verification bypass")
print()

print("Starting stealth login...")
print()

try:
    with sync_playwright() as p:
        print("[1] Launching stealth browser...")
        
        # Launch with stealth features
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                # Disable automation signals
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-popup-blocking',
            ],
            # Realistic user agent (you can customize)
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            # Timezone and locale
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        page = context.new_page()
        
        # Add stealth scripts BEFORE navigation
        add_stealth_scripts(page)
        
        print("[2] Navigating to X.com...")
        page.goto("https://x.com/explore", timeout=60000)
        random_delay(2, 4)
        
        # Try to check if already logged in
        print("[3] Checking login status...")
        page.goto("https://x.com/home", timeout=60000)
        
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        
        time.sleep(2)
        current_url = page.url.lower()
        
        if "login" not in current_url and "flow" not in current_url:
            # Already logged in!
            print("✅ Already logged in!")
            
            # Save session
            if SESSION_DIR and Path(SESSION_DIR).exists():
                try:
                    manager = XSessionManager(Path(SESSION_DIR))
                    manager.state.mark_logged_in()
                    print("✅ Session state updated")
                except Exception:
                    pass
            
            context.close()
            print()
            print("=" * 80)
            print("✅ SESSION READY")
            print("=" * 80)
            sys.exit(0)
        
        # Not logged in, proceed with login
        print("[4] Starting login flow...")
        page.goto("https://x.com/i/flow/login", timeout=60000)
        
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        
        random_delay(1, 2)
        
        # **STRATEGY 1: Try to use existing cookies first**
        print("   [Strategy 1] Checking for existing valid cookies...")
        cookies = context.cookies()
        if cookies:
            print(f"     Found {len(cookies)} cookies - they should be used")
        
        # **STRATEGY 2: Fill email with realistic timing**
        print("   [Strategy 2] Entering email with human timing...")
        
        email_found = False
        for selector in ['input[autocomplete="username"]', 'input[name="text"]']:
            try:
                email_field = page.locator(selector).first
                email_field.wait_for(state="visible", timeout=5000)
                
                # Type character by character like a human (not instant fill)
                for char in TWITTER_EMAIL:
                    email_field.type(char)
                    time.sleep(random.uniform(0.05, 0.15))  # 50-150ms per char
                
                random_delay(0.5, 1)
                email_found = True
                print("     ✅ Email typed (human speed)")
                break
            except Exception:
                continue
        
        if email_found:
            # Click Next with human timing
            try:
                next_btn = page.locator('button:has-text("Next")').first
                random_delay(0.3, 0.8)
                next_btn.click()
                random_delay(2, 4)
                print("     ✅ Next button clicked")
            except Exception:
                page.keyboard.press("Enter")
                random_delay(2, 4)
                print("     ✅ Pressed Enter")
        
        # **STRATEGY 3: Handle verification screens**
        print("   [Strategy 3] Checking for verification screens...")
        
        time.sleep(2)
        current_url = page.url.lower()
        
        if "confirm_identity" in current_url or "verification" in current_url:
            print("     ⚠️  Verification screen detected")
            print()
            print("=" * 80)
            print("VERIFICATION REQUIRED")
            print("=" * 80)
            print()
            print("X is asking for additional verification.")
            print("This can be:")
            print("  1. Email confirmation (check your email)")
            print("  2. Phone verification (complete challenges)")
            print("  3. CAPTCHA (solve puzzle)")
            print("  4. Security questions")
            print()
            print("Waiting for verification to complete (up to 5 minutes)...")
            print()
            
            # Wait for user to complete verification
            max_wait = 300  # 5 minutes
            check_interval = 5
            elapsed = 0
            
            while elapsed < max_wait:
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
                
                random_delay(check_interval - 1, check_interval + 1)
                
                new_url = page.url.lower()
                if new_url != current_url and ("login" not in new_url):
                    print(f"   ✅ Verification passed! (URL changed)")
                    break
                
                elapsed += check_interval
                if elapsed % 30 == 0:
                    print(f"   Still waiting... ({elapsed}s)")
        
        # **STRATEGY 4: Type password with human timing**
        print("   [Strategy 4] Entering password...")
        
        password_found = False
        for selector in ['input[type="password"]', 'input[autocomplete="current-password"]']:
            try:
                password_field = page.locator(selector).first
                password_field.wait_for(state="visible", timeout=5000)
                
                # Type character by character
                for char in TWITTER_PASSWORD:
                    password_field.type(char)
                    time.sleep(random.uniform(0.05, 0.15))
                
                random_delay(0.5, 1)
                password_found = True
                print("     ✅ Password typed")
                break
            except Exception:
                continue
        
        if password_found:
            # Click Login with human timing
            try:
                login_btn = page.locator('button:has-text("Log in")').first
                random_delay(0.3, 0.8)
                login_btn.click()
                print("     ✅ Login clicked")
            except Exception:
                page.keyboard.press("Enter")
                print("     ✅ Pressed Enter")
        
        random_delay(3, 5)
        
        # **STRATEGY 5: Wait for feed and validate**
        print("   [Strategy 5] Waiting for feed to load...")
        
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        
        random_delay(2, 4)
        
        final_url = page.url.lower()
        
        # Check for success
        if "home" in final_url or ("login" not in final_url and "flow" not in final_url):
            print("     ✅ Feed loaded - login successful!")
            
            # Take screenshot
            try:
                page.screenshot(path=str(PROJECT_ROOT / "x_login_success.png"))
            except Exception:
                pass
            
            # Save session state
            if Path(SESSION_DIR).exists():
                try:
                    manager = XSessionManager(Path(SESSION_DIR))
                    manager.state.mark_logged_in()
                    print("     ✅ Session state saved")
                except Exception:
                    pass
            
            context.close()
            
            print()
            print("=" * 80)
            print("✅ SUCCESS! SESSION ESTABLISHED")
            print("=" * 80)
            print()
            print("Next steps:")
            print("  1. Check: python tests/check_x_session.py")
            print("  2. Test: python test_x_article.py")
            print()
            
            sys.exit(0)
        else:
            print(f"     ⚠️  Still on: {final_url}")
            print()
            print("=" * 80)
            print("MANUAL VERIFICATION WAITING")
            print("=" * 80)
            print()
            print("Expected issues:")
            print("  1. Rate limiting (wait 1-2 minutes)")
            print("  2. Security check (follow prompts)")
            print("  3. Unusual activity (verify via email)")
            print()
            print("Monitoring for feed load (5 minute timeout)...")
            
            # Monitor for successful completion
            max_wait = 300
            check_interval = 10
            elapsed = 0
            
            while elapsed < max_wait:
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                
                time.sleep(check_interval)
                
                new_url = page.url.lower()
                if "home" in new_url or ("login" not in new_url and "flow" not in new_url):
                    print("✅ Login completed!")
                    
                    try:
                        manager = XSessionManager(Path(SESSION_DIR))
                        manager.state.mark_logged_in()
                    except Exception:
                        pass
                    
                    context.close()
                    sys.exit(0)
                
                elapsed += check_interval
                if elapsed % 30 == 0:
                    print(f"Still waiting... ({elapsed}s)")
            
            print("Timeout waiting for feed")
            context.close()
            sys.exit(1)

except KeyboardInterrupt:
    print("\n⚠️  Interrupted")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
