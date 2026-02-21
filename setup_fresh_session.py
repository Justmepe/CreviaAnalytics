#!/usr/bin/env python3
"""
Fresh X Session Setup - After account recovery

Since previous automated login attempts may have corrupted the session,
we need to set up a clean session with manual login.

This script:
1. Backs up the corrupted session (just in case)
2. Helps you set up a fresh manual login
3. Prepares the session for automation
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
SESSION_DIR = PROJECT_ROOT / "x_browser_session"
BACKUP_DIR = PROJECT_ROOT / "x_browser_session_backup"

print("\n" + "=" * 80)
print("FRESH X SESSION SETUP")
print("=" * 80 + "\n")

print("Current situation:")
print("  - Previous login attempts corrupted the X session")
print("  - Browser redirects to login even with saved cookies")
print("  - Account was temporarily locked (should be fine now)")
print()

# Backup corrupted session
if SESSION_DIR.exists():
    print("[1] Backing up corrupted session...")
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    shutil.copytree(SESSION_DIR, BACKUP_DIR)
    print(f"    Backed up to: {BACKUP_DIR}")
    print()
    
    # Remove corrupted session
    print("[2] Removing corrupted session...")
    shutil.rmtree(SESSION_DIR)
    print(f"    Removed: {SESSION_DIR}")
    print()

print("[3] Preparing fresh session directory...")
SESSION_DIR.mkdir(exist_ok=True)
print(f"    Created: {SESSION_DIR}")
print()

print("=" * 80)
print("NEXT STEPS: MANUAL LOGIN")
print("=" * 80)
print()

print("Run this command to open the browser and log in manually:")
print()
print("  python tests/setup_x_session.py")
print()
print("Then:")
print("  1. A browser will open")
print("  2. Log in to X manually with your account")
print("  3. Homepage should show your feed")
print("  4. Script will automatically save the session")
print()
print("After login completes, test posting with:")
print()
print("  python test_posting_simple.py")
print()
print("=" * 80 + "\n")
