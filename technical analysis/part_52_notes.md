# Part 52 — Multi-Timeframe Visual Analysis (Direction Confirmer)
**Type:** Indicator | **Verdict:** LOW-MEDIUM — Simple 3-TF boolean alignment, no scoring. Part 48 HI is mathematically superior.
**URL:** https://www.mql5.com/en/articles/20387

## What This Is
Checks if current TF, HTF1 (H1), and HTF2 (M30) all show the same candle direction (close > open). If all three agree = confirmed signal. If current TF disagrees with HTFs = counter-trend warning.

## Algorithm (Full Reconstruction)
```python
def check_mtf_direction(current_close, current_open,
                         htf1_close, htf1_open,
                         htf2_close, htf2_open,
                         min_pips=0.0, point_size=0.00001):
    cur_bull  = current_close > current_open + (min_pips * point_size)
    cur_bear  = current_close < current_open - (min_pips * point_size)
    htf1_bull = htf1_close > htf1_open
    htf1_bear = htf1_close < htf1_open
    htf2_bull = htf2_close > htf2_open
    htf2_bear = htf2_close < htf2_open
    if cur_bull and htf1_bull and htf2_bull:
        return 1   # all three bullish
    if cur_bear and htf1_bear and htf2_bear:
        return -1  # all three bearish
    if htf1_bull and htf2_bull and cur_bear:
        return 0   # counter-trend on current TF
    if htf1_bear and htf2_bear and cur_bull:
        return 0   # counter-trend
    return 0  # mixed
```

## Parameter Defaults
- HTF1 = H1 (primary higher timeframe)
- HTF2 = M30 (secondary higher timeframe)
- MinPipsForSignal = 0 (minimum candle body in pips)
- BarsToDraw = 500, RefreshSeconds = 1

## Why Part 48 (Harmony Index) Is Superior
Part 52 is binary all-or-nothing. Part 48 HI is weighted and graded:
```python
weights = {"H4": 0.35, "H1": 0.30, "M15": 0.25, "M5": 0.10}
HI = sum(bias[tf]*w for tf,w in weights.items()) / sum(weights.values())
# HI > 0.5 = bullish consensus; > 0.8 = strong. Binary fails when H4 and H1 disagree.
```
The boolean system fails when H1 is bullish but H4 is bearish. HI handles this gracefully.

## CreviaDeriv Integration — Quick Pre-filter
```python
def quick_mtf_gate(m15_close, m15_open, h1_close, h1_open, trade_dir):
    m15_bull = m15_close > m15_open
    h1_bull  = h1_close > h1_open
    if trade_dir == "BUY":
        return m15_bull and h1_bull
    else:
        return (not m15_bull) and (not h1_bull)
# Fast gate-zero before running full EntryEngine analysis
```

## What To Use From This Part
1. MinPipsForSignal concept = our minimum body filter (body < ATR*0.1 = skip)
2. HTF1=H1 aligns with our M15 structure context: require H1 candle to agree with trade direction
3. On Deriv synthetics: require M15 + H1 direction alignment to filter spike-zone false entries
4. This is a fast boolean pre-screen; Part 48 HI for weighted confirmation in production
