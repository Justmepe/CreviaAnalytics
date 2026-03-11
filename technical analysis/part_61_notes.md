# Part 61 — Structural Slanted Trendline Breakouts with 3-Swing Validation
**Type:** Indicator | **Verdict:** HIGH EXTRACT — 3-swing validation = stronger than 2-touch. ThirdSwingToleranceATR=0.15. Anti-repainting deduplication.
**URL:** https://www.mql5.com/en/articles/21277

## What This Is
Upgrades basic 2-touch trendlines to require a 3rd swing confirmation. The first two swings anchor the line,
the third must fall within ThirdSwingToleranceATR=0.15 of the interpolated line. Only 3-confirmed lines
are used for breakout detection. Directly upgrades our StructureEngine v14.0 trendline quality gate.

## 3-Swing Validation Formula
```python
def interpolate_line_at_index(p1_idx, p1_price, p2_idx, p2_price, target_idx) -> float:
    if p2_idx == p1_idx: return p1_price
    slope = (p2_price - p1_price) / (p2_idx - p1_idx)
    return p1_price + slope * (target_idx - p1_idx)

def third_swing_confirms(p1_idx, p1_price, p2_idx, p2_price,
                           p3_idx, p3_price, atr: float,
                           tol_atr=0.15) -> bool:
    interpolated = interpolate_line_at_index(p1_idx, p1_price, p2_idx, p2_price, p3_idx)
    tolerance = tol_atr * atr
    return abs(p3_price - interpolated) <= tolerance
```

## Breakout Detection (Anti-Repainting)
```python
def detect_trendline_breakout(closes, bar_times, tl_p1_idx, tl_p1_price,
                               tl_p2_idx, tl_p2_price, buf_pts=5e-5) -> dict:
    last_buy_bar = None
    last_sell_bar = None
    results = []
    for i in range(1, len(closes)):
        line_prev = interpolate_line_at_index(tl_p1_idx, tl_p1_price,
                                              tl_p2_idx, tl_p2_price, i-1)
        line_curr = interpolate_line_at_index(tl_p1_idx, tl_p1_price,
                                              tl_p2_idx, tl_p2_price, i)
        # CrossedUp: prev below, curr above
        crossed_up   = closes[i-1] <= line_prev + buf_pts and closes[i] > line_curr + buf_pts
        # CrossedDown: prev above, curr below
        crossed_down = closes[i-1] >= line_prev - buf_pts and closes[i] < line_curr - buf_pts
        if crossed_up and bar_times[i] != last_buy_bar:
            last_buy_bar = bar_times[i]
            results.append({'bar': i, 'direction': 'BUY', 'time': bar_times[i]})
        if crossed_down and bar_times[i] != last_sell_bar:
            last_sell_bar = bar_times[i]
            results.append({'bar': i, 'direction': 'SELL', 'time': bar_times[i]})
    return results
```

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| SwingLookback | 5 | Fractal neighborhood |
| ThirdSwingToleranceATR | 0.15 | Third swing proximity threshold |
| MinTouchPointsRequired | 3 | After 3-swing confirmation |
| BreakoutBufferPoints | 5 | Points beyond line for trigger |
| BreakoutUseClose | True | Closed-bar only (no repainting) |
| RequireThirdSwingAfterAnchor2 | True | 3rd swing must be chronologically after 2nd |

## StructureEngine v14.0 Integration
```python
# Upgrade _fit_trendline() to require 3-touch confirmation
def is_trendline_confirmed(support_tl, all_lows, atr, tol_atr=0.15):
    if support_tl is None: return False
    if support_tl.get('n_touches', 0) < 3: return False  # need at least 3 touches

    # Find 3 most recent touch points and validate 3rd vs line from 1st+2nd
    # If touches list available:
    touches = support_tl.get('touch_indices', [])
    if len(touches) < 3: return False

    p1_i, p2_i, p3_i = touches[0], touches[1], touches[-1]
    interp = interpolate_line_at_index(
        p1_i, all_lows[p1_i], p2_i, all_lows[p2_i], p3_i)
    return abs(all_lows[p3_i] - interp) <= tol_atr * atr

# In gate H check: only respect trendline if confirmed by 3 swings
if not is_trendline_confirmed(structure.support_trendline, all_lows, atr):
    pass  # trendline not yet validated — skip gate H on this line
```

## How ThirdSwingToleranceATR=0.15 Compares to Our 0.5
Our current `tol = atr * 0.5` is 3.3x more permissive than Part 61's 0.15.
This means we accept 'near-touches' that Part 61 would reject.
Recommendation:
- Gate H (trendline respect): use tol=0.15 ATR (strict — only well-validated lines)
- _fit_trendline (touch counting): keep 0.5 ATR (permissive — finds lines more easily)

## Superior Version
1. Store touch_indices list in support/resistance trendline dict in StructureState
2. Gate H should only fire if n_touches >= 3 (currently checks R^2 >= 0.7, not touch count)
3. Deduplication: if gate H fires, don't fire again within 5 bars on same line
4. 3rd swing confirmation on M1 micro trendline: more reliable M1 entries near zone