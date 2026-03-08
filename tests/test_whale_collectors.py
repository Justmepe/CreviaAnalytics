# -*- coding: utf-8 -*-
"""
Quick integration test for Etherscan + Solscan collectors.
Runs both pollers once and reports what was returned.

Usage:
    python tests/test_whale_collectors.py
"""

import asyncio
import os
import sys

# Force UTF-8 output so the script runs cleanly on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.data.whale_collector import WhaleCollector


async def main():
    collector = WhaleCollector()

    eth_key = os.getenv('ETHERSCAN_API_KEY', '')
    sol_key = os.getenv('SOLSCAN_API_KEY', '')

    print(f"ETHERSCAN_API_KEY : {'[OK] set (' + eth_key[:6] + '...)' if eth_key else '[!!] missing'}")
    print(f"SOLSCAN_API_KEY   : {'[OK] set (' + sol_key[:6] + '...)' if sol_key else '[!!] missing'}")
    print()

    # -- Etherscan ---------------------------------------------------------------
    print("-- Etherscan (ETH large transfers) --")
    if not eth_key:
        print("  SKIPPED -- key not configured")
    else:
        try:
            results = await collector.poll_eth_large_transfers()
            if results:
                print(f"  [OK] {len(results)} transaction(s) above threshold")
                for tx in results[:3]:
                    print(f"     {tx['tx_hash'][:12]}...  {tx['amount_native']:.2f} ETH"
                          f"  (${tx['amount_usd']:,.0f})"
                          f"  {tx['from_address'][:10]}... -> {tx['to_address'][:10]}...")
                if len(results) > 3:
                    print(f"     ... and {len(results) - 3} more")
            else:
                print("  [WARN] 0 transactions above threshold (500 ETH minimum)")
                print("         API responded OK but no txns met the size filter")
        except Exception as e:
            print(f"  [FAIL] {e}")

    print()

    # -- Solscan ---------------------------------------------------------------
    print("-- Solscan (SOL large transfers) --")
    if not sol_key:
        print("  NOTE: running without auth key (public rate limit applies)")

    try:
        results = await collector.poll_sol_large_transfers()
        if results:
            print(f"  [OK] {len(results)} transaction(s) above threshold")
            for tx in results[:3]:
                print(f"     {tx['tx_hash'][:12]}...  {tx['amount_native']:.0f} SOL"
                      f"  (${tx['amount_usd']:,.0f})")
            if len(results) > 3:
                print(f"     ... and {len(results) - 3} more")
        else:
            print("  [WARN] 0 transactions above threshold (10,000 SOL minimum)")
            print("         API responded OK but no txns met the size filter")
    except Exception as e:
        print(f"  [FAIL] {e}")

    print()

    # -- Queue check -----------------------------------------------------------
    queued = collector.queue.qsize()
    print(f"-- Queue: {queued} item(s) emitted total --")

    await collector._close()


if __name__ == '__main__':
    asyncio.run(main())
