# Part 40 — Market DNA Passport
**Type:** Analysis Tool | **Verdict:** HIGH EXTRACT — 17-metric instrument calibration, retracement frequencies, mutation detection
**URL:** https://www.mql5.com/en/articles/19460

## Retracement Frequency Detection
```python
def compute_retracement_frequencies(swings: list, bars, window: int = 50) -> dict:
    """For each impulse swing, find max retracement in next window bars."""
    buckets = {'38': 0, '50': 0, '62': 0, '>70': 0, 'none': 0}
    for i, swing in enumerate(swings[:-1]):
        impulse_size = abs(swings[i+1].price - swing.price)
        if impulse_size == 0: continue
        max_retr = 0
        for j in range(swing.bar_idx, min(swing.bar_idx + window, len(bars))):
            retr = abs(bars[j].close - swings[i+1].price) / impulse_size
            max_retr = max(max_retr, retr)
        if   max_retr < 0.45:   buckets['38'] += 1
        elif max_retr < 0.55:   buckets['50'] += 1
        elif max_retr < 0.68:   buckets['62'] += 1
        elif max_retr >= 0.68:  buckets['>70'] += 1
    total = sum(buckets.values()) or 1
    return {k: v/total for k, v in buckets.items()}
```

## Smoothness Index
```python
def compute_smoothness_index(bars, fractal_density: float, vol_clustering: float) -> float:
    """
    0 = very choppy (many fractals, clustered volatility)
    1 = very smooth/trending (few fractals, consistent volatility)
    """
    smoothness = 1.0 - fractal_density   # fewer fractals = smoother
    smoothness = (smoothness + (1.0 - vol_clustering)) / 2
    return max(0.0, min(1.0, smoothness))
```

## Cosine Distance for Regime Change
```python
import numpy as np

def cosine_distance(dna_A: list, dna_B: list) -> float:
    a, b = np.array(dna_A), np.array(dna_B)
    return 1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

def is_regime_change(current_dna, prior_dna, threshold=0.12) -> bool:
    return cosine_distance(current_dna, prior_dna) > threshold
```

## Practical Application to CreviaDeriv
Run MarketDNA at startup for each symbol. Store results. Use to calibrate:

| DNA Metric | Config Effect |
|---|---|
| `smoothness > 0.7` | `enable_corrective_trades = False` (trending market) |
| `smoothness < 0.4` | `enable_corrective_trades = True` (ranging) |
| `retr_38_freq > 0.4` | Shallow HL zones are sufficient |
| `retr_62_freq > 0.4` | Deep zone setback expected — widen zone depth |
| `pct_spikes > 0.05` | Use velocity percentile (Part 29) not fixed VWV threshold |
| Regime mutation detected | Pause trading, re-calibrate |

## EURUSD H1 Benchmark
- 171 swings, 9.62-bar avg cycle, 98% breakout follow-through
- London dominates range share
- This is our baseline for calibrating EURUSD-specific settings
