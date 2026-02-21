# Crypto Market Analysis Engine - Implementation Plan

## Project Overview
A modular crypto market analysis engine that explains what changed, where capital moved, and what likely caused it, across sentiment, derivatives, on-chain data, and news — without making predictions or trade calls.

---

## Phase 1: Project Structure & Core Setup

### 1.1 Directory Structure
```
crypto-analysis-engine/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # API keys, settings
│   │   └── asset_detector.py      # Auto-detect asset type
│   ├── pillars/
│   │   ├── __init__.py
│   │   ├── sentiment.py           # Pillar A: Market Sentiment
│   │   ├── news.py                # Pillar B: News & Events
│   │   ├── derivatives.py         # Pillar C: Derivatives & Leverage
│   │   ├── onchain.py             # Pillar D: On-Chain & Flow
│   │   └── sector_specific.py     # Pillar E: Asset-specific logic
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── memecoin_analyzer.py
│   │   ├── privacy_analyzer.py
│   │   ├── defi_analyzer.py
│   │   └── majors_analyzer.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── formatter.py           # Format analysis output
│   │   └── social_content.py      # Generate social media posts
│   └── utils/
│       ├── __init__.py
│       ├── data_fetchers.py       # API integrations
│       └── helpers.py             # Common utilities
├── tests/
│   ├── test_pillars.py
│   ├── test_analyzers.py
│   └── test_output.py
├── data/
│   └── cache/                     # Store API responses
├── requirements.txt
├── README.md
└── main.py                        # Entry point
```

### 1.2 Technology Stack
- **Language**: Python 3.9+
- **Data Sources**: 
  - CoinGecko API (free tier)
  - Binance API (derivatives data)
  - Alternative.me (Fear & Greed)
  - CryptoPanic (news aggregation)
  - Glassnode (on-chain, if budget allows)
- **Libraries**: 
  - `requests` - API calls
  - `pandas` - data processing
  - `python-dotenv` - config management
  - `pytest` - testing

---

## Phase 2: Core Components (Sequential Build Order)

### File 1: `requirements.txt`
**Purpose**: Define all dependencies
**Dependencies**: None
**Completion Criteria**: File lists all required packages with versions

### File 2: `src/core/config.py`
**Purpose**: Centralized configuration management
**Key Features**:
- API key storage (env variables)
- Rate limiting configs
- Asset type definitions
- Pillar activation rules
**Dependencies**: None
**Completion Criteria**: Config loads without errors, validates API keys

### File 3: `src/utils/helpers.py`
**Purpose**: Common utility functions
**Key Features**:
- Timestamp handling
- Percentage calculators
- Risk level mappers (Low/Medium/High)
- Data validation
**Dependencies**: config.py
**Completion Criteria**: Unit tests pass for all helper functions

### File 4: `src/utils/data_fetchers.py`
**Purpose**: API integration layer
**Key Features**:
- CoinGecko wrapper
- Binance derivatives wrapper
- News API wrapper
- Caching mechanism
- Error handling & retries
**Dependencies**: config.py, helpers.py
**Completion Criteria**: Successfully fetches data from all APIs

### File 5: `src/core/asset_detector.py`
**Purpose**: Auto-detect asset type from ticker/name
**Key Features**:
- Classify as: BTC/ETH, Memecoin, Privacy, DeFi, Other
- Use market cap, tags, and naming patterns
**Dependencies**: data_fetchers.py
**Completion Criteria**: Correctly classifies 20+ test assets

---

## Phase 3: Analysis Pillars (Core Logic)

### File 6: `src/pillars/sentiment.py`
**Purpose**: Pillar A - Market Sentiment
**Key Metrics**:
- Fear & Greed Index
- Funding rate averages
- Social volume trends
**Outputs**:
- Risk-on/off environment
- Market crowd level
- Leverage intensity
**Dependencies**: data_fetchers.py
**Completion Criteria**: Returns structured sentiment data

### File 7: `src/pillars/news.py`
**Purpose**: Pillar B - News & Events
**Key Features**:
- Fetch relevant news (timestamped)
- Calculate relevance score (direct/indirect/macro)
- Detect event timing vs price move
**Dependencies**: data_fetchers.py, helpers.py
**Completion Criteria**: Identifies and scores 5+ news items per asset

### File 8: `src/pillars/derivatives.py`
**Purpose**: Pillar C - Derivatives & Leverage
**Key Metrics**:
- Funding rate (current + 24h change)
- Open interest delta
- Liquidation clusters
- Price vs OI divergence
**Outputs**:
- Leverage buildup detection
- Short covering signals
- Risk-off positioning
**Dependencies**: data_fetchers.py
**Completion Criteria**: Generates pressure analysis for any asset

### File 9: `src/pillars/onchain.py`
**Purpose**: Pillar D - On-Chain & Flow
**Key Metrics**:
- Exchange inflows/outflows
- Wallet activity
- Holder concentration
- Liquidity changes
**Dependencies**: data_fetchers.py
**Completion Criteria**: Returns flow data for supported assets

### File 10: `src/pillars/sector_specific.py`
**Purpose**: Pillar E - Asset-Specific Logic
**Key Features**:
- Memecoin metrics (velocity, churn, bot activity)
- Privacy coin metrics (availability, regulatory sensitivity)
- DeFi metrics (TVL, yield, governance)
**Dependencies**: All other pillars
**Completion Criteria**: Activates correct metrics per asset type

---

## Phase 4: Specialized Analyzers

### File 11: `src/analyzers/majors_analyzer.py`
**Purpose**: BTC/ETH analysis
**Active Pillars**: A, B, C, D
**Special Focus**: Macro events, ETF flows, institutional activity
**Dependencies**: All pillars
**Completion Criteria**: Generates complete analysis for BTC or ETH

### File 12: `src/analyzers/memecoin_analyzer.py`
**Purpose**: Memecoin analysis
**Active Pillars**: A, B, D, E
**Special Focus**: Volume velocity, holder churn, bot detection
**Dependencies**: All pillars
**Completion Criteria**: Identifies pump/dump patterns accurately

### File 13: `src/analyzers/privacy_analyzer.py`
**Purpose**: Privacy coin analysis
**Active Pillars**: A, B, D, E
**Special Focus**: Regulatory news, exchange availability
**Dependencies**: All pillars
**Completion Criteria**: Detects delisting risks, regulatory triggers

### File 14: `src/analyzers/defi_analyzer.py`
**Purpose**: DeFi protocol analysis
**Active Pillars**: A, B, D, E
**Special Focus**: TVL changes, yield shifts, exploit risks
**Dependencies**: All pillars
**Completion Criteria**: Identifies liquidity migration, governance events

---

## Phase 5: Output Generation

### File 15: `src/output/formatter.py`
**Purpose**: Structure analysis into 4-section format
**Sections**:
1. Snapshot (What Changed)
2. Market Pressure Breakdown
3. Event & Context Mapping
4. Risk & Conditions Summary
**Dependencies**: All analyzers
**Completion Criteria**: Outputs clean, readable analysis

### File 16: `src/output/social_content.py`
**Purpose**: Generate social media posts
**Features**:
- Daily market briefs (100-200 words)
- Asset-specific breakdowns
- Trending topics lists
- Engagement hooks (questions)
**Templates**:
- Breaking news format
- Sentiment update format
- Category snapshot format
**Dependencies**: formatter.py
**Completion Criteria**: Generates 3 post types per analysis

---

## Phase 6: Integration & Testing

### File 17: `main.py`
**Purpose**: Main entry point and orchestration
**Features**:
- CLI interface (select asset → analyze)
- Pillar activation logic
- Output routing (terminal/file/API)
**Dependencies**: All components
**Completion Criteria**: End-to-end analysis works for any asset

### File 18: `tests/test_pillars.py`
**Purpose**: Test all 5 pillars
**Dependencies**: All pillar files
**Completion Criteria**: 90%+ test coverage

### File 19: `tests/test_analyzers.py`
**Purpose**: Test specialized analyzers
**Dependencies**: All analyzer files
**Completion Criteria**: Correct asset routing, accurate outputs

### File 20: `tests/test_output.py`
**Purpose**: Test output formatting
**Dependencies**: Output files
**Completion Criteria**: All 4 sections present and valid

### File 21: `README.md`
**Purpose**: Project documentation
**Contents**:
- Setup instructions
- API key configuration
- Usage examples
- Architecture overview
**Dependencies**: None
**Completion Criteria**: A new user can set up and run the tool

---

## Phase 7: Enhancement (Optional)

### File 22: `src/utils/cache_manager.py`
**Purpose**: Intelligent caching to reduce API calls
**Dependencies**: helpers.py

### File 23: `src/output/web_dashboard.py`
**Purpose**: Simple web UI (Flask/Streamlit)
**Dependencies**: All components

### File 24: `src/schedulers/daily_scanner.py`
**Purpose**: Automated daily scans
**Dependencies**: main.py

---

## Development Workflow

### For Each File:
1. **Review the spec** (this plan + docs)
2. **Write the code** (one file at a time)
3. **Test locally** (verify it works)
4. **Update this checklist** (mark as complete)
5. **Move to next file**

### Completion Checklist:
```
Phase 1: Setup
[ ] File 1: requirements.txt
[ ] File 2: src/core/config.py
[ ] File 3: src/utils/helpers.py
[ ] File 4: src/utils/data_fetchers.py
[ ] File 5: src/core/asset_detector.py

Phase 2: Pillars
[ ] File 6: src/pillars/sentiment.py
[ ] File 7: src/pillars/news.py
[ ] File 8: src/pillars/derivatives.py
[ ] File 9: src/pillars/onchain.py
[ ] File 10: src/pillars/sector_specific.py

Phase 3: Analyzers
[ ] File 11: src/analyzers/majors_analyzer.py
[ ] File 12: src/analyzers/memecoin_analyzer.py
[ ] File 13: src/analyzers/privacy_analyzer.py
[ ] File 14: src/analyzers/defi_analyzer.py

Phase 4: Output
[ ] File 15: src/output/formatter.py
[ ] File 16: src/output/social_content.py

Phase 5: Integration
[ ] File 17: main.py
[ ] File 18: tests/test_pillars.py
[ ] File 19: tests/test_analyzers.py
[ ] File 20: tests/test_output.py
[ ] File 21: README.md

Phase 6: Enhancements (Optional)
[ ] File 22: src/utils/cache_manager.py
[ ] File 23: src/output/web_dashboard.py
[ ] File 24: src/schedulers/daily_scanner.py
```

---

## Success Metrics

### Functional Requirements:
- ✅ Analyzes any crypto asset
- ✅ Auto-detects asset type
- ✅ Activates relevant pillars
- ✅ Generates 4-section analysis
- ✅ Creates social media content
- ✅ No predictions, only explanations

### Technical Requirements:
- ✅ Modular architecture
- ✅ API rate limiting
- ✅ Error handling
- ✅ 80%+ test coverage
- ✅ <5 second analysis time

### Content Quality:
- ✅ Factual accuracy
- ✅ Clear explanations
- ✅ No hype or advice
- ✅ Probability of causes (not outcomes)

---

## Notes

- Start with free APIs (CoinGecko, Binance public)
- Cache aggressively to respect rate limits
- Build incrementally - each file should work standalone
- Test with diverse assets: BTC, DOGE, XMR, AAVE
- Social content should be 100-200 words per post

**Remember**: This is an analysis lens, not a trading bot. Focus on explaining "what changed and why," not "what happens next."
