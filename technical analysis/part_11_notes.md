# Part 11 — Heikin Ashi Signal EA
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor | **Verdict:** EXTRACT — HA formulas, shadow/body ratio, three-phase reversal logic
**Published:** 2025-02-07

---

## What It Does
Computes Heikin Ashi candles from raw OHLC, detects reversals via 3-phase check (prior trend → shadow ratio → direction change), confirms with RSI at tuned thresholds (34/65 not 30/70), draws signal arrows.

---

## Heikin Ashi Formulas (Keep These Exactly)
```python
# Pure function — no side effects
def heikin_ashi(opens, highs, lows, closes):
    n = len(closes)
    ha_close = [(opens[i]+highs[i]+lows[i]+closes[i])/4 for i in range(n)]
    ha_open  = [0.0] * n
    ha_open[0] = (opens[0]+closes[0])/2  # first bar special case
    for i in range(1, n):
        ha_open[i] = (ha_open[i-1]+ha_close[i-1])/2
    ha_high = [max(highs[i], ha_open[i], ha_close[i]) for i in range(n)]
    ha_low  = [min(lows[i],  ha_open[i], ha_close[i]) for i in range(n)]
    return ha_open, ha_high, ha_low, ha_close
```

---

## Three-Phase Reversal Detection
```python
def detect_reversal(ha_open, ha_high, ha_low, ha_close,
                    trend_candles=3, consecutive=2, shadow_ratio=1.5):
    # Phase 1: Was there a prior trend?
    bearish_trend = all(ha_close[-i] < ha_close[-i-1] for i in range(1, trend_candles+1))
    bullish_trend = all(ha_close[-i] > ha_close[-i-1] for i in range(1, trend_candles+1))

    # Phase 2: Does the reversal candle have a strong shadow?
    # For buy (after bearish trend): long lower shadow
    body = abs(ha_close[-2] - ha_open[-2])
    lower_shadow = ha_open[-2] - ha_low[-2]  # for bearish candle, open > close
    upper_shadow = ha_high[-2] - ha_open[-2]  # for bullish candle

    buy_shadow_ok  = bearish_trend and body > 0 and (lower_shadow/body) >= shadow_ratio
    sell_shadow_ok = bullish_trend and body > 0 and (upper_shadow/body) >= shadow_ratio

    # Phase 3: Current bar confirms direction change
    current_bullish = ha_close[-1] > ha_open[-1]
    current_bearish = ha_close[-1] < ha_open[-1]

    is_buy  = buy_shadow_ok  and current_bullish
    is_sell = sell_shadow_ok and current_bearish
    return is_buy, is_sell
```

---

## RSI Thresholds: Tuned Not Standard
| Standard | Tuned (this article) | Rationale |
|---|---|---|
| Buy < 30 | Buy < 34 | Catches more reversals before they run |
| Sell > 70 | Sell > 65 | Catches overbought earlier |

**Lesson**: Standard indicator thresholds are starting points, not gospel. Test on your instruments and tune accordingly. Our ADX > 20 (not > 0 or > 25) follows the same principle.

---

## Backtested Results (27 Days)
| Instrument | Buy | Sell |
|---|---|---|
| EURUSD | 85% | 80% |
| Crash 900 | 77.8% | 60% |
| Step Index | 83.3% | 63.6% |

**Buy accuracy > Sell accuracy** on every instrument — expected for synthetic indices (Boom/Crash have upward drift). Our system should track buy vs sell separately.

---

## Our Superior Version Design

### HA as M1 Pre-Filter
Apply HA to M1 bars before our EMA3 crossover check:
```python
# Current: EMA3 on raw M1 closes
ema3 = ema(m1_closes, 3)

# Improved: EMA3 on HA M1 closes (less noise)
_, _, _, ha_closes = heikin_ashi(m1_opens, m1_highs, m1_lows, m1_closes)
ema3_ha = ema(ha_closes, 3)
```
HA-smoothed EMA3 reduces fake crossovers during choppy M1 action near zone boundaries.

### Shadow Ratio = Our Departure Candle
| Part 11 | Our System |
|---|---|
| `lower_shadow / body >= 1.5` | departure candle: close below zone_mid, close < open |
| Ensures reversal has FORCE | Ensures price is actively leaving the zone |
| Works on HA candles | Works on raw M1 candles |

Both are measuring the same thing: **is this reversal committed or tentative?**

### Add Zone Alignment
```python
# Part 11 fires signal at any HA reversal + RSI
# Our version: only accept HA reversal WHEN AT A ZONE
if detect_reversal(ha_series) and rsi_ok:
    if zone_interaction and zone.is_demand:  # we're at a demand zone
        signal = BUY  # structural alignment confirmed
```

---

## Validation for CreviaDeriv
1. **HA smoothing reduces noise**: Directly applicable — consider HA pre-filter for M1 EMA3
2. **Shadow/body ratio = departure check**: Same structural logic, different implementation
3. **Tuned thresholds beat standards**: Our ADX=20 and MIN_RRR=1.5 are both tuned, not textbook
4. **Buy/sell accuracy asymmetry**: Track separately by instrument type (forex vs synthetic)
