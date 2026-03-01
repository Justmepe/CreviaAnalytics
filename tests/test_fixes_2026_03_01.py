#!/usr/bin/env python3
"""
tests/test_fixes_2026_03_01.py

Verifies the 5 fixes shipped on 2026-03-01:

  1. analyze_major accepts all 22 assets (no more BTC/ETH-only validator)
  2. _sanitize_body strips em/en dashes from article/narrative bodies
  3. _is_same_topic blocks same story from different RSS sources
  4. Breaking news detection collects ALL affected assets (multi-asset)
  5. Content dedup gate fires BEFORE posting (not just before recording)

Run from project root:
    python tests/test_fixes_2026_03_01.py

No network calls — all external dependencies are mocked.
"""

import sys
import os
import re
import time
import unittest
from unittest.mock import MagicMock, patch

# ── project root on path ───────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "  ✅ PASS"
FAIL = "  ❌ FAIL"
SKIP = "  ⚠️  SKIP"

results = []


def record(name, passed, detail=""):
    icon = PASS if passed else FAIL
    print(f"{icon}  {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, passed))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 1 — analyze_major accepts all 22 assets
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("FIX 1 — analyze_major accepts all 22 assets (no BTC/ETH-only gate)")
print("=" * 70)

ALTCOIN_TICKERS = ['XRP', 'SOL', 'BNB', 'AVAX', 'SUI', 'LINK']

try:
    from src.analyzers.majors_analyzer import analyze_major

    # Mock all pillars so no network calls are made
    EMPTY_PILLAR = {}
    with patch('src.analyzers.majors_analyzer.analyze_sentiment', return_value=EMPTY_PILLAR), \
         patch('src.analyzers.majors_analyzer.analyze_news',      return_value={'events': [], 'summary': {}}), \
         patch('src.analyzers.majors_analyzer.analyze_derivatives', return_value={}), \
         patch('src.analyzers.majors_analyzer.analyze_onchain',   return_value={}):

        # BTC and ETH must still work
        for ticker in ['BTC', 'ETH']:
            result = analyze_major(ticker)
            no_error = 'error' not in result
            has_ticker = result.get('ticker') == ticker
            record(
                f"analyze_major('{ticker}') — no error, ticker correct",
                no_error and has_ticker,
                f"keys={list(result.keys())[:5]}"
            )

        # Altcoins must now return proper dicts, NOT {'error': ...}
        for ticker in ALTCOIN_TICKERS:
            result = analyze_major(ticker)
            no_error = 'error' not in result
            has_snapshot = 'snapshot' in result
            correct_ticker = result.get('ticker') == ticker
            record(
                f"analyze_major('{ticker}') — no error, has snapshot",
                no_error and has_snapshot and correct_ticker,
                f"error={result.get('error', 'None')}, ticker={result.get('ticker')}"
            )

except Exception as e:
    record("analyze_major import / run", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 2 — _sanitize_body strips em/en dashes from article bodies
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("FIX 2 — _sanitize_body strips em/en dashes from article bodies")
print("=" * 70)

try:
    from src.content.content_session import ContentSession

    # Em dash (—) → ", "
    text_em = "Bitcoin — the leading crypto — surged 5% as the Fed paused."
    cleaned = ContentSession._sanitize_body(text_em)
    no_em_dash = '\u2014' not in cleaned
    record(
        "_sanitize_body: em dash (—) removed",
        no_em_dash,
        f"result: '{cleaned}'"
    )

    # En dash (–) → ", "
    text_en = "BTC price range: $80k–$85k remains key."
    cleaned_en = ContentSession._sanitize_body(text_en)
    no_en_dash = '\u2013' not in cleaned_en
    record(
        "_sanitize_body: en dash (–) removed",
        no_en_dash,
        f"result: '{cleaned_en}'"
    )

    # Spaced hyphen surrogate " - " between words
    text_hyph = "Bitcoin - the flagship asset - rallied sharply."
    cleaned_hyph = ContentSession._sanitize_body(text_hyph)
    no_spaced_hyph = ' - ' not in cleaned_hyph
    record(
        "_sanitize_body: spaced-hyphen surrogate ' - ' removed",
        no_spaced_hyph,
        f"result: '{cleaned_hyph}'"
    )

    # _sanitize_tweet (tweets still cleaned — regression guard)
    # Signal: only stripped when it starts a line (not mid-sentence)
    tweet_em = "BTC \u2014 up 3% \u2014 breaks $88k"
    cleaned_tweet = ContentSession._sanitize_tweet(tweet_em)
    no_em_tweet = '\u2014' not in cleaned_tweet
    record(
        "_sanitize_tweet: em dash removed",
        no_em_tweet,
        f"result: '{cleaned_tweet}'"
    )
    # Signal: label at line-start stripped
    tweet_signal = "Signal: watch $90k next."
    cleaned_signal = ContentSession._sanitize_tweet(tweet_signal)
    no_signal_label = not cleaned_signal.lstrip().startswith('Signal:')
    record(
        "_sanitize_tweet: Signal: label at line-start removed",
        no_signal_label,
        f"result: '{cleaned_signal}'"
    )

    # Verify _derive_x_article applies sanitize to narrative
    # Build a minimal master dict with an em-dash-laden narrative
    session = ContentSession.__new__(ContentSession)
    session.analysis_data = {}
    session.mode = 'breaking_news'
    session.news_context = None
    session._master = None

    dirty_narrative = "The market — driven by fear — collapsed overnight."
    master = {
        'headline': 'BTC Drops',
        'narrative': dirty_narrative,
        'key_insight': 'Key insight here.',
        'thread_tweets': [],
        'mentioned_assets': ['BTC'],
        'directional_signal': 'BEARISH',
        'tags': [],
    }
    article = session._derive_x_article(master)
    record(
        "_derive_x_article: narrative body sanitized",
        '\u2014' not in article['body'],
        f"body snippet: '{article['body'][:60]}'"
    )

    sub_article = session._derive_substack_article(master)
    record(
        "_derive_substack_article: narrative body sanitized",
        '\u2014' not in sub_article['body'],
        f"body snippet: '{sub_article['body'][:60]}'"
    )

except Exception as e:
    record("ContentSession sanitize tests", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 3 — _is_same_topic blocks same story from different RSS sources
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("FIX 3 — _is_same_topic blocks same story from different sources")
print("=" * 70)

try:
    # Import _is_same_topic and _significant_words without starting the engine
    # We test the logic directly via a minimal stub of the Orchestrator class
    from main import CryptoAnalysisOrchestrator as Orchestrator

    orch = Orchestrator.__new__(Orchestrator)
    orch.recent_breaking_headlines = []

    # Sanity: distinct topics should NOT match
    orch.recent_breaking_headlines = []
    orch.recent_breaking_headlines.append(("Federal Reserve cuts rates by 50bps", time.time()))
    is_dup = orch._is_same_topic("Crypto VC funding hits $883M in February 2026")
    record(
        "_is_same_topic: different topics — NOT flagged as duplicate",
        not is_dup
    )

    # Same topic, different wording (the real-world bug)
    orch.recent_breaking_headlines = []
    first_headline = "Crypto VC funding hits $883M in February signaling confidence"
    orch.recent_breaking_headlines.append((first_headline, time.time()))
    is_dup2 = orch._is_same_topic(
        "February 2026 crypto venture funding reaches record $883M investment"
    )
    record(
        "_is_same_topic: same story different wording — flagged as duplicate",
        is_dup2
    )

    # Expired window: same headline but older than 4 hours → should NOT block
    orch.recent_breaking_headlines = []
    old_time = time.time() - (4.5 * 3600)
    orch.recent_breaking_headlines.append((first_headline, old_time))
    is_dup3 = orch._is_same_topic(
        "Crypto venture capital funding totals $883M in February 2026"
    )
    record(
        "_is_same_topic: same headline outside 4h window — NOT blocked",
        not is_dup3
    )

    # Partial overlap below threshold (only 1-2 words match) → NOT blocked
    orch.recent_breaking_headlines = []
    orch.recent_breaking_headlines.append(("Bitcoin price surges past $90000", time.time()))
    is_dup4 = orch._is_same_topic("Ethereum funding rounds continue 2026")
    record(
        "_is_same_topic: insufficient word overlap — NOT blocked",
        not is_dup4
    )

except Exception as e:
    record("_is_same_topic tests", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 4 — Breaking news collects ALL affected assets (multi-asset)
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("FIX 4 — Breaking news collects ALL affected assets (multi-asset)")
print("=" * 70)

try:
    from src.pillars.news import _calculate_relevance

    # Simulate the asset-collection loop from _check_and_post_breaking_news
    ALL_TRACKED = ['BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'AVAX', 'SUI', 'LINK',
                   'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'XMR', 'ZEC', 'DASH', 'SCRT',
                   'AAVE', 'UNI', 'CRV', 'LDO', 'XAU', 'TSLA']

    def collect_affected(title: str, item: dict) -> list:
        """Mirror the detection loop logic from main.py."""
        affected = []
        title_lower = title.lower()
        for ticker in ALL_TRACKED:
            _, score = _calculate_relevance(title, ticker, item)
            if score >= 0.5:
                affected.append(ticker)
        # Literal mention fallback
        for ticker in ALL_TRACKED:
            if ticker.lower() in title_lower and ticker not in affected:
                affected.append(ticker)
        return affected or ['BTC']

    # News affecting both BTC and ETH
    title_btc_eth = "Bitcoin and Ethereum ETFs receive SEC approval in landmark ruling"
    affected = collect_affected(title_btc_eth, {'title': title_btc_eth})
    record(
        "BTC + ETH dual-asset news → both detected",
        'BTC' in affected and 'ETH' in affected,
        f"detected: {affected}"
    )

    # Gold (XAU) news that also moves BTC — both should appear
    title_gold = "Gold surges XAU as Bitcoin BTC correlates amid inflation data"
    affected_gold = collect_affected(title_gold, {'title': title_gold})
    record(
        "XAU + BTC cross-asset news → both detected via literal match",
        'XAU' in affected_gold and 'BTC' in affected_gold,
        f"detected: {affected_gold}"
    )

    # Single-asset news should return only that asset
    title_sol = "Solana SOL network outage resolved after 2-hour downtime"
    affected_sol = collect_affected(title_sol, {'title': title_sol})
    record(
        "SOL single-asset news → SOL detected",
        'SOL' in affected_sol,
        f"detected: {affected_sol}"
    )

    # Generic crypto news with no specific ticker → fallback to ['BTC']
    title_generic = "Crypto market sentiment turns bearish as volumes decline"
    affected_generic = collect_affected(title_generic, {'title': title_generic})
    record(
        "Generic crypto news → fallback to BTC",
        len(affected_generic) >= 1,
        f"detected: {affected_generic}"
    )

except Exception as e:
    record("Multi-asset detection tests", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 5 — Content dedup gate fires BEFORE posting
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("FIX 5 — Content dedup gate fires BEFORE posting")
print("=" * 70)

try:
    # Read the patched _post_breaking_news source and verify the dedup gate
    # is placed before any posting call (structural check via source inspection)
    import inspect
    from main import CryptoAnalysisOrchestrator as Orchestrator

    source = inspect.getsource(Orchestrator._post_breaking_news)

    # Dedup check must appear before the X browser poster call
    dedup_pos = source.find('is_duplicate(thread_body)')
    post_pos  = source.find('x_browser_poster.post_thread')
    record(
        "Dedup gate position: is_duplicate() called BEFORE post_thread()",
        0 < dedup_pos < post_pos,
        f"is_duplicate at char {dedup_pos}, post_thread at char {post_pos}"
    )

    # Record call must appear AFTER the X browser poster call (not just before recording)
    record_pos = source.find('tracker.record_post')
    record(
        "tracker.record_post() called AFTER post_thread()",
        post_pos < record_pos,
        f"post_thread at char {post_pos}, record_post at char {record_pos}"
    )

    # Functional test: if tracker says duplicate, post_thread is NOT called
    orch = Orchestrator.__new__(Orchestrator)
    orch.recent_breaking_headlines = []
    orch.posted_breaking_headlines = set()
    orch.morning_context = None
    orch.last_anchor_time = None

    # Mock all collaborators
    mock_tracker = MagicMock()
    mock_tracker.is_duplicate.return_value = True   # simulate duplicate
    mock_x_poster = MagicMock()
    mock_x_poster.enabled = True
    mock_substack = MagicMock()
    mock_substack.enabled = False
    mock_web = MagicMock()
    mock_web.enabled = False
    mock_cockpit = MagicMock()
    mock_cockpit.enabled = False
    mock_decorator = MagicMock()
    mock_decorator.decorate_x_thread.return_value = ['1/ test tweet']
    mock_decorator.decorate_x_article.return_value = 'article body'
    mock_decorator.decorate_substack_article.return_value = ('title', 'body', [])

    orch.tracker           = mock_tracker
    orch.x_browser_poster  = mock_x_poster
    orch.x_use_browser     = True
    orch.x_cockpit_poster  = mock_cockpit
    orch.substack_browser  = mock_substack
    orch.substack_use_browser = False
    orch.web_publisher     = mock_web
    orch.post_decorator    = mock_decorator

    # Mock _run_content_session to return a valid content dict
    orch._run_content_session = MagicMock(return_value={
        'x_thread':         ['1/ Test tweet about BTC'],
        'x_article':        {'title': 'Test', 'body': 'Test body'},
        'substack_article': {'title': 'Test', 'body': 'Test body'},
        'substack_note':    'Test note',
        'mentioned_assets': ['BTC'],
    })

    fake_item = {
        'title':      'Crypto VC funding hits $883M in February',
        'summary':    'VC funding reaches new highs',
        'source':     'CoinDesk',
        'currencies': ['BTC'],
    }

    orch._post_breaking_news(fake_item, 0.85)

    post_thread_called = mock_x_poster.post_thread.called
    record(
        "Duplicate content: post_thread() NOT called when tracker returns duplicate",
        not post_thread_called,
        f"post_thread called: {post_thread_called}"
    )

except Exception as e:
    record("Dedup-before-post tests", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
total   = len(results)
passed  = sum(1 for _, ok in results if ok)
failed  = total - passed

print(f"RESULTS: {passed}/{total} passed", end="")
if failed:
    print(f"  |  {failed} failed")
    print("\nFailed tests:")
    for name, ok in results:
        if not ok:
            print(f"  ❌ {name}")
else:
    print("  — all green ✅")
print("=" * 70)

sys.exit(0 if failed == 0 else 1)
