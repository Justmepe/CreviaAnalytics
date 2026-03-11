# Part 54 — Filtering Trends with HA and EMA (HA+EMA Pre-filter)
**Type:** Indicator/EA | **Verdict:** HIGH EXTRACT — HA noise reduction on M1, EMA triple confirmation, EMA50 slope as trend gate
**URL:** https://www.mql5.com/en/articles/20851

## What This Is
Uses Heikin-Ashi candles as a noise filter before applying EMA crossover signals. HA smooths M1 price action so that EMA3 signals on HA prices are more reliable than on raw prices. The EMA50 slope provides structural trend context.

## Heikin-Ashi Formula
```python
def compute_ha(opens, highs, lows, closes):
    import numpy as np
    n = len(closes)
    ha_close = (opens + highs + lows + closes) / 4.0
    ha_open  = np.zeros(n)
    ha_open[0] = (opens[0] + closes[0]) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0
    ha_high = np.maximum(highs, np.maximum(ha_open, ha_close))
    ha_low  = np.minimum(lows,  np.minimum(ha_open, ha_close))
    return ha_open, ha_high, ha_low, ha_close
```

## EMA Triple Confirmation (BUY conditions)
1. HA close > HA open (bullish HA candle)
2. HA close > EMA20 of HA highs (momentum above upper band)
3. HA close > EMA50(raw closes) AND EMA50 slope is positive (structural trend)

```python
import pandas as pd, numpy as np

def check_ha_ema_buy(ha_open, ha_high, ha_close, closes):
    ema20_h = pd.Series(ha_high).ewm(span=20).mean().values
    ema50_c = pd.Series(closes).ewm(span=50).mean().values
    i = -1
    ha_bull   = ha_close[i] > ha_open[i]
    above_20h = ha_close[i] > ema20_h[i]
    above_50  = ha_close[i] > ema50_c[i]
    slope_up  = ema50_c[i] > ema50_c[i-4]  # net slope 4 bars
    return ha_bull and above_20h and above_50 and slope_up
```

## HA Color Streak as Trend Strength
```python
def ha_trend_state(ha_opens, ha_closes, lookback=3):
    colors = [1 if ha_closes[i] > ha_opens[i] else -1 for i in range(-lookback, 0)]
    if all(c == 1 for c in colors): return 1   # strong bullish
    if all(c == -1 for c in colors): return -1  # strong bearish
    return 0  # mixed
```
3+ consecutive same-color HA bars = momentum candles (no wicks) = high conviction.

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| EMA50_Period | 50 | Structural trend filter (raw closes) |
| EMA20H_Period | 20 | Applied to HA highs |
| EMA20L_Period | 20 | Applied to HA lows |
| WorkTF | M15 | Working timeframe |

## CreviaDeriv Integration
```python
# Apply HA smoothing to M1 bars before EMA3 gate check
ha_o, ha_h, ha_l, ha_c = compute_ha(
    np.array([b.open  for b in m1_bars]),
    np.array([b.high  for b in m1_bars]),
    np.array([b.low   for b in m1_bars]),
    np.array([b.close for b in m1_bars])
)
ha_ema3 = pd.Series(ha_c).ewm(span=3, adjust=False).mean().values
ema3_bull_cross = ha_ema3[-2] < ha_c[-2] and ha_ema3[-1] > ha_c[-1]

# EMA50 slope replaces ADX as trend quality gate
raw_ema50 = pd.Series([b.close for b in m1_bars]).ewm(span=50).mean().values
trend_rising = raw_ema50[-1] > raw_ema50[-4]

# ha_trend_state for departure_strength boost
ha_streak = ha_trend_state(ha_o, ha_c, lookback=3)
if ha_streak == signal.direction_int:  # 3 consecutive HA candles agree
    departure_strength = min(4, departure_strength + 1)
```

## Superior Version Rules
1. Apply HA ONLY to EMA3 gate — keep raw OHLC for departure candle (HA obscures real wicks)
2. EMA20H/L bands replace fixed zone boundary checks on M1 (dynamic support/resistance)
3. 3+ consecutive HA candle streak = momentum confirmation = bump departure_strength by 1
4. On Crash/Boom: HA eliminates single-spike EMA3 false crosses (most important use case)