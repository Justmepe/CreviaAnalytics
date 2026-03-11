# Part 60 — Objective Swing-Based Trendlines
**Type:** Indicator | **Verdict:** MEDIUM — Validates StructureEngine v14.0 trendline-first. ATR*0.8 filter (vs our 0.5). MinTouchPoints=2.
**URL:** https://www.mql5.com/en/articles/21226

## What This Is
Swing-detection + trendline fitting tool that confirms our StructureEngine v14.0 approach is correct.
Key differences from our implementation: ATR multiplier 0.8 (more permissive than our 0.5),
minimum 2 touch points for a valid line, chronological ordering required.

## Swing Detection Algorithm
```python
def detect_swings(bars, lookback=5, atr_filter=0.8, use_atr=True) -> list:
    highs = [b.high for b in bars]
    lows  = [b.low  for b in bars]

    # ATR for size qualification
    import numpy as np
    ranges = [b.high - b.low for b in bars]
    atr = np.mean(ranges[-14:]) if len(ranges) >= 14 else np.mean(ranges)
    min_swing_size = atr * atr_filter if use_atr else 0

    swings = []
    for i in range(lookback, len(bars)-lookback):
        # Swing high: center bar high > all neighbors
        is_high = all(highs[i] > highs[i+j] and highs[i] > highs[i-j]
                      for j in range(1, lookback+1))
        if is_high:
            swing_size = highs[i] - min(lows[max(0,i-lookback):i+lookback+1])
            if swing_size >= min_swing_size:
                swings.append(('high', i, highs[i]))

        # Swing low: center bar low < all neighbors
        is_low = all(lows[i] < lows[i+j] and lows[i] < lows[i-j]
                     for j in range(1, lookback+1))
        if is_low:
            swing_size = max(highs[max(0,i-lookback):i+lookback+1]) - lows[i]
            if swing_size >= min_swing_size:
                swings.append(('low', i, lows[i]))

    swings.sort(key=lambda x: x[1])  # chronological ordering required
    return swings
```

## Trendline Validation Rules
```python
def validate_trendline(swing_type: str, swings: list,
                        min_touches=2, direction='auto') -> bool:
    if swing_type not in ('high', 'low'):
        return False
    filtered = [s for s in swings if s[0] == swing_type]
    if len(filtered) < min_touches:
        return False

    # Direction requirement
    prices = [s[2] for s in filtered]
    if swing_type == 'high' and direction == 'resistance':
        # Resistance trendline: descending highs
        if prices[-1] >= prices[0]: return False  # must be descending
    elif swing_type == 'low' and direction == 'support':
        # Support trendline: ascending lows
        if prices[-1] <= prices[0]: return False  # must be ascending

    return True
```

## Comparison With Our StructureEngine v14.0
| Feature | Part 60 | Our v14.0 |
|---------|---------|-----------|
| ATR filter | 0.8x ATR | 0.5x ATR (tighter) |
| Touch points | MinTouchPoints=2 | n_touches from _fit_trendline |
| Direction | Descending highs = resistance | Same |
| Chronological | Required | Yes (swing ordering) |
| Trendline type | Rays (extended) | Best-fit slope |

## ATR Multiplier Consideration
```python
# Our current: tol = atr * 0.5 (tighter, fewer fractals pass filter)
# Part 60: atr * 0.8 (more permissive, captures more swings)
# Recommendation: use 0.5 for major TF (M15), 0.8 for minor TF (M1)
# This way M15 structure is clean; M1 allows more granular swing detection
LOOKBACK_ATR_MULT = {'M1': 0.8, 'M5': 0.7, 'M15': 0.5, 'H1': 0.4}
```

## CreviaDeriv Calibration
```python
# In StructureEngine.identify_swing_points() — tune ATR tolerance by timeframe
atr_mult = LOOKBACK_ATR_MULT.get(timeframe, 0.5)
tol = atr * atr_mult
support    = self._fit_trendline(lows,  is_support=True,  tol=tol, require_ascending=True)
resistance = self._fit_trendline(highs, is_support=False, tol=tol, require_descending=True)
# This makes M1 trendlines slightly more permissive than M15 = appropriate
```

## What This Validates
1. Our trendline-first approach in v14.0 is the correct architecture (not fractal-first)
2. Chronological swing ordering matches our implementation
3. Descending highs = resistance / ascending lows = support is industry standard
4. Our ATR tolerance 0.5 is slightly tighter than their 0.8 — for M1 consider loosening to 0.7

## Key Difference: Ray vs Best-Fit
Part 60 extends trendlines as rays (maintaining original slope indefinitely).
Our v14.0 uses best-fit slope via O(n^2) max-touch algorithm.
Best-fit is more accurate. Ray is simpler and works well when only 2 touch points.
For 2-touch lines: ray = best-fit. For 3+ touches: our best-fit wins.