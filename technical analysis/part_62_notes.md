# Part 62 — Adaptive Parallel Channel Detection and Breakout System
**Type:** EA | **Verdict:** HIGH EXTRACT — Liquidity sweep rejection = critical upgrade to zone invalidation. Retest mode = zone retest confirmation. MaxSlopeDifference for channel vs wedge classification.
**URL:** https://www.mql5.com/en/articles/21443

## What This Is
Detects parallel channels (two parallel trendlines). Key extractions: liquidity sweep rejection filter
(wick beyond boundary + close back inside = NOT a breakout) and retest mode (wait for price to return
to broken zone before confirming entry). Both directly upgrade our zone invalidation logic.

## Parallel Channel Detection Algorithm
```python
def is_parallel_channel(upper_slope, lower_slope, max_slope_diff=0.1) -> bool:
    return abs(upper_slope - lower_slope) <= max_slope_diff

def score_channel_candidate(upper_touches, lower_touches,
                              upper_slope, lower_slope,
                              channel_width_atr, atr,
                              min_width_atr=1.0) -> float:
    if not is_parallel_channel(upper_slope, lower_slope):
        return 0.0
    if channel_width_atr < min_width_atr:
        return 0.0
    return float(upper_touches + lower_touches)  # score by total touch count
```

## Liquidity Sweep Rejection (CRITICAL)
```python
def is_liquidity_sweep(bar_high, bar_low, bar_close,
                        boundary_level: float,
                        direction: str) -> bool:
    if direction == 'upward_break':
        # Bullish sweep: bar wicked above boundary but closed BELOW = false break
        return bar_high > boundary_level and bar_close < boundary_level
    else:  # downward_break
        # Bearish sweep: bar wicked below boundary but closed ABOVE = false break
        return bar_low < boundary_level and bar_close > boundary_level

# APPLY to zone invalidation in EntryEngine:
def is_zone_truly_broken(bar, zone_level, direction, atr, tol_atr=0.1) -> bool:
    tol = atr * tol_atr
    if direction == 'BUY':  # zone is demand — break = close below bottom
        if bar.close < zone_level - tol:
            # Additional check: not a sweep (wick only below, close above)
            if is_liquidity_sweep(bar.high, bar.low, bar.close, zone_level, 'downward_break'):
                return False  # sweep, not a real break
            return True
    else:  # zone is supply — break = close above top
        if bar.close > zone_level + tol:
            if is_liquidity_sweep(bar.high, bar.low, bar.close, zone_level, 'upward_break'):
                return False
            return True
    return False
```

## Retest Mode — Zone Confirmation After Break
```python
from enum import Enum

class ZoneBreakState(Enum):
    INTACT      = 'intact'      # price has not touched zone
    TESTING     = 'testing'     # price in zone now
    BREAK_PENDING = 'pending'   # first close beyond zone
    RETEST      = 'retest'      # price returned after break
    CONFIRMED   = 'confirmed'   # retest + bounce = confirmed break

def update_zone_break_state(state: ZoneBreakState, bar, zone_top, zone_bottom,
                             zone_type: str, atr: float) -> ZoneBreakState:
    tol = atr * 0.10
    if state == ZoneBreakState.BREAK_PENDING:
        # Waiting for retest: has price come back near zone?
        near_zone = zone_bottom - tol <= bar.close <= zone_top + tol
        if near_zone:
            return ZoneBreakState.RETEST
    elif state == ZoneBreakState.RETEST:
        # In retest: did price bounce away (confirming break)?
        if zone_type == 'supply' and bar.close < zone_bottom - tol:
            return ZoneBreakState.CONFIRMED
        if zone_type == 'demand' and bar.close > zone_top + tol:
            return ZoneBreakState.CONFIRMED
    return state
```

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| MaxSlopeDifference | 0.1 | Channel must have parallel slopes |
| MinChannelWidthATR | 1.0 | Minimum useful channel height |
| TouchToleranceATR | 0.2 | Proximity for touch counting |
| MinTouchPointsRequired | 2 | Per boundary |
| SwingLookback | 5 | Fractal detection window |
| LookbackBars | 150 | Historical search window |

## MaxSlopeDifference for Pattern Classification
```python
def classify_pattern_type(upper_slope, lower_slope) -> str:
    if abs(upper_slope - lower_slope) <= 0.1:
        return 'channel'    # parallel = horizontal or diagonal channel
    if upper_slope > 0 and lower_slope > 0 and lower_slope > upper_slope:
        return 'rising_wedge'   # converging upward (Part 63)
    if upper_slope < 0 and lower_slope < 0 and upper_slope < lower_slope:
        return 'falling_wedge'  # converging downward (Part 63)
    return 'triangle'   # one slope flat, other slanted
```

## Superior Version Improvements
1. Liquidity sweep check on EVERY zone break evaluation — prevents false invalidation on spike bars
2. Retest mode: after supply zone break, enter only when price retests zone from below (becomes support)
3. On Crash/Boom: spike candles ARE liquidity sweeps — wick far below + close back above = demand zone holds
4. TouchToleranceATR=0.2 is tighter than our 0.5 — use 0.2 for supply/demand zone boundaries
5. Store ZoneBreakState per zone in ZoneState dataclass for retest tracking across bars