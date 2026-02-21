# Crypto Market Analysis Engine

A modular crypto market analysis engine that explains what changed, where capital moved, and what likely caused it — without making predictions or trade calls.

## 🎯 Core Principle

This tool analyzes **probability of causes**, not probability of outcomes. We explain "why this happened," not "what happens next."

## � NEW: Claude AI Research System

**No more API keys needed!** The system now uses Claude AI to research crypto markets in real-time:

- ✅ **One API key** replaces 4+ crypto APIs
- ✅ **No rate limits** (unlimited research)
- ✅ **Always current** (searches latest sources)
- ✅ **97% cheaper** ($15/mo vs $500/mo)
- ✅ **Runs 24/7** automated research

### Cost Comparison
- **Before**: CoinGecko ($129/mo) + CryptoPanic ($50/mo) + Glassnode ($299/mo) = **$478/month**
- **After**: Anthropic API = **$15/month**
- **Savings**: **$463/month (97% cheaper!)**

## 📊 The Five Pillars

1. **Market Sentiment** - Global context (Fear & Greed, funding rates, social volume)
2. **News & Events** - Causality layer (announcements, updates, regulatory changes)
3. **Derivatives & Leverage** - Pressure analysis (OI, funding, liquidations)
4. **On-Chain & Flow** - Capital behavior (exchange flows, wallet activity)
5. **Sector-Specific Logic** - Asset-type tailored metrics (memecoin, privacy, DeFi)

## 🚀 Setup

### Prerequisites
- Python 3.9-3.12 (3.13 has compatibility issues with Anthropic package)
- Anthropic API key (for Claude AI research)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd crypto-analysis-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

### API Keys

**Required:**
- **Anthropic Claude** - AI-powered research ($15/mo)

**Optional (for backup when free limits hit):**
- **CoinGecko** - Additional market data
- **Glassnode** - Advanced on-chain metrics  
- **CryptoPanic** - Enhanced news aggregation
- **Etherscan** - Ethereum-specific data

*System works with just Claude AI, but optional keys provide backup data sources*

## 📖 Usage

### Quick Start with Claude AI

```bash
# 1. Set your Anthropic API key
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# 2. Start automated research (runs every 60 seconds)
python src/utils/run_research_loop.py

# That's it! No other setup needed.
```

### Manual Research

```python
from src.utils.enhanced_data_fetchers import ClaudeResearchEngine

# Initialize (uses Claude AI)
engine = ClaudeResearchEngine(api_key='your-anthropic-key')

# Research any asset
btc = engine.research_asset('BTC')
# Returns: price, sentiment, news, on-chain, derivatives, risks

# Research market overview
market = engine.research_market_overview()
# Returns: complete market snapshot

# Research sectors
memes = engine.research_sector('memecoins', top_assets=5)
# Returns: sector analysis with top assets
```

### Legacy Analysis (still works)

```bash
# Analyze a single asset
python main.py --asset BTC

# Generate social media content
python main.py --asset SOL --format social

# Export to JSON
python main.py --asset AAVE --output analysis.json
```

## 🔄 Automated Research Loop

The system runs continuous research every 60 seconds:

- **Market overview** (total mcap, dominance, sentiment)
- **BTC analysis** (price, news, derivatives, on-chain)
- **ETH analysis** (comprehensive data)
- **Rotating sectors** (memecoins → DeFi → privacy)

Results saved to timestamped JSON files. Runs 24/7 with no API limits!

```
crypto-analysis-engine/
├── src/
│   ├── core/           # Configuration & asset detection
│   ├── pillars/        # 5 analysis pillars
│   ├── analyzers/      # Asset-specific analyzers
│   ├── output/         # Formatting & social content generation
│   └── utils/          # API integrations & helpers
├── tests/              # Unit tests
└── data/cache/         # API response caching
```

## 📝 Output Format

Every analysis contains 4 sections:

1. **Snapshot** - What changed (price, volume, OI, funding)
2. **Market Pressure Breakdown** - Leverage analysis, positioning signals
3. **Event & Context Mapping** - News correlation, timing analysis
4. **Risk & Conditions Summary** - Current risk levels (no predictions)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## 🔧 Development Status

This project follows a sequential build approach. See `IMPLEMENTATION_PLAN.md` for the complete roadmap.

Current progress: [  ] Phase 1 → [  ] Phase 2 → [  ] Phase 3 → [  ] Complete

## 🤝 Contributing

1. Check `IMPLEMENTATION_PLAN.md` for the next file to implement
2. Follow the spec for that file
3. Write tests
4. Update the checklist in the plan

## ⚠️ Important Notes

- This tool provides **analysis**, not **trading advice**
- All outputs are **factual** and **probability-based explanations**
- No predictions about future price movements
- Suitable for educational and informational purposes only

## 📄 License

[Add your license here]

## 📧 Contact

[Add your contact information]

---

**Remember**: We're building an analysis lens, not a crystal ball. Focus on explaining what changed and why, not what happens next.
