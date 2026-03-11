# Part 44 — Building a VWMA Crossover Signal EA
**Type:** EA | **Verdict:** LOW-MEDIUM — VWMA formula, SR clearance concept
**URL:** https://www.mql5.com/en/articles/19843

## VWMA Formula
```python
def compute_vwma(closes: np.ndarray, volumes: np.ndarray, period: int) -> np.ndarray:
    """Volume-Weighted Moving Average."""
    result = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        c = closes[i-period+1:i+1]
        v = volumes[i-period+1:i+1]
        result[i] = np.dot(c, v) / np.sum(v) if np.sum(v) > 0 else c[-1]
    return result
```

## VWMA vs EMA3
- VWMA weights bars by volume — high-volume bars have more influence
- EMA3 weights bars by recency — most recent bars have most influence
- For our M1 entry: VWMA(3) would capture momentum where volume is highest
- For Deriv synthetics: tick_volume ∝ time not activity → VWMA loses its advantage. Use EMA3 for synthetics, VWMA for real forex.

## SR Clearance Pattern
```python
def cleared_sr_level(price, sr_level, direction, offset_pips):
    """Signal fires only after price has clearly cleared the S/R level."""
    if direction == "BUY":
        return price > sr_level + offset_pips * pip_size
    return price < sr_level - offset_pips * pip_size
```
Maps to our zone exit: departure candle must close outside zone boundary by ATR*0.3.
