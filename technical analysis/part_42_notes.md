# Part 42 — Interactive Chart Testing with Statistical Levels
**Type:** EA | **Verdict:** LOW-MEDIUM — extends Part 41 with volume-weighted stats, asymmetric z-scores
**URL:** https://www.mql5.com/en/articles/19697

## Volume-Weighted TP Distribution
```python
def compute_vwtp_stats(highs, lows, closes, volumes, lookback=1000):
    """Volume-weighted typical price statistics."""
    tp  = (highs[-lookback:] + lows[-lookback:] + closes[-lookback:]) / 3
    vol = volumes[-lookback:]
    vwmean = np.average(tp, weights=vol)      # VWAP-style mean
    vw_var = np.average((tp - vwmean)**2, weights=vol)
    vwstd  = np.sqrt(vw_var)
    return {'vwmean': vwmean, 'vwstd': vwstd}
```

## KDE Mode
```python
from scipy.stats import gaussian_kde

def kde_mode(tp: np.ndarray, bandwidth_factor: float = 1.0, grid_points: int = 100):
    """Find the most common typical price via kernel density estimation."""
    kde = gaussian_kde(tp, bw_method=lambda s: s.scotts_factor() * bandwidth_factor)
    grid = np.linspace(tp.min(), tp.max(), grid_points)
    density = kde(grid)
    return grid[np.argmax(density)]   # price with highest density = mode
```

## Combined Usage with Part 41
Part 41 gives the basic statistical framework. Part 42 adds volume weighting and KDE mode. The complete stats function:
```python
def full_tp_stats(h, l, c, vol, lookback=1000):
    tp   = (h[-lookback:] + l[-lookback:] + c[-lookback:]) / 3
    v    = vol[-lookback:]
    mean = np.average(tp, weights=v)     # volume-weighted
    std  = np.sqrt(np.average((tp-mean)**2, weights=v))
    mode = kde_mode(tp)
    p25, p75 = np.percentile(tp, [25, 75])
    return {'mean': mean, 'std': std, 'mode': mode, 'p25': p25, 'p75': p75}
```

**Note**: Deriv tick_volume is time-proportional for synthetics — use unweighted mean for Crash/Boom/Volatility. Use volume-weighted only for FTMO forex.
