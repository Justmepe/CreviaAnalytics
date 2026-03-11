# Part 48 — Multi-Timeframe Harmony Index
**Type:** Dashboard | **Verdict:** HIGH EXTRACT — HI formula is production-ready multi-TF confidence score
**URL:** https://www.mql5.com/en/articles/20097

## Harmony Index Formula
```python
def compute_harmony_index(bias_by_tf, weights, ema_period=8, prev_hi_ema=0.0):
    total_w = sum(weights[tf] for tf in bias_by_tf)
    hi_raw  = sum(bias_by_tf[tf] * weights[tf] for tf in bias_by_tf) / total_w
    alpha   = 2 / (ema_period + 1)
    hi_ema  = prev_hi_ema + alpha * (hi_raw - prev_hi_ema)
    if   hi_ema >= 0.8:  cls = "STRONG_BULLISH"
    elif hi_ema >= 0.4:  cls = "MODERATE_BULLISH"
    elif hi_ema <= -0.8: cls = "STRONG_BEARISH"
    elif hi_ema <= -0.4: cls = "MODERATE_BEARISH"
    else:                cls = "NEUTRAL"
    return hi_raw, hi_ema, cls
```

## 3-Bar Staircase (Better Than SMA for Bias)
```python
def staircase_bias(highs, lows):
    if highs[-1] > highs[-2] > highs[-3] and lows[-1] > lows[-2] > lows[-3]: return 1
    if highs[-1] < highs[-2] < highs[-3] and lows[-1] < lows[-2] < lows[-3]: return -1
    return 0
```

## CreviaDeriv HI (M15+M1)
```python
weights = {"M15_structure": 0.60, "M1_ema": 0.25, "M1_adx": 0.15}
bias = {
    "M15_structure": 1 if market_structure == BULLISH else (-1 if BEARISH else 0),
    "M1_ema":        1 if ema3_crossed_up else (-1 if ema3_crossed_down else 0),
    "M1_adx":        1 if adx_rising else 0
}
hi_raw, hi_ema, cls = compute_harmony_index(bias, weights)
# Entry gate: require MODERATE_BULLISH or STRONG_BULLISH for BUY
```
