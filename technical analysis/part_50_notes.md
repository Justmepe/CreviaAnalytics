# Part 50 — RVGI, CCI and SMA Confluence Engine
**Type:** Expert Advisor | **Verdict:** HIGH EXTRACT — RVGI formula, 3-layer confluence gating, ATR TP validated
**URL:** https://www.mql5.com/en/articles/20262

## What This Is
A 3-layer confluence EA that requires SMA structural bias + CCI exhaustion reversal + RVGI momentum crossover to all align before taking a trade. All three signals on a closed bar = entry. This is a sophisticated filter stack comparable to our gate chain.

## RVGI Formula (Relative Vigor Index)
```python
def compute_rvgi(opens, highs, lows, closes, smooth=4):
    """
    RVGI measures momentum by comparing close-open to high-low range.
    Positive RVGI = bullish momentum (closes > opens, vigorous buyers).
    Negative RVGI = bearish momentum.
    """
    raw = []
    for i in range(3, len(closes)):
        # Numerator: weighted close-open across 4 bars (triangular weighting)
        num = ((closes[i] - opens[i]) +
               2*(closes[i-1] - opens[i-1]) +
               2*(closes[i-2] - opens[i-2]) +
               (closes[i-3] - opens[i-3]))
        # Denominator: weighted high-low across 4 bars
        den = ((highs[i] - lows[i]) +
               2*(highs[i-1] - lows[i-1]) +
               2*(highs[i-2] - lows[i-2]) +
               (highs[i-3] - lows[i-3]))
        raw.append(num / den if abs(den) > 1e-9 else 0.0)
    # Two smoothing passes (same period)
    import pandas as pd
    rvgi = pd.Series(raw).rolling(smooth).mean().values
    signal_line = pd.Series(rvgi).rolling(smooth).mean().values
    return rvgi, signal_line
```

## CCI Formula
```python
def compute_cci(highs, lows, closes, period=14):
    """CCI: deviation from mean typical price, normalized by mean deviation."""
    typical = (highs + lows + closes) / 3.0
    cci = []
    for i in range(period-1, len(typical)):
        window = typical[i-period+1:i+1]
        sma = np.mean(window)
        mean_dev = np.mean(np.abs(window - sma))
        cci.append((typical[i] - sma) / (0.015 * mean_dev) if mean_dev > 1e-9 else 0.0)
    return np.array(cci)
```

## 3-Layer Confluence Gate
```python
def check_rvgi_confluence(closes, sma30, cci14, rvgi, signal_line):
    """
    All 3 conditions must align on closed bar.
    Returns: +1 (bullish), -1 (bearish), 0 (no signal)
    """
    # BULLISH: Price BELOW SMA (room to rise) + CCI exits oversold + RVGI turns up
    if (closes[-1] < sma30[-1] and
        cci14[-2] <= -100 and cci14[-1] > -100 and   # crossed above -100
        rvgi[-2] < signal_line[-2] and rvgi[-1] > signal_line[-1]):  # RVGI bullish cross
        return 1
    # BEARISH: Price ABOVE SMA (room to fall) + CCI exits overbought + RVGI turns down
    if (closes[-1] > sma30[-1] and
        cci14[-2] >= 100 and cci14[-1] < 100 and     # crossed below +100
        rvgi[-2] > signal_line[-2] and rvgi[-1] < signal_line[-1]):  # RVGI bearish cross
        return -1
    return 0
```

## TP/SL Defaults — Validates Our Architecture
- SL: `entry - ATR * 1.5` (buy) / `entry + ATR * 1.5` (sell)
- TP1: `entry + ATR * 1.0`
- TP2: `entry + ATR * 2.0`
This exactly mirrors our partial-close structure (P1=1xATR, P2=2xATR). Industry validated.

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| InpSMA_Period | 30 | Structural trend context |
| InpCCI_Period | 14 | Oversold/overbought threshold |
| InpRVI_Smooth | 4 | RVGI smoothing window |
| InpATR_Period | 14 | Volatility baseline |
| InpATR_Multiplier | 1.5 | SL distance |
| InpTarget1_ATR | 1.0 | TP1 distance |
| InpTarget2_ATR | 2.0 | TP2 distance |

## CreviaDeriv Integration
**RVGI as EMA3 Supplement:**
```python
# In EntryEngine._check_ema_cross() — add RVGI as tiebreaker
rvgi_vals, rvgi_sig = compute_rvgi(opens, highs, lows, closes, smooth=4)
rvgi_bullish = rvgi_vals[-2] < rvgi_sig[-2] and rvgi_vals[-1] > rvgi_sig[-1]
rvgi_bearish = rvgi_vals[-2] > rvgi_sig[-2] and rvgi_vals[-1] < rvgi_sig[-1]

# Use as second confirmation: EMA3 cross + RVGI cross = double momentum confirmation
gate_ok = ema_cross and (rvgi_bullish if direction == 'BUY' else rvgi_bearish)
```

**CCI as Zone Exhaustion Detector:**
```python
# Before accepting zone touch — check if CCI confirms exhaustion at zone
cci_oversold = cci[-2] <= -100 and cci[-1] > -100   # reversing from oversold at demand
cci_overbought = cci[-2] >= 100 and cci[-1] < 100   # reversing from overbought at supply
if direction == 'BUY' and not cci_oversold:
    departure_strength -= 1   # weaker if no CCI exhaustion confirmation
```

## Superior Version Improvements
1. RVGI zero-line cross is stronger than signal-line cross: add `rvgi[-1] > 0` as confirmation
2. SMA30 is slow — replace with EMA20 for faster trend detection on M1 (our existing EMA3 context)
3. ATR multiplier 1.5 for SL matches our `_calculate_precision_sl()` 2×ATR floor — consistent
4. RVGI works on HA prices: `compute_rvgi(ha_opens, ha_highs, ha_lows, ha_closes)` reduces noise
