#!/usr/bin/env python3
"""
X SESSION SETUP - Manual Login Once, Save for Automation

This script:
1. Opens a persistent browser
2. You log in manually to your X account
3. Session is saved to x_browser_session/
4. Session state is tracked for automation

You only need to run this once (or when session expires).
"""

import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
import platform

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SESSION_DIR = str(PROJECT_ROOT / "x_browser_session")

# Find system Chrome installation (not Chromium)
def find_chrome_executable():
    """Detect system Chrome browser instead of using Playwright's Chromium"""
    system = platform.system()
    
    if system == "Windows":
        # Windows Chrome paths
        possible_paths = [
            Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)
    elif system == "Darwin":  # macOS
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        import shutil
        chrome_path = shutil.which("google-chrome") or shutil.which("chromium")
        if chrome_path:
            return chrome_path
    
    return None  # Fall back to Chromium

try:
    from src.utils.x_session_manager import XSessionManager
    HAS_SESSION_MANAGER = True
except ImportError:
    HAS_SESSION_MANAGER = False

print("=" * 80)
print("X BROWSER SESSION SETUP")
print("=" * 80)
print()
print("This script will:")
print("1. Open a persistent browser")
print("2. You log in manually to X.com")
print("3. Session is saved for automated posting")
print("4. Session state is tracked automatically")
print()
print("IMPORTANT:")
print("- Log in to your X account normally")
print("- Do NOT close the browser - it will close automatically")
print("- When you see 'Session saved!' you're done")
print()

input("Press Enter to start...")
print()

try:
    with sync_playwright() as p:
        print(f"[1] Creating persistent browser session at:")
        print(f"    {SESSION_DIR}")
        print()
        
        # Use system Chrome instead of Chromium to avoid detection
        chrome_path = find_chrome_executable()
        if chrome_path:
            print(f"[!] Using system Chrome: {chrome_path}")
        else:
            print(f"[!] Using Playwright Chromium (system Chrome not found)")
        print()
        
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            executable_path=chrome_path,  # Use real Chrome if found
            # Disable automation detection flags for real Chrome
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        page = context.new_page()
        
        print("[2] Opening X.com...")
        page.goto("https://x.com/home")
        time.sleep(2)
        
        print("[3] Checking if you're logged in...")
        page.goto("https://x.com/home")
        
        print()
        print("=" * 80)
        print("LOGIN IN THE BROWSER WINDOW")
        print("=" * 80)
        print()
        print("If you see the login page:")
        print("  1. Enter your email or username")
        print("  2. Enter your password")
        print("  3. Complete any 2FA if needed")
        print()
        print("Once logged in and you can see your X feed,")
        print("close the browser window to continue.")
        print()
        print("=" * 80)
        print()
        
        # Wait for user to close the browser
        # The context will auto-save cookies/session data
        input("Press Enter once you've closed the browser and are ready to continue...")
        
        # Verify session was saved
        if Path(SESSION_DIR).exists():
            print()
            print("=" * 80)
            print("SUCCESS! Session saved to: " + SESSION_DIR)
            print("=" * 80)
            print()
            
            # Mark session as logged in with session manager (if available)
            if HAS_SESSION_MANAGER:
                try:
                    manager = XSessionManager(Path(SESSION_DIR))
                    manager.state.mark_logged_in()
                    print("✅ Session state tracked")
                    print("   Login timestamp recorded")
                    print("   Cookie expiry tracked")
                except Exception as e:
                    print(f"⚠️  Warning: Could not track session state: {e}")
            
            print()
            print("You can now use automated posting!")
            print()
            print("Quick start:")
            print("  1. Check session: python tests/check_x_session.py")
            print("  2. Test posting: python test_x_article.py")
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
