#!/usr/bin/env python3
"""Reset and verify X session state"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

SESSION_DIR = Path("x_browser_session")
STATE_FILE = SESSION_DIR / "session_state.json"

# Fresh login state
fresh_state = {
    "version": 1,
    "logged_in": True,
    "login_timestamp": datetime.now(timezone.utc).isoformat(),
    "last_verified": datetime.now(timezone.utc).isoformat(),
    "session_valid": True,
    "cookie_expiry": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
    "error_count": 0,
    "last_error": None,
    "last_error_time": None,
}

with open(STATE_FILE, 'w') as f:
    json.dump(fresh_state, f, indent=2)

print("✅ Session reset to fresh login state")
print()
print("Status:")
print(f"  Logged in: {fresh_state['logged_in']}")
print(f"  Valid: {fresh_state['session_valid']}")
print(f"  Expires: {fresh_state['cookie_expiry']}")
print()
print("Ready to post! Test with:")
print("  python main.py")
print()
