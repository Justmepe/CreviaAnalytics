# Part 38 — Tick Buffer VWAP and Short-Window Imbalance Engine
**Type:** Tick-Based EA | **Verdict:** MEDIUM — Flow formula, spread filter, hysteresis pattern
**URL:** https://www.mql5.com/en/articles/19290

## Flow Formula (Adapted for Bar Data)
```python
def compute_bar_flow(bars, lookback: int = 10) -> float:
    """
    Returns flow in [-1, +1].
    +1 = all bars closed bullish (buying pressure)
    -1 = all bars closed bearish (selling pressure)
    """
    recent = bars[-lookback:]
    up = sum(1 for b in recent if b.close > b.open)
    dn = lookback - up
    return (up - dn) / lookback   # normalized to [-1, +1]
```

## Spread Filter (Immediate Use)
```python
def spread_is_cheap(spread: float, atr: float, factor: float = 0.5) -> bool:
    """True if spread is less than 50% of ATR — trade is viable."""
    return spread < atr * factor

# Add to entry gate:
if not spread_is_cheap(symbol_info.spread * symbol_info.point, atr[-1]):
    return None   # skip — spread too wide
```

## Hysteresis Pattern (Apply to ADX Gate)
```python
class HysteresisGate:
    """Fires on crossing threshold, resets at lower level. Prevents rapid toggling."""
    def __init__(self, fire_threshold: float, reset_factor: float = 0.8):
        self.fire_th  = fire_threshold
        self.reset_th = fire_threshold * reset_factor
        self._active  = False

    def check(self, value: float) -> bool:
        if not self._active and value > self.fire_th:
            self._active = True
        elif self._active and value < self.reset_th:
            self._active = False
        return self._active

# ADX gate with hysteresis: fire at ADX=20, reset only at ADX=16
adx_gate = HysteresisGate(fire_threshold=20, reset_factor=0.8)
```

## Notes
- Tick flow on Deriv synthetics = meaningless (tick volume ∝ time, not activity)
- Bar-level flow adaptation is a reasonable proxy for M1 bars
- Spread filter is immediately applicable to our FTMO forex symbols
