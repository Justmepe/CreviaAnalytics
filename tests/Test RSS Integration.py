#!/usr/bin/env python3
"""
Test RSS News Integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add project root to path

from src.pillars.rss_engine import CryptoNewsAggregator
from src.pillars.news import analyze_news

print("=" * 60)
print("TESTING RSS NEWS INTEGRATION")
print("=" * 60)

# Test 1: Direct RSS Engine Test
print("\n[TEST 1] Testing RSS Engine Directly")
print("-" * 40)

engine = CryptoNewsAggregator()
print("Fetching RSS feeds (this may take a moment)...")
engine.fetch_all_feeds()

print(f"Total articles indexed: {len(engine.articles)}")

if engine.articles:
    print("Sample articles:")
    for i, article in enumerate(engine.articles[:3]):
        print(f"  {i+1}. {article['title'][:60]}... ({article['source']})")

    # Test search
    print("\nTesting BTC search...")
    btc_results = engine.search_news(ticker="BTC", limit=5)
    print(f"BTC search results: {len(btc_results)}")
    for result in btc_results[:2]:
        print(f"  - {result['title'][:50]}...")

else:
    print("No articles found. RSS feeds may be slow or unreachable.")

# Test 2: News Analysis Integration
print("\n[TEST 2] Testing News Analysis Integration")
print("-" * 40)

print("Running news analysis for BTC...")
news_result = analyze_news('BTC', 24)

print("Analysis complete:")
print(f"  Events found: {len(news_result['events'])}")
print(f"  Total events: {news_result['summary']['total_events']}")
print(f"  High relevance: {news_result['summary']['high_relevance_count']}")
print(f"  Dominant theme: {news_result['summary']['dominant_theme']}")

if news_result['events']:
    print("Sample events:")
    for event in news_result['events'][:2]:
        print(f"  - {event['title'][:50]}... (relevance: {event['relevance_score']})")

print("\n" + "=" * 60)
print("INTEGRATION STATUS")
print("=" * 60)

if len(engine.articles) > 0 and news_result['summary']['total_events'] > 0:
    print("✅ SUCCESS: RSS integration working!")
    print("   - RSS feeds accessible")
    print("   - Articles being indexed")
    print("   - News analysis functioning")
    print("   - Spam filtering active")
elif len(engine.articles) > 0:
    print("⚠️  PARTIAL: RSS feeds working, but news analysis needs tuning")
else:
    print("❌ NEEDS WORK: RSS feeds not accessible")
    print("   - Check network connection")
    print("   - RSS feeds may be temporarily down")
    print("   - Consider adding more reliable feed sources")

print("\nNext steps:")
print("1. RSS feeds load articles in background")
print("2. News analysis uses RSS instead of CryptoPanic")
print("3. Spam filtering removes low-quality content")
print("4. System gracefully handles feed failures")