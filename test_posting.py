#!/usr/bin/env python3
"""
Manual posting verification — runs one test post on each channel:
  1. X Thread (main account — true thread, not single tweet)
  2. X Article (main account)
  3. X Thread (@CreviaCockpit account)
  4. Substack Note
  5. Substack Article

Usage:
    python test_posting.py [--x-thread] [--x-article] [--x-cockpit] [--sub-note] [--sub-article] [--all]

Run all by default if no flag is given.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Test content ──────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc).strftime('%b %d %H:%M UTC')

THREAD_TWEETS = [
    f"1/ 🧪 CREVIA SYSTEM TEST — {NOW}\n\nPosting pipeline verification. Ignore this thread.",
    "2/ BTC is the benchmark asset. Thread composer test: verifying true reply chain (not separate tweets).",
    "3/ ETH funding rates, whale flows, and regime detection all online. Cockpit tracking live.\n\nFull analysis → https://crevia.creohub.io",
]

X_ARTICLE_TITLE = f"Crevia System Test — {NOW}"
X_ARTICLE_BODY = f"""# System Verification Post

**Date:** {NOW}

This is an automated system verification post from Crevia Cockpit.

## What This Tests

- X Article posting via browser automation
- Title rendering in article view
- Body formatting (headers, bold, links)

## Status

All systems nominal. Live data, regime detection, and whale flow scanner are active.

→ [Crevia Cockpit](https://crevia.creohub.io)
"""

SUBSTACK_NOTE = (
    f"[System Test — {NOW}]\n\n"
    "Crevia Cockpit posting pipeline online. BTC regime detection, whale scanner, "
    "and live trade setups all active.\n\n"
    "Full analysis → https://crevia.creohub.io"
)

SUBSTACK_ARTICLE_TITLE = f"Crevia System Verification — {NOW}"
SUBSTACK_ARTICLE_BODY = f"""# System Verification

**Published:** {NOW}

This is a system verification post confirming that the Crevia Cockpit content pipeline is operational.

## Pipeline Status

- **X thread composer**: True reply-chain posting (not separate tweets)
- **X Articles**: Long-form article publishing
- **Substack Notes**: Short-form note posting
- **Substack Articles**: Full article publishing

## Live Features

Crevia Cockpit provides real-time regime detection, whale flow scanning, and trade setups for crypto markets.

→ [crevia.creohub.io](https://crevia.creohub.io)
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def hr(label: str):
    logger.info(f"\n{'='*70}")
    logger.info(f"  {label}")
    logger.info(f"{'='*70}")


def result(ok: bool, label: str):
    status = "PASS" if ok else "FAIL"
    logger.info(f"  [{status}] {label}")
    return ok


# ── Test runners ──────────────────────────────────────────────────────────────

def test_x_thread(session_dir: str = None, account_label: str = "main"):
    """Post a true X thread (reply chain) and verify it succeeded."""
    hr(f"X THREAD — @{account_label}")
    from src.utils.x_browser_poster import XBrowserPoster
    kwargs = {"headless": False}
    if session_dir:
        kwargs["session_dir"] = session_dir
    poster = XBrowserPoster(**kwargs)

    if not poster.enabled:
        logger.warning(f"  [SKIP] X Browser Poster disabled for '{account_label}' — session missing")
        return False

    thread_data = {
        "tweets": THREAD_TWEETS,
        "tweet_count": len(THREAD_TWEETS),
        "copy_paste_ready": "\n\n".join(THREAD_TWEETS),
        "type": "test",
    }

    logger.info(f"  Posting {len(THREAD_TWEETS)}-tweet thread to X ({account_label})...")
    res = poster.post_thread(thread_data)

    ok = bool(res and res.get("success"))
    result(ok, f"X Thread ({account_label}) — {res.get('posted_count', 0) if res else 0} tweets posted")
    if not ok and res:
        logger.error(f"  Error: {res.get('error', 'unknown')}")
    return ok


def test_x_article(session_dir: str = None, account_label: str = "main"):
    """Post an X Article and verify."""
    hr(f"X ARTICLE — @{account_label}")
    from src.utils.x_browser_poster import XBrowserPoster
    kwargs = {"headless": False}
    if session_dir:
        kwargs["session_dir"] = session_dir
    poster = XBrowserPoster(**kwargs)

    if not poster.enabled:
        logger.warning(f"  [SKIP] X Browser Poster disabled for '{account_label}' — session missing")
        return False

    logger.info(f"  Posting article: '{X_ARTICLE_TITLE}'...")
    res = poster.post_article(X_ARTICLE_TITLE, X_ARTICLE_BODY)

    ok = bool(res)
    result(ok, f"X Article ({account_label}) — {'posted' if ok else 'FAILED'}")
    return ok


def test_substack_note():
    """Post a Substack Note."""
    hr("SUBSTACK NOTE")
    from src.utils.substack_browser_poster import SubstackBrowserPoster
    poster = SubstackBrowserPoster()

    if not poster.enabled:
        logger.warning("  [SKIP] Substack Browser Poster disabled — session missing")
        return False

    logger.info(f"  Posting note ({len(SUBSTACK_NOTE)} chars)...")
    note_id = poster.post_note(SUBSTACK_NOTE)

    ok = bool(note_id)
    result(ok, f"Substack Note — {'posted (ID: ' + str(note_id) + ')' if ok else 'FAILED'}")
    return ok


def test_substack_article():
    """Post a Substack Article."""
    hr("SUBSTACK ARTICLE")
    from src.utils.substack_browser_poster import SubstackBrowserPoster
    poster = SubstackBrowserPoster()

    if not poster.enabled:
        logger.warning("  [SKIP] Substack Browser Poster disabled — session missing")
        return False

    logger.info(f"  Posting article: '{SUBSTACK_ARTICLE_TITLE}'...")
    art_id = poster.post_article(SUBSTACK_ARTICLE_TITLE, SUBSTACK_ARTICLE_BODY)

    ok = bool(art_id)
    result(ok, f"Substack Article — {'posted (ID: ' + str(art_id) + ')' if ok else 'FAILED'}")
    return ok


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Verify all posting channels")
    p.add_argument("--x-thread",   action="store_true", help="Test X thread (main account)")
    p.add_argument("--x-article",  action="store_true", help="Test X article (main account)")
    p.add_argument("--x-cockpit",  action="store_true", help="Test X thread (@CreviaCockpit)")
    p.add_argument("--sub-note",   action="store_true", help="Test Substack note")
    p.add_argument("--sub-article", action="store_true", help="Test Substack article")
    p.add_argument("--all",        action="store_true", help="Run all tests")
    return p.parse_args()


def main():
    args = parse_args()
    run_all = args.all or not any([
        args.x_thread, args.x_article, args.x_cockpit,
        args.sub_note, args.sub_article,
    ])

    results = {}

    if run_all or args.x_thread:
        results["X Thread (main)"] = test_x_thread()

    if run_all or args.x_article:
        results["X Article (main)"] = test_x_article()

    if run_all or args.x_cockpit:
        cockpit_dir = str(Path(__file__).parent / "x_browser_session_cockpit")
        results["X Thread (@CreviaCockpit)"] = test_x_thread(
            session_dir=cockpit_dir, account_label="CreviaCockpit"
        )

    if run_all or args.sub_note:
        results["Substack Note"] = test_substack_note()

    if run_all or args.sub_article:
        results["Substack Article"] = test_substack_article()

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("  SUMMARY")
    logger.info(f"{'='*70}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for label, ok in results.items():
        logger.info(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    logger.info(f"\n  {passed}/{total} passed")
    logger.info(f"{'='*70}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
