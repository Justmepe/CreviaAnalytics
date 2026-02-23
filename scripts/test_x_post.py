"""
Quick test to verify XBrowserPoster can post a tweet on VPS.
Usage: python scripts/test_x_post.py
Run this from the project root: /var/www/CreviaAnalytics/
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# DISPLAY for Xvfb (already set in XBrowserPoster, but set here too for safety)
os.environ.setdefault('DISPLAY', ':99')

from src.utils.x_browser_poster import XBrowserPoster

print("Initializing XBrowserPoster (headless=False)...")
poster = XBrowserPoster(headless=False)

if not poster.enabled:
    print("ERROR: XBrowserPoster not enabled. Check session dir exists.")
    sys.exit(1)

print(f"Poster enabled: {poster.enabled}")
print(f"Session dir: {poster.session_dir}")

# First verify session
print("\nVerifying session...")
is_valid = poster.verify_session()
print(f"Session valid: {is_valid}")

if not is_valid:
    print("ERROR: Session not valid. Re-run scripts/import_x_cookies.py first.")
    sys.exit(1)

# Post a test tweet
test_tweet = "Crevia Analytics engine online. Market intelligence feed active. #Crypto #Bitcoin"
print(f"\nPosting test tweet: {test_tweet[:50]}...")

result = poster.post_tweet(test_tweet)
if result:
    print(f"SUCCESS: Tweet posted ({result})")
else:
    print("FAILED: Tweet post returned None")
    sys.exit(1)
