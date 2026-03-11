# Part 51 — Revolutionary Chart Search Technology (Pattern Catalog)
**Type:** Indicator | **Verdict:** MEDIUM — Complete 15-pattern catalog with exact detection rules. Three White Soldiers/Black Crows get departure_strength=4.
**URL:** https://www.mql5.com/en/articles/20313

## What This Is
A systematic candlestick pattern detector covering all major 1/2/3-bar formations. Core value: exact binary detection logic for each pattern — not probabilistic, just geometric rule-checking. Use as ground truth for our departure candle scoring.

## Complete Pattern Catalog with Detection Rules
```python
import numpy as np

def classify_candle_pattern(bars, i):
    """
    bars: list of dicts with keys o, h, l, c (open, high, low, close)
    i: current bar index
    Returns: (pattern_name, direction, strength)
    """
    if i < 2:
        return ('none', 0, 0)

    c0 = bars[i]    # current
    c1 = bars[i-1]  # previous
    c2 = bars[i-2]  # bar before that

    body0 = abs(c0['c'] - c0['o'])
    body1 = abs(c1['c'] - c1['o'])
    body2 = abs(c2['c'] - c2['o'])
    rng0 = c0['h'] - c0['l'] or 1e-10
    rng1 = c1['h'] - c1['l'] or 1e-10

    bull0 = c0['c'] > c0['o']
    bear0 = c0['c'] < c0['o']
    bull1 = c1['c'] > c1['o']
    bear1 = c1['c'] < c1['o']

    # --- THREE-CANDLE PATTERNS (highest priority, strength=4) ---

    # Three White Soldiers: 3 consecutive bullish bars, each closes higher
    if (bull0 and bull1 and (c2['c'] > c2['o']) and
        c0['c'] > c1['c'] > c2['c'] and
        c0['o'] > c1['o']):
        return ('three_white_soldiers', 1, 4)

    # Three Black Crows: 3 consecutive bearish bars, each closes lower
    if (bear0 and bear1 and (c2['c'] < c2['o']) and
        c0['c'] < c1['c'] < c2['c'] and
        c0['o'] < c1['o']):
        return ('three_black_crows', -1, 4)

    # Morning Star: bearish + small body + bullish engulf
    if (bear1 and body1 < rng1*0.3 and bull0 and
        c0['c'] > (c2['c'] + c2['o'])/2):
        return ('morning_star', 1, 3)

    # Evening Star: bullish + small body + bearish
    if (bull1 and body1 < rng1*0.3 and bear0 and
        c0['c'] < (c2['c'] + c2['o'])/2):
        return ('evening_star', -1, 3)

    # --- TWO-CANDLE PATTERNS (strength=2) ---

    # Bullish Engulfing
    if (bear1 and bull0 and
        c0['o'] <= c1['c'] and c0['c'] >= c1['o']):
        return ('bullish_engulfing', 1, 2)

    # Bearish Engulfing
    if (bull1 and bear0 and
        c0['o'] >= c1['c'] and c0['c'] <= c1['o']):
        return ('bearish_engulfing', -1, 2)

    # Piercing Line: bearish prev, bullish curr closes above midpoint
    if (bear1 and bull0 and
        c0['o'] < c1['c'] and c0['c'] > (c1['o'] + c1['c'])/2):
        return ('piercing_line', 1, 2)

    # Dark Cloud Cover: bullish prev, bearish curr closes below midpoint
    if (bull1 and bear0 and
        c0['o'] > c1['c'] and c0['c'] < (c1['o'] + c1['c'])/2):
        return ('dark_cloud_cover', -1, 2)

    # --- SINGLE-CANDLE PATTERNS (strength=1-3) ---

    # Marubozu: body >= 90% of range (no wicks = conviction)
    if body0 >= rng0 * 0.90:
        return ('marubozu', 1 if bull0 else -1, 3)

    # Pin Bar (Hammer/Shooting Star): small body, long shadow
    upper_shadow = c0['h'] - max(c0['o'], c0['c'])
    lower_shadow = min(c0['o'], c0['c']) - c0['l']
    if lower_shadow >= rng0*0.60 and body0 <= rng0*0.20:
        return ('hammer', 1, 2)   # bullish reversal at support
    if upper_shadow >= rng0*0.60 and body0 <= rng0*0.20:
        return ('shooting_star', -1, 2)   # bearish reversal at resistance

    # Doji: body <= 10% of range
    if body0 <= rng0 * 0.10:
        return ('doji', 0, 1)   # indecision — direction from context

    return ('simple_directional', 1 if bull0 else -1, 1)
```

## Departure Strength Mapping
```python
PATTERN_STRENGTH = {
    'three_white_soldiers': 4,
    'three_black_crows':    4,
    'morning_star':         3,
    'evening_star':         3,
    'marubozu':             3,
    'bullish_engulfing':    2,
    'bearish_engulfing':    2,
    'piercing_line':        2,
    'dark_cloud_cover':     2,
    'hammer':               2,
    'shooting_star':        2,
    'doji':                 1,   # context-dependent
    'simple_directional':   1,
}
```

## CreviaDeriv Integration — Upgrade departure_strength
```python
# In EntryEngine._detect_departure_candle()
pattern, direction, strength = classify_candle_pattern(m1_bars, -1)
if direction != signal.direction_int:
    return None   # pattern direction conflicts with trade direction

departure_strength = strength  # 1-4 based on pattern
# Additional boost: pattern win rate from Part 43
win_rate = pattern_win_rates.get(pattern, 0.5)
if win_rate > 0.65:
    departure_strength = min(4, departure_strength + 1)
elif win_rate < 0.52:
    departure_strength = max(1, departure_strength - 1)
```

## Superior Version vs ta-lib
- Our `classify_candle_pattern()` above does NOT require ta-lib installation
- ta-lib returns -100/0/100 integers; our version returns (name, direction, strength) tuple — richer
- Three-candle patterns critical for Deriv synthetics: Crash/Boom often show Three Black Crows before reversals
- Add `LookbackPeriod=1000` scan at startup per Part 43's win-rate computation
