"""
Test XHttpPoster (twikit-based) on VPS or local.
Usage: python scripts/test_x_http.py
"""
import os, sys, logging, json
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.x_http_poster import XHttpPoster

print("=== XHttpPoster Test ===")
poster = XHttpPoster()
print(f"enabled: {poster.enabled}")

if not poster.enabled:
    print("ERROR: Not enabled. Check x_cookies.json exists and twikit is installed.")
    sys.exit(1)

# Show cookie info
cookies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'x_cookies.json')
with open(cookies_path) as f:
    cookies = json.load(f)
names = [c['name'] for c in cookies]
print(f"Cookies loaded: {names}")

# Verify session (may give false negatives — always attempt posting anyway)
print("\nVerifying session (non-blocking)...")
valid = poster.verify_session()
print(f"verify_session result: {valid}")

# Always try posting regardless of verify result
tweet = "Crevia Analytics engine test. Crypto intelligence feed active. $BTC $ETH #Crypto"
print(f"\nAttempting tweet: {tweet[:60]}...")
result = poster.post_tweet(tweet)
print(f"post_tweet result: {result}")

if result:
    print(f"\nSUCCESS! Tweet ID: {result}")
else:
    print("\nFAILED. Check ERROR logs above.")
    sys.exit(1)
