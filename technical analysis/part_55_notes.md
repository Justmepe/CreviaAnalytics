# Part 55 — CPI Mini-Candle Overlay (Candle Pressure Index)
**Type:** Indicator | **Verdict:** HIGH EXTRACT — CPI formula = CPP from Part 37, 5-zone classification, non-repainting noise gate
**URL:** https://www.mql5.com/en/articles/20949

## What This Is
CPI (Candle Pressure Index) measures WHERE within a candle the bar closed, normalized to [-1, +1]. Same formula as CPP (Part 37) and CLV (Parts 55-57). Strong Buy = close at top; Strong Sell = close at bottom. Non-repainting: only closed bars evaluated.

## CPI Formula
```python
def compute_cpi(high: float, low: float, close: float) -> float:
    rng = high - low
    if rng < 1e-9:
        return 0.0  # noise gate: flat bar = neutral
    return (2 * close - high - low) / rng
    # +1.0 = closed at high (max buying pressure)
    # 0.0  = closed at midpoint (balanced)
    # -1.0 = closed at low (max selling pressure)
```

## 5-Zone Classification
```python
STRONG_THRESHOLD = 0.60  # default
MILD_THRESHOLD   = 0.20  # default

def classify_cpi(cpi: float) -> str:
    if cpi >= STRONG_THRESHOLD:   return 'strong_buy'   # closed in top 20%
    if cpi >= MILD_THRESHOLD:     return 'mild_buy'     # top 20-40%
    if cpi > -MILD_THRESHOLD:     return 'neutral'      # middle 40%
    if cpi > -STRONG_THRESHOLD:   return 'mild_sell'    # bottom 20-40%
    return 'strong_sell'                                 # closed in bottom 20%
```

## Signal State Transitions (Non-Repainting)
```python
def cpi_signal_on_close(prev_cpi: float, curr_cpi: float) -> str:
    prev_strong = abs(prev_cpi) >= STRONG_THRESHOLD
    curr_strong = abs(curr_cpi) >= STRONG_THRESHOLD
    if not prev_strong and curr_strong:
        return 'entered_strong_zone'   # new conviction candle
    if prev_strong and not curr_strong:
        return 'exited_strong_zone'    # conviction waning
    if prev_cpi * curr_cpi < 0:
        return 'sign_flip'             # pressure reversed
    return 'no_event'
```

## CPI as Departure Gate
```python
# In EntryEngine._detect_departure_candle()
h, l, c = m1_bars[-1].high, m1_bars[-1].low, m1_bars[-1].close
cpi = compute_cpi(h, l, c)

if signal.direction == 'BUY':
    if cpi >= 0.60:   departure_strength = 4  # closed near high = strong departure
    elif cpi >= 0.20: departure_strength = 2  # mild close position
    else:             return None  # closed in bottom half = weak BUY departure

if signal.direction == 'SELL':
    if cpi <= -0.60:  departure_strength = 4  # closed near low = strong departure
    elif cpi <= -0.20: departure_strength = 2
    else:              return None  # closed in top half = weak SELL departure
```

## Noise Gate — Critical for M1
```python
MIN_RANGE_POINTS = 5  # skip calculation if candle < 5 points
def safe_cpi(high, low, close, min_range=5.0, point=0.00001) -> float:
    if (high - low) < min_range * point:
        return 0.0  # doji-like bar: no pressure signal
    return compute_cpi(high, low, close)
```
On M1 during low-volatility periods, candles may be near-flat. The noise gate prevents
division by tiny range giving spurious +/-1 signals.

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| StrongThreshold | 0.60 | CPI boundary for strong zone |
| MildThreshold | 0.20 | CPI boundary for mild zone |
| MarkerScale | 0.25 | Mini-candle height on chart |
| MinRangePoints | 5 | Noise gate (skip flat bars) |

## Relationship to Other Parts
- Part 37 CPP: same formula, named CPP. Used as departure gate there too.
- Part 56: uses CPI to classify zone acceptance (close beyond level + CPI >= 0.20 = broken).
- Part 57 CLV: same formula again, used for market state classification.
- Conclusion: CPI/CPP/CLV are the SAME metric with different names. Implement once, use everywhere.

## Superior Version
Combine CPI with candle type for departure scoring matrix:
| Candle Type | CPI | departure_strength |
|-------------|-----|-------------------|
| Marubozu | >= 0.60 | 4 |
| Engulfing | >= 0.60 | 4 |
| Engulfing | 0.20-0.60 | 3 |
| Pin Bar | >= 0.60 | 3 |
| Simple bull | >= 0.60 | 2 |
| Simple bull | 0.20-0.60 | 1 |
| Any | < 0.20 (wrong dir) | reject |