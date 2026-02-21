#!/usr/bin/env python3
"""
DEPRECATED - DO NOT USE

This script uses Claude for DATA fetching which wastes API tokens.
Use main.py instead, which uses DataAggregator for data and
Claude only for content writing.

To run the analysis engine:
    python main.py

Old description (for reference):
Automated Crypto Research Loop - Runs Claude AI research every 60 seconds.
This approach has been replaced by DataAggregator + main.py orchestrator.
"""

import sys
print("=" * 60)
print("DEPRECATED: This script is no longer recommended.")
print("")
print("Use 'python main.py' instead, which:")
print("  - Fetches data from free APIs (no Claude tokens wasted)")
print("  - Uses Claude ONLY for content writing (threads, reports)")
print("=" * 60)
sys.exit(1)

# --- ORIGINAL CODE BELOW (kept for reference) ---

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.enhanced_data_fetchers import AutomatedResearchLoop
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Optional backup API keys for fallback when scraping limits are hit
BACKUP_API_KEYS = {
    'coingecko': os.getenv('COINGECKO_API_KEY', ''),
    'glassnode': os.getenv('GLASSNODE_API_KEY', ''),
    'cryptopanic': os.getenv('CRYPTOPANIC_API_KEY', ''),
    'etherscan': os.getenv('ETHERSCAN_API_KEY', ''),
}

if not ANTHROPIC_API_KEY:
    print("❌ ERROR: ANTHROPIC_API_KEY not set!")
    print("\nPlease set your Anthropic API key:")
    print("  export ANTHROPIC_API_KEY='sk-ant-...'\n")
    print("Or add to .env file:")
    print("  ANTHROPIC_API_KEY=sk-ant-...\n")
    sys.exit(1)

print("=" * 80)
print("AUTOMATED CRYPTO RESEARCH LOOP")
print("=" * 80)
print()
print("This will research crypto markets every 60 seconds using Claude AI")
print("No crypto API keys needed - Claude searches the web!")
print()
print("Research includes:")
print("  • Market overview")
print("  • BTC analysis")
print("  • ETH analysis")
print("  • Rotating sector analysis (memecoins, DeFi, privacy)")
print()
print("Results saved to: research_YYYYMMDD_HHMMSS.json")
print()
print("Press Ctrl+C to stop")
print("=" * 80)
print()

# Create and start research loop
loop = AutomatedResearchLoop(
    claude_api_key=ANTHROPIC_API_KEY,
    interval_seconds=60,  # Research every 60 seconds
    backup_api_keys=BACKUP_API_KEYS
)

try:
    loop.start()
except KeyboardInterrupt:
    print("\n✅ Research loop stopped successfully")
    print(f"Latest research available in: {loop.get_latest_research()}")