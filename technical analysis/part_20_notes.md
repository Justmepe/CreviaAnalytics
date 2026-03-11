# Part 20 — External Flow (IV) — Correlation Pathfinder
**Series:** Price Action Analysis Toolkit Development
**Type:** EA + Python Flask | **Verdict:** PARTIAL EXTRACT — correlation thresholds, rolling correlation, position sizing gate
**Published:** 2025-05

---

## What It Does
Sends OHLC data for two currency pairs to a Python Flask server, which computes Pearson correlation (overall + 50-bar rolling) and returns a PNG chart plus correlation value. Helps traders understand if two pairs are moving together or independently.

---

## The Key Formula (Pandas, one line)
```python
import pandas as pd

# Rolling correlation — this is what matters for live trading
df['rolling_corr'] = df['pair1_close'].rolling(window=50).corr(df['pair2_close'])
current_corr = df['rolling_corr'].iloc[-1]

# Overall (less useful — use rolling instead)
overall_corr = df['pair1_close'].corr(df['pair2_close'])
```

---

## Correlation Thresholds

| Range | Classification | Our Action |
|---|---|---|
| >= 0.8 | Very strong positive | Don't take both in same direction; halve 2nd position |
| 0.5–0.8 | Moderate positive | Reduce 2nd position by 25% |
| 0.0–0.5 | Weak positive | Full size — mostly independent |
| -0.5–0.0 | Weak negative | Full size — slight hedge |
| <= -0.5 | Strong negative | Full size — natural hedge |

---

## Critical Finding from Test
EUR/USD vs GBP/USD (April 2-9, 2025):
- **Overall correlation**: 0.35 (weakly positive — would say "mostly independent")
- **Recent rolling correlation**: 0.83 (highly correlated — actually moving together!)

**Lesson**: Always use rolling window for live trading decisions. Overall correlation hides regime changes.

---

## What to Keep
- Pearson rolling correlation (50-bar window)
- Correlation thresholds as position sizing rules
- Rolling vs overall distinction

## What to Discard
- HTTP bridge architecture
- Flask server
- MQL5 CopyRates() pattern

---

## Our Superior Version Design

### CorrelationFilter
```python
class CorrelationFilter:
    def __init__(self, window: int = 50, threshold: float = 0.8):
        self.window = window
        self.threshold = threshold

    def compute(self, closes1: np.ndarray, closes2: np.ndarray) -> float:
        """Returns current rolling correlation coefficient."""
        s1 = pd.Series(closes1)
        s2 = pd.Series(closes2)
        return s1.rolling(self.window).corr(s2).iloc[-1]

    def position_size_factor(self, corr: float) -> float:
        """Returns multiplier (0.0-1.0) for position size based on correlation with existing positions."""
        if abs(corr) >= 0.8:   return 0.5    # highly correlated — halve size
        if abs(corr) >= 0.5:   return 0.75   # moderately correlated — reduce
        return 1.0                             # independent — full size
```

### Integration with TradingOrchestrator
```python
# Before executing a signal:
def _apply_correlation_sizing(self, signal, open_positions):
    if not open_positions:
        return signal.position_size  # no correlation to check

    factor = 1.0
    for pos in open_positions:
        corr = self.correlation_filter.compute(
            self.data[signal.symbol]['close'],
            self.data[pos.symbol]['close']
        )
        same_direction = (signal.direction == pos.direction)
        if same_direction:
            factor = min(factor, self.correlation_filter.position_size_factor(corr))

    return signal.position_size * factor
```

---

## Validation for CreviaDeriv
1. **Multi-symbol scan creates correlation risk**: scanning EURUSD, GBPUSD, AUDUSD simultaneously — if all are correlated (common during USD news), we're effectively 3x leveraged on one USD move. Correlation filter prevents this.
2. **Rolling 50 bars on M15 = 12.5 hours** — captures the current intraday correlation regime. Appropriate for our M15 structure analysis.
3. **Overall correlation is misleading** — confirmed by the test data. Our system should never use overall correlation for live decisions.
