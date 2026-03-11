# Part 16 — Introducing Quarters Theory (II) — Intrusion Detector EA
**Series:** Price Action Analysis Toolkit Development
**Type:** EA (Monitoring Only) | **Verdict:** EXTRACT — intrusion check pattern, deduplication flag, multi-level monitoring
**Published:** 2025-03

---

## What It Does
On every tick, checks if price is within `AlertTolerance` of any quarter level. Fires a contextual alert on first intrusion, suppresses re-alerts while price lingers (boolean flag per level), resets flag when price leaves. No buy/sell signals — pure proximity alerting.

---

## Core Intrusion Check
```python
def check_intrusions(price: float, levels: dict, tolerance: float, state: dict) -> list:
    """
    Returns list of new intrusions (first touch only, not re-fires while lingering).
    state = {level_name: bool} — tracks which levels have been alerted.
    """
    intrusions = []
    for name, level in levels.items():
        in_zone = abs(price - level) <= tolerance
        if in_zone and not state.get(name, False):
            intrusions.append(Intrusion(name=name, level=level, is_new=True))
            state[name] = True      # suppress re-alert
        elif not in_zone:
            state[name] = False     # reset when price leaves
    return intrusions
```

This is identical to what our `_is_interacting()` does, but extended to multiple levels simultaneously.

---

## Contextual Commentary by Zone Type

| Zone | Comment |
|---|---|
| Major Support | Key support. Break below signals range shift. |
| Major Resistance | Pivotal resistance. Breakout starts new range. |
| Large Quarter | Decisive break → next 250-pip move. |
| Overshoot | Reversal likely if momentum fails. |
| Undershoot | Insufficient bullish force — possible bearish reversal. |
| Small Quarter | Minor fluctuation. |

**Our version**: translate these to zone quality scores, not text messages.

---

## AlertTolerance — The Problem

Original: `AlertTolerance = 0.0025` (25 pips for EUR/USD)

Problems:
- EUR/USD: 25 pips is reasonable
- USD/JPY: 25 pips in JPY terms needs different scaling
- Crash 300 at 9500: 25 pips = 0.25 points — way too tight

**Our fix**: `tolerance = ATR(14) × 0.3`
- Scales with instrument volatility
- Works across synthetics, forex, metals

```python
def compute_tolerance(atr: float, atr_factor: float = 0.3) -> float:
    return atr * atr_factor
```

---

## What to Keep
- Intrusion check: `abs(price - level) <= tolerance`
- Boolean flag deduplication per level
- Flag reset when price leaves zone
- Simultaneous multi-level monitoring (all levels checked per tick)
- Contextual classification per zone type

## What to Discard
- Fixed tolerance (0.0025) — replace with ATR-normalized
- No buy/sell signal generation
- Forex-only framing
- MQL5 chart rendering

## What to Improve
- ATR-normalized tolerance
- Intrusion depth tracking: `depth = abs(price - level)` — deeper = stronger move
- Intrusion duration: bars spent inside tolerance zone
- Signal upgrade: overshoot intrusion + momentum filter = reversal signal

---

## Our Superior Version Design

### QuarterLevelMonitor
```python
@dataclass
class Intrusion:
    name: str
    level: float
    zone_type: str     # 'major', 'large_quarter', 'overshoot', 'small_quarter'
    is_new: bool       # True = first bar, False = still inside
    depth: float       # abs(price - level) — penetration depth
    bars_inside: int   # how many consecutive bars in zone

class QuarterLevelMonitor:
    def __init__(self, major_step: float, atr_tolerance_factor: float = 0.3):
        self.major_step = major_step
        self.atr_factor = atr_tolerance_factor
        self._state: dict = {}      # level_name -> bars_inside count (0 = not in zone)

    def update(self, price: float, atr: float) -> List[Intrusion]:
        tolerance = atr * self.atr_factor
        levels = compute_quarter_levels(price, self.major_step)
        all_levels = self._flatten(levels)
        intrusions = []
        for name, level, zone_type in all_levels:
            depth = abs(price - level)
            if depth <= tolerance:
                self._state[name] = self._state.get(name, 0) + 1
                intrusions.append(Intrusion(
                    name=name, level=level, zone_type=zone_type,
                    is_new=self._state[name] == 1,
                    depth=depth,
                    bars_inside=self._state[name]
                ))
            else:
                self._state[name] = 0
        return intrusions
```

### Integration with Zone Interaction
```python
# In EntryEngine: extend zone interaction check to include quarter level proximity
quarter_monitor = QuarterLevelMonitor(major_step=0.1, atr_tolerance_factor=0.3)

def scan_for_entries(bars, zones, structure, config):
    intrusions = quarter_monitor.update(bars[-1].close, atr[-1])
    for zone in zones:
        zone_touch = _is_interacting(bars, zone)
        if zone_touch:
            # Check if zone is at a quarter level (confluence)
            nearby_quarter = [i for i in intrusions if abs(i.level - zone.mid) < atr * 0.5]
            if nearby_quarter:
                zone.quality_score += 15  # quarter level alignment bonus
```

---

## Validation for CreviaDeriv
1. **_is_interacting() IS an intrusion check** — same pattern, our code already does this correctly
2. **Boolean flag deduplication** — our single-signal-per-zone logic is the correct implementation of this
3. **ATR-normalized tolerance is essential** — fixed pip thresholds don't work across instruments. Our code must use ATR throughout.
4. **Intrusion duration (bars_inside)** is a new metric worth adding: a zone that price enters and immediately exits (1-2 bars) is a STRONGER signal than a zone where price lingers for 10 bars (suggests absorption, not rejection).
