# Part 41 — Building a Statistical Price-Level EA
**Type:** EA | **Verdict:** MEDIUM — z-score deviation, P25/P75 value area, KDE mode
**URL:** https://www.mql5.com/en/articles/19589

## Z-Score Confluence with Zones
```python
def compute_tp_stats(highs, lows, closes, lookback=1000):
    tp = (highs[-lookback:] + lows[-lookback:] + closes[-lookback:]) / 3
    return {
        'mean': np.mean(tp), 'std': np.std(tp),
        'p25':  np.percentile(tp, 25), 'p75': np.percentile(tp, 75),
        'median': np.median(tp)
    }

def z_score_at_zone(zone_mid, stats) -> float:
    return (zone_mid - stats['mean']) / (stats['std'] + 1e-10)

# In EntryEngine: if zone is DEMAND and z_score < -1.5 (below mean), quality bonus
# if zone is SUPPLY and z_score > +1.5 (above mean), quality bonus
def statistical_zone_bonus(zone, stats):
    z = z_score_at_zone(zone.mid, stats)
    if zone.type == 'DEMAND' and z < -1.5: return 15   # statistically depressed
    if zone.type == 'SUPPLY' and z >  1.5: return 15   # statistically elevated
    return 0
```

## P25/P75 as Value Area
```python
# P25 = lower quartile — fair value floor
# P75 = upper quartile — fair value ceiling
# Demand zones below P25 = undervalued area (statistical + structural support)
# Supply zones above P75 = overvalued area (statistical + structural resistance)
```

## Skewness for Direction Bias
```python
from scipy.stats import skew, kurtosis
sk = skew(tp)
# sk > 0: right-skewed (more closes below mean, occasional spikes up) → slight bearish bias (mean reversion)
# sk < 0: left-skewed (more closes above mean) → slight bullish bias
# Note: positive skew = SELL bias in mean-reversion context; interpret carefully for trend-following
```
