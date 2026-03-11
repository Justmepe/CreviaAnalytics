# Part 57 — Market State Classification Module (4-State System)
**Type:** Module | **Verdict:** HIGH EXTRACT — CLV-based 4-state: Compression/Transition/Expansion/Trend. Hierarchical evaluation.
**URL:** https://www.mql5.com/en/articles/20996

## What This Is
Adds 2 states our system lacks: Compression (pre-breakout squeeze) and Expansion (explosive move in progress).
Our StructureEngine has BULLISH/BEARISH/RANGING/UNKNOWN. This adds Compression as a sub-state of RANGING
and Expansion as a super-state above BULLISH/BEARISH. Full 4-state system enables smarter entry behavior.

## CLV Formula (= CPI = CPP — same metric, third alias)
```python
def compute_clv(high: float, low: float, close: float) -> float:
    rng = high - low
    if rng < 1e-9: return 0.0
    return (2 * close - high - low) / rng  # [-1, +1]
```

## 4-State Classification (Hierarchical — evaluated in this order)
```python
from dataclasses import dataclass
from enum import Enum
import numpy as np

class MarketState4(Enum):
    EXPANSION   = 'expansion'    # explosive breakout candle
    COMPRESSION = 'compression'  # range shrinking = breakout imminent
    TREND       = 'trend'        # directional momentum confirmed
    TRANSITION  = 'transition'   # default / undetermined

def classify_4state(bars,
                     lookback=60,
                     compression_bars=16,
                     range_shrink_ratio=0.70,
                     expansion_mult=1.80,
                     clv_strong=0.60,
                     trend_bars=20,
                     swing_left_right=3) -> MarketState4:
    highs  = np.array([b.high  for b in bars[-lookback:]])
    lows   = np.array([b.low   for b in bars[-lookback:]])
    closes = np.array([b.close for b in bars[-lookback:]])
    ranges = highs - lows
    avg_range = np.mean(ranges)

    # 1. EXPANSION: last bar is unusually large AND closes decisively
    last_range = ranges[-1]
    last_clv   = compute_clv(highs[-1], lows[-1], closes[-1])
    if last_range >= avg_range * expansion_mult and abs(last_clv) >= clv_strong:
        return MarketState4.EXPANSION

    # 2. COMPRESSION: recent N-bar average range < prior N-bar average * ratio
    recent_ranges = ranges[-compression_bars:]
    prior_ranges  = ranges[-2*compression_bars:-compression_bars]
    if len(prior_ranges) >= compression_bars:
        recent_avg = np.mean(recent_ranges)
        prior_avg  = np.mean(prior_ranges)
        if recent_avg <= prior_avg * range_shrink_ratio:
            return MarketState4.COMPRESSION

    # 3. TREND: mean CLV over trend_bars is directional + swing score consistent
    recent_clvs = [compute_clv(highs[i], lows[i], closes[i])
                   for i in range(-trend_bars, 0)]
    mean_clv_bias = np.mean(recent_clvs)
    # Simple swing score: count higher-highs and higher-lows (or lower-lows + lower-highs)
    swing_score = 0
    for i in range(1, len(highs[-trend_bars:])):
        idx = -trend_bars + i
        if highs[idx] > highs[idx-1]: swing_score += 1
        elif highs[idx] < highs[idx-1]: swing_score -= 1
    clv_threshold = 0.30  # InpTrendBiasCLV (not given in article, estimated)
    if abs(mean_clv_bias) >= clv_threshold and abs(swing_score) >= trend_bars * 0.3:
        return MarketState4.TREND

    # 4. TRANSITION: default
    return MarketState4.TRANSITION
```

## Parameter Defaults
| Parameter | Default | Purpose |
|-----------|---------|---------|
| InpLookbackBars | 60 | Baseline range calculation window |
| InpCompressionBars | 16 | Recent volatility comparison window |
| InpRangeShrinkRatio | 0.70 | Compression threshold |
| InpExpansionMult | 1.80 | Expansion bar size threshold |
| InpCLVStrong | 0.60 | Expansion decisiveness filter |
| InpTrendBars | 20 | Mean CLV measurement window |
| InpSwingLeftRight | 3 | Swing detection strictness |

## CreviaDeriv Integration — State-Aware Entry Behavior
```python
state = classify_4state(m1_bars)

if state == MarketState4.COMPRESSION:
    # Range squeezing — expand scanning window, expect breakout
    # Do NOT enter during compression (wait for Expansion)
    return None  # skip entry until expansion fires

elif state == MarketState4.EXPANSION:
    # Explosive move — accept single-bar departure, lower confirmation count
    # Only enter in DIRECTION of expansion (match CLV direction to trade direction)
    expansion_dir = 1 if last_clv > 0 else -1
    if expansion_dir != signal.direction_int:
        return None  # expansion in opposite direction = skip
    departure_strength = max(departure_strength, 3)  # floor at 3 during expansion

elif state == MarketState4.TREND:
    # Directional trend — prefer impulsive zones
    if not zone.is_impulsive:
        return None  # skip corrective zones in trend state

elif state == MarketState4.TRANSITION:
    pass  # standard gate chain applies
```

## Why This Matters
Our current system treats all RANGING market the same. But:
- Compression RANGING = breakout about to fire = WAIT for Expansion signal
- Normal RANGING = corrective trades possible
- Expansion during RANGING = rare but highly reliable breakout entry

## Superior Version
1. Add state to EntrySignal metadata for logging/analysis
2. In Compression: tighten SL (expect squeeze breakout = price will move fast)
3. In Expansion: widen TP2 to ATR*3.0 (expansion moves are larger)
4. Run 4-state on BOTH M15 and M1: M15 Compression + M1 Expansion = prime entry