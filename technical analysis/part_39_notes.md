# Part 39 — Automating BOS and ChoCH Detection in MQL5
**Type:** Indicator | **Verdict:** HIGH EXTRACT — os_state machine validates and clarifies our StructureEngine
**URL:** https://www.mql5.com/en/articles/19365

## os_state Machine (Cleaner BOS/ChoCH Logic)
```python
class StructureBreakDetector:
    """
    os_state: +1 = bullish bias (last break was upward)
               -1 = bearish bias (last break was downward)
    """
    def __init__(self):
        self.os_state = 0  # unknown until first break

    def process_fractal_break(self, break_direction: int, level: float) -> str:
        """
        break_direction: +1 = closed above fractal high, -1 = closed below fractal low
        Returns: 'BOS', 'CHOCH', or 'NONE'
        """
        if self.os_state == 0:
            self.os_state = break_direction
            return 'NONE'   # first break — just initialize

        if break_direction == self.os_state:
            result = 'BOS'    # same direction = trend continuation
        else:
            result = 'CHOCH'  # opposite direction = character change
            self.os_state = break_direction   # flip state

        return result
```

## CrossedOver / CrossedUnder (Closed-Bar Pattern)
```python
def crossed_over(prev_close: float, curr_close: float, level: float) -> bool:
    """Price closed below level, then closed above → bullish BOS/ChoCH."""
    return prev_close <= level and curr_close > level

def crossed_under(prev_close: float, curr_close: float, level: float) -> bool:
    """Price closed above level, then closed below → bearish BOS/ChoCH."""
    return prev_close >= level and curr_close < level
```

## Full Detection Flow
```python
def detect_bos_choch(bars, fractals, detector: StructureBreakDetector):
    prev_c = bars[-2].close
    curr_c = bars[-1].close

    for frac in fractals:
        if frac.is_high and crossed_over(prev_c, curr_c, frac.price):
            result = detector.process_fractal_break(+1, frac.price)
            if result: return result, 'BUY'

        if frac.is_low and crossed_under(prev_c, curr_c, frac.price):
            result = detector.process_fractal_break(-1, frac.price)
            if result: return result, 'SELL'

    return None, None
```

## How This Maps to Our StructureEngine
Our `detect_structure_break()` checks direction vs `market_structure`. This is equivalent but less explicit than `os_state`. The os_state approach is:
1. More readable — clearly says "opposite direction = ChoCH"
2. More stateful — tracks the sequence explicitly
3. Matches how ICT/SMC practitioners think about BOS/ChoCH

Consider refactoring `detect_structure_break()` to use `os_state` internally.
