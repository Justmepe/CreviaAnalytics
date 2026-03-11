# Part 58 — Range Contraction Analysis and Maturity Classification
**Type:** Module | **Verdict:** HIGH EXTRACT — Additive maturity score, overlap ratio, boundary tests counter, breakout readiness
**URL:** https://www.mql5.com/en/articles/21109

## What This Is
A compression maturity scorer. Goes deeper than Part 57 compression detection by scoring HOW COMPRESSED
the range is (None/Early/Building/Mature). Mature = breakout imminent. Adds zone quality factor.

## Candle Overlap Ratio (Key Formula)
```python
def candle_overlap_ratio(bars, window=30) -> float:
    ratios = []
    for i in range(1, len(bars)):
        h1, l1 = bars[i].high, bars[i].low
        h2, l2 = bars[i-1].high, bars[i-1].low
        intersection = max(0, min(h1, h2) - max(l1, l2))
        union = max(h1, h2) - min(l1, l2)
        if union > 0:
            ratios.append(intersection / union)
    return sum(ratios[-window:]) / len(ratios[-window:]) if ratios else 0.0
# High overlap = price moves little bar-to-bar = compression
# Low overlap = price expanding = trending or volatile
```

## Additive Maturity Scoring
```python
from enum import Enum
import numpy as np

class RangeMaturity(Enum):
    NONE     = 'none'
    EARLY    = 'early'     # some contraction, not yet developed
    BUILDING = 'building'  # contraction + boundary tests
    MATURE   = 'mature'    # all criteria met = breakout imminent

def compute_range_maturity(bars,
                            window=30,
                            prev_window=30,
                            rejection_min_pts=3.0,
                            min_tests_early=2,
                            min_tests_mature=4) -> tuple:
    if len(bars) < window + prev_window:
        return RangeMaturity.NONE, 0

    recent = bars[-window:]
    prior  = bars[-window-prev_window:-window]

    recent_ranges = np.array([b.high - b.low for b in recent])
    prior_ranges  = np.array([b.high - b.low for b in prior])
    recent_avg = np.mean(recent_ranges)
    prior_avg  = np.mean(prior_ranges)

    score = 0

    # 1. Contraction: recent range < prior range
    if recent_avg < prior_avg * 0.85:
        score += 1
    if recent_avg < prior_avg * 0.70:
        score += 1  # strong contraction = +2 total

    # 2. Overlap: high overlap = low momentum
    overlap = candle_overlap_ratio(recent, window)
    if overlap > 0.55:
        score += 1
    if overlap > 0.70:
        score += 1

    # 3. Boundary tests (price approaches extremes of the range)
    range_high = max(b.high for b in recent)
    range_low  = min(b.low  for b in recent)
    box_height = range_high - range_low
    touch_tol  = box_height * 0.10  # 10% of range

    boundary_tests = sum(
        1 for b in recent
        if b.high >= range_high - touch_tol or b.low <= range_low + touch_tol
    )

    # 4. Rejection candles at boundary (wick beyond + close inside)
    rejections = 0
    for b in recent:
        upper_wick = b.high - max(b.open, b.close)
        lower_wick = min(b.open, b.close) - b.low
        if (b.high >= range_high - touch_tol and
                upper_wick >= rejection_min_pts * 0.00001 and
                b.close < range_high - touch_tol):
            rejections += 1
        if (b.low <= range_low + touch_tol and
                lower_wick >= rejection_min_pts * 0.00001 and
                b.close > range_low + touch_tol):
            rejections += 1

    if boundary_tests >= min_tests_early:
        score += 1
    if rejections >= 2:
        score += 1
    if boundary_tests >= min_tests_mature and rejections >= 3:
        score += 1

    # 5. Invalidation: any close outside range box = not a clean compression
    for b in recent:
        if b.close > range_high or b.close < range_low:
            return RangeMaturity.NONE, 0  # box violated

    # Map score to maturity
    if score >= 6:   return RangeMaturity.MATURE,   score
    if score >= 4:   return RangeMaturity.BUILDING, score
    if score >= 2:   return RangeMaturity.EARLY,    score
    return RangeMaturity.NONE, score
```

## Parameter Defaults
| Parameter | Default | Purpose |
|-----------|---------|---------|
| InpWindowBars | 30 | Active analysis window |
| InpPrevWindowBars | 30 | Reference comparison period |
| InpRejectionMinPts | 3 | Min wick size for rejection count |
| InpMinTestsForEarly | 2 | Min boundary tests for Early |
| InpMinTestsForMature | 4 | Min boundary tests for Mature |

## CreviaDeriv Integration
```python
maturity, score = compute_range_maturity(m15_bars[-60:])

if maturity == RangeMaturity.MATURE:
    # Breakout imminent — enter on first breakout candle with zone touch
    entry_mode = 'breakout_priority'
    # Tighten SL: range is compressed, reversals are small
    sl_multiplier = 1.0  # instead of 1.5

elif maturity == RangeMaturity.BUILDING:
    # Range maturing but not yet ripe — wait for zone touch with departure
    entry_mode = 'standard'

elif maturity == RangeMaturity.EARLY:
    entry_mode = 'standard'  # no change

elif maturity == RangeMaturity.NONE:
    # Price is trending or erratic — standard trend-following
    entry_mode = 'trend_follow'

# Add maturity to zone quality score
maturity_boost = {RangeMaturity.MATURE: 20, RangeMaturity.BUILDING: 10,
                  RangeMaturity.EARLY: 5, RangeMaturity.NONE: 0}
zone.quality += maturity_boost[maturity]
```

## Superior Version Improvements
1. Use M15 bars for range maturity (M1 is too noisy for 30-bar window)
2. Mature + zone at boundary = highest priority entry setup
3. Overlap ratio alone is useful as M1 trend filter: high overlap = don't enter trend-following trades
4. Add dead-drift penalty: if range/ATR < 0.3 for 20+ bars, penalize score (choppy, not true compression)
5. Track maturity score over time: NONE → EARLY → BUILDING → MATURE = ascending setup quality