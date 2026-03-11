# Part 12 — External Flow (III) TrendMap
**Series:** Price Action Analysis Toolkit Development
**Type:** MQL5 EA + Python Flask | **Verdict:** EXTRACT — Fibonacci framework, VWAP-vs-midpoint bias filter
**Published:** 2025-02-13

---

## What It Does
Detects swing H/L over a lookback window, derives 7 Fibonacci levels, calculates VWAP, and uses VWAP position relative to the 50% Fibonacci midpoint as a directional bias. Enters at 38.2% (support, bullish bias) or 61.8% (resistance, bearish bias).

---

## The Key Insight: VWAP vs Fibonacci Midpoint
```python
midpoint = (swing_high + swing_low) / 2   # = 50% Fibonacci level
bias = 'BULLISH' if vwap < midpoint else 'BEARISH'

# Entry zones:
fib_38 = swing_high - 0.382 * (swing_high - swing_low)  # support
fib_62 = swing_high - 0.618 * (swing_high - swing_low)  # resistance

if bias == 'BULLISH' and close_near(fib_38):  signal = 'BUY'
if bias == 'BEARISH' and close_near(fib_62):  signal = 'SELL'
```

VWAP below midpoint = buyers paid above fair value = bullish. Price at 38.2% retracement = logical support = BUY entry.

---

## Fibonacci Calculator (Keep This Exactly)
```python
def fibonacci(swing_high, swing_low):
    r = swing_high - swing_low
    return {
        '0.0':   swing_high,
        '0.236': swing_high - 0.236 * r,
        '0.382': swing_high - 0.382 * r,
        '0.500': swing_high - 0.500 * r,   # midpoint
        '0.618': swing_high - 0.618 * r,
        '0.786': swing_high - 0.786 * r,
        '1.0':   swing_low
    }
```

---

## Our Superior Version Design

### Zone + Fibonacci Confluence
When a supply/demand zone COINCIDES with a Fibonacci level, that's a high-confidence setup:
```python
def fib_zone_confluence(zone, swing_high, swing_low, tolerance_pct=0.002):
    fib = fibonacci(swing_high, swing_low)
    zone_mid = (zone.price_high + zone.price_low) / 2
    for level, price in fib.items():
        if abs(price - zone_mid) / price < tolerance_pct:
            return True, float(level)  # zone aligns with this Fib level
    return False, None
```

### VWAP Bias as Pre-Filter
Add to EntryEngine: only allow BUY setups when VWAP bias = BULLISH:
```python
if session_vwap < fib_midpoint:  # bullish bias
    if zone.type == 'DEMAND':    # structural alignment
        if vwv_score > threshold: # velocity confirmation
            signal = BUY
```

---

## Validation for CreviaDeriv
1. **Fibonacci 38.2% ≈ our demand zones**: Both mark where price should find support after a corrective pullback. Our zones are more precise (derived from actual supply/demand structure), but Fibonacci provides a secondary validation layer.
2. **Swing H/L detection**: Our StructureEngine uses fractal-based detection (proper HH/HL/LH/LL). This tool uses window max/min — much simpler. Ours is strictly superior.
3. **VWAP bias filter is addable to our system**: As a pre-filter before zone interaction check — adds a macro fair-value context layer.
