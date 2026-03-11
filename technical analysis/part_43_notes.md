# Part 43 — Candlestick Probability and Breakouts
**Type:** Analysis | **Verdict:** HIGH EXTRACT — pattern win rates for departure_strength calibration
**URL:** https://www.mql5.com/en/articles/19738

## Pattern Win Rate Calculator
```python
def compute_pattern_win_rates(bars, lookback=2000, lookahead=5) -> dict:
    """
    For each detected pattern in history, check if next N bars moved in expected direction.
    Returns: {pattern_name: win_rate_float}
    """
    results = {}

    for i in range(lookback, len(bars) - lookahead):
        o,h,l,c = bars[i].open, bars[i].high, bars[i].low, bars[i].close
        po,ph,pl,pc = bars[i-1].open, bars[i-1].high, bars[i-1].low, bars[i-1].close
        atr = compute_atr(bars, i, 14)

        pattern = classify_candle(o, h, l, c, po, ph, pl, pc, atr)
        if pattern == 'NONE': continue

        # Determine expected direction
        is_bullish = 'BULLISH' in pattern or 'HAMMER' in pattern
        expected = 1 if is_bullish else -1

        # Check within-N follow through
        success = any(
            (bars[i+j].close > bars[i].close if expected == 1
             else bars[i+j].close < bars[i].close)
            for j in range(1, lookahead+1)
        )

        if pattern not in results:
            results[pattern] = {'wins': 0, 'total': 0}
        results[pattern]['total'] += 1
        if success: results[pattern]['wins'] += 1

    return {k: v['wins']/v['total'] if v['total'] > 5 else 0.5
            for k, v in results.items()}
```

## Win Rate to Departure Strength
```python
def win_rate_to_departure_strength(win_rate: float) -> int:
    if win_rate >= 0.70: return 4   # high historical confidence
    if win_rate >= 0.60: return 3
    if win_rate >= 0.55: return 2
    if win_rate >= 0.50: return 1
    return 0   # below random — don't use this pattern

# Usage:
rates = compute_pattern_win_rates(historical_bars)
pattern = classify_candle(...)
strength = win_rate_to_departure_strength(rates.get(pattern, 0.5))
```

## Integration with MarketDNA (Part 40)
Run `compute_pattern_win_rates()` as part of per-symbol MarketDNA initialization. Store alongside the 17 DNA metrics. Refresh monthly or on regime change detection.
