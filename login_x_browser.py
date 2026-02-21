#!/usr/bin/env python3
"""
X Browser Login - Manual Login Setup

Opens Chrome browser to log in to X manually.
Session is automatically saved for automation.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SESSION_DIR = PROJECT_ROOT / "x_browser_session"

print("\n" + "=" * 80)
print("X BROWSER LOGIN")
print("=" * 80 + "\n")

print("This will:")
print("  1. Open Chrome browser")
print("  2. You log in to X manually")
print("  3. Session is saved automatically")
print()

# Setup
SESSION_DIR.mkdir(exist_ok=True)
print(f"Session directory: {SESSION_DIR}")
print()

# Open browser with Playwright
try:
    from playwright.sync_api import sync_playwright
    import time
    import platform
    import os
    
    def find_chrome():
        """Find system Chrome installation"""
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
    
    print("Opening Chrome browser...")
    print()
    
    with sync_playwright() as p:
        chrome_path = find_chrome()
        
        # Launch persistent context (saves cookies automatically)
        context = p.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            executable_path=chrome_path,
            viewport={"width": 1280, "height": 900},
            args=['--disable-blink-features=AutomationControlled'],
        )
        
        page = context.new_page()
        
        print("=" * 80)
        print("BROWSER OPENED - LOG IN TO X")
        print("=" * 80)
        print()
        print("1. Browser window is open to X login page")
        print("2. Enter your credentials:")
        print(f"   Username/Email: petergikonyo025@gmail.com or Peter_N_Gikonyo")
        print(f"   Password: (check your .env file)")
        print()
        print("3. Complete any 2FA if prompted")
        print()
        print("4. Once you see your X feed, close this window when done")
        print()
        print("The session will be saved automatically!")
        print()
        print("=" * 80)
        print()
        
        # Navigate to X
        page.goto("https://x.com/home", timeout=30000)
        
        # Wait for user to close the browser window
        # The context will auto-close when next line completes
        try:
            page.wait_for_url("https://x.com/home", timeout=300000)  # 5 minute timeout
        except:
            pass  # User closed window or timeout
        
        context.close()
    
    print()
    print("=" * 80)
    print("LOGIN COMPLETE")
    print("=" * 80)
    print()
    print("Your X session has been saved!")
    print(f"Session location: {SESSION_DIR}")
    print()
    print("The automation can now use your logged-in session.")
    print()
    print("Next: Start the system")
    print("  python main.py")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
