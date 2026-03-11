# Part 27 — Liquidity Sweep with MA Filter Tool
**Type:** EA | **Verdict:** HIGH EXTRACT — zone sweep detection is our departure candle, made explicit
**URL:** https://www.mql5.com/en/articles/18379

## Sweep Detection Logic
```python
def detect_liquidity_sweep(curr, prev, strict: bool = False) -> int:
    """
    curr/prev: bar objects with .open, .high, .low, .close
    Returns: +1 bullish sweep, -1 bearish sweep, 0 none
    """
    if prev.close == prev.open:  # doji — skip
        return 0

    # Bullish sweep: wick below prev low, close recovers above prev open
    if (curr.close > curr.open and
        curr.low < prev.low and
        curr.close > prev.open):
        if strict and curr.close <= prev.high:
            return 0   # strict: must close above prev high
        return 1

    # Bearish sweep: wick above prev high, close drops below prev open
    if (curr.close < curr.open and
        curr.high > prev.high and
        curr.close < prev.open):
        if strict and curr.close >= prev.low:
            return 0   # strict: must close below prev low
        return -1

    return 0
```

## Zone + Sweep Confluence (Best Entry Pattern)
```python
def is_zone_sweep_entry(curr, prev, zone, market_structure, strict=False) -> bool:
    """
    Bullish: price wicks into demand zone, closes back above → zone sweep confirmed.
    """
    sweep = detect_liquidity_sweep(curr, prev, strict)

    if sweep == 1:   # bullish
        zone_touch   = curr.low <= zone.upper and curr.low >= zone.lower - atr * 0.5
        ms_aligned   = market_structure in ('BULLISH', 'BULLISH_IMPULSIVE')
        return zone_touch and ms_aligned

    if sweep == -1:  # bearish
        zone_touch   = curr.high >= zone.lower and curr.high <= zone.upper + atr * 0.5
        ms_aligned   = market_structure in ('BEARISH', 'BEARISH_IMPULSIVE')
        return zone_touch and ms_aligned

    return False
```

## Key Insight: Our Departure Candle IS a Sweep
Our current departure check (`close > open AND zone interaction`) is a weaker version of the bullish sweep. The sweep adds:
1. Requires prior low penetration (stops were swept)
2. Requires recovery above prior candle's open (full reversal)

Upgrade departure gate to explicit sweep check = more selective = fewer but better signals.

## Strict vs Less-Strict
- **Less-strict**: Close recovers above prev open — confirms direction change
- **Strict**: Close recovers above prev HIGH — much stronger confirmation

Use strict mode at our strongest zones (impulsive, quality >= 70). Use less-strict at corrective zones.
