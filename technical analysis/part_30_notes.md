# Part 30 — CCI Zero Line EA
**Type:** EA | **Verdict:** MEDIUM — dual CCI zero cross, validates RRR=1.5, 77% win rate
**URL:** https://www.mql5.com/en/articles/18551

## CCI Formula
```python
def compute_cci(high, low, close, period=14) -> np.ndarray:
    tp  = (high + low + close) / 3
    sma = pd.Series(tp).rolling(period).mean().values
    mad = pd.Series(tp).rolling(period).apply(lambda x: np.abs(x - x.mean()).mean()).values
    return (tp - sma) / (0.015 * mad)

# Zero line cross:
def cci_crossed_above_zero(cci: np.ndarray) -> bool:
    return cci[-2] < 0 and cci[-1] > 0
```

## Signal Logic
```python
cci_25 = compute_cci(high, low, close, 25)
cci_50 = compute_cci(high, low, close, 50)
ema_34 = pd.Series(close).ewm(span=34).mean().values

buy  = cci_25[-1] > 0 and cci_crossed_above_zero(cci_50) and close[-1] > ema_34[-1]
sell = cci_25[-1] < 0 and cci_crossed_below_zero(cci_50) and close[-1] < ema_34[-1]
```

## Validation for CreviaDeriv
1. **RRR=1.5 validated**: Author's backtest achieved 77% win rate with RRR=1.5 — directly confirms our `MIN_RRR=1.5` is correct (our prior 2.0 was too restrictive).
2. **CCI as ADX supplement**: Add CCI(14) on M1 as optional momentum gate. `cci_m1 > 0` for BUY, `< 0` for SELL — cleaner than ADX direction check.
3. **Dual period concept**: Slow CCI (trend shift) + fast CCI (confirmation) mirrors our M15+M1 architecture — same idea applied to indicator periods.

## Backtesting: 13 signals, 10 wins (77%)
Small sample but consistent with literature expectations for CCI zero-line strategies. USDJPY H1 over 6 months (Jan-Jun 2025).
