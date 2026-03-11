# Part 18 — Introducing Quarters Theory (III) — Quarters Board
**Series:** Price Action Analysis Toolkit Development
**Type:** EA (UI Tool) | **Verdict:** LOW EXTRACT — completes Quarters trilogy, no new calculation logic
**Published:** 2025-04

---

## What It Does
Adds interactive button controls to toggle quarter level display (large quarters, small quarters, overshoot zones) without editing code. Adds a real-time SMA(50) trend label alongside the levels.

**No new formulas vs Parts 15-16.** Same level calculations, new UI layer only.

---

## Quarters Trilogy Complete

| Part | Role | Extract? |
|---|---|---|
| 15 | Level calculator (formulas) | YES — QuarterLevelCalculator |
| 16 | Intrusion monitor (alerts) | YES — QuarterLevelMonitor |
| 18 | UI toggles (buttons) | NO — discard for Python |

### Our Combined QuarterLevelService
```python
class QuarterLevelService:
    """Combines Parts 15+16 functionality. No UI layer needed."""

    def __init__(self, major_step: float, atr_tolerance_factor: float = 0.3):
        self.calculator = QuarterLevelCalculator(major_step)
        self.monitor    = QuarterLevelMonitor(major_step, atr_tolerance_factor)

    def update(self, price: float, atr: float) -> tuple:
        levels     = self.calculator.compute(price)
        intrusions = self.monitor.update(price, atr)
        return levels, intrusions

    def get_zone_quality_bonus(self, zone_mid: float, zone_side: str,
                                levels: QuarterLevels, atr: float) -> int:
        """Returns quality bonus points if zone aligns with a quarter level."""
        for lq in levels.large_quarters:
            if abs(zone_mid - lq) < atr * 0.5:
                return 15   # large quarter alignment
        if abs(zone_mid - levels.major_lower) < atr or abs(zone_mid - levels.major_upper) < atr:
            return 20       # major level alignment
        return 0
```

---

## The Only New Insight: SMA Trend Label

```python
# Their approach (weak):
trend = 'Uptrend' if bid > sma50 else 'Downtrend' if bid < sma50 else 'Sideways'

# Our approach (better — from StructureEngine):
trend = structure.market_structure.value  # BULLISH / BEARISH / RANGING / UNKNOWN
```

Their SMA(50) trend classification is already subsumed by our StructureEngine's HH/HL/LH/LL pattern detection. No upgrade needed.

---

## Validation for CreviaDeriv
- Quarters trilogy architecturally complete. `QuarterLevelService` can be implemented now with all three parts' insights combined.
- Confirms: SMA(50) trend classification is the simplest possible trend filter. Our StructureEngine is strictly better.
