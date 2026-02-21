"""
X Auto-Login Handler - Interactive Session Recovery

This handles automatic session restoration or guides users through re-login
when the session has become invalid.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Import session manager
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.x_session_manager import XSessionManager


class XAutoLoginHandler:
    """
    Detects session issues and guides user through re-authentication.
    
    Can be called interactively or programmatically to restore X sessions.
    """

    def __init__(self, session_dir: Optional[str] = None, headless: bool = False):
        self.session_dir = Path(session_dir) if session_dir else PROJECT_ROOT / "x_browser_session"
        self.headless = headless
        self.manager = XSessionManager(self.session_dir)

    def check_and_restore_session(self) -> bool:
        """
        Check session health and attempt restoration if needed.
        
        Returns True if session is healthy, False if needs manual intervention.
        """
        if not HAS_PLAYWRIGHT:
            logger.error("Playwright not installed")
            return False

        print("\n" + "=" * 80)
        print("X SESSION CHECK")
        print("=" * 80 + "\n")

        # Show current status
        self.manager.print_status()

        # Check if session exists
        if not self.manager.session_exists():
            print("❌ NO SESSION FOUND")
            print("   Run: python tests/setup_x_session.py\n")
            return False

        # Check if session is healthy
        if self.manager.is_session_healthy():
            print("✅ SESSION IS HEALTHY - Ready to use\n")
            return True

        print("⚠️  SESSION NEEDS VERIFICATION\n")
        print("Attempting to validate session by checking X.com...")
        print()

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    str(self.session_dir),
                    headless=self.headless,
                    viewport={"width": 1280, "height": 900},
                    args=['--disable-blink-features=AutomationControlled'],
                )

                is_valid, message = self.manager.validate_session_in_browser(context)
                context.close()

                if is_valid:
                    print(f"✅ {message}\n")
                    return True
                else:
                    print(f"❌ {message}")
                    print("   Session is no longer valid.\n")

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            print(f"❌ Failed to validate: {e}\n")

        # Session is invalid - prompt for re-login
        return self.prompt_re_login()

    def prompt_re_login(self) -> bool:
        """
        Interactively guide user through re-login process.
        
        Returns True on successful re-login, False on failure.
        """
        print("=" * 80)
        print("SESSION RECOVERY - MANUAL RE-LOGIN REQUIRED")
        print("=" * 80)
        print()
        print("Your X session has expired. Follow these steps:")
        print()
        print("1. A browser window will open automatically")
        print("2. Log in to your X account (email/password)")
        print("3. Complete any 2FA challenges")
        print("4. Once you see your feed, close the browser")
        print("5. Session will be saved automatically")
        print()

        try:
            response = input("Ready? Press Enter to start (or type 'skip' to cancel)... ").strip().lower()
            if response == 'skip':
                print("Skipped re-login\n")
                return False

            print()
            print("Opening browser for X login...")
            print()

            with sync_playwright() as p:
                # Clear old session first
                self.manager.clear_session()
                time.sleep(1)

                # Create fresh persistent context
                context = p.chromium.launch_persistent_context(
                    str(self.session_dir),
                    headless=False,  # Always show browser for login
                    viewport={"width": 1280, "height": 900},
                )
                page = context.new_page()

                print("=" * 80)
                print("LOGIN IN THE BROWSER WINDOW THAT OPENED")
                print("=" * 80)
                print()
                print("Steps:")
                print("  1. Enter your email or username")
                print("  2. Enter your password")
                print("  3. Complete any 2FA if prompted")
                print("  4. Wait until you see your X feed")
                print("  5. Close the browser window")
                print()
                print("This script will automatically detect when you're logged in.")
                print()
                print("=" * 80)
                print()

                # Navigate to X
                page.goto("https://x.com/home", timeout=60000)

                # Wait for user to login (up to 5 minutes)
                max_wait = 300  # 5 minutes
                check_interval = 5  # Check every 5 seconds
                elapsed = 0

                while elapsed < max_wait:
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass

                    current_url = page.url.lower()

                    # Check if we're logged in (not on login page)
                    if "login" not in current_url and "flow" not in current_url:
                        # Try to find feed indicator
                        try:
                            page.locator('div[data-testid="primaryColumn"]').first.wait_for(timeout=5000)
                            # Successfully logged in!
                            print("✅ LOGGED IN SUCCESSFULLY!")
                            print()
                            time.sleep(2)
                            self.manager.state.mark_logged_in()
                            context.close()
                            print("Session saved automatically.")
                            print("You can now use X automation!\n")
                            return True
                        except Exception:
                            pass

                    elapsed += check_interval
                    if elapsed < max_wait:
                        time.sleep(check_interval)

                # Timeout - user didn't complete login
                print()
                print("❌ Login timeout - session not updated")
                print("   Make sure you:")
                print("   - Entered correct credentials")
                print("   - Completed any 2FA")
                print("   - Wait for the feed to fully load")
                print()
                context.close()
                return False

        except Exception as e:
            logger.error(f"Re-login failed: {e}")
            print(f"\n❌ Error during re-login: {e}\n")
            return False


def auto_login_if_needed(session_dir: Optional[str] = None, interactive: bool = True) -> bool:
    """
    Utility function to check and restore X session as needed.
    
    Call this at the start of your automation scripts to ensure
    a valid X session is available.
    
    Args:
        session_dir: Custom session directory (default: x_browser_session/)
        interactive: If True, guide user through re-login if needed
        
    Returns:
        True if session is healthy, False if needs manual intervention
    """
    handler = XAutoLoginHandler(session_dir, headless=not interactive)

    if interactive:
        return handler.check_and_restore_session()
    else:
        # Non-interactive mode: just check status
        if handler.manager.session_exists() and handler.manager.is_session_healthy():
            return True
        else:
            logger.warning("Session not healthy - interactive re-login needed")
            return False
