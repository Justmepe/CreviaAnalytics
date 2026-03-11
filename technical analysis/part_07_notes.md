# Part 07 — Signal Pulse EA
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor | **Verdict:** EXTRACT — multi-timeframe confluence architecture
**Published:** 2025-01-16 | **Depends on:** Parts 1-5

---

## What It Does
Generates buy/sell arrow signals only when Bollinger Bands AND Stochastic Oscillator both confirm the same direction on ALL THREE timeframes simultaneously (M15, M30, H1). Draws coloured arrows on chart. No SL/TP — pure entry detection.

---

## The Core Insight
**Multi-timeframe alignment eliminates noise.** A BB lower-touch + oversold Stochastic on M15 alone happens frequently. The same condition on M15, M30, AND H1 at the same moment is rare — but when it happens, it's almost always a high-quality reversal point.

Extreme threshold: K < 5 (not the usual 20). This makes signals even rarer but higher quality.

---

## The Series Advance from Part 5
| Part 5 | Part 7 |
|--------|--------|
| Single timeframe | Three timeframes |
| RSI + BB + ATR | BB + Stochastic |
| Has SL/TP (ATR-based) | No SL/TP (signals only) |

Part 7 adds the multi-timeframe dimension. Part 5 + Part 7 together = signal quality filter on two axes: indicator convergence AND timeframe convergence.

---

## Signal Logic

### Buy (ALL 3 conditions must hold on ALL 3 timeframes)
```
For each of M15, M30, H1:
    close[TF] < BB_lower[TF]   AND   Stochastic_K[TF] < 5
All 3 → BUY signal → green up-arrow
```

### Sell
```
For each of M15, M30, H1:
    close[TF] > BB_upper[TF]   AND   Stochastic_K[TF] > 95
All 3 → SELL signal → red down-arrow
```

---

## Arrow Deduplication
```python
def arrow_exists(price, direction, min_distance, history):
    for signal in history:
        if signal.direction == direction and abs(signal.price - price) < min_distance:
            return True
    return False
```
This prevents re-firing the same signal on consecutive ticks while price stays at the extreme.

---

## Config Parameters
| Param | Default |
|---|---|
| `timeframe_1` | M15 |
| `timeframe_2` | M30 |
| `timeframe_3` | H1 |
| `bb_period` | 20 |
| `bb_deviation` | 2.0 |
| `k_period` | 14 |
| `d_period` | 3 |
| `slowing` | 3 |
| `signal_offset` | 10 points |
| `min_arrow_distance` | 5 points |

---

## What to Keep
- Multi-timeframe AND gate — same concept as our M15 structure + M1 entry split
- Extreme thresholds (K<5, K>95) — same philosophy as our ADX > 20 (not > 0) requirement
- Signal deduplication — our single-signal-per-zone-interaction maps to this exactly
- Signal history log — foundation for performance tracking and zone management

## What to Discard
- BB + Stochastic triggers — we use zone touch instead
- Three fixed TFs (M15/M30/H1) — we use M15+M1 with clear role separation
- No SL/TP — we always compute risk levels with signal

## What to Improve
- Add SL/TP to signal (use ATR floor + structural anchor)
- Replace BB+Stochastic with supply/demand zone touch
- Add VWV gate — no volume/velocity check here

---

## Architecture This Tool Reveals
```
MultiTimeframeDataFetcher   ← get_multi_tf_bars(symbol, ['M15','M30','H1'])
StochasticCalculator        ← stochastic(H, L, C, k_period, d_period) → {K, D}
SignalEngine                ← evaluate(tf1, tf2, tf3, config) → Signal | None
ArrowManager                ← add_arrow(time, price, dir, min_dist) → bool (dedup)
```

---

## Validation for CreviaDeriv
1. **MTF confirmation = standard**: Our M15+M1 split is the industry-standard approach. This validates it.
2. **Extreme thresholds reduce noise**: K<5 (not 20) → fewer signals, higher quality. Our ADX>20 (not >0) follows exactly the same logic.
3. **Zone deduplication is correct**: Signals should fire once per structural moment, not repeatedly while price lingers. Our single-signal-per-zone approach is right.
