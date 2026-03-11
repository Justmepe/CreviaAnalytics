# Part 09 — External Flow
**Series:** Price Action Analysis Toolkit Development
**Type:** MQL5 EA + Python Flask Server | **Verdict:** ARCHITECTURE REFERENCE — validates our Python-first design
**Published:** 2025-01-23

---

## What It Does
First hybrid tool in the series. MQL5 EA collects 10 days of D1 OHLCV, serialises to CSV, POSTs to a Python Flask server. Python calculates 10-day average price, compares to last close → BUY if above, SELL if below. Returns JSON. MT5 displays signal on chart.

---

## The Series Pivot
Parts 1-8 were pure MQL5. **Part 9 is the author acknowledging MQL5 is insufficient for advanced analysis.** They build a bridge to Python because MQL5 cannot use Pandas, scikit-learn, or complex data structures. This is the series trying to reach what we ARE from day one.

---

## The Signal (Extremely Simple)
```
avg_price = mean((high + low + open + close) / 4) for last 10 D1 bars
signal = 'BUY' if last_close > avg_price else 'SELL'
```
This is the baseline — a price-vs-mean comparison. Not a real strategy, just a direction indicator.

---

## Bridge Architecture
```
MT5 EA
  ↓  collect 10 D1 bars
  ↓  format → CSV string
  ↓  HTTP POST to localhost:5000/analyze
Python Flask
  ↓  decode CSV → Pandas DataFrame
  ↓  calculate avg_price, avg_volume, signal
  ↓  return JSON {signal, avg_price, avg_volume, explanation}
MT5 EA
  ↓  parse JSON
  ↓  display on chart via Comment()
```

**Their bridge = our BrokerDataAdapter.** We just start from the Python side.

---

## Why This Architecture Exists (and Why We Don't Need It)
| Their Problem | Our Solution |
|---|---|
| MQL5 can't use Pandas | We're already in Python |
| MQL5 can't connect to external APIs | BrokerDataAdapter does this natively |
| Need Flask server running 24/7 | No server needed — direct broker API calls |
| CSV serialisation fragility | Native Pandas DataFrames throughout |
| HTTP latency on every signal | Direct function calls, no network hop |

---

## Our Superior Version: The Signal They Should Have Built
Their `avg_price` comparison misses everything that matters. Our gate chain replaces it entirely:

```python
# Part 9's signal (what they built)
signal = 'BUY' if last_close > avg_price_10d else 'SELL'

# Our signal (what it should be)
# Gate A: Are we in a scanning window for this symbol?
# Gate B: Is price interacting with a demand/supply zone on M1?
# Gate C: Is there an EMA3 crossover in the right direction?
# Gate D: Is ADX rising and > 20 (sleeping market filter)?
# Gate E: Does the zone classify correctly (demand=BUY, supply=SELL)?
# Gate F: Is VWV score above threshold (enough energy for a move)?
# Gate G: Is there a valid departure candle in the right direction?
# Gate H: Does M15 trendline respect the direction?
# → All gates pass → Signal with SL/TP
```

---

## What to Keep
- Data flow architecture concept (collect → analyse → display)
- Time-interval throttling for signal updates (not on every tick)
- JSON response structure with explanation field (good for logging)
- D1-to-M1 timeframe context pattern (confirmed by our M15→M1 split)

## What to Discard
- The entire HTTP bridge
- Flask server dependency
- CSV serialisation
- avg_price comparison signal
- 10-day simple average (no trend structure)

## Validation for CreviaDeriv
1. **Python-first is right**: The complexity of this bridge proves our architecture decision is correct.
2. **D1 context → M1 execution**: Their D1 signal + M1 trade matches our M15 structure → M1 entry pattern. Higher-TF bias into lower-TF precision is the right approach at any scale.
3. **Signal with explanation**: Their JSON includes `explanation` string. Our EntrySignal should carry a human-readable reason string — useful for live logging, debugging, and performance review.
