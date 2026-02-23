"""
Test XHttpPoster (twikit-based) on VPS or local.
Usage: python scripts/test_x_http.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.x_http_poster import XHttpPoster

print("=== XHttpPoster Test ===")
poster = XHttpPoster()
print(f"enabled: {poster.enabled}")

if not poster.enabled:
    print("ERROR: Not enabled. Check x_cookies.json exists and twikit is installed.")
    sys.exit(1)

# Verify session
print("\nVerifying session...")
valid = poster.verify_session()
print(f"Session valid: {valid}")

if not valid:
    print("ERROR: Session invalid. Re-export cookies with scripts/export_x_cookies.py")
    sys.exit(1)

# Post test tweet
tweet = "Crevia Analytics engine online. Crypto intelligence feed active. $BTC $ETH #Crypto"
print(f"\nPosting: {tweet[:60]}...")
result = poster.post_tweet(tweet)
print(f"Result: {result}")

if result:
    print(f"\nSUCCESS! Tweet ID: {result}")
else:
    print("\nFAILED. Check logs above.")
    sys.exit(1)
