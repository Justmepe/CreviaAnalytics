# Part 21 — Market Structure Flip Detector Tool
**Type:** EA | **Verdict:** HIGH EXTRACT — ATR-adaptive lookback formula, state machine validation
**URL:** https://www.mql5.com/en/articles/17891

## Key Formula — ATR-to-Depth (immediate upgrade for StructureEngine)
```python
def atr_depth(atr: float, symbol_point: float,
              multiplier: float = 1.0, loosen: float = 0.5) -> int:
    raw = (atr / symbol_point) * multiplier
    return max(2, int(raw * loosen))

# Usage in StructureEngine.identify_swing_points():
# OLD: lookback = LOOKBACK_MAP.get(timeframe, 3)
# NEW: lookback = atr_depth(atr[-1], symbol_point)
```

**Why it matters**: On EUR/USD M15, ATR ~0.0012, point=0.00001 → raw=120, depth=60... that's too wide. Need to calibrate loosen factor per timeframe:
- M1: loosen=0.05 → depth ≈ 6 bars
- M15: loosen=0.01 → depth ≈ 1–3 bars
- Use as a clamp: `depth = min(atr_depth(...), LOOKBACK_MAP[tf] * 2)`

## State Machine
```python
state = 'uptrend'   # or 'downtrend'
prev_high = None
prev_low = None

for swing in swings_chronological:
    if swing.is_high:
        if state == 'uptrend' and prev_high and swing.price < prev_high:
            emit_flip('BEARISH_FLIP')   # ChoCH
            state = 'downtrend'
        prev_high = swing.price
    else:  # low
        if state == 'downtrend' and prev_low and swing.price > prev_low:
            emit_flip('BULLISH_FLIP')   # ChoCH
            state = 'uptrend'
        prev_low = swing.price
```

## Backtesting Results
| TF | Direction | Win Rate |
|---|---|---|
| M5 | BUY | **83%** |
| M5 | SELL | 70% |
| M15 | SELL | 71% |
| M15 | BUY | 64% |

M5 BUY 83% is notably high. Our M1 entry at the M15 flip should replicate this.

## Priority Upgrade for CreviaDeriv
Replace `LOOKBACK_MAP` with ATR-adaptive depth in `identify_swing_points()`. Add clamp to prevent extreme values on synthetics.
