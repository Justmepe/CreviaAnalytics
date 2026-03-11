# Part 26 — Pin Bar, Engulfing Patterns and RSI Divergence (Multi-Pattern) Tool
**Type:** EA | **Verdict:** HIGH EXTRACT — dual confirmation architecture, pin bar formula with 10% body floor
**URL:** https://www.mql5.com/en/articles/17962

## Dual Confirmation Pattern
```python
def combined_signal(pattern_signal: int, divergence_signal: int) -> int:
    """Both must fire in same direction. 0 = skip."""
    if pattern_signal != 0 and divergence_signal != 0:
        if pattern_signal == divergence_signal:
            return pattern_signal   # +1 or -1
    return 0
```

## Pin Bar (with 10% body floor — key refinement vs Part 24)
```python
def is_pin_bar(o, h, l, c, wick_ratio=2.0) -> int:
    body     = abs(c - o)
    rng      = h - l
    top_wick = h - max(o, c)
    bot_wick = min(o, c) - l

    if body < 0.1 * rng or rng == 0:   # 10% body minimum
        return 0

    if bot_wick >= wick_ratio * body and top_wick < 0.5 * body:
        return 1    # bullish pin bar
    if top_wick >= wick_ratio * body and bot_wick < 0.5 * body:
        return -1   # bearish pin bar
    return 0
```

## Engulfing
```python
def is_engulfing(o, h, l, c, po, ph, pl, pc) -> int:
    curr_body = abs(c - o)
    prev_body = abs(pc - po)
    prev_bearish = pc < po
    prev_bullish = pc > po

    if prev_bearish and o <= pc and c >= po and curr_body > prev_body:
        return 1    # bullish engulfing
    if prev_bullish and o >= pc and c <= po and curr_body > prev_body:
        return -1   # bearish engulfing
    return 0
```

## RSI Divergence (simplified 5-15 bar scan)
```python
def scan_rsi_divergence(closes, rsi, scan_window=(5,15)) -> int:
    lo, hi = scan_window
    current_close = closes[-1]
    current_rsi   = rsi[-1]

    for n in range(lo, hi+1):
        ref_close = closes[-n]
        ref_rsi   = rsi[-n]
        # Bullish: price lower but RSI higher
        if current_close < ref_close and current_rsi > ref_rsi and current_rsi > 30:
            return 1
        # Bearish: price higher but RSI lower
        if current_close > ref_close and current_rsi < ref_rsi and current_rsi < 70:
            return -1
    return 0
```

## Upgrade Path for CreviaDeriv
Current departure gate: `close > open` (directional only)
Upgraded gate:
1. `classify_candle()` → pin bar or engulfing = pattern confirmed
2. `scan_rsi_divergence()` or Part 13 swing-based = divergence confirmed
3. Both required for HIGH confidence; just candle for MEDIUM

This maps directly into our departure_strength scoring from Part 24.
