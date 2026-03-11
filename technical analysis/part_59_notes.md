# Part 59 — Geometric Asymmetry: Precision Breakouts from Fractal Consolidation
**Type:** Module | **Verdict:** HIGH EXTRACT — 3-vote geometric asymmetry system, leg ratios as departure_strength upgrade
**URL:** https://www.mql5.com/en/articles/21197

## What This Is
Measures breakout QUALITY by comparing the departure leg to the approach leg geometrically.
A true breakout exits a consolidation zone FASTER, LONGER, and STEEPER than it entered.
3 independent geometric votes confirm asymmetry. Need 2/3 to confirm a valid breakout.

## Fractal Leg Detection
```python
def find_swing_legs(bars, lookback=5) -> list:
    highs = [b.high for b in bars]
    lows  = [b.low  for b in bars]
    swings = []
    for i in range(lookback, len(bars)-lookback):
        # Strict 5-bar rule: center must exceed all 4 neighbors
        if all(highs[i] > highs[i+j] and highs[i] > highs[i-j] for j in range(1,lookback+1)):
            swings.append(('high', i, highs[i]))
        if all(lows[i] < lows[i+j] and lows[i] < lows[i-j] for j in range(1,lookback+1)):
            swings.append(('low', i, lows[i]))
    swings.sort(key=lambda x: x[1])
    return swings  # chronological order
```

## 3-Vote Geometric Asymmetry System
```python
from dataclasses import dataclass

@dataclass
class GeometricLeg:
    length: float   # price distance |p0 - p1|
    dt_secs: float  # time in seconds
    n_bars: int

def compute_geometric_votes(approach_leg: GeometricLeg,
                             departure_leg: GeometricLeg,
                             len_ratio_min=1.35,
                             slope_ratio_min=1.15,
                             time_compress_max=0.95) -> tuple:
    votes = 0
    details = {}

    # Vote 1: Distance ratio (departure is longer than approach)
    len_ratio = departure_leg.length / approach_leg.length if approach_leg.length > 0 else 0
    if len_ratio >= len_ratio_min:
        votes += 1
    details['len_ratio'] = len_ratio

    # Vote 2: Slope ratio (departure is steeper = same distance, less time)
    approach_slope  = approach_leg.length / approach_leg.dt_secs  if approach_leg.dt_secs  > 0 else 0
    departure_slope = departure_leg.length / departure_leg.dt_secs if departure_leg.dt_secs > 0 else 0
    slope_ratio = departure_slope / approach_slope if approach_slope > 0 else 0
    if slope_ratio >= slope_ratio_min:
        votes += 1
    details['slope_ratio'] = slope_ratio

    # Vote 3: Time compression (departure took fewer bars = urgency)
    time_ratio = departure_leg.dt_secs / approach_leg.dt_secs if approach_leg.dt_secs > 0 else 1
    if time_ratio <= time_compress_max:
        votes += 1
    details['time_ratio'] = time_ratio

    return votes, details
```

## Breakout Confirmation Parameters
| Parameter | Default | Purpose |
|-----------|---------|---------|
| InpLenRatioMin | 1.35 | Departure 35% longer than approach |
| InpSlopeRatioMin | 1.15 | Departure 15% steeper |
| InpTimeCompressionMax | 0.95 | Departure took < 95% of approach time |
| InpMinGeometryVotes | 2 | Need 2/3 votes for confirmation |
| InpBreakBufferPts | 5.0 | Minimum penetration beyond boundary |
| InpMaxLegBars | 50 | Max bars for a valid leg |
| InpRangeATRMax | 2.00 | Range height <= 2x ATR |

## CreviaDeriv Integration — Departure Strength Upgrade
```python
def departure_strength_from_geometry(approach_leg: GeometricLeg,
                                      departure_leg: GeometricLeg) -> int:
    votes, details = compute_geometric_votes(approach_leg, departure_leg)
    if votes == 3: return 4    # all 3 metrics confirm: perfect asymmetric breakout
    if votes == 2: return 3    # 2/3 confirmed: strong departure
    if votes == 1: return 1    # only 1 vote: weak, may be noise
    return 1                   # 0 votes: symmetric = not a quality breakout

# In EntryEngine — build approach/departure legs from recent M1 swings
def estimate_legs_from_bars(m1_bars, zone_touch_bar_idx: int) -> tuple:
    # Approach leg: from last swing extreme to zone touch bar
    # Departure leg: from zone touch bar to current bar
    approach_bars = m1_bars[max(0, zone_touch_bar_idx-30):zone_touch_bar_idx+1]
    departure_bars = m1_bars[zone_touch_bar_idx:]

    approach_len = abs(approach_bars[-1].close - approach_bars[0].close)
    departure_len = abs(departure_bars[-1].close - departure_bars[0].close)
    approach_dt  = len(approach_bars) * 60   # M1 = 60 seconds per bar
    departure_dt = len(departure_bars) * 60

    app_leg = GeometricLeg(approach_len, approach_dt, len(approach_bars))
    dep_leg = GeometricLeg(departure_len, departure_dt, len(departure_bars))
    return app_leg, dep_leg
```

## Why This Is Critical for Deriv Synthetics
Crash/Boom indices have frequent false breakouts where price spikes out then reverses.
Geometric asymmetry filters these out: a spike that reverts has a VERY symmetric departure
(it reverts back in same time/distance). A true directional move is asymmetric:
departure longer + steeper + faster than the approach leg.

## Superior Version vs Simple Departure Candle
Simple departure: just checks if last candle is bullish/bearish with decent body.
Geometric departure: checks the SEQUENCE of price action from zone touch to now.
Our version: combine both — candle type (Part 51) + CPI (Part 55) + geometric ratio (Part 59).
```python
final_strength = candle_type_strength + (1 if cpi_strong else 0) + (geo_votes - 1)
final_strength = max(1, min(4, final_strength))
```