# Part 23 — Currency Strength Meter
**Type:** Dashboard | **Verdict:** EXTRACT — strength formula, sign inversion, 3-TF context, pre-filter gate
**URL:** https://www.mql5.com/en/articles/18108

## Strength Formula
```python
def compute_currency_strength(closes_by_pair: dict, currency: str,
                               lookback: int) -> float:
    """
    closes_by_pair: {'EURUSD': np.array, 'GBPUSD': np.array, ...}
    Returns: strength score (% change, sign-adjusted)
    """
    scores = []
    for pair, closes in closes_by_pair.items():
        base  = pair[:3]
        quote = pair[3:]
        if currency not in (base, quote):
            continue
        pct = (closes[-1] - closes[-lookback]) / closes[-lookback] * 100
        if currency == quote:
            pct *= -1   # invert: if USD is quote and pair fell, USD strengthened
        scores.append(pct)
    return sum(scores) / len(scores) if scores else 0.0

# Classifications:
def classify(strength: float) -> str:
    if strength > 0.3:  return 'STRONG'
    if strength < -0.3: return 'WEAK'
    return 'NEUTRAL'
```

## 3-TF Context
| TF | Lookback | Time Period | Use |
|---|---|---|---|
| M15 | 96 bars | 24h | Current intraday strength |
| H1 | 48 bars | 48h | Short-term trend direction |
| H4 | 30 bars | 120h (5 days) | Weekly bias |

For entry decisions: M15 strength must agree with H1. H4 gives context only.

## Pre-Filter Gate (New Entry Gate)
```python
def passes_currency_strength_gate(signal, strength_m15, strength_h1, threshold=0.1):
    if signal.direction == 'BUY':
        base_strong  = strength_m15[signal.base_currency] > threshold
        quote_weak   = strength_m15[signal.quote_currency] < -threshold
        h1_confirms  = strength_h1[signal.base_currency] > 0   # at least positive
        return base_strong and quote_weak and h1_confirms
    else:  # SELL
        base_weak    = strength_m15[signal.base_currency] < -threshold
        quote_strong = strength_m15[signal.quote_currency] > threshold
        h1_confirms  = strength_h1[signal.base_currency] < 0
        return base_weak and quote_strong and h1_confirms
```

## Validation for CreviaDeriv
- Synthetics (Crash/Boom/Volatility): currency strength doesn't apply — skip this gate for synthetic symbols
- Forex only: applies to all EUR, GBP, USD, JPY pairs
- Adds directional confluence beyond structural analysis — catches cases where our zone aligns with structure but the currency is fundamentally moving against us
