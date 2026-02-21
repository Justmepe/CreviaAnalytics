# System Architecture: Claude AI Integration

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              CRYPTO ANALYSIS ENGINE - MAIN ORCHESTRATOR          │
│                    (Powered by Claude AI)                        │
└─────────────────────────────────────────────────────────────────┘

                          ┌──────────────────┐
                          │  RESEARCH PHASE  │ (60s)
                          │  Global Markets  │
                          │  Asset Data      │
                          │  RSS News Feeds  │
                          └────────┬─────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   ANALYSIS PHASE (300s)      │
                    │                              │
                    ├─ Majors (BTC, ETH)           │
                    ├─ Memecoins (DOGE, SHIB)      │
                    ├─ Privacy (XMR, ZEC)          │
                    ├─ DeFi (AAVE, UNI)            │
                    │                              │
                    ├─ 📰 NEWS REPORTS ✨ NEW    │
                    │   └─ Claude AI analysis      │
                    │   └─ Price fact-checking     │
                    │   └─ Professional memos      │
                    │                              │
                    └────────┬────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  THREAD GENERATION (3600s)  │ ✨ NOW WITH CLAUDE AI
              │                             │
              ├─ Claude-powered threads     │
              │  (if API available)         │
              │                             │
              └─ Template fallback          │
              │  (if API unavailable)       │
              │                             │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     OUTPUT FILES (📁)       │
              │                             │
              ├─ x_thread_*.txt             │
              │  (Copy-paste to Twitter)    │
              │                             │
              ├─ news_memo_*.txt ✨ NEW    │
              │  (Fact-checked reports)     │
              │                             │
              └─ analysis_*.txt             │
                 (Detailed breakdowns)      │
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAIN ORCHESTRATOR                        │
│  (main.py) - Continuous Loop                                    │
└─────────────────────────────────────────────────────────────────┘
        │                    │                      │
        │                    │                      │
        ▼                    ▼                      ▼
┌──────────────┐    ┌─────────────────────┐  ┌────────────────┐
│   RESEARCH   │    │   ANALYSIS          │  │ THREAD GEN     │
│              │    │                     │  │                │
│ •Global      │    │ •Analyze assets     │  │ •Claude AI ✨  │
│  metrics     │    │  (20+ metrics)      │  │                │
│              │    │                     │  │ •Generate      │
│ •Fetch       │    │ •Generate news  ✨  │  │  tweets        │
│  prices      │    │  reports (Claude)   │  │                │
│              │    │                     │  │ •Save format   │
│ •Sentiment   │    │ •Save analyses      │  │  for X/Twitter │
│  data        │    │                     │  │                │
│              │    │ •Save news memos ✨ │  │                │
└──────────────┘    └─────────────────────┘  └────────────────┘
        │                    │                      │
        └────────────────────┴──────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │   DATA PERSISTENCE (JSON)   │
              │                             │
              ├─ data/research_*.json       │
              ├─ data/analyses_*.json       │
              │                             │
              └─────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     OUTPUT TEXT FILES       │
              │   (Ready to copy-paste)     │
              │                             │
              ├─ output/x_thread_*.txt      │
              ├─ output/news_memo_*.txt ✨  │
              └─ output/analysis_*.txt      │
```

## Claude AI Integration Points

```
┌──────────────────────────────────────────────────────┐
│           CLAUDE AI INTEGRATION POINTS                │
│                                                      │
│  ✨ = NEW or ENHANCED with Claude AI                 │
└──────────────────────────────────────────────────────┘

1. X THREAD GENERATION ✨
   ├─ Input: Market data, sentiment, sectors
   ├─ Claude Process:
   │  ├─ Receives comprehensive market context
   │  ├─ Writes 10 engaging tweets
   │  ├─ Professional Bloomberg-style tone
   │  └─ Returns copy-paste ready format
   └─ Fallback: Professional templates

2. NEWS REPORT GENERATION ✨
   ├─ Input: RSS articles, real-time prices
   ├─ Claude Process:
   │  ├─ Analyzes article headlines
   │  ├─ Fact-checks against live prices
   │  ├─ Writes Bloomberg-style memo
   │  └─ Attributes sources
   └─ Fallback: Markdown formatter

3. SENTIMENT ANALYSIS
   ├─ Uses Fear/Greed Index
   ├─ Claude interprets sentiment context
   └─ Feeds into thread generation

4. MARKET NARRATIVE
   ├─ Claude extracts key events
   ├─ Creates coherent story
   └─ Weaves into thread narrative
```

## Data Flow: Article to Published Thread

```
                    RSS FEEDS (19 sources)
                           │
                ┌──────────▼──────────┐
                │  ARTICLE EXTRACTION  │
                │  • De-duplication    │
                │  • Spam filtering    │
                │  • Price extraction  │
                └──────────┬───────────┘
                           │
                ┌──────────▼──────────┐
                │ NEWS NARRATOR       │ ✨ Claude AI
                │ • Read articles     │
                │ • Fetch live prices │
                │ • Call Claude API   │
                │ • Generate memo     │
                └──────────┬───────────┘
                           │
                ┌──────────▼──────────┐
                │ FACT-CHECK LAYER    │
                │ • Compare to prices │
                │ • Detect outdated   │
                │ • Mark discrepancies│
                └──────────┬───────────┘
                           │
                ┌──────────▼──────────┐
                │ OUTPUT FORMATTER    │
                │ • Professional text │
                │ • Markdown style    │
                │ • Source attribution│
                └──────────┬───────────┘
                           │
              ┌────────────▼─────────────┐
              │  output/news_memo_*.txt  │
              │  (Ready for copy-paste)  │
              └──────────────────────────┘
```

## X Thread Generation Flow

```
           BTC/ETH ANALYSIS + MARKET DATA
                      │
        ┌─────────────▼─────────────┐
        │  DATA AGGREGATION         │
        │  • Current prices         │
        │  • Sentiment index        │
        │  • Key levels & support   │
        │  • Sector analysis        │
        │  • Whale activity         │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  CLAUDE AI GENERATION ✨  │
        │  if ANTHROPIC_API_KEY:    │
        │    ├─ Send context        │
        │    ├─ Generate tweets     │
        │    ├─ Format output       │
        │    └─ Return 10-tweet set │
        │  else:                    │
        │    └─ Use templates       │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  FORMAT & POLISH          │
        │  • Emoji integration      │
        │  • Newline formatting     │
        │  • Hashtag inclusion      │
        │  • Character counting     │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  FILE PERSISTENCE         │
        │  output/x_thread_*.txt    │
        │  COPY-PASTE READY!        │
        └───────────────────────────┘
```

## Configuration Hierarchy

```
ENVIRONMENT (.env)
├─ ANTHROPIC_API_KEY          → Claude AI activation
├─ ANTHROPIC_MODEL            → Model selection
├─ RESEARCH_INTERVAL=60       → Market data refresh
├─ ANALYSIS_INTERVAL=300      → Asset analysis
└─ THREAD_INTERVAL=3600       → Thread generation

APPLICATION (main.py)
├─ MAJOR_ASSETS               → BTC, ETH
├─ MEMECOIN_ASSETS            → DOGE, SHIB, PEPE
├─ PRIVACY_ASSETS             → XMR, ZEC, DASH
└─ DEFI_ASSETS                → AAVE, UNI, CRV

MODULES
├─ x_thread_generator.py      → Thread creation (Claude)
├─ news_narrator.py           → News analysis (Claude)
├─ rss_engine.py              → News feeds
├─ enhanced_data_fetchers.py  → Claude API wrapper
└─ helpers.py                 → Utilities
```

## Error Handling & Fallbacks

```
CLAUDE AI GENERATION REQUEST
        │
        ▼
    ┌─API Call──┐
    │           │
    ▼           ▼
  SUCCESS    FAILURE
    │           │
    │    ┌──────▼──────┐
    │    │ Error Type? │
    │    └──┬──┬──┬────┘
    │       │  │  │
    │       │  │  └─ 404 NotFound
    │       │  │     → Try fallback model
    │       │  │        → Try next model
    │       │  │           → Use templates ✅
    │       │  │
    │       │  └─ Rate limit
    │       │     → Queue & retry
    │       │
    │       └─ Network error
    │          → Use templates ✅
    │
    ▼
RETURN RESULT
├─ Claude: Professional AI-generated
├─ Template: Professional fallback
└─ Both: Copy-paste ready
```

---

**Legend:**
- ✨ = Claude AI powered (new or enhanced)
- ✅ = Fully implemented and tested
- 📁 = File/directory reference
- 📰 = News/article data

**Last Updated:** February 1, 2026
