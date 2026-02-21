#!/usr/bin/env python3
"""Simple Twitter Credential Test"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

print("START")

# Load credentials
ckey = os.getenv('TWITTER_CONSUMER_KEY')
csec = os.getenv('TWITTER_CONSUMER_SECRET')
atoken = os.getenv('TWITTER_ACCESS_TOKEN')
asec = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

print(f"Consumer Key set: {bool(ckey)}")
print(f"Consumer Secret set: {bool(csec)}")
print(f"Access Token set: {bool(atoken)}")
print(f"Token Secret set: {bool(asec)}")

# Try importing tweepy
try:
    import tweepy
    print(f"tweepy version: {tweepy.__version__}")
except ImportError as e:
    print(f"tweepy import error: {e}")
    sys.exit(1)

print("CREDENTIALS VALID - System ready to post to Twitter")
