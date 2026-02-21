# 🚀 Getting Started - First Steps

## Welcome to Your Crypto Analysis Engine!

You now have a complete project structure with 24 files ready to implement. Here's how to get started **right now**.

---

## ✅ Step 1: Extract and Set Up

```bash
# Extract the archive
tar -xzf crypto-analysis-engine.tar.gz
cd crypto-analysis-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

---

## 📖 Step 2: Read These Documents (5 minutes)

1. **IMPLEMENTATION_PLAN.md** (3 min) - Understand the 24-file roadmap
2. **DEVELOPMENT_GUIDE.md** (2 min) - Learn the workflow

**Don't read everything** - just skim to understand the structure.

---

## 💻 Step 3: Start Coding (File 2)

Open `src/core/config.py` and implement it:

```python
"""
File 2: Configuration Management
"""

from os import getenv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
COINGECKO_API_KEY = getenv('COINGECKO_API_KEY')
BINANCE_API_KEY = getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = getenv('BINANCE_API_SECRET')
CRYPTOPANIC_API_KEY = getenv('CRYPTOPANIC_API_KEY')
GLASSNODE_API_KEY = getenv('GLASSNODE_API_KEY')

# Asset Type Classifications
ASSET_TYPES = {
    'MAJORS': ['BTC', 'ETH'],
    'PRIVACY': ['XMR', 'ZEC', 'DASH'],
    'DEFI': ['AAVE', 'UNI', 'CRV', 'COMP', 'MKR'],
    'MEMECOIN': ['DOGE', 'SHIB', 'PEPE', 'FLOKI']
}

# Which pillars to activate for each asset type
PILLAR_ACTIVATION_RULES = {
    'MAJORS': ['A', 'B', 'C', 'D'],      # All except E
    'MEMECOIN': ['A', 'B', 'D', 'E'],    # Skip derivatives
    'PRIVACY': ['A', 'B', 'D', 'E'],     # Skip derivatives
    'DEFI': ['A', 'B', 'D', 'E'],        # Skip derivatives
    'OTHER': ['A', 'B', 'C', 'D']        # Default
}

# Cache Settings
CACHE_ENABLED = getenv('CACHE_ENABLED', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(getenv('CACHE_TTL_SECONDS', 300))

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(getenv('MAX_REQUESTS_PER_MINUTE', 30))

# Validation
def validate_config():
    """Ensure required API keys are present"""
    required_keys = {
        'COINGECKO_API_KEY': COINGECKO_API_KEY,
    }
    
    missing = [k for k, v in required_keys.items() if not v]
    
    if missing:
        raise ValueError(f"Missing required API keys: {', '.join(missing)}")
    
    return True

# Auto-validate on import
if __name__ != "__main__":
    try:
        validate_config()
        print("✓ Config loaded successfully")
    except ValueError as e:
        print(f"⚠️  Config warning: {e}")
```

Test it:
```bash
python -c "from src.core.config import ASSET_TYPES; print(ASSET_TYPES)"
```

---

## ✅ Step 4: Mark Progress

Open `CHECKLIST.md` and mark File 2 as complete:
```markdown
Phase 1: Foundation
- [ ] File 1: requirements.txt
- [✅] File 2: src/core/config.py  <- DONE!
- [ ] File 3: src/utils/helpers.py  <- Next
```

---

## 🔁 Step 5: Repeat for Next File

1. Open `src/utils/helpers.py`
2. Read the TODOs
3. Implement the functions
4. Test them
5. Mark as complete
6. Move to next file

---

## 💡 Pro Tips

### Use Mock Data Initially
Don't wait for real API keys. Use fake data:

```python
# In data_fetchers.py during development
def get_coin_data(ticker):
    # Return mock data for testing
    return {
        'id': ticker.lower(),
        'symbol': ticker,
        'current_price': 50000,
        'market_cap': 1000000000,
        'categories': ['layer-1']
    }
```

### Test As You Go
After each function:
```python
# Create test_current.py
from src.utils.helpers import calculate_percentage_change

result = calculate_percentage_change(100, 150)
assert result == 50.0
print("✅ Test passed!")
```

### Commit After Each File
```bash
git add src/core/config.py
git commit -m "Implement File 2: config.py"
```

---

## 🎯 Your First Goal

**Complete Phase 1 (Files 2-5) in your first session.**

By the end, you should be able to run:
```python
from src.core.asset_detector import detect_asset_type
asset_type, confidence = detect_asset_type('BTC')
print(f"{asset_type} ({confidence})")  # MAJORS (0.95)
```

This proves your foundation works!

---

## 📚 Quick Reference

**File you're working on?** → Read its header comments for detailed TODOs

**Stuck?** → Check DEVELOPMENT_GUIDE.md for troubleshooting

**Need the big picture?** → See PROJECT_MAP.md for structure

**Want to track progress?** → Use CHECKLIST.md

---

## 🚀 Ready?

1. Extract the project
2. Set up environment
3. Open `src/core/config.py`
4. Start coding!

**Remember**: One file at a time. Test before moving on. You've got this! 💪
