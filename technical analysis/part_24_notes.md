# Part 24 — Price Action Quantification Analysis Tool
**Type:** EA | **Verdict:** HIGH EXTRACT — all four candlestick pattern formulas, departure gate upgrade
**URL:** https://www.mql5.com/en/articles/18207

## All Four Formulas (copy-ready)
```python
def classify_candle(o: float, h: float, l: float, c: float,
                    prev_o: float, prev_h: float, prev_l: float, prev_c: float,
                    atr: float,
                    wick_ratio: float = 2.0, doji_ratio: float = 0.1,
                    marubozu_ratio: float = 0.9) -> str:
    body     = abs(c - o)
    rng      = h - l
    top_wick = h - max(o, c)
    bot_wick = min(o, c) - l
    min_body = atr * 0.1   # ATR-normalized minimum

    if body < min_body or rng == 0:
        return 'MICRO'

    # Marubozu (strongest signal)
    if (body >= marubozu_ratio * rng and
        top_wick <= (1 - marubozu_ratio) * rng and
        bot_wick <= (1 - marubozu_ratio) * rng):
        return 'BULLISH_MARUBOZU' if c > o else 'BEARISH_MARUBOZU'

    # Bullish Pin Bar
    if bot_wick >= wick_ratio * body and top_wick < 0.3 * body:
        return 'BULLISH_PIN_BAR'

    # Bearish Pin Bar
    if top_wick >= wick_ratio * body and bot_wick < 0.3 * body:
        return 'BEARISH_PIN_BAR'

    # Engulfing
    prev_body = abs(prev_c - prev_o)
    if (prev_c < prev_o and o <= prev_c and c >= prev_o and body > prev_body):
        return 'BULLISH_ENGULFING'
    if (prev_c > prev_o and o >= prev_c and c <= prev_o and body > prev_body):
        return 'BEARISH_ENGULFING'

    # Doji
    if body <= doji_ratio * rng and top_wick > body and bot_wick > body:
        return 'DOJI'

    # Simple directional
    return 'BULLISH' if c > o else 'BEARISH'
```

## Departure Gate Upgrade
```python
DEPARTURE_STRENGTH = {
    'BULLISH_MARUBOZU': 3,
    'BULLISH_ENGULFING': 2,
    'BULLISH_PIN_BAR':  2,
    'BULLISH':          1,
    'DOJI':             0,
    'MICRO':            0,
}

def passes_departure_gate(pattern: str, direction: str, min_strength: int = 1) -> bool:
    if direction == 'BUY':
        return DEPARTURE_STRENGTH.get(pattern, 0) >= min_strength
    else:  # SELL
        sell_map = {p.replace('BULLISH', 'BEARISH'): s for p, s in DEPARTURE_STRENGTH.items()}
        return sell_map.get(pattern, 0) >= min_strength
```

## Pattern Strengths Summary
| Pattern | Strength | Meaning |
|---|---|---|
| Marubozu | 3 | Full momentum — no hesitation |
| Engulfing | 2 | Overtook prior candle completely |
| Pin Bar | 2 | Rejected key level hard |
| Simple directional | 1 | Just closed in direction (current gate) |
| Doji | 0 | Indecision — skip |
| Micro | 0 | Too small to matter |

## Validation
ATR-normalized min body (`atr * 0.1`) is essential — a 10-point minimum is irrelevant for Crash 300 trading at 9000. Min body must scale with instrument volatility.
