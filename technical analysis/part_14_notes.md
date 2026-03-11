# Part 14 — Parabolic Stop and Reverse Tool
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor | **Verdict:** EXTRACT — multi-bar confirmation pattern, SAR gap check, pending signal mechanism
**Published:** 2025-02

---

## What It Does
Detects Parabolic SAR reversals by requiring N prior bars confirming the previous trend BEFORE accepting the flip as a valid signal. A "pending mechanism" then monitors the next 3 bars to see if price confirms the expected SAR level. Draws Wingdings arrows on signal.

---

## SAR Dot Semantics
```
SAR dot BELOW price → uptrend (bullish SAR)
SAR dot ABOVE price → downtrend (bearish SAR)
Dot FLIPS side      → reversal signal candidate
```

---

## Signal Logic
```python
def check_buy_signal(sar, opens, closes, config):
    # Current bar: bullish body AND SAR below price (bullish flip)
    if closes[0] <= opens[0]: return False          # not bullish bar
    if sar[0] >= closes[0]:   return False          # SAR still above

    # Prior N bars: must have been bearish with SAR above (confirming prior downtrend)
    for i in range(1, config.min_consecutive_dots + 1):
        if closes[i] >= opens[i]:   return False    # wasn't bearish
        if sar[i] <= closes[i]:     return False    # SAR wasn't above

    # Gap check: SAR dot spacing not erratic
    gap_pct = abs(sar[0] - sar[1]) / closes[0]
    if gap_pct > config.max_dot_gap_pct / 100:      return False

    return True  # valid signal candidate

# Same logic inverted for SELL
```

---

## Pending Signal Mechanism
```python
pending_level = sar[0]   # capture SAR at flip bar
pending_dir   = 'BUY'
pending_bars_left = 3

# Each subsequent bar:
if direction == 'BUY' and low <= pending_level:
    confirm_signal()
elif pending_bars_left == 0:
    warn("Possible fake signal — price did not reach SAR level")
```

---

## Config Comparison

| Param | Original | Standard PSAR | Our Version |
|---|---|---|---|
| `SARStep` | 0.1 | 0.02 | 0.02 |
| `SARMaximum` | 1.0 | 0.2 | 0.2 |
| `MinConsecutiveDots` | 2 | — | 3 |
| `MaxDotGapPercentage` | 1.0% | — | 1.0% |

Author's 0.1/1.0 is 5× more aggressive than standard — SAR moves very fast, detects more flips but generates more noise. Standard 0.02/0.2 for higher-quality structural reversals.

---

## What to Keep
- **Multi-bar prior-trend confirmation** — N bars in prior direction validates the setup (prevents acting on first SAR tick)
- **Gap consistency check** — SAR dot spacing % filter is a new filter type: "indicator behaving normally" validation
- **Pending + timeout** — capture expected level, monitor N bars, warn on timeout (fake signal detection)
- **Fake signal warning** — explicit feedback when a signal fails to follow through

## What to Discard
- SAR as primary entry trigger (too lagging — use it for trailing SL instead)
- 3-bar pending window (too short for M15 — 5–8 bars on M1 more appropriate)
- No SL/TP
- Aggressive 0.1/1.0 settings

## What to Improve
- **Use SAR for trailing stop management** after P1 is hit: trail SL to SAR value, which naturally accelerates with the trend
- **SAR + zone confluence**: SAR flips bullish while price is inside demand zone = powerful reversal confirmation
- **ATR-normalized gap check**: `abs(sar[i] - sar[i-1]) / ATR` instead of % of close — works consistently across instruments

---

## Our Superior Version Design

### SAR as Trailing SL (Primary Use Case)
```python
class SarTrailingStop:
    def __init__(self, step=0.02, maximum=0.2):
        self.sar = PsarCalculator(step, maximum)

    def update_sl(self, trade, highs, lows):
        """After P1 hit, trail SL to current SAR value."""
        current_sar = self.sar.compute(highs, lows)[-1]
        if trade.direction == 'BUY':
            new_sl = max(trade.current_sl, current_sar)
        else:
            new_sl = min(trade.current_sl, current_sar)
        return new_sl
```

### SAR + Zone Confluence Signal
```python
def check_sar_zone_confluence(zone, sar, opens, closes, config):
    """SAR flip that occurs while inside a demand/supply zone = high-conviction."""
    if zone.type == 'DEMAND':
        sar_flipped_bullish = check_buy_signal(sar, opens, closes, config)
        price_in_zone = zone.lower <= closes[0] <= zone.upper
        return sar_flipped_bullish and price_in_zone
    # mirror for SUPPLY
```

---

## Validation for CreviaDeriv
1. **Multi-bar confirmation = departure candle concept**: both enforce "condition must persist N bars, not flash once." Our departure candle gate is the correct implementation.
2. **SAR as trailing stop is better than as entry**: SAR is inherently a trailing indicator (it follows price with acceleration). After P1, it's perfect for dynamic stop management.
3. **Gap check generalizes**: any indicator metric can have a "rate of change % threshold" to detect when it's behaving erratically. Add to VWV: if VWV jumps > 3× previous, it's a spike not a trend.
4. **Pending signal = zone proximity**: "wait up to N bars for price to reach the expected level" is exactly how zone interaction works in our EntryEngine.
