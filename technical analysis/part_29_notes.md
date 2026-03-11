# Part 29 — Boom and Crash Interceptor EA
**Type:** EA | **Verdict:** HIGH EXTRACT — velocity percentile spike detection, ATR surge filter
**URL:** https://www.mql5.com/en/articles/18616

## Velocity Percentile (VWV Upgrade)
```python
def velocity_percentile_score(closes: np.ndarray, window: int = 96) -> float:
    """Returns percentile rank (0.0-1.0) of current price move vs history."""
    deltas = np.abs(np.diff(closes[-window:]))
    current_delta = deltas[-1]
    rank = np.sum(deltas <= current_delta) / len(deltas)
    return rank   # 0.95 = top 5% of moves in window

def is_spike(closes, window=96, pctile_threshold=0.95) -> bool:
    return velocity_percentile_score(closes, window) >= pctile_threshold

# VelocityPctile=120 in original = more extreme than max in window:
def is_extreme_spike(closes, window=96) -> bool:
    deltas = np.abs(np.diff(closes[-window:]))
    return deltas[-1] > np.max(deltas[:-1])   # exceeds historical max
```

## ATR Surge Filter (New)
```python
def is_atr_surging(atr: np.ndarray, multiplier: float = 1.5) -> bool:
    """Current ATR meaningfully above prior ATR — volatility expanding."""
    return atr[-1] > atr[-2] * multiplier
```

## Combined VWV Upgrade for Crash/Boom
```python
def vwv_strong_synthetics(closes, atr, window=96) -> bool:
    """Enhanced VWV for Crash/Boom — velocity percentile + ATR surge."""
    spike = velocity_percentile_score(closes, window) > 0.90
    expanding = is_atr_surging(atr, multiplier=1.3)
    return spike and expanding
```

## Calibration by Instrument
| Instrument | Velocity Pctile Threshold |
|---|---|
| Crash/Boom 500/900/1000 | 95th — spike only |
| Volatility 25/50/75 | 75th — elevated moves |
| Forex | 70th — momentum confirmation |
| Step Index | 80th — step-function spikes |

## Direct Relevance
Our `_energy_src='range_atr'` for synthetics already captures spike energy. Adding percentile ranking makes it adaptive — threshold automatically adjusts to current market regime rather than being calibrated against historical ATR scale.
