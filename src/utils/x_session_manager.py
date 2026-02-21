"""
X/Twitter Session Manager - Persistence & Auto-Login

Handles:
- Session validation and health checks
- Automatic session restoration on startup
- Cookie persistence with TTL tracking
- Automatic re-authentication when needed
- Session state monitoring and logging
"""

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SESSION_DIR = PROJECT_ROOT / "x_browser_session"
SESSION_STATE_FILE = PROJECT_ROOT / "x_browser_session" / "session_state.json"


class SessionState:
    """Tracks session validity, cookie expiration, and login metadata."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or SESSION_STATE_FILE
        self.state: Dict[str, Any] = {
            'version': 1,
            'logged_in': False,
            'login_timestamp': None,
            'last_verified': None,
            'session_valid': False,
            'cookie_expiry': None,
            'error_count': 0,
            'last_error': None,
            'last_error_time': None,
        }
        self.lock = Lock()
        self._load()

    def _load(self) -> None:
        """Load session state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    self.state.update(loaded)
                    logger.info(f"[SessionState] Loaded state from {self.state_file}")
        except Exception as e:
            logger.warning(f"[SessionState] Failed to load state: {e}")

    def _save(self) -> None:
        """Persist session state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[SessionState] Failed to save state: {e}")

    def mark_logged_in(self) -> None:
        """Record successful login."""
        with self.lock:
            now = datetime.now(timezone.utc).isoformat()
            self.state['logged_in'] = True
            self.state['login_timestamp'] = now
            self.state['session_valid'] = True
            self.state['error_count'] = 0
            self.state['last_error'] = None
            # Assume cookies expire in 90 days (X typically uses ~30-90 days)
            expiry = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            self.state['cookie_expiry'] = expiry
            self.state['last_verified'] = now
            self._save()
            logger.info("[SessionState] Marked session as logged in")

    def mark_verified(self) -> None:
        """Update last verification time (session is healthy)."""
        with self.lock:
            self.state['last_verified'] = datetime.now(timezone.utc).isoformat()
            self.state['session_valid'] = True
            self.state['error_count'] = 0
            self._save()

    def mark_error(self, error_msg: str) -> None:
        """Record an error (session possibly compromised)."""
        with self.lock:
            self.state['last_error'] = error_msg
            self.state['last_error_time'] = datetime.now(timezone.utc).isoformat()
            self.state['error_count'] = self.state.get('error_count', 0) + 1
            # After 3 consecutive errors, mark session invalid
            if self.state['error_count'] >= 3:
                self.state['session_valid'] = False
            self._save()
            logger.warning(f"[SessionState] Error recorded: {error_msg} (count: {self.state['error_count']})")

    def is_session_valid(self) -> bool:
        """Check if session is marked as valid."""
        with self.lock:
            return self.state.get('session_valid', False)

    def is_cookie_expired(self) -> bool:
        """Check if cookies have likely expired."""
        with self.lock:
            expiry_str = self.state.get('cookie_expiry')
            if not expiry_str:
                return True
            try:
                expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                return datetime.now(timezone.utc) > expiry
            except Exception:
                return True

    def reset(self) -> None:
        """Reset session state when re-authenticating."""
        with self.lock:
            self.state = {
                'version': 1,
                'logged_in': False,
                'login_timestamp': None,
                'last_verified': None,
                'session_valid': False,
                'cookie_expiry': None,
                'error_count': 0,
                'last_error': None,
                'last_error_time': None,
            }
            self._save()


class XSessionManager:
    """
    Manages X/Twitter browser session lifecycle with persistence.

    Handles:
    - Session validation on startup
    - Automatic re-login if needed
    - Cookie expiration tracking
    - Health monitoring
    """

    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = Path(session_dir) if session_dir else SESSION_DIR
        self.state = SessionState(self.session_dir / "session_state.json")
        self.lock = Lock()

    def session_exists(self) -> bool:
        """Check if a browser session directory exists."""
        return self.session_dir.exists()

    def is_session_healthy(self) -> bool:
        """
        Determine if current session is healthy enough for posting.

        Returns True if:
        - Session directory exists
        - State is marked as valid
        - Cookies haven't expired
        - Error count is low
        """
        if not self.session_exists():
            logger.warning("[XSessionManager] Session directory doesn't exist")
            return False

        if self.state.is_cookie_expired():
            logger.warning("[XSessionManager] Cookies appear to have expired")
            return False

        if not self.state.is_session_valid():
            logger.warning("[XSessionManager] Session marked as invalid")
            return False

        # Check if verification is stale (> 7 days since last check)
        last_verified = self.state.state.get('last_verified')
        if last_verified:
            try:
                verified_time = datetime.fromisoformat(last_verified.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) - verified_time > timedelta(days=7):
                    logger.info("[XSessionManager] Session not verified in 7+ days")
                    # Don't fail here, just warn - we'll verify on first use
            except Exception:
                pass

        return True

    def validate_session_in_browser(self, context) -> Tuple[bool, str]:
        """
        Validate session by checking if we're logged in.

        Opens a test page and checks for login redirect.
        Returns (is_valid, message)
        """
        try:
            page = context.new_page()
            page.goto("https://x.com/home", timeout=60000)
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            time.sleep(2)

            # Check if redirected to login
            current_url = page.url.lower()
            page.close()

            if "login" in current_url or "flow" in current_url:
                logger.warning(f"[XSessionManager] Session validation failed - redirected to login: {page.url}")
                self.state.mark_error("Redirected to login page")
                return False, "Session expired - would redirect to login"

            logger.info("[XSessionManager] Session validation successful")
            self.state.mark_verified()
            return True, "Session is valid"

        except Exception as e:
            error_msg = f"Session validation error: {e}"
            logger.error(f"[XSessionManager] {error_msg}")
            self.state.mark_error(error_msg)
            return False, error_msg

    def clear_session(self) -> None:
        """
        Completely clear the session (for re-authentication).

        Removes the persistent context and resets state.
        """
        try:
            if self.session_dir.exists():
                import shutil
                logger.info(f"[XSessionManager] Clearing session at {self.session_dir}")
                shutil.rmtree(self.session_dir)
            self.state.reset()
            logger.info("[XSessionManager] Session cleared - requires re-login")
        except Exception as e:
            logger.error(f"[XSessionManager] Failed to clear session: {e}")

    def get_session_info(self) -> Dict[str, Any]:
        """Get human-readable session status."""
        with self.state.lock:
            info = {
                'session_exists': self.session_exists(),
                'is_healthy': self.is_session_healthy(),
                'logged_in': self.state.state.get('logged_in', False),
                'login_time': self.state.state.get('login_timestamp'),
                'last_verified': self.state.state.get('last_verified'),
                'session_valid': self.state.state.get('session_valid'),
                'cookie_expiry': self.state.state.get('cookie_expiry'),
                'error_count': self.state.state.get('error_count', 0),
                'last_error': self.state.state.get('last_error'),
                'last_error_time': self.state.state.get('last_error_time'),
            }
            return info

    def print_status(self) -> None:
        """Print a human-readable session status report."""
        info = self.get_session_info()
        
        print("\n" + "=" * 80)
        print("X SESSION STATUS")
        print("=" * 80)
        print(f"Session exists:        {info['session_exists']}")
        print(f"Session healthy:       {info['is_healthy']}")
        print(f"Logged in:             {info['logged_in']}")
        print(f"Session valid:         {info['session_valid']}")
        print(f"Login timestamp:       {info['login_time']}")
        print(f"Last verified:         {info['last_verified']}")
        print(f"Cookie expiry:         {info['cookie_expiry']}")
        print(f"Error count:           {info['error_count']}")
        if info['last_error']:
            print(f"Last error:            {info['last_error']}")
            print(f"Last error time:       {info['last_error_time']}")
        print("=" * 80 + "\n")
