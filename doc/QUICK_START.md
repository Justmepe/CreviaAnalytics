# Quick Reference: Claude AI in Your Crypto Engine

## TL;DR - What Changed

✨ **X Threads Now Use Claude AI**
- Natural, professional 10-tweet threads
- Copy-paste ready for Twitter/X
- Falls back to templates if Claude unavailable

✨ **News Reports Now Use Claude AI**  
- Fact-checked market memos
- Real-time price grounding
- Professional Bloomberg-style tone

✨ **Main Orchestrator Updated**
- Added news report generation phase
- Enhanced thread generation
- Continuous 24/7 analysis cycle

---

## Quick Start

### 1. Setup (One Time)
```bash
# Ensure .env has:
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Install/update dependencies
pip install anthropic feedparser dateparser beautifulsoup4
```

### 2. Run the Engine
```bash
cd /path/to/crypto-analysis-engine
python main.py
```

### 3. Check Generated Content
```bash
# X threads (copy-paste to Twitter)
cat output/x_thread_*.txt

# News reports (fact-checked)
cat output/news_memo_*.txt

# Detailed analyses
cat output/analysis_*.txt
```

---

## File Locations

| File | Purpose |
|------|---------|
| `src/output/x_thread_generator.py` | X thread creation (Claude AI) |
| `src/content/news_narrator.py` | News report generation (Claude AI) |
| `main.py` | Orchestrator with news + threads |
| `output/x_thread_*.txt` | Generated threads (ready to post) |
| `output/news_memo_*.txt` | Generated news reports |
| `data/research_*.json` | Raw market data |
| `data/analyses_*.json` | Analysis results |

---

## Customization

### Change Thread Tone
Edit `src/output/x_thread_generator.py` line ~120:
```python
prompt = f"""You are a professional crypto analyst...
# Modify this prompt for different tone
```

### Change News Report Style
Edit `src/content/news_narrator.py` line ~130:
```python
prompt = f"""You are a senior crypto market analyst...
# Modify this prompt for different style
```

### Change Timing
Edit `.env`:
```env
RESEARCH_INTERVAL=60       # Seconds between market data fetches
ANALYSIS_INTERVAL=300      # Seconds between analyses
THREAD_INTERVAL=3600       # Seconds between thread generation
```

---

## Outputs Explained

### X Thread Format
```
1/ Market overview (price, sentiment)
2/ Sentiment check (fear/greed index)
3/ Macro context (global market events)
4/ Key levels (support/resistance)
5/ Memecoins analysis
6/ Privacy coins analysis
7/ DeFi analysis
8/ Whale activity
9/ Alt rotation patterns
10/ Final take (actionable insights)
```
✅ Copy-paste directly to Twitter

### News Report Format
```
📊 Market Update — BTC
================
Current Price: $78,500.00 (live data)

Top Headlines:
• [Article 1] via [Source]
• [Article 2] via [Source]

Key Developments:
1. [Analysis with source]
2. [Analysis with source]

Fact-Check Notes:
• Headline mentions $X vs current $Y (marked)
```
✅ Professional, source-attributed

---

## Troubleshooting

### Threads Not Generating?
```bash
# Check .env has API key
grep ANTHROPIC_API_KEY .env

# Check output directory exists
ls -la output/

# Check logs
tail -50 crypto_engine.log
```

### News Reports Missing?
```bash
# Verify RSS feeds are working
python -c "from src.pillars.rss_engine import CryptoNewsAggregator; a = CryptoNewsAggregator(); print(len(a.force_fetch_all_feeds()))"

# Check price data
python -c "from src.utils.data_fetchers import fetch_coin_data; print(fetch_coin_data('BTC'))"
```

### API Errors?
```bash
# Test Claude API
python tests/test_claude_model.py

# Check API key validity
python -c "import anthropic; c = anthropic.Anthropic(); print(c.beta.threads.create())"
```

---

## Performance Targets

| Operation | Time | Frequency |
|-----------|------|-----------|
| Market Research | 15-20s | Every 60s |
| Asset Analysis | 30-40s | Every 300s |
| News Reports | 5-10s | Every 300s |
| X Thread Gen | 5-10s | Every 3600s |
| **Full Cycle** | **~60s** | **Continuous** |

---

## Claude API Usage

| Type | Tokens | Frequency |
|------|--------|-----------|
| X Thread | ~500 | 1/hour |
| News Memo | ~300 | 4/hour |
| **Estimated** | **~2000/hour** | - |
| **Daily** | **~48K** | - |
| **Monthly** | **~1.4M** | - |

---

## Key Features ✨

| Feature | Status | Details |
|---------|--------|---------|
| Claude AI Threads | ✅ | Natural, professional |
| Claude AI News | ✅ | Fact-checked reports |
| Model Fallback | ✅ | Auto-tries next model |
| Template Fallback | ✅ | If API unavailable |
| 19 RSS Feeds | ✅ | Constant updates |
| Price Grounding | ✅ | Real-time verification |
| Copy-Paste Ready | ✅ | No formatting needed |
| 24/7 Operation | ✅ | Continuous loop |

---

## Testing

```bash
# Test thread generation
python tests/test_claude_x_thread.py
# Output: tests/claude_x_thread_example.txt

# Test setup
python tests/setup_test.py
# Validates: Python, API key, dependencies, connectivity

# Test news generation  
python tests/generate_fact_checked_news.py
# Output: tests/fact_checked_memo_*.txt
```

---

## Common Questions

**Q: Will it post automatically to Twitter?**
A: No, it generates ready-to-post text files. You copy-paste the content.

**Q: What if Claude API is down?**
A: Falls back to professional templates. Quality is maintained.

**Q: Can I customize the writing style?**
A: Yes! Edit the prompts in `x_thread_generator.py` and `news_narrator.py`.

**Q: How much does Claude cost?**
A: Sonnet model is $3/1M input tokens. You'll use ~1-2K tokens/hour.

**Q: What data sources are used?**
A: 19 RSS feeds + CoinGecko APIs + real-time price feeds.

**Q: Can I adjust the schedule?**
A: Yes! Use environment variables (RESEARCH_INTERVAL, ANALYSIS_INTERVAL, THREAD_INTERVAL).

---

## Next Steps

1. ✅ **Start it**: `python main.py`
2. 📊 **Monitor**: Watch `output/` directory
3. 📱 **Post**: Copy-paste threads to Twitter
4. 🎯 **Optimize**: Customize prompts for your style
5. 📈 **Scale**: Adjust intervals and asset list

---

**Your crypto analysis engine is now powered by Claude AI! 🚀**

Need help? Check the full docs:
- `CLAUDE_INTEGRATION.md` - Detailed integration guide
- `ARCHITECTURE.md` - System architecture
- `IMPLEMENTATION_SUMMARY.md` - Complete changes

**Version**: 2.0 (Claude AI Enhanced)
**Status**: ✅ Production Ready
**Last Updated**: February 1, 2026
