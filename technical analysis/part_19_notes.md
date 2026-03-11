# Part 19 — ZigZag Analyzer
**Series:** Price Action Analysis Toolkit Development
**Type:** Indicator | **Verdict:** EXTRACT — linear regression trendline formula, parallel channel detection, two-tier S/R
**Published:** 2025-05

---

## What It Does
Runs ZigZag indicator to find swing highs/lows, then fits linear regression trendlines through those swings. If both support and resistance trendlines slope the same direction, uses averaged slope for a parallel channel. Also draws major/minor horizontal S/R from swing extremes.

---

## Linear Regression Trendline Formula
```python
def fit_regression_trendline(times: list, prices: list) -> tuple:
    """
    Least-squares linear regression through swing points.
    times:  bar indices (x-axis)
    prices: swing prices (y-axis)
    Returns: (slope, intercept, r_squared)
    """
    n = len(times)
    sum_t  = sum(times)
    sum_p  = sum(prices)
    sum_tp = sum(t * p for t, p in zip(times, prices))
    sum_t2 = sum(t ** 2 for t in times)

    slope     = (n * sum_tp - sum_t * sum_p) / (n * sum_t2 - sum_t ** 2)
    intercept = (sum_p - slope * sum_t) / n

    # R²
    mean_p    = sum_p / n
    ss_tot    = sum((p - mean_p) ** 2 for p in prices)
    predicted = [slope * t + intercept for t in times]
    ss_res    = sum((p - pred) ** 2 for p, pred in zip(prices, predicted))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return slope, intercept, r_squared
```

---

## Parallel Channel Detection
```python
def detect_parallel_channel(slope_support, slope_resistance) -> float:
    """
    If both trendlines slope the same direction, they form a channel.
    Returns averaged slope for parallel channel, or None if not parallel.
    """
    if (slope_support > 0) == (slope_resistance > 0):  # same sign
        return (slope_support + slope_resistance) / 2.0
    return None   # diverging/converging lines — not a channel
```

---

## ZigZag Parameters (Baseline)

| Param | Default | Meaning |
|---|---|---|
| `ZZ_Depth` | 12 | Min bars between ZigZag reversals |
| `ZZ_Deviation` | 5% | Min % price change for a valid reversal |
| `ZZ_Backstep` | 3 | Bars to look back to confirm the swing |

Our fractal detection uses `min_swing_diff_pct=0.05%` — much finer. For M15 structural swings, consider 1-2% to filter to major swings only.

---

## Two-Tier S/R from Swings
```python
def compute_two_tier_sr(swing_highs: list, swing_lows: list) -> dict:
    return {
        'major_resistance': max(swing_highs),
        'minor_resistance': sorted(swing_highs)[-2],   # second highest
        'major_support':    min(swing_lows),
        'minor_support':    sorted(swing_lows)[1],     # second lowest
    }
```

---

## What to Keep
- Linear regression formula (exact — confirmed standard least-squares)
- Parallel channel detection (same-sign slopes → averaged slope)
- Two-tier S/R from swing extremes
- ZigZag parameter baseline (depth=12, deviation=5%, backstep=3)

## What to Discard
- ZigZag as primary swing source (our fractal is better)
- 10-swing hard limit
- No signal generation
- No R² quality filter (we already have this in Gate H)

## What to Improve
- Add R² output to our trendline fitting — we already use it, but verify formula matches
- Add parallel channel detection as post-processing in StructureEngine
- Consider large-swing filter (deviation=1-2%) as an optional mode for M15 structure

---

## Validation for CreviaDeriv
1. **Our trendline formula should match this** — verify `_fit_trendline()` uses max-touch (O(n²)) vs least-squares. Both are valid; max-touch is better for S/R. Linear regression is better for trend direction.
2. **Parallel channel is a new structural pattern** — when StructureEngine detects support and resistance trendlines with same-sign slopes, flag this as a channel. Channels have different breakout implications than wedges (converging) or expanding patterns (diverging).
3. **ZigZag deviation=5% is major-swing only** — at M15, this captures only the most significant structural swings. Could add a "major swing filter" mode to our swing detection for cleaner higher-timeframe structure.
