# 🏗️ COMPLETE ARCHITECTURE MAP - Crevia Analytics System

## 📊 One-Diagram Flow

```
RSS FEEDS
   ↓
DATA LAYER (src/data/)
├── aggregator.py (main interface)
├── providers/ (6 sources: Binance, CoinGecko, CoinMarketCap, Glassnode, DeFiLlama, Alternative.me)
└── models.py (data structures)
   ↓
ANALYSIS LAYER (src/pillars/ + src/analyzers/)
├── Pillar A: sentiment.py (Market Sentiment)
├── Pillar B: news.py + rss_engine.py (News & Events)
├── Pillar C: derivatives.py (Futures Pressure)
├── Pillar D: onchain.py (Capital Flows)
├── Pillar E: sector_specific.py (DeFi/Memecoins)
└── Analyzers:
    ├── majors_analyzer.py (BTC/ETH)
    ├── memecoin_analyzer.py
    ├── privacy_analyzer.py
    └── defi_analyzer.py
   ↓
JSON ANALYSIS OUTPUT
(saved to data/ directory)
   ↓
CLAUDE API (ONLY for writing)
Takes JSON → Creates refined post
   ↓
POSTING LAYER (src/utils/)
├── x_thread_builder.py (formats tweets)
├── x_poster.py (posts to X/Twitter)
├── discord_notifier.py (sends to Discord)
└── x_integration.py (orchestrates)
   ↓
POSTED TO X/TWITTER + DISCORD
```

---

## 📁 Directory Structure - What Each Does

### **src/data/** - Data Fetching Layer (NO Claude)
```
aggregator.py (579 lines)
  - Main interface that all analysis uses
  - Combines 6 data sources with auto-fallback
  - Caches data to reduce API calls
  - Methods:
    * get_price(ticker) → PriceSnapshot
    * get_prices_batch(tickers) → Dict[ticker, PriceSnapshot]
    * get_global_metrics() → MarketMetrics
    * get_derivatives(ticker) → DerivativesData
    * get_defi_metrics(ticker) → DeFiMetrics
    * get_onchain(ticker) → OnChainMetrics

models.py
  - Data structures (TypedDict/dataclass)
  - PriceSnapshot, DerivativesData, MarketMetrics, etc.

providers/
  ├── binance_provider.py - Real-time prices, funding rates, OI
  ├── coingecko_provider.py - Market cap, supply, ATH, volume
  ├── coinmarketcap_provider.py - Global metrics fallback
  ├── glassnode_provider.py - On-chain data, whale tracking
  ├── defillama_provider.py - DeFi TVL, protocol stats
  └── alternativeme_provider.py - Fear/Greed Index
```

### **src/pillars/** - Analysis Pillars (Transforms Data → Insights)
```
3 types of analysis:
1. MARKET CONTEXT (why did it happen?)
2. TECHNICAL/SENTIMENT (what's the tone?)
3. DATA INTERPRETATION (how do we explain it?)

sentiment.py (Pillar A)
  ├── Global fear/greed level
  ├── Social media sentiment
  ├── On-chain momentum
  └── Output: { sentiment, confidence, signals, timestamp }

news.py (Pillar B)
  ├── Searches RSS feeds (via rss_engine.py)
  ├── Calculates relevance to asset
  ├── Maps sentiment from headlines
  └── Output: { events[], summary, interpretation }

rss_engine.py (Core RSS Aggregator)
  ├── Fetches from 20+ curated feeds (CoinDesk, Cointelegraph, etc.)
  ├── Deduplicates & scores articles
  ├── Background polling (async)
  └── Methods:
      * force_fetch_all_feeds()
      * search_news(ticker, limit)
      * start_background_polling(interval)

derivatives.py (Pillar C)
  ├── Funding rates (bullish/bearish pressure)
  ├── Open interest (leverage levels)
  ├── Liquidation cascades
  └── Output: { funding_analysis, oi_analysis, leverage_risk }

onchain.py (Pillar D)
  ├── Whale movements
  ├── Exchange flows (accumulation/distribution)
  ├── Active addresses
  └── Output: { whale_activity, exchange_flows, holders_behavior }

sector_specific.py (Pillar E)
  ├── DeFi sentiment (TVL trends, yield rates)
  ├── Memecoin momentum
  ├── Privacy coin regulations
  └── Output: { sector_trends, opportunities, risks }
```

### **src/analyzers/** - Asset-Specific Analysis
```
Each analyzer combines ALL pillars for a specific asset type

majors_analyzer.py (BTC/ETH)
  - Uses: Sentiment + News + Derivatives + On-Chain
  - Output structure:
    {
      'ticker': 'BTC',
      'snapshot': { price, change, catalyst },
      'pressure': { funding, leverage, liquidations },
      'events': { news, interpretation, sentiment },
      'risks': { leverage, whale, macro },
      'pillar_data': { raw data from all pillars }
    }

memecoin_analyzer.py (DOGE, SHIB, etc.)
  - Uses: Sentiment + News + Sector
  - Focuses on: Whale movement, social buzz, media attention

privacy_analyzer.py (XMR, ZEC, etc.)
  - Uses: News + Sentiment + Regulations
  - Focuses on: Regulatory pressure, adoption, controversy

defi_analyzer.py (AAVE, UNI, etc.)
  - Uses: Sentiment + On-Chain + Sector
  - Focuses on: TVL trends, yield, liquidation risks
```

### **main.py** - Orchestrator
```
CryptoAnalysisEngine class:

start()
  └── Main loop that runs 3 phases:

    1. RESEARCH PHASE (every 60s, NO Claude)
       - Calls DataAggregator for all data
       - Saves raw data to latest_research{}
       - Fetches: global metrics, prices, derivatives, on-chain

    2. ANALYSIS PHASE (every 300s)
       - Calls each analyzer (majors, altcoins, sectors)
       - Each analyzer uses pillars to interpret data
       - Saves JSON analysis to data/ directory
       - Output: structured JSON files (analyses_TIMESTAMP.json)

    3. THREAD GENERATION PHASE (every 3600s, USES Claude)
       - Loads JSON analysis from data/
       - Calls Claude API to create refined post
       - Passes to x_thread_builder.py
       - Posts to X/Twitter + Discord
```

---

## 🔄 The Complete Data Flow

### Phase 1: Research (Data Layer)
```
API Calls (Binance, CoinGecko, etc.)
    ↓
DataAggregator.get_price()
DataAggregator.get_global_metrics()
DataAggregator.get_derivatives()
    ↓
Raw data cached in main.py.latest_research{}
```

Example structure:
```python
latest_research = {
    'global': {
        'total_market_cap': 1850000000000,
        'btc_dominance': 44.5,
        'fear_greed_index': 68,
        'btc_funding_rate': 0.00085
    },
    'BTC': {
        'price': 52500,
        'change_24h': 2.45,
        'funding_rate': 0.00085,
        'timestamp': 1707495600
    },
    'ETH': { ... }
}
```

### Phase 2: Analysis (Pillars + Analyzers)
```
Raw data from Phase 1
    ↓
majors_analyzer.analyze_major('BTC')
    ├── sentiment.analyze_sentiment('BTC')
    ├── news.analyze_news('BTC')
    ├── derivatives.analyze_derivatives('BTC')
    └── onchain.analyze_onchain('BTC')
    ↓
Combined into structured JSON
    ↓
Saved to: data/analyses_YYYYMMDD_HHMMSS.json
```

Example output (simplified):
```json
{
  "ticker": "BTC",
  "timestamp": "2026-02-09T15:30:00Z",
  "snapshot": {
    "btc_price": 52500,
    "change_24h": 2.45,
    "catalyst": "Strong institutional buying, ETF inflows"
  },
  "pressure": {
    "funding_rate": 0.00085,
    "oi_change": 2.1,
    "liquidation_risk": "Low"
  },
  "events": {
    "recent_news": [
      {
        "title": "Bitcoin ETF hits new AUM record",
        "source": "CoinDesk",
        "sentiment": "positive",
        "relevance": 0.95
      }
    ]
  },
  "risks": {
    "macro_risk": "Fed uncertainty",
    "leverage_risk": "Moderate"
  }
}
```

### Phase 3: Content Generation (Claude API)
```
JSON analysis from Phase 2
    ↓
Claude API Call:
"Based on this BTC analysis JSON, write a 5-tweet thread..."
    ↓
Claude Response:
"1/ BTC holding $52.5K amid strong institutional interest...
 2/ ETF inflows hitting new highs | funding rates elevated...
 3/ Key resistance at $53K..."
    ↓
x_thread_builder.py:
- Parse tweets
- Format with emojis
- Create copy-paste ready thread
    ↓
x_integration.py.build_thread_with_claude()
    ↓
x_poster.py.post_thread()  → X/Twitter
discord_notifier.py         → Discord
```

---

## 🎯 JSON to Post Pipeline

### Step 1: Analysis JSON (from Phase 2)
```json
{
  "ticker": "BTC",
  "snapshot": { "price": 52500, "change": 2.45 },
  "pressure": { "funding_rate": 0.00085 },
  "events": { "news": [...] },
  "risks": { ... }
}
```

### Step 2: Claude Prompt (in x_thread_builder.py)
```
{
  "prompt": "Based on this BTC market analysis JSON: {...}",
  "context": {
    "market_cap": 1.85T,
    "sentiment": "Bullish",
    "majors_data": { BTC, ETH, SOL, BNB }
  },
  "requirements": [
    "5-7 tweets max",
    "Use emojis naturally",
    "Include key numbers",
    "Professional tone",
    "Mark each tweet 1/, 2/, etc"
  ],
  "max_tokens": 4000
}
```

### Step 3: Claude Response
```
1/ Bitcoin holding above $52K as institutional demand remains strong 📊
   ETF inflows hit another record | Fear/Greed at 68 (Greed territory)

2/ Futures funding rates elevated at 0.085% | Watch for liquidation cascade
   if support breaks. Current open interest: $45B

3/ News flow positive: ETF approvals, corporate adoption stories 🚀
   But macro uncertainty (Fed policy) remains a wildcard

4/ On-chain: Whale accumulation continuing | Small holders selling
   Supply shock potential if this trend continues

5/ Play → Bitcoin likely holds $51K support through weekend
   Resistance at $53K | Monitor funding rates for reversals ⚠️
```

### Step 4: x_thread_builder.py
- Parses Claude response
- Cleans up formatting
- Adds strategic emojis if missing
- Creates `copy_paste_ready` format
- Returns dict:
```python
{
  'tweets': [tweet1, tweet2, ...],
  'tweet_count': 5,
  'copy_paste_ready': formatted_string,
  'generated_by': 'Claude AI',
  'thread_type': 'comprehensive_analysis'
}
```

### Step 5: Posting
```python
system.poster.post_thread(thread_result)
# Posts each tweet in sequence to X/Twitter

discord.send_message(summary_message)
# Sends notification to Discord with key stats
```

---

## 🔌 How to Use This System

### For Automated Posting:
```bash
python main.py
# Runs full cycle: Research → Analysis → Claude Generation → Post
```

### For Manual Analysis:
```python
from src.data.aggregator import DataAggregator
from src.analyzers.majors_analyzer import analyze_major

agg = DataAggregator()
btc_price = agg.get_price('BTC')
btc_analysis = analyze_major('BTC')

print(btc_analysis)  # Full JSON structure
```

### For Custom Claude Prompt:
```python
from src.utils.x_integration import XpostingSystem

system = XpostingSystem()

analysis_data = {
    'majors': { 'BTC': {...}, 'ETH': {...} },
    'defi': [...],
    'memecoins': [...],
    'market_context': {...}
}

thread = system.build_thread_with_claude(analysis_data)
system.poster.post_thread(thread)
```

---

## ✅ Key Points

1. **Data Layer** (src/data/): NO Claude - just APIs
   - Binance, CoinGecko, CoinMarketCap, Glassnode, DeFiLlama, Alternative.me
   - Automatic fallbacks if one source fails

2. **Analysis Layer** (src/pillars + src/analyzers): NO Claude - just logic
   - Combines 5 pillars (Sentiment, News, Derivatives, On-Chain, Sector)
   - Outputs structured JSON analysis

3. **Content Layer** (Claude API): ONE JOB - Turn JSON into posts
   - Takes structured analysis JSON
   - Creates engaging tweets
   - Returns formatted thread

4. **Posting Layer** (src/utils/): NO Claude - just posting
   - x_thread_builder: Formats tweets
   - x_poster: Posts to X
   - discord_notifier: Sends to Discord

**Architecture is clean, separated, and efficient!**
