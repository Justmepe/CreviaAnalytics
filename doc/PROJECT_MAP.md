# Project Structure Map

```
crypto-analysis-engine/
│
├── 📚 Documentation
│   ├── README.md                    # Project overview & setup
│   ├── IMPLEMENTATION_PLAN.md       # Complete build sequence (24 files)
│   ├── DEVELOPMENT_GUIDE.md         # How to work through the project
│   └── CHECKLIST.md                 # Quick progress tracker
│
├── ⚙️ Configuration
│   ├── .env.example                 # API keys template
│   ├── .gitignore                   # Git ignore rules
│   └── requirements.txt             # Python dependencies
│
├── 🚀 Main Entry Point
│   └── main.py                      # CLI interface (File 17)
│
├── 📦 Source Code (src/)
│   │
│   ├── 🔧 Core (src/core/)
│   │   ├── __init__.py
│   │   ├── config.py                # File 2: Configuration management
│   │   └── asset_detector.py        # File 5: Auto-detect asset type
│   │
│   ├── 🏛️ Analysis Pillars (src/pillars/)
│   │   ├── __init__.py
│   │   ├── sentiment.py             # File 6: Pillar A - Market Sentiment
│   │   ├── news.py                  # File 7: Pillar B - News & Events
│   │   ├── derivatives.py           # File 8: Pillar C - Derivatives
│   │   ├── onchain.py               # File 9: Pillar D - On-Chain
│   │   └── sector_specific.py       # File 10: Pillar E - Sector Logic
│   │
│   ├── 🎯 Specialized Analyzers (src/analyzers/)
│   │   ├── __init__.py
│   │   ├── majors_analyzer.py       # File 11: BTC/ETH
│   │   ├── memecoin_analyzer.py     # File 12: Memecoins
│   │   ├── privacy_analyzer.py      # File 13: Privacy coins
│   │   └── defi_analyzer.py         # File 14: DeFi protocols
│   │
│   ├── 📤 Output Generation (src/output/)
│   │   ├── __init__.py
│   │   ├── formatter.py             # File 15: 4-section formatter
│   │   └── social_content.py        # File 16: Social media posts
│   │
│   └── 🛠️ Utilities (src/utils/)
│       ├── __init__.py
│       ├── helpers.py               # File 3: Common utilities
│       ├── data_fetchers.py         # File 4: API integrations
│       └── cache_manager.py         # File 22: Cache layer (optional)
│
├── 🧪 Tests (tests/)
│   ├── __init__.py
│   ├── test_pillars.py              # File 18: Pillar tests
│   ├── test_analyzers.py            # File 19: Analyzer tests
│   └── test_output.py               # File 20: Output tests
│
└── 💾 Data (data/)
    └── cache/                       # API response cache
        └── .gitkeep
```

---

## 🔄 Data Flow

```
User Input (ticker: BTC)
    ↓
main.py
    ↓
asset_detector.py → Detects: MAJORS
    ↓
majors_analyzer.py → Activates Pillars: A, B, C, D
    ↓
Pillar A (sentiment.py) → Fear & Greed, Funding Rates
Pillar B (news.py) → Recent news, events
Pillar C (derivatives.py) → OI, liquidations
Pillar D (onchain.py) → Exchange flows
    ↓
formatter.py → Structures into 4 sections
    ↓
social_content.py → Generates posts (optional)
    ↓
Output to user (text/JSON/social post)
```

---

## 📋 Build Order

### Phase 1: Foundation (Can work in parallel)
```
File 2: config.py
File 3: helpers.py
File 4: data_fetchers.py (needs config.py)
File 5: asset_detector.py (needs config + data_fetchers)
```

### Phase 2: Pillars (Can work in parallel)
```
File 6: sentiment.py
File 7: news.py
File 8: derivatives.py
File 9: onchain.py
File 10: sector_specific.py
```

### Phase 3: Analyzers (Can work in parallel)
```
File 11: majors_analyzer.py
File 12: memecoin_analyzer.py
File 13: privacy_analyzer.py
File 14: defi_analyzer.py
```

### Phase 4: Output (Sequential)
```
File 15: formatter.py
File 16: social_content.py (needs formatter)
```

### Phase 5: Integration (Sequential)
```
File 17: main.py (needs everything)
File 18-20: tests (need respective modules)
```

---

## 🎯 Key Files to Start With

1. **IMPLEMENTATION_PLAN.md** - Read this first for complete roadmap
2. **DEVELOPMENT_GUIDE.md** - Read this for workflow tips
3. **src/core/config.py** - Start coding here (File 2)

---

## ✅ Success Checkpoints

After each phase, you should be able to run:

**Phase 1**: 
```python
from src.core.asset_detector import detect_asset_type
detect_asset_type('BTC')  # Returns: ('MAJORS', 0.95)
```

**Phase 2**:
```python
from src.pillars.sentiment import analyze_sentiment
analyze_sentiment()  # Returns: {environment: 'risk-on', ...}
```

**Phase 3**:
```python
from src.analyzers.majors_analyzer import analyze_major
analyze_major('BTC')  # Returns: Complete analysis dict
```

**Phase 4**:
```python
from src.output.formatter import format_analysis
format_analysis(data)  # Returns: 4-section formatted text
```

**Phase 5**:
```bash
python main.py --asset BTC  # Outputs: Complete analysis
```
