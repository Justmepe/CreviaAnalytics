# Part 15 — Introducing Quarters Theory (I) — Quarters Drawer Script
**Series:** Price Action Analysis Toolkit Development
**Type:** Script | **Verdict:** EXTRACT — hierarchical price level framework, overshoot zone formula, SL placement logic
**Published:** 2025-02

---

## What It Does
Computes and draws three tiers of price levels around the current price: major whole-number boundaries, large quarters (÷4), and small quarters (÷10÷4). Marks overshoot zones — bands where price may briefly exceed a level before reversing.

---

## Level Hierarchy (All Formulas)

```python
def compute_quarter_levels(price: float, major_step: float) -> dict:
    lower_major = math.floor(price / major_step) * major_step
    upper_major = lower_major + major_step

    # Large quarters: 3 levels at MajorStep/4 intervals
    lq_inc = major_step / 4.0
    large_quarters = [lower_major + i * lq_inc for i in range(1, 4)]
    # e.g., EURUSD 1.2xxx → [1.2250, 1.2500, 1.2750]

    # Small quarters: 27 levels within the major range
    seg_step = major_step / 10.0
    sq_size  = seg_step / 4.0
    small_quarters = []
    for seg in range(10):
        for j in range(1, 4):
            small_quarters.append(lower_major + seg * seg_step + j * sq_size)
    # e.g., first 3: [1.2025, 1.2050, 1.2075], next 3: [1.2125, 1.2150, 1.2175], ...

    # Overshoot zones: band of MajorStep/40 around each large quarter
    ov_offset = major_step / 40.0
    overshoot_bands = [(lq - ov_offset, lq + ov_offset) for lq in large_quarters]
    # e.g., around 1.2500: (1.2475, 1.2525)

    return {
        "major": (lower_major, upper_major),
        "large_quarters": large_quarters,
        "small_quarters": small_quarters,
        "overshoot_bands": overshoot_bands
    }
```

---

## MajorStep by Instrument

| Instrument | MajorStep | Large Quarters |
|---|---|---|
| EURUSD, GBPUSD (4-digit) | 0.1000 | 0.0250 apart |
| USDJPY (2-digit) | 1.0 | 0.25 apart |
| XAUUSD (Gold) | 100.0 | 25.0 apart |
| Crash/Boom indices | 1000 | 250 apart |
| Volatility 75 | 1000 | 250 apart |
| Volatility 25 | 100 | 25 apart |

**For synthetics**: Use ATR(200) × 10 as auto-calibrated MajorStep if manual value not set.

---

## Overshoot Zone — The Key Insight

Price at a large quarter level often **slightly exceeds** it before reversing. This is:
- Stop hunters sweeping liquidity beyond the obvious level
- Institutional orders absorbing at the level + overshoot

**SL placement rule**: SL should be beyond the overshoot band, not just beyond the zone:
```
Demand zone at 1.2490
Large quarter at 1.2500, overshoot band: (1.2475, 1.2525)
Bad SL: 1.2490 (inside overshoot — gets hit by wicks)
Good SL: 1.2470 (below entire overshoot band)
```

---

## What to Keep
- Three-tier hierarchy (major → large → small) — structured S/R map
- `floor()` formula for finding the enclosing major range — exact and simple
- Overshoot offset = `MajorStep / 40` — scales with instrument
- MajorStep as configurable instrument parameter

## What to Discard
- Script (runs once) — need dynamic calculation on each data update
- Chart drawing only — need data output for integration
- No action on levels — pure display tool

## What to Improve
- **Auto-calibrate MajorStep** from ATR for synthetics
- **Zone alignment score**: if zone boundary within 10% of `MajorStep/4` of a large quarter → +15 quality bonus
- **TP targeting**: use large quarters as TP1/TP2, major level as TP3/P4
- **SL upgrade**: SL beyond overshoot zone, not just beyond zone boundary

---

## Our Superior Version Design

### QuarterLevelCalculator (pure, instrument-aware)
```python
@dataclass
class QuarterLevels:
    major_lower: float
    major_upper: float
    large_quarters: List[float]     # 3 levels
    small_quarters: List[float]     # 27 levels
    overshoot_bands: List[Tuple[float, float]]  # 3 bands

class QuarterLevelCalculator:
    def __init__(self, major_step: float = None, atr: float = None):
        # Auto-calibrate if major_step not given
        self.major_step = major_step or (atr * 10 if atr else None)

    def compute(self, price: float) -> QuarterLevels:
        ...
```

### Integration: TP Targeting
```python
def get_quarter_tp_targets(entry: float, direction: str, levels: QuarterLevels) -> List[float]:
    """Return nearest large quarter levels in trade direction for TP1, TP2."""
    if direction == 'BUY':
        candidates = [lq for lq in levels.large_quarters if lq > entry]
        candidates += [levels.major_upper]
    else:
        candidates = [lq for lq in reversed(levels.large_quarters) if lq < entry]
        candidates += [levels.major_lower]
    return sorted(candidates)[:4]   # TP1 through TP4
```

### Integration: SL Beyond Overshoot
```python
def adjust_sl_beyond_overshoot(sl: float, direction: str, levels: QuarterLevels) -> float:
    """Push SL to be outside the overshoot zone of the nearest quarter level."""
    if direction == 'BUY':
        # Find the nearest overshoot band below entry
        bands_below = [(lo, hi) for lo, hi in levels.overshoot_bands if hi < entry]
        if bands_below:
            nearest_lo = max(lo for lo, hi in bands_below)
            sl = min(sl, nearest_lo - pip_buffer)
    # mirror for SELL
    return sl
```

---

## Validation for CreviaDeriv
1. **Round number S/R is real**: Institutional orders cluster at large quarter levels. Our zone boundaries that align with these levels have extra structural significance.
2. **Overshoot concept = liquidity sweep**: Price briefly exceeding a level before reversing is the same as our "spike below zone then rejection" entry pattern. Quarter theory gives us the expected sweep width.
3. **Hierarchical S/R matches our zone architecture**: Major = our broader structural zones (500-bar highs/lows). Large quarters = our supply/demand zones. Small quarters = M1-level micro-structure.
4. **SL beyond overshoot = beyond stop hunt zone**: Standard practice. Our `_calculate_precision_sl()` finds the external swing — which often aligns with an overshoot zone beyond a quarter level. This validates the approach.
