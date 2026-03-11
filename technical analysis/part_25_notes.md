# Part 25 — Dual EMA Fractal Breaker
**Type:** EA | **Verdict:** LOW-MEDIUM — EMA200 macro filter concept; our StructureEngine is superior
**URL:** https://www.mql5.com/en/articles/18297

## EMA200 as Macro Filter
```python
# Their approach:
ema200 = exponential_moving_average(closes, 200)
ema14  = exponential_moving_average(closes, 14)
macro_bullish = closes[-1] > ema200[-1] and ema14[-1] > ema200[-1]

# Our superior version (already implemented):
macro_bullish = structure.market_structure == MarketStructure.BULLISH

# Optional upgrade: use BOTH
macro_bullish = (structure.market_structure == MarketStructure.BULLISH and
                 closes_m15[-1] > ema200_m15[-1])   # structural + EMA200 agreement
```

## What We Already Do Better
- Fractal breakout = their entry → our zone touch is more precise (has upper/lower bounds)
- EMA200 trend filter → our market_structure is superior (HH/HL/LH/LL, not just price vs MA)
- EMA14 momentum → our EMA3 is more responsive at M1 timescale

## One Useful Addition
EMA200 on M15 as a "maturity confirmation": when market_structure flips BULLISH but price is still below EMA200, the structure break is very fresh. Add as optional quality filter: `ema200_aligned = m15_close > ema200_m15` to boost zone quality score when both agree.
