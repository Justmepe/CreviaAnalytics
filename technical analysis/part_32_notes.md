# Part 32 — Python Candlestick Recognition Engine (II) — Ta-Lib
**Type:** Python | **Verdict:** MEDIUM — ta-lib CDL batch detection, signed codes, priority hierarchy
**URL:** https://www.mql5.com/en/articles/18824

## TA-Lib Pattern Detection (Drop-In)
```python
import talib
import numpy as np

def detect_all_patterns(opens, highs, lows, closes):
    o, h, l, c = (np.asarray(x, dtype=float) for x in (opens, highs, lows, closes))

    patterns = {
        'engulfing':    talib.CDLENGULFING(o, h, l, c),
        'harami':       talib.CDLHARAMI(o, h, l, c),
        'doji':         talib.CDLDOJI(o, h, l, c),
        'hammer':       talib.CDLHAMMER(o, h, l, c),
        'shooting_star':talib.CDLSHOOTINGSTAR(o, h, l, c),
        'morning_star': talib.CDLMORNINGSTAR(o, h, l, c),
        'evening_star': talib.CDLEVENINGSTAR(o, h, l, c),
        'pin_bar':      talib.CDLHAMMER(o, h, l, c),   # hammer ~ bullish pin
    }

    # Priority: Engulfing > Harami > Doji (for the latest bar)
    for name in ['engulfing', 'harami', 'doji', 'hammer', 'shooting_star', 'morning_star', 'evening_star']:
        val = patterns[name][-1]
        if val != 0:
            direction = 'BULLISH' if val > 0 else 'BEARISH'
            return name, direction
    return 'NONE', 'NEUTRAL'
```

## Ta-Lib Return Code Pattern
- `> 0` → bullish (100 or 200)
- `< 0` → bearish (-100 or -200)
- `== 0` → no pattern
- Magnitude 200 = stronger confirmation in some patterns (e.g., CDLMORNINGSTAR strength)

## Integration
Use as the backend for our departure gate:
```python
pattern, direction = detect_all_patterns(bars.open, bars.high, bars.low, bars.close)
departure_ok = (direction == 'BULLISH' and signal.direction == 'BUY') or \
               (direction == 'BEARISH' and signal.direction == 'SELL')
```
Keep our ATR-normalized body size check as a pre-filter before calling ta-lib (filters micro-candles that ta-lib won't reject).
