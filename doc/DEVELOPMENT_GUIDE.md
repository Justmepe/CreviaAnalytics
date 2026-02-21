# Development Workflow Guide

## 🎯 How to Work Through This Project

This project follows a **sequential build approach** where each file builds on previous ones. You'll implement one file at a time, test it, then move to the next.

---

## 📋 The Build Sequence

### Phase 1: Foundation (Files 1-5)
These files have NO dependencies on each other and can be done in any order:

1. ✅ `requirements.txt` - Already created
2. ⬜ `src/core/config.py` - Start here
3. ⬜ `src/utils/helpers.py` - Can do in parallel with config
4. ⬜ `src/utils/data_fetchers.py` - Depends on config.py
5. ⬜ `src/core/asset_detector.py` - Depends on config + data_fetchers

**Goal**: By end of Phase 1, you can fetch data and detect asset types.

**Test**: Run `python -c "from src.core.asset_detector import detect_asset_type; print(detect_asset_type('BTC'))"`

---

### Phase 2: Analysis Pillars (Files 6-10)
All depend on data_fetchers. Can be done in parallel:

6. ⬜ `src/pillars/sentiment.py`
7. ⬜ `src/pillars/news.py`
8. ⬜ `src/pillars/derivatives.py`
9. ⬜ `src/pillars/onchain.py`
10. ⬜ `src/pillars/sector_specific.py`

**Goal**: Each pillar can run independently and return structured data.

**Test**: 
```python
from src.pillars.sentiment import analyze_sentiment
result = analyze_sentiment()
print(result)  # Should show fear & greed index, funding rates, etc.
```

---

### Phase 3: Specialized Analyzers (Files 11-14)
All depend on pillars. Can be done in parallel:

11. ⬜ `src/analyzers/majors_analyzer.py`
12. ⬜ `src/analyzers/memecoin_analyzer.py`
13. ⬜ `src/analyzers/privacy_analyzer.py`
14. ⬜ `src/analyzers/defi_analyzer.py`

**Goal**: Each analyzer runs the right pillars for its asset type.

**Test**:
```python
from src.analyzers.majors_analyzer import analyze_major
result = analyze_major('BTC')
print(result)  # Should show all pillar results combined
```

---

### Phase 4: Output Generation (Files 15-16)
Depends on analyzers:

15. ⬜ `src/output/formatter.py`
16. ⬜ `src/output/social_content.py`

**Goal**: Convert raw analysis into readable formats.

**Test**:
```python
from src.output.formatter import format_analysis
from src.analyzers.majors_analyzer import analyze_major

data = analyze_major('BTC')
formatted = format_analysis(data, format='text')
print(formatted)  # Should show 4-section analysis
```

---

### Phase 5: Integration (Files 17-21)
Ties everything together:

17. ⬜ `main.py` - The CLI interface
18. ⬜ `tests/test_pillars.py`
19. ⬜ `tests/test_analyzers.py`
20. ⬜ `tests/test_output.py`
21. ✅ `README.md` - Already created

**Goal**: Complete end-to-end workflow.

**Test**:
```bash
python main.py --asset BTC
# Should output complete analysis
```

---

## 🔄 Workflow for Each File

When implementing a file:

### 1. Read the File Header
Every file has a header with:
- Purpose
- Dependencies
- Implementation checklist
- Example code structure

### 2. Check Dependencies
Before starting a file, ensure its dependencies are complete:
```bash
# Example: Before working on data_fetchers.py
python -c "from src.core.config import COINGECKO_API_KEY; print('Config works!')"
```

### 3. Implement Incrementally
Don't try to do everything at once:
1. Start with basic structure
2. Add one function
3. Test it
4. Add next function
5. Repeat

### 4. Test Immediately
After each function:
```python
# Create a test file: test_current.py
from src.utils.helpers import calculate_percentage_change

result = calculate_percentage_change(100, 150)
print(f"Expected: 50%, Got: {result}%")
```

### 5. Update Checklist
Mark the file as complete in `IMPLEMENTATION_PLAN.md`

---

## 🧪 Testing Strategy

### Unit Tests (As You Go)
Create small test files for each module:

```bash
# Test a specific function
python -c "from src.utils.helpers import calculate_percentage_change; \
           assert calculate_percentage_change(100, 150) == 50.0; \
           print('✓ Test passed')"
```

### Integration Tests (Phase 5)
Run the full test suite:
```bash
pytest tests/
```

### Manual Tests (Throughout)
Try real-world scenarios:
```python
from src.analyzers.memecoin_analyzer import analyze_memecoin
result = analyze_memecoin('DOGE')
print(result)
```

---

## 📊 Progress Tracking

Use the checklist in `IMPLEMENTATION_PLAN.md`:

```markdown
Phase 1: Setup
[✅] File 1: requirements.txt
[⬜] File 2: src/core/config.py  <- Currently working on this
[⬜] File 3: src/utils/helpers.py
...
```

---

## 🚨 Common Pitfalls to Avoid

### 1. Don't Skip Files
Even if a file seems simple, implement it. The sequence matters.

### 2. Don't Work on Multiple Files Simultaneously
Finish one file, test it, then move on.

### 3. Test Before Moving On
If file 4 doesn't work, file 5 won't work either.

### 4. Use Mock Data Initially
Don't wait for real API access. Use mock data:
```python
# data_fetchers.py during development
def get_coin_data(ticker):
    # Mock data for testing
    return {
        'symbol': ticker,
        'current_price': 50000,
        'market_cap': 1000000000
    }
```

### 5. Handle Errors Gracefully
Every API call should have error handling:
```python
try:
    data = requests.get(url).json()
except Exception as e:
    print(f"Error: {e}")
    return None
```

---

## 🎓 Learning Resources

### APIs You'll Use:
- **CoinGecko**: https://www.coingecko.com/en/api/documentation
- **Binance**: https://binance-docs.github.io/apidocs/spot/en/
- **Alternative.me**: https://alternative.me/crypto/fear-and-greed-index/
- **CryptoPanic**: https://cryptopanic.com/developers/api/

### Python Concepts:
- **Requests library**: Making API calls
- **Pandas**: Data manipulation
- **Pytest**: Testing
- **dotenv**: Environment variables

---

## 💡 Tips for Success

1. **Work in short bursts**: 30-60 minutes per file
2. **Commit after each file**: Use git to track progress
3. **Ask for help early**: If stuck for >30 min, ask for guidance
4. **Use print statements liberally**: Debug as you go
5. **Read error messages carefully**: They usually tell you what's wrong

---

## 🎯 Example: Implementing File 2 (config.py)

Here's how you'd approach the first real file:

### Step 1: Read the requirements
Open `src/core/config.py` and read all TODOs.

### Step 2: Set up .env
```bash
cp .env.example .env
# Edit .env and add a test API key
```

### Step 3: Implement incrementally
```python
# First: Just load environment
from dotenv import load_dotenv
load_dotenv()
print("✓ Env loaded")

# Second: Load one API key
from os import getenv
COINGECKO_API_KEY = getenv('COINGECKO_API_KEY')
print(f"✓ Got key: {COINGECKO_API_KEY[:10]}...")

# Third: Add validation
def validate_config():
    if not COINGECKO_API_KEY:
        raise ValueError("CoinGecko API key missing")
    print("✓ Config valid")

validate_config()
```

### Step 4: Test
```bash
python -c "from src.core.config import validate_config; validate_config()"
# Should print: ✓ Config valid
```

### Step 5: Mark complete
Update `IMPLEMENTATION_PLAN.md`:
```markdown
Phase 1: Setup
[✅] File 1: requirements.txt
[✅] File 2: src/core/config.py  <- DONE!
[⬜] File 3: src/utils/helpers.py <- Next
```

---

## 📞 When You're Ready to Move On

After completing each phase, you should be able to:

**After Phase 1**: Fetch data from APIs and detect asset types
**After Phase 2**: Run individual analysis pillars
**After Phase 3**: Analyze specific asset types
**After Phase 4**: Generate formatted output
**After Phase 5**: Use the complete system end-to-end

---

## 🎉 Final Deliverable

When all files are complete, you'll have:
- A working CLI tool (`python main.py --asset BTC`)
- Automated tests (` pytest`)
- Social media post generator
- Modular, extensible architecture
- Professional documentation

**Ready to start? Begin with File 2: `src/core/config.py`**
