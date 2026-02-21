#!/usr/bin/env python3
"""
Quick Substack Cookie Capture - Manual Method

This guide will help you get a fresh substack.sid cookie from your browser.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent / 'data'

def main():
    print("\n" + "="*70)
    print("SUBSTACK COOKIE CAPTURE - MANUAL METHOD")
    print("="*70 + "\n")
    
    print("Your current cookie is expired. Let's get a fresh one!\n")
    
    print("Steps:")
    print("  1. Open https://substack.com in your Chrome browser")
    print("  2. Login with your email: petergikonyo025@gmail.com")
    print("  3. Once logged in, press F12 to open DevTools")
    print("  4. Go to the Application tab")
    print("  5. On the left, click 'Cookies' -> 'https://substack.com'")
    print("  6. Look for the cookie named 'substack.sid'")
    print("  7. Click on it and copy the entire Value (right side)")
    print("  8. Paste the value when prompted below\n")
    
    print("-" * 70)
    
    cookie_value = input("\nPaste your substack.sid cookie value here:\n> ").strip()
    
    if not cookie_value:
        print("\nCancelled.")
        return False
    
    if len(cookie_value) < 20:
        print("\nError: Cookie appears to be too short. Are you sure you copied it?")
        return False
    
    print(f"\nGot cookie: {cookie_value[:40]}...\n")
    
    # Save to .env
    env_file = Path(__file__).parent / '.env'
    
    if env_file.exists():
        # Read current env
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update or add the cookie
        found = False
        for i, line in enumerate(lines):
            if line.startswith('SUBSTACK_SID='):
                lines[i] = f'SUBSTACK_SID={cookie_value}\n'
                found = True
                break
        
        if not found:
            lines.append(f'SUBSTACK_SID={cookie_value}\n')
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"[OK] Saved to .env")
    
    # Also save to cookie file for immediate use
    DATA_DIR.mkdir(exist_ok=True)
    cookie_file = DATA_DIR / 'substack_cookies.json'
    
    cookie_data = {
        'cookies': {'substack.sid': cookie_value},
        'saved_at': datetime.now(timezone.utc).isoformat(),
        'source': 'manual_paste',
    }
    
    with open(cookie_file, 'w') as f:
        json.dump(cookie_data, f, indent=2)
    
    print(f"[OK] Also saved to {cookie_file}")
    
    print("\nDone! Your Substack posting should now work.")
    print("You can test with: python test_substack_post.py\n")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
