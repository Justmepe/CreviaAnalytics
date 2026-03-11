# Part 31 — Python Candlestick Recognition Engine (I)
**Type:** Python/Flask | **Verdict:** MEDIUM — Morning/Evening Star 3-candle formulas are the key addition
**URL:** https://www.mql5.com/en/articles/18789

## Morning Star (3-candle pattern at zone)
```python
def is_morning_star(bars, i) -> bool:
    """bars[i] = most recent. Checks bars[i], [i-1], [i-2]."""
    b0 = bars[i-2]   # large bearish
    b1 = bars[i-1]   # small body (doji-like)
    b2 = bars[i]     # large bullish

    b0_body = abs(b0.close - b0.open)
    b1_body = abs(b1.close - b1.open)
    b2_body = abs(b2.close - b2.open)
    b0_mid  = (b0.open + b0.close) / 2

    return (b0.close < b0.open and                  # b0 bearish
            b1_body < 0.5 * b0_body and             # b1 small
            b2.close > b2.open and                  # b2 bullish
            b2.close > b0_mid)                      # b2 closes above b0 midpoint

def is_evening_star(bars, i) -> bool:
    b0, b1, b2 = bars[i-2], bars[i-1], bars[i]
    b0_body = abs(b0.close - b0.open)
    b1_body = abs(b1.close - b1.open)
    b0_mid  = (b0.open + b0.close) / 2
    return (b0.close > b0.open and
            b1_body < 0.5 * b0_body and
            b2.close < b2.open and
            b2.close < b0_mid)
```

## Harami (Inside Body)
```python
def is_bullish_harami(bars, i) -> bool:
    prev, curr = bars[i-1], bars[i]
    prev_hi = max(prev.open, prev.close)
    prev_lo = min(prev.open, prev.close)
    curr_hi = max(curr.open, curr.close)
    curr_lo = min(curr.open, curr.close)
    return (prev.close < prev.open and       # prev bearish
            curr.close > curr.open and       # curr bullish
            curr_hi <= prev_hi and           # current body inside prior body
            curr_lo >= prev_lo)
```

## Integration with classify_candle() (from Part 24)
Extend to include: Hammer, Shooting Star, Harami, Morning Star, Evening Star. These 5 added to the existing 4 (Pin Bar, Doji, Engulfing, Marubozu) = 9-pattern classifier.
