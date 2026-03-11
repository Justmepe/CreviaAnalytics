# Part 33 — Candle Range Theory Tool
**Type:** Indicator | **Verdict:** HIGH EXTRACT — CRT 4-class system as departure and pre-filter
**URL:** https://www.mql5.com/en/articles/18911

## CRT Classifier
```python
def classify_crt(bar, prev_bar, atr: float,
                  large_mult: float = 1.5, small_mult: float = 0.5) -> str:
    tr = max(bar.high - bar.low,
             abs(bar.high - prev_bar.close),
             abs(bar.low  - prev_bar.close))

    is_ib = bar.high < prev_bar.high and bar.low > prev_bar.low
    is_ob = bar.high > prev_bar.high and bar.low < prev_bar.low

    if is_ib: return 'IB'    # inside — consolidation
    if is_ob: return 'OB'    # outside — engulfing, ambiguous
    if tr >= large_mult * atr: return 'LR'   # expansion
    if tr <= small_mult * atr: return 'SR'   # compression
    return 'NR'   # normal range
```

## Departure Strength with CRT
```python
DEPARTURE_STRENGTH = {
    'LR':   4,   # large range = maximum momentum
    'NR':   2,   # normal range with direction = moderate
    'IB':   1,   # inside bar — low momentum
    'OB':   0,   # outside — ambiguous, skip
    'SR':   0,   # small range alone = skip (but good PRE-zone compression signal)
}
```

## Compression Detection (Pre-Zone)
```python
def is_compressed_setup(bars, prev_bars, atr_series, lookback=3) -> bool:
    """Returns True if last N bars were all Small Range — coiled spring."""
    types = [classify_crt(bars[-i], prev_bars[-i], atr_series[-i]) for i in range(1, lookback+1)]
    return all(t == 'SR' for t in types)

# In EntryEngine: if is_compressed_setup(): signal_confidence += 10
```

## Practical Signal Rules
| Candle at Zone Touch | Action |
|---|---|
| LR (large range) toward zone | Aggressive momentum entry — departure strength 4 |
| SR sequence (3+) then zone touch | Setup compression — high probability |
| IB at zone | Consolidation — wait for IB breakout in trade direction |
| OB at zone | Skip — no directional clarity |

## Validation
Tested on Step Index, Crash 1000, Boom 1000 — all synthetics we trade on Deriv. Direct relevance. No repainting (shift=1 for closed bars only).
