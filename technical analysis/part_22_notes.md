# Part 22 — Correlation Dashboard
**Type:** EA Dashboard | **Verdict:** EXTRACT — returns-based correlation, N×N matrix, AlertThreshold
**URL:** https://www.mql5.com/en/articles/18052

## Key Upgrade vs Part 20: Returns-Based Correlation
```python
# WRONG (Part 20): correlate raw closing prices
r = df['eurusd_close'].rolling(50).corr(df['gbpusd_close'])  # spurious!

# RIGHT (Part 22): correlate returns (% changes)
df['eurusd_ret'] = df['eurusd_close'].pct_change()
df['gbpusd_ret'] = df['gbpusd_close'].pct_change()
r = df['eurusd_ret'].rolling(50).corr(df['gbpusd_ret'])  # stationary, valid
```

## Correlation Matrix (Our Version)
```python
def compute_correlation_matrix(closes: dict, window: int = 50) -> pd.DataFrame:
    """
    closes: {'EURUSD': np.array, 'GBPUSD': np.array, ...}
    Returns: correlation matrix as DataFrame
    """
    returns = {sym: pd.Series(c).pct_change() for sym, c in closes.items()}
    df = pd.DataFrame(returns)
    return df.rolling(window).corr().iloc[-len(closes):]  # latest window only
```

## Position Sizing Integration
```python
def get_correlation_size_factor(new_symbol: str, open_positions: list,
                                 corr_matrix: pd.DataFrame) -> float:
    max_corr = 0.0
    for pos in open_positions:
        try:
            r = abs(corr_matrix.loc[new_symbol, pos.symbol])
            max_corr = max(max_corr, r)
        except KeyError:
            continue
    if max_corr >= 0.8: return 0.5
    if max_corr >= 0.5: return 0.75
    return 1.0
```

## Why Returns > Prices
Raw price correlation is non-stationary — two uptrending assets will always show high correlation even if they move independently at each bar. Returns capture actual co-movement, which is what matters for risk management.
