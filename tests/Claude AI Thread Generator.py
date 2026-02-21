#!/usr/bin/env python3
"""
Claude AI X/Twitter Thread Generator
Uses Claude to write a professional, engaging thread from analysis data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add project root to path

import os
import anthropic
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("=" * 80)
print("CLAUDE AI X/TWITTER THREAD GENERATOR")
print("=" * 80)

# =============================================================================
# Check Claude API Setup
# =============================================================================

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

if not ANTHROPIC_API_KEY:
    print("\n❌ ANTHROPIC_API_KEY not found!")
    print("\nTo use Claude for thread generation:")
    print("1. Get API key from: https://console.anthropic.com/")
    print("2. Add to .env file: ANTHROPIC_API_KEY=your_key_here")
    print("3. Run this script again")
    print("\n💡 Claude can write much more engaging threads than templates!")
    sys.exit(1)

print("✅ Claude API key found - ready to generate!")

# Test Claude API connectivity
print("\n[Step 0] Testing Claude API connectivity...")
try:
    test_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    test_response = test_client.messages.create(
        model="claude-3-5-sonnet-20240620",  # Try a known working model
        max_tokens=50,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("   ✅ Claude API connection successful!")
except Exception as e:
    print(f"   ❌ Claude API connection failed: {e}")
    print("   💡 Check your internet connection or API key validity")
    print("   💡 You can still use the template generator:")
    print("      python 'tests/Example generate x thread - MULTIPLE ASSETS.py'")
    sys.exit(1)

# =============================================================================
# Load Analysis Data (from our enhanced run)
# =============================================================================

print("\n[Step 1] Loading comprehensive analysis data...")

from src.analyzers.majors_analyzer import analyze_major
from src.analyzers.memecoin_analyzer import analyze_memecoin
from src.analyzers.privacy_analyzer import analyze_privacy_coin
from src.analyzers.defi_analyzer import analyze_defi_protocol

# Load the same data from our enhanced run
btc = analyze_major('BTC')
eth = analyze_major('ETH')

memecoins = [
    analyze_memecoin('DOGE'),
    analyze_memecoin('SHIB'),
    analyze_memecoin('PEPE'),
    analyze_memecoin('FLOKI'),
    analyze_memecoin('BONK')
]

privacy_coins = [
    analyze_privacy_coin('XMR'),
    analyze_privacy_coin('ZEC'),
    analyze_privacy_coin('DASH'),
    analyze_privacy_coin('XEM')
]

defi_protocols = [
    analyze_defi_protocol('AAVE'),
    analyze_defi_protocol('UNI'),
    analyze_defi_protocol('CRV'),
    analyze_defi_protocol('COMP'),
    analyze_defi_protocol('MKR')
]

print(f"   ✓ Loaded {2 + len(memecoins) + len(privacy_coins) + len(defi_protocols)} analyses")

# =============================================================================
# Generate Claude Prompt for Professional Thread
# =============================================================================

print("\n[Step 2] Creating Claude prompt for professional thread...")

def create_comprehensive_thread_prompt(
    btc_analysis: Dict,
    eth_analysis: Dict,
    memecoins: List[Dict],
    privacy_coins: List[Dict],
    defi_protocols: List[Dict]
) -> str:
    """Create a comprehensive prompt for Claude to write a professional X thread"""

    # Extract key market data
    btc_price = btc_analysis.get('snapshot', {}).get('current_price', 'Unknown')
    eth_price = eth_analysis.get('snapshot', {}).get('current_price', 'Unknown')
    btc_change = btc_analysis.get('snapshot', {}).get('price_change_24h', 'Unknown')
    eth_change = eth_analysis.get('snapshot', {}).get('price_change_24h', 'Unknown')

    # Get market sentiment (try to get Fear & Greed from various sources)
    fear_greed = "14 (Extreme Fear)"  # From our recent analysis

    # Extract key insights from each sector
    def summarize_sector(analyses: List[Dict], sector_name: str) -> str:
        """Summarize key insights from a sector"""
        insights = []
        for analysis in analyses[:3]:  # Top 3 insights
            ticker = analysis.get('ticker', 'Unknown')
            snapshot = analysis.get('snapshot', {}).get('summary', 'No data')
            insights.append(f"• {ticker}: {snapshot}")
        return "\n".join(insights)

    meme_insights = summarize_sector(memecoins, "Memecoins")
    privacy_insights = summarize_sector(privacy_coins, "Privacy")
    defi_insights = summarize_sector(defi_protocols, "DeFi")

    # Create comprehensive prompt
    prompt = f"""<task>
Write a professional, engaging X/Twitter thread about the current crypto market conditions. Make it informative, data-driven, and engaging for crypto traders and investors.
</task>

<market_overview>
Current Date: {datetime.now().strftime('%B %d, %Y')}
BTC Price: ${btc_price}
ETH Price: ${eth_price}
BTC 24h Change: {btc_change}
ETH 24h Change: {eth_change}
Fear & Greed Index: {fear_greed}
Total Market Cap: ~$3.1T
</market_overview>

<sector_analysis>
MEMECOINS (Top Insights):
{meme_insights}

PRIVACY COINS (Top Insights):
{privacy_insights}

DEFI PROTOCOLS (Top Insights):
{defi_insights}
</sector_analysis>

<writing_requirements>
• Format as a 10-tweet thread (1/, 2/, 3/, etc.)
• Each tweet under 280 characters
• Professional analyst tone - informative, not hype
• Include specific data points and price levels
• End with engagement question
• Add relevant hashtags at the end
• Use market analysis terminology appropriately
• Focus on "what's happening now" not predictions
• NO financial advice or trading recommendations
</writing_requirements>

<thread_structure>
1. Opening: Market overview with key levels
2. Sentiment: Fear & Greed analysis and implications
3. Macro: Broader market conditions and drivers
4. Key Levels: Support/resistance with technical context
5. Memecoins: Sector analysis and key movers
6. Privacy: Regulatory context and performance
7. DeFi: TVL trends and protocol highlights
8. Whale Activity: Institutional positioning insights
9. Alt Rotation: Sector rotation and opportunities
10. Final Take: Summary with key takeaways and engagement hook
</thread_structure>

<critical_rules>
• NO PREDICTIONS about future price movements
• NO BUY/SELL/HOLD recommendations
• Focus on current conditions and analysis
• Use phrases like "suggests", "indicates", "likely driven by"
• Be factual and data-driven
• Maintain professional, credible tone
</critical_rules>

Write the complete 10-tweet thread now:"""

    return prompt

# Generate the prompt
claude_prompt = create_comprehensive_thread_prompt(
    btc, eth, memecoins, privacy_coins, defi_protocols
)

print("   ✓ Professional Claude prompt created")

# =============================================================================
# Call Claude API to Generate Thread
# =============================================================================

print("\n[Step 3] Calling Claude to write the thread...")

try:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4000,
        temperature=0.7,  # Creative but professional
        system="You are a professional crypto market analyst writing for X/Twitter. Write engaging, informative content that educates and engages the crypto community.",
        messages=[
            {
                "role": "user",
                "content": claude_prompt
            }
        ]
    )

    claude_thread = response.content[0].text
    print("   ✓ Claude generated professional thread!")

except Exception as e:
    print(f"   ❌ Claude API error: {e}")
    print("   💡 Check your ANTHROPIC_API_KEY and try again")
    sys.exit(1)

# =============================================================================
# Format for Copy-Paste
# =============================================================================

print("\n[Step 4] Formatting for X/Twitter...")

def format_claude_thread_for_twitter(thread_text: str) -> str:
    """Format Claude's thread for easy copy-paste to Twitter"""
    # Split by numbered tweets and clean up
    lines = thread_text.strip().split('\n')
    formatted_tweets = []

    current_tweet = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this starts a new tweet (1., 2., etc.)
        if line.match(r'^\d+\.') or line.startswith(('1/', '2/', '3/')):
            if current_tweet:
                formatted_tweets.append(current_tweet.strip())
            current_tweet = line
        else:
            current_tweet += " " + line

    # Add the last tweet
    if current_tweet:
        formatted_tweets.append(current_tweet.strip())

    # Join with separators
    return '\n⸻\n'.join(formatted_tweets)

formatted_thread = format_claude_thread_for_twitter(claude_thread)

# =============================================================================
# Display Results
# =============================================================================

print("\n" + "=" * 80)
print("CLAUDE-GENERATED X THREAD")
print("=" * 80)
print()
print(formatted_thread)
print()
print("=" * 80)

# =============================================================================
# Save to File
# =============================================================================

print("\n[Step 5] Saving Claude thread...")

filename = f"x_thread_claude_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

with open(filename, 'w', encoding='utf-8') as f:
    f.write(formatted_thread)

print(f"   ✓ Saved to: {filename}")

# =============================================================================
# Comparison with Template
# =============================================================================

print("\n" + "=" * 80)
print("COMPARISON: Template vs Claude")
print("=" * 80)

print("""
TEMPLATE-GENERATED THREAD:
• Uses predefined templates and phrases
• Consistent structure but predictable
• Fast generation (no API calls)
• Good for automation and consistency

CLAUDE-GENERATED THREAD:
• Creative, natural writing style
• More engaging and human-like
• Adapts tone and phrasing dynamically
• Better at storytelling and engagement
• More professional analyst voice

WHICH IS BETTER?
• Claude threads are generally more engaging and professional
• But require API calls (cost and speed)
• Template threads are reliable and instant
• Use Claude for important posts, templates for regular updates
""")

print("\n✅ Claude thread generation complete!")
print(f"\n📄 Claude thread saved to: {filename}")
print("\n💡 Copy the thread above and post to X/Twitter!")
print("\n🔄 Want another thread? Run this script again with fresh data!")