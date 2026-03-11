# Part 28 — Opening Range Breakout Tool
**Type:** EA | **Verdict:** MEDIUM — 3-stage confirmation pattern is the key extract
**URL:** https://www.mql5.com/en/articles/18486

## 3-Stage Breakout Confirmation
```python
class BreakoutTracker:
    """Tracks break → retest → re-break for a given level."""
    def __init__(self, level: float, direction: int):
        self.level     = level
        self.direction = direction   # +1=above, -1=below
        self.stage     = 0           # 0=waiting, 1=broke, 2=retested, 3=confirmed

    def update(self, bar) -> bool:
        if self.stage == 0:
            if self._is_break(bar):   self.stage = 1
        elif self.stage == 1:
            if self._is_retest(bar):  self.stage = 2
        elif self.stage == 2:
            if self._is_rebreak(bar): self.stage = 3; return True
        return False

    def _is_break(self, bar):
        return (bar.close > self.level) if self.direction == 1 else (bar.close < self.level)
    def _is_retest(self, bar):
        return abs(bar.close - self.level) < self.level * 0.001   # within 0.1% of level
    def _is_rebreak(self, bar):
        return self._is_break(bar)
```

## Application to Zone Retests
```
1st zone touch (break into zone) → pullback → 2nd touch (re-enter zone) → departure = ENTRY
```
This is stricter than our current single-touch gate. Use as a HIGH-confidence filter when zone quality < 70.

## Session Opening Range as Zone
```python
def compute_opening_range(bars_m1, session_start_idx, range_minutes=15):
    session_bars = bars_m1[session_start_idx:session_start_idx + range_minutes]
    return {
        'upper': max(b.high for b in session_bars),
        'lower': min(b.low  for b in session_bars),
        'mid':   (upper + lower) / 2
    }
```
Could add to ZoneIdentifier as a 'SESSION_RANGE' zone type — high-impact S/R for the current day.
