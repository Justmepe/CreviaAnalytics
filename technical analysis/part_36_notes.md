# Part 36 — Unlocking Direct Python Access to MetaTrader 5 Market Streams
**Type:** Python + MT5 | **Verdict:** LOW-MEDIUM — z_spike formula and EMA envelope are the extracts
**URL:** https://www.mql5.com/en/articles/19065

## z_spike (Normalized Velocity)
```python
def compute_z_spike(closes: np.ndarray, window: int = 20) -> np.ndarray:
    """
    First difference normalized by rolling std — z-score of price changes.
    Values > 2.0 = statistically significant spike (>2 std devs).
    """
    diffs = pd.Series(closes).diff()
    rolling_std = diffs.rolling(window).std()
    z = diffs / rolling_std
    return z.fillna(0).values

# Use alongside VWV:
z = compute_z_spike(closes)
is_spike = abs(z[-1]) > 2.0   # 2 standard deviations
```

## EMA Envelope Bands
```python
def ema_envelope(closes: np.ndarray, span: int = 20, pct: float = 0.003) -> tuple:
    """Returns (lower_band, upper_band) = EMA ± 0.3%."""
    ema = pd.Series(closes).ewm(span=span).mean().values
    return ema * (1 - pct), ema * (1 + pct)

# Micro-zone: price at env_low = dynamic support
# price at env_high = dynamic resistance
```

## When to Use z_spike vs VWV
| Instrument | Primary | Reason |
|---|---|---|
| Crash/Boom | z_spike | Spike detection — sudden directional moves |
| Volatility | Both | Both capture energy, z_spike is more sensitive |
| Forex | VWV | Sustained momentum, not spike behavior |

## Practical z_spike Thresholds
- `|z| > 1.5` — above average move (70th percentile)
- `|z| > 2.0` — significant spike (95th percentile for normal distribution)
- `|z| > 3.0` — extreme spike (99.7th percentile) — Crash/Boom signal territory
