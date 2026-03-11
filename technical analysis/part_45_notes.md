# Part 45 — Creating a Dynamic Level-Analysis Panel
**Type:** EA Analysis | **Verdict:** MEDIUM — zone touch probability, breakout vs reversal classification
**URL:** https://www.mql5.com/en/articles/19842

## Zone Touch Probability (Upgrade for ZoneIdentifier)
```python
def compute_zone_touch_probability(bars, zone_upper, zone_lower, atr,
                                    lookback=500) -> dict:
    """Compute historical bullish/bearish touch and breakout rates for a zone."""
    tolerance = atr * 0.3
    bull_touch = bear_touch = bull_break = bear_break = 0

    for i in range(lookback, len(bars)):
        bar = bars[i]
        touched_zone = (bar.high >= zone_lower - tolerance and
                        bar.low  <= zone_upper + tolerance)
        if not touched_zone: continue

        if bar.close > zone_upper:     bull_touch += 1
        elif bar.close < zone_lower:   bear_touch += 1

        if (bars[i-1].close < zone_lower and bar.close < zone_lower - atr*0.2):
            bear_break += 1
        elif (bars[i-1].close > zone_upper and bar.close > zone_upper + atr*0.2):
            bull_break += 1

    total_touches = bull_touch + bear_touch or 1
    total_breaks  = bull_break + bear_break or 1
    return {
        "bull_touch_pct": bull_touch / total_touches,
        "bear_touch_pct": bear_touch / total_touches,
        "bull_break_pct": bull_break / total_breaks,
        "bear_break_pct": bear_break / total_breaks,
        "bias": "SUPPORT" if bull_touch > bear_touch else "RESISTANCE"
    }

# Add to zone quality scoring:
# if zone_touch_prob["bull_touch_pct"] > 0.70: zone.quality += 15
```
