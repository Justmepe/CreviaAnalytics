"""
X (Twitter) Thread Builder with Claude AI Support

Formats analysis content into optimized tweet threads:
- Breaks long text into tweet segments (280 chars max)
- Adds thread markers (1/, 2/, 3/... or natural flow)
- Generates thread objects with metadata
- Supports multiple thread types (daily scan, breaking news, analysis)
- Optional Claude AI integration for natural, flowing content
- Strategic emoji usage for category/sentiment indication
- Comprehensive thread structure (12+ tweets with narrative flow)
"""

import re
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class Tweet:
    """Single tweet in a thread"""
    text: str
    position: int  # Position in thread (1, 2, 3...)
    total_in_thread: int  # Total tweets in thread
    character_count: int = 0
    
    def __post_init__(self):
        self.character_count = len(self.text)
    
    def is_valid(self) -> bool:
        """Check if tweet is valid (≤280 chars)"""
        return self.character_count <= 280
    
    def get_display_text(self) -> str:
        """Get displayable tweet text"""
        return self.text


@dataclass
class ThreadMetadata:
    """Metadata for a complete thread"""
    thread_id: str
    thread_type: str  # 'daily_scan', 'breaking_news', 'analysis'
    created_at: str
    tweet_count: int
    total_characters: int
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


class ThreadBuilder:
    """
    Builds optimized tweet threads from analysis content.
    
    Handles:
    - Text segmentation into 280-char chunks
    - Thread numbering (1/, 2/, 3/... or natural)
    - Hook/opener for first tweet
    - Call-to-action for last tweet
    - Hashtag optimization
    """
    
    MAX_TWEET_LENGTH = 280
    TWITTER_URL_LENGTH = 23  # X counts URLs as fixed 23 chars
    
    def __init__(self):
        self.tweets: List[Tweet] = []
        self.metadata: Optional[ThreadMetadata] = None
    
    # =========================================================================
    # Main Building Methods
    # =========================================================================
    
    def build_daily_scan_thread(
        self,
        summary: str,
        key_moves: List[str],
        market_analysis: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Build a 'Daily Scan' thread (what happened in last 24 hours).
        
        Structure:
        1/ Opening hook
        2/ Key market moves (formatted list)
        3/ Analysis
        4/ Impact & outlook
        5/ Closing CTA
        """
        self.tweets = []
        
        # Tweet 1: Opening hook
        hook = f"📊 DAILY SCAN: {summary}\n\nThread on last 24h action 👇"
        self.tweets.append(Tweet(
            text=hook,
            position=1,
            total_in_thread=0  # Will update
        ))
        
        # Tweet 2-3: Key moves (formatted as list)
        moves_text = "Key moves:\n" + "\n".join(f"• {move}" for move in key_moves)
        self._add_wrapped_tweet(moves_text)
        
        # Tweet N: Analysis
        self._add_wrapped_tweet(f"Analysis:\n{market_analysis}")
        
        # Final tweet: CTA
        closing = "What's your take? Reply with your analysis 👇\n\n#Crypto #Markets"
        self.tweets.append(Tweet(
            text=closing,
            position=len(self.tweets) + 1,
            total_in_thread=0
        ))
        
        # Update thread positions
        total = len(self.tweets)
        for i, tweet in enumerate(self.tweets):
            tweet.position = i + 1
            tweet.total_in_thread = total
        
        # Add numbering
        self._add_thread_numbering()
        
        # Create metadata
        self.metadata = ThreadMetadata(
            thread_id=f"daily_scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            thread_type="daily_scan",
            created_at=datetime.now(timezone.utc).isoformat(),
            tweet_count=len(self.tweets),
            total_characters=sum(t.character_count for t in self.tweets),
            tags=tags or ["crypto", "markets", "analysis"]
        )
        
        return self.to_dict()
    
    def build_breaking_news_thread(
        self,
        headline: str,
        what_happened: str,
        impact: str = None,
        our_take: str = None,
        tags: List[str] = None,
        use_claude: bool = True
    ) -> Dict[str, Any]:
        """
        Build a 'Breaking News' thread (event-triggered).

        Uses Claude AI by default for professional Bloomberg-quality analysis.
        Falls back to template if Claude unavailable.

        Args:
            headline: News headline
            what_happened: Summary/description of the event
            impact: Optional impact analysis (used in fallback)
            our_take: Optional analysis (used in fallback)
            tags: Optional hashtags
            use_claude: Whether to use Claude AI (default: True)

        Returns:
            Dict with thread data
        """

        # Try Claude AI first if enabled
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if use_claude and api_key:
            try:
                return self._generate_breaking_news_with_claude(
                    headline=headline,
                    what_happened=what_happened,
                    tags=tags
                )
            except Exception as e:
                print(f"[WARN] Claude breaking news generation failed: {e}. Using template.")

        # Fallback to template-based generation
        return self._generate_breaking_news_template(
            headline=headline,
            what_happened=what_happened,
            impact=impact or "High-impact event",
            our_take=our_take or "Developing story",
            tags=tags
        )

    def _generate_breaking_news_with_claude(
        self,
        headline: str,
        what_happened: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Generate professional breaking news thread with Claude AI"""
        from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required for Claude generation")

        now = datetime.now(timezone.utc)
        date_str = now.strftime('%B %d, %Y')
        time_str = now.strftime('%H:%M UTC')

        # Claude prompt for professional breaking news
        prompt = f"""You are a PROFESSIONAL crypto analyst writing a breaking news thread for X/Twitter.

BREAKING NEWS:
Headline: {headline}
Details: {what_happened}

DATE/TIME: {date_str}, {time_str}

TASK: Write a professional 5-7 tweet thread analyzing this breaking news.

STRUCTURE:
Tweet 1: 🚨 BREAKING alert with headline
Tweet 2: WHAT HAPPENED - Concise factual summary
Tweet 3: CONTEXT - Why this matters, background, key players involved
Tweet 4: MARKET IMPACT - How this affects crypto markets, prices, sentiment
Tweet 5: ANALYSIS - Professional take on implications, what to watch next
Tweet 6 (optional): KEY LEVELS - Specific price levels or metrics to monitor
Tweet 7: BOTTOM LINE - Concise takeaway + what traders/investors should do

CRITICAL RULES:
1. Professional Bloomberg/Reuters tone - serious, factual, data-driven
2. NO speculation or predictions - stick to facts and known implications
3. Each tweet 220-275 chars (leave room for numbering)
4. Use emojis strategically: 🚨 for alert, ⚠️ for caution, 📊 for data, 💡 for insights
5. Include date/time reference in tweet 1
6. Number tweets clearly: 1/, 2/, 3/, etc.
7. Focus on ACTIONABLE insights - what this means for markets
8. If price movements mentioned, be specific with numbers
9. Maintain credibility - acknowledge what we DON'T know
10. End with clear takeaway, not generic CTA

TONE:
- Professional but engaging (Bloomberg meets X/Twitter)
- Factual and credible, not sensational
- Clear and concise, every word adds value
- Authoritative but measured

FORMAT EXAMPLE:
1/ 🚨 BREAKING: [Headline]

{date_str}, {time_str}

[One-sentence hook that captures why this matters]

2/ WHAT HAPPENED

[Factual 2-3 sentence summary of the event. Who, what, when, where.]

3/ CONTEXT

[Why this matters. Background. Key players. Historical precedent if relevant.]

(continue with numbered tweets...)

Return ONLY the complete thread with numbered tweets. No preamble or explanation."""

        claude_engine = ClaudeResearchEngine(api_key)
        response = claude_engine._call_model(prompt, max_tokens=1500)

        # Extract text
        thread_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                thread_text += block.text

        # Split into tweets
        tweets = self._split_claude_thread(thread_text)

        if len(tweets) < 3:
            # Claude didn't format properly, fallback
            raise ValueError("Claude returned insufficient tweets")

        return {
            'thread': thread_text,
            'tweets': tweets,
            'tweet_count': len(tweets),
            'copy_paste_ready': '\n\n'.join(tweets),
            'generated_by': 'Claude AI (Breaking News)',
            'date_generated': date_str,
            'type': 'breaking_news',
            'tags': tags or ['breaking', 'crypto']
        }

    def _generate_breaking_news_template(
        self,
        headline: str,
        what_happened: str,
        impact: str,
        our_take: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Fallback template-based breaking news thread"""
        self.tweets = []

        # Tweet 1: Breaking news alert
        alert = f"🚨 BREAKING: {headline}"
        self.tweets.append(Tweet(
            text=alert,
            position=1,
            total_in_thread=0
        ))

        # Tweet 2: Context
        self._add_wrapped_tweet(f"What happened:\n{what_happened}")

        # Tweet N: Impact
        self._add_wrapped_tweet(f"Market impact:\n{impact}")

        # Tweet N+1: Our analysis
        self._add_wrapped_tweet(f"Our take:\n{our_take}")

        # Final: CTA
        closing = "How does this affect your strategy? Drop your thoughts 👇"
        self.tweets.append(Tweet(
            text=closing,
            position=len(self.tweets) + 1,
            total_in_thread=0
        ))

        # Update positions
        total = len(self.tweets)
        for i, tweet in enumerate(self.tweets):
            tweet.position = i + 1
            tweet.total_in_thread = total

        self._add_thread_numbering()

        self.metadata = ThreadMetadata(
            thread_id=f"news_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            thread_type="breaking_news",
            created_at=datetime.now(timezone.utc).isoformat(),
            tweet_count=len(self.tweets),
            total_characters=sum(t.character_count for t in self.tweets),
            tags=tags or ["breaking", "news", "crypto"]
        )

        return self.to_dict()
    
    def build_hourly_scan_thread(
        self,
        summary: str,
        price_changes: Dict[str, float],  # {"BTC": 2.5, "ETH": -1.2}
        key_events: List[str],
        market_sentiment: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Build an 'Hourly Scan' thread (real-time market updates).
        
        Structure:
        1/ Opening - what's changing now
        2/ Price moves (formatted list)
        3/ Key events
        4/ Market sentiment
        5/ Closing CTA
        """
        self.tweets = []
        
        # Tweet 1: Opening hook
        hook = f"⏰ HOURLY SCAN: {summary}\n\nLive market update 👇"
        self.tweets.append(Tweet(
            text=hook,
            position=1,
            total_in_thread=0
        ))
        
        # Tweet 2-3: Price changes (formatted as list)
        if price_changes:
            price_text = "Price movements:\n"
            for asset, change in price_changes.items():
                arrow = "📈" if change > 0 else "📉"
                price_text += f"{arrow} {asset}: {change:+.2f}%\n"
            self._add_wrapped_tweet(price_text)
        
        # Tweet N: Key events
        if key_events:
            events_text = "Key events:\n" + "\n".join(f"• {event}" for event in key_events)
            self._add_wrapped_tweet(events_text)
        
        # Tweet N+1: Sentiment
        self._add_wrapped_tweet(f"Market sentiment:\n{market_sentiment}")
        
        # Final tweet: CTA
        closing = "What moves are you watching? Reply below 👇\n\n#Crypto #Markets #Live"
        self.tweets.append(Tweet(
            text=closing,
            position=len(self.tweets) + 1,
            total_in_thread=0
        ))
        
        # Update thread positions
        total = len(self.tweets)
        for i, tweet in enumerate(self.tweets):
            tweet.position = i + 1
            tweet.total_in_thread = total
        
        # Add numbering
        self._add_thread_numbering()
        
        # Create metadata
        self.metadata = ThreadMetadata(
            thread_id=f"hourly_scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            thread_type="hourly_scan",
            created_at=datetime.now(timezone.utc).isoformat(),
            tweet_count=len(self.tweets),
            total_characters=sum(t.character_count for t in self.tweets),
            tags=tags or ["crypto", "markets", "live", "analysis"]
        )
        
        return self.to_dict()
    
    def build_with_claude_ai(
        self,
        analysis_data: Dict[str, Any],
        thread_type: str = 'comprehensive',
        max_tweets: int = 12
    ) -> Dict[str, Any]:
        """
        Build thread using Claude AI for natural, flowing content.
        Uses comprehensive prompts inspired by Bloomberg crypto analysis.
        
        Args:
            analysis_data: Dict with 'majors' (BTC/ETH/SOL/BNB), 'defi', 'memecoins', 
                          'privacy_coins', 'market_context' (cap, dominance, sentiment)
            thread_type: 'comprehensive' (12+ tweets), 'quick' (5-7 tweets), 'focused' (3-5 tweets)
            max_tweets: Maximum tweets to generate
        
        Returns:
            Dict with 'thread', 'tweets', 'tweet_count', 'copy_paste_ready'
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Fall back to template-based if Claude not available
            return self._build_with_templates(analysis_data)
        
        try:
            return self._generate_with_claude(analysis_data, thread_type, max_tweets)
        except Exception as e:
            print(f"[WARN] Claude generation failed: {e}. Using template fallback.")
            return self._build_with_templates(analysis_data)
    
    def _generate_with_claude(
        self,
        data: Dict[str, Any],
        thread_type: str,
        max_tweets: int
    ) -> Dict[str, Any]:
        """Generate comprehensive thread using Claude AI"""
        from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

        # Get API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        now = datetime.now(timezone.utc)
        date_str = now.strftime('%B %d, %Y')
        time_str = now.strftime('%H:%M UTC')
        
        # Build comprehensive context
        context = {
            'date': date_str,
            'time': time_str,
            'majors': data.get('majors', {}),
            'market': data.get('market_context', {}),
            'defi': data.get('defi', []),
            'memecoins': data.get('memecoins', []),
            'privacy_coins': data.get('privacy_coins', [])
        }
        
        context_json = json.dumps(context, indent=2)
        
        # Sophisticated claude prompt with detailed requirements
        if thread_type == 'comprehensive':
            thread_structure = """
COMPREHENSIVE DAILY SCAN THREAD STRUCTURE (12+ tweets):

Tweet 1: 📊 DAILY CRYPTO MARKET SCAN
- Date: {date}
- Time: {time}
- Opening hook that sets the tone

Tweet 2: 1️⃣ Market Overview (Top-Down Snapshot)
- Total Market Cap: $ + 24h Change %
- 24h Liquidations: $ (Longs $ / Shorts $)
- Bitcoin Dominance: %
- Fear & Greed Index: {value} ({label})
- Narrative Summary (2-3 sentences): What's happening structurally? Risk-on or risk-off? Who's getting squeezed?

Tweet 3: 2️⃣ Bitcoin (BTC) Analysis - Price & Structure
- Current Price: $ + 24h/7d Change %
- Trend: Bullish/Bearish/Range
- Market Structure: HH/HL or LH/LL
- Trading above/below key MAs

Tweet 4: Bitcoin - Key Levels & Derivatives
- Major Resistance/Support
- Funding Rate: %
- Open Interest: $ (↑/↓)
- Interpretation: Leading or lagging? Squeeze setup?

Tweet 5: 3️⃣ Ethereum (ETH) Analysis
- Price: $ + 24h Change %
- ETH/BTC Pair Trend
- Dominance Change
- Key Resistance/Support
- Is ETH gaining relative strength? Capital rotation?

Tweet 6: 4️⃣ Altcoin Market & Sector Rotation
- TOTAL3 structure & trend
- Top Performers (24h): List with %
- Worst Performers: List with %
- Sector highlights: AI, DeFi, Gaming, Memes, RWA
- Is capital rotating or exiting risk?

Tweet 7: 5️⃣ Derivatives & Leverage Data
- Total Liquidations (24h)
- Long/Short Ratio
- Funding extremes? OI vs Price divergence?
- Interpretation: Squeeze setup? Spot-driven or leverage-driven?

Tweet 8: 6️⃣ Stablecoin Flows & Liquidity
- USDT/USDC Market Cap Changes
- Exchange Net flows (Inflow/Outflow)
- Is fresh capital entering or leaving?

Tweet 9: 7️⃣ Macro & External Catalysts
- Traditional Markets: S&P 500, Nasdaq, DXY, 10Y Yield
- Events Today: CPI/FOMC/ETF flows/Regulation/Unlocks
- Is crypto reacting to macro or trading independently?

Tweet 10: 8️⃣ On-Chain Highlights (if available)
- Whale Transactions
- Exchange Reserves Trend
- Miner Flows
- ETF Net Inflows/Outflows

Tweet 11: 9️⃣ Sentiment & Positioning
- Fear & Greed deeper analysis
- Social Sentiment & Retail Activity
- Are we in euphoria, disbelief, panic, or exhaustion?

Tweet 12: 🔟 Scenarios & Trade Setup
🟢 Bullish Scenario: Trigger, Targets, Invalidation
🔴 Bearish Scenario: Trigger, Targets, Invalidation

Tweet 13: 1️⃣1️⃣ Risk Assessment
- Volatility: Expanding/Contracting
- Liquidity: Thin/Thick
- Event Risk & Weekend Risk
- Risk Level Today: Low/Medium/High

Tweet 14+: 1️⃣2️⃣ Professional Notes & CTA
- Accumulation or distribution?
- Who is trapped?
- What would hurt most participants?
- Final call-to-action

CRITICAL: Each section MUST reference actual data from the provided JSON. Do NOT invent numbers.
"""
        else:
            thread_structure = f"""
Generate {['quick (5-7)', 'focused (3-5)'][thread_type == 'focused']} tweet thread covering:
- Market environment and sentiment
- Major assets (BTC, ETH, SOL) with prices and funding
- Key notable moves in DeFi/Memecoins if relevant
- Derivatives setup (liquidations, funding)
- Action items for traders
"""

        prompt = f"""You are a PROFESSIONAL crypto analyst writing a Bloomberg-quality X/Twitter thread.

CRITICAL: Today's date is {date_str} at {time_str}. Use these EXACT values. Do NOT guess or invent dates/times.

MARKET DATA (Real-time from Binance/CoinGecko/Coinglass):
{context_json}

{thread_structure}

CRITICAL RULES - READ CAREFULLY:
1. Use ONLY data from the JSON above. Do NOT invent or hallucinate prices/numbers
2. If data is missing (null, 0, or unavailable), state "data unavailable" or skip that metric
3. Include EXACT date/time in tweet 1: "{date_str}, {time_str}"
4. For liquidations: Use liquidations_24h_long and liquidations_24h_short from derivatives data
5. For Fear & Greed: Use exact value and classification from market_context
6. Mention ALL coins provided in each sector (majors, defi, memecoins, privacy)
7. NO price predictions. Focus on "what happened" and "why", not "what will happen"
8. If funding rate is 0, say "neutral funding" not "0% funding"
9. Be specific with percentages (e.g., "BTC +2.3%" not "BTC up")

TONE & STYLE:
- Professional, data-driven analysis (Bloomberg Terminal meets X/Twitter)
- Use emojis strategically but professionally:
  📊 for data/metrics, 🚀 for bullish signals, 🐻 for bearish, ⚠️ for risk warnings
  🐸 for memecoins, 🕶️ for privacy coins, 🧩 for DeFi, 💎 for majors
- Each tweet 220-275 chars (leave room for numbering)
- Number tweets clearly: 1/, 2/, 3/, etc.
- Build narrative flow - each tweet builds on the previous
- Include specific percentages, dollar amounts, and data points
- Provide actionable insights and levels traders can watch
- Professional but engaging tone (serious analysis, not hype)

STRUCTURAL REQUIREMENTS:
- First tweet: Hook with date/time
- Middle tweets: Data-driven analysis with specifics
- Final tweets: Scenarios, risk assessment, professional takeaways
- NO generic fluff. Every sentence should add value.
- NO phrases like "let's dive in" or "here's what you need to know"
- Focus on WHY markets are moving (narrative), not just WHAT moved

FORMAT EXAMPLE:
1/ 📊 DAILY CRYPTO MARKET SCAN

{date_str}, {time_str}

Total Cap: $2.1T (+1.2%)
BTC Dom: 56.3%
Fear & Greed: 62 (Greed)
24h Liq: $180M ($120M longs / $60M shorts)

Risk-on environment with shorts getting squeezed.

2/ 1️⃣ BITCOIN ANALYSIS

Price: $43,250 (+2.3% 24h, +5.1% 7d)
Structure: Bullish (HH/HL pattern intact)
Trading above 200 DMA

Resistance: $44,500
Support: $42,000

Funding: +0.015% (neutral-to-positive)
OI: $18.2B (↑ 3.2%)

(continue with numbered tweets following the structure...)

Return ONLY the complete thread with numbered tweets. No preamble or explanation."""
        
        claude_engine = ClaudeResearchEngine(api_key)
        response = claude_engine._call_model(prompt, max_tokens=4000)
        
        # Extract text
        thread_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                thread_text += block.text
        
        # Split into tweets
        tweets = self._split_claude_thread(thread_text)
        
        if len(tweets) < 3:
            # Fallback if Claude didn't format properly
            tweets = split_text_into_tweets(thread_text, max_length=280)
        
        # Format results
        return {
            'thread': thread_text,
            'tweets': tweets,
            'tweet_count': len(tweets),
            'copy_paste_ready': '\n\n'.join(tweets),
            'generated_by': 'Claude AI',
            'date_generated': date_str,
            'type': 'comprehensive_analysis'
        }
    
    def _split_claude_thread(self, thread_text: str) -> List[str]:
        """Split Claude-generated thread into individual tweets"""
        # Try splitting by numbered markers first (1/, 2/, etc.)
        pattern = r'\d+\/\s+'
        parts = re.split(pattern, thread_text)
        
        # Remove empty parts and rejoin with numbering
        tweets = []
        for i, part in enumerate(parts):
            if part.strip():
                tweet = part.strip()
                # Clean up extra blank lines
                tweet = '\n'.join(line for line in tweet.split('\n') if line.strip())
                tweets.append(tweet)
        
        return tweets if tweets else split_text_into_tweets(thread_text)
    
    def _build_with_templates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback template-based thread generation"""
        # Simple fallback that combines available data
        majors = data.get('majors', {})
        defi = data.get('defi', [])
        memes = data.get('memecoins', [])
        
        tweets = [
            f"📊 Market Update\nGenerated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\nThread on today's moves 👇",
            f"Majors: {', '.join(str(m) for m in list(majors.keys())[:4]) if majors else 'TBD'}\nDeFi and Memecoins showing strong activity.",
            f"Key to watch: Major support/resistance levels and on-chain flows.",
            f"What's your take? Share your analysis in the replies 👇"
        ]
        
        return {
            'thread': '\n\n'.join(tweets),
            'tweets': tweets,
            'tweet_count': len(tweets),
            'copy_paste_ready': '\n\n'.join(tweets),
            'generated_by': 'Templates (Claude unavailable)',
            'type': 'quick_update'
        }
    
    # =========================================================================
    # Additional Thread Builders
    # =========================================================================
    
    def build_analysis_thread(
        self,
        title: str,
        sections: Dict[str, str],  # {"section_name": "content..."}
        conclusion: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Build an 'Analysis' thread (deep dive on topic).
        
        Structure:
        1/ Title/hook
        2-N/ Each section as separate tweet(s)
        N+1/ Conclusion
        N+2/ CTA
        """
        self.tweets = []
        
        # Tweet 1: Hook
        hook = f"Deep dive: {title}\n\nThread with analysis 👇"
        self.tweets.append(Tweet(
            text=hook,
            position=1,
            total_in_thread=0
        ))
        
        # Tweets 2-N: Sections
        for section_name, content in sections.items():
            section_text = f"📌 {section_name}:\n{content}"
            self._add_wrapped_tweet(section_text)
        
        # Conclusion
        self._add_wrapped_tweet(f"Conclusion:\n{conclusion}")
        
        # Final CTA
        cta = "What's your take? Let's discuss in replies 👇"
        self.tweets.append(Tweet(
            text=cta,
            position=len(self.tweets) + 1,
            total_in_thread=0
        ))
        
        # Update positions
        total = len(self.tweets)
        for i, tweet in enumerate(self.tweets):
            tweet.position = i + 1
            tweet.total_in_thread = total
        
        self._add_thread_numbering()
        
        self.metadata = ThreadMetadata(
            thread_id=f"analysis_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            thread_type="analysis",
            created_at=datetime.now(timezone.utc).isoformat(),
            tweet_count=len(self.tweets),
            total_characters=sum(t.character_count for t in self.tweets),
            tags=tags or ["analysis", "research"]
        )
        
        return self.to_dict()
    
    def build_custom_thread(
        self,
        segments: List[str],
        thread_type: str = "custom",
        add_numbering: bool = True,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Build custom thread from list of text segments.
        
        Args:
            segments: List of text pieces (will be split if > 280 chars)
            thread_type: Type identifier for this thread
            add_numbering: Whether to add 1/, 2/, 3/... numbering
            tags: Hashtags/tags for the thread
        """
        self.tweets = []
        
        for segment in segments:
            self._add_wrapped_tweet(segment)
        
        # Update positions
        total = len(self.tweets)
        for i, tweet in enumerate(self.tweets):
            tweet.position = i + 1
            tweet.total_in_thread = total
        
        if add_numbering:
            self._add_thread_numbering()
        
        self.metadata = ThreadMetadata(
            thread_id=f"{thread_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            thread_type=thread_type,
            created_at=datetime.now(timezone.utc).isoformat(),
            tweet_count=len(self.tweets),
            total_characters=sum(t.character_count for t in self.tweets),
            tags=tags or []
        )
        
        return self.to_dict()
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _add_wrapped_tweet(self, text: str):
        """
        Add text, wrapping into multiple tweets if necessary.
        Tries to break at sentence boundaries when possible.
        """
        if len(text) <= self.MAX_TWEET_LENGTH:
            # Fits in one tweet
            self.tweets.append(Tweet(
                text=text,
                position=len(self.tweets) + 1,
                total_in_thread=0
            ))
        else:
            # Need to split across multiple tweets
            sentences = text.split('. ')
            current_tweet = ""
            
            for sentence in sentences:
                test_text = current_tweet + sentence + ("." if not sentence.endswith('.') else "")
                
                if len(test_text) <= self.MAX_TWEET_LENGTH:
                    current_tweet = test_text + " "
                else:
                    # Current tweet is full, save it
                    if current_tweet.strip():
                        self.tweets.append(Tweet(
                            text=current_tweet.strip(),
                            position=len(self.tweets) + 1,
                            total_in_thread=0
                        ))
                    current_tweet = sentence + "."
            
            # Add remaining
            if current_tweet.strip():
                self.tweets.append(Tweet(
                    text=current_tweet.strip(),
                    position=len(self.tweets) + 1,
                    total_in_thread=0
                ))
    
    def _add_thread_numbering(self):
        """Add 1/, 2/, 3/... to beginning of each tweet"""
        for i, tweet in enumerate(self.tweets):
            number = f"{i + 1}/"
            
            # Check if adding number would exceed limit
            if len(number) + 1 + len(tweet.text) <= self.MAX_TWEET_LENGTH:
                tweet.text = f"{number} {tweet.text}"
            else:
                # Number would make it too long - skip numbering for this tweet
                pass
    
    def validate_thread(self) -> tuple[bool, List[str]]:
        """
        Validate thread structure.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if not self.tweets:
            errors.append("Thread has no tweets")
            return False, errors
        
        for tweet in self.tweets:
            if not tweet.is_valid():
                errors.append(
                    f"Tweet {tweet.position} exceeds 280 chars "
                    f"({tweet.character_count} chars)"
                )
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thread to dictionary format for storage/transmission"""
        valid, errors = self.validate_thread()
        
        return {
            'metadata': asdict(self.metadata) if self.metadata else None,
            'tweets': [
                {
                    'position': t.position,
                    'text': t.text,
                    'char_count': t.character_count,
                    'total_in_thread': t.total_in_thread
                }
                for t in self.tweets
            ],
            'validation': {
                'is_valid': valid,
                'errors': errors
            }
        }
    
    def to_json(self) -> str:
        """Convert thread to JSON"""
        return json.dumps(self.to_dict(), indent=2)
    
    def get_tweets_for_posting(self) -> List[str]:
        """Get just the tweet texts in order"""
        return [t.text for t in self.tweets]
    
    def get_thread_summary(self) -> Dict[str, Any]:
        """Get summary of thread"""
        return {
            'thread_id': self.metadata.thread_id if self.metadata else None,
            'thread_type': self.metadata.thread_type if self.metadata else None,
            'tweet_count': len(self.tweets),
            'total_characters': sum(t.character_count for t in self.tweets),
            'average_tweet_length': sum(t.character_count for t in self.tweets) / len(self.tweets) if self.tweets else 0,
            'created_at': self.metadata.created_at if self.metadata else None
        }


# =========================================================================
# Utility Functions
# =========================================================================

def split_text_into_tweets(text: str, max_length: int = 280) -> List[str]:
    """Utility to split long text into tweet-sized chunks"""
    tweets = []
    current = ""
    
    for sentence in text.split('. '):
        test = current + sentence + ". "
        
        if len(test) <= max_length:
            current = test
        else:
            if current:
                tweets.append(current.strip())
            current = sentence + ". "
    
    if current:
        tweets.append(current.strip())
    
    return tweets


def estimate_thread_length(text: str, max_tweet_length: int = 280) -> int:
    """Estimate how many tweets a thread will need"""
    return len(split_text_into_tweets(text, max_tweet_length))
