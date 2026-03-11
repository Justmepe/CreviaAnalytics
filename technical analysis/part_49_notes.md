# Part 49 — Integrating Trend, Momentum, and Volatility Indicators
**Type:** Dashboard | **Verdict:** MEDIUM — 3-group voting, ADX=25 threshold, RSI28 complement
**URL:** https://www.mql5.com/en/articles/20168

## 3-Group Weighted Vote
| Group | Weight | Indicators |
|---|---|---|
| Trend | 3x | EMA50, EMA200, ADX14 |
| Momentum | 2x | RSI14, RSI28, MACD, Stoch, Momentum14, CCI20, Williams_R |
| Volatility | 1x | ATR14, BB(20,2) |

## ADX Threshold: 25 vs Our 20
```python
# Original: adx > 25 = strong trend
# Our current: adx_sleeping = adx < 20
# Recommendation: adx > 22 as compromise
adx_strong = adx[-1] > 22  # fewer but stronger signals than 20
```

## RSI28 as Macro Complement to RSI14
```python
rsi14 = compute_rsi(closes, 14)  # short-term
rsi28 = compute_rsi(closes, 28)  # medium-term
bullish_momentum = rsi14[-1] > 50 and rsi28[-1] > 50  # both confirm
```

## Key Insight: ATR/BB are Filters, Not Voters
Volatility indicators have no directional bias. Including them in a directional vote dilutes the signal. Our gate chain is correct: VWV as FILTER (energy sufficient?), not as directional voter.
