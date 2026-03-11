# Part 13 — RSI Sentinel Tool
**Series:** Price Action Analysis Toolkit Development
**Type:** Indicator / EA | **Verdict:** EXTRACT — 4-type divergence framework, swing-based RSI comparison, accuracy reporting
**Published:** 2025-02-14

---

## What It Does
Detects all four types of RSI divergence in real time using swing-based comparison of RSI vs price direction. Draws arrows at signal bars. Tracks and reports accuracy (regular vs hidden separately) by checking price direction N bars after each signal.

---

## The Four Divergence Types

| Type | Price | RSI | Meaning |
|---|---|---|---|
| Regular Bullish | Lower Low | Higher Low | Reversal up — momentum weakening before price |
| Regular Bearish | Higher High | Lower High | Reversal down — momentum weakening before price |
| Hidden Bullish | Higher Low | Lower Low | Continuation up — pullback with strong RSI |
| Hidden Bearish | Lower High | Higher High | Continuation down — pullback with weak RSI |

**Key insight**: Regular = reversal setup. Hidden = continuation setup. Both are legitimate signals in different market contexts. We currently only look for reversals (zone touch = potential reversal) — hidden divergence adds the continuation/retest perspective.

---

## Detection Algorithm
```python
# 1. Compute RSI(14) for last lookback bars
# 2. Find significant swing lows/highs:
def is_swing_low(lows, i, left, right, min_diff_pct):
    return (lows[i] == min(lows[i-left:i+right+1]) and
            (lows[i-1] - lows[i]) / lows[i] >= min_diff_pct)

def is_swing_high(highs, i, left, right, min_diff_pct):
    return (highs[i] == max(highs[i-left:i+right+1]) and
            (highs[i] - highs[i+1]) / highs[i] >= min_diff_pct)

# 3. Take two most recent swing lows (for bullish) or swing highs (for bearish)
# 4. Classify:
rsi_diff = abs(rsi[s1] - rsi[s2])
if rsi_diff >= min_rsi_diff:
    if price[s1] < price[s2] and rsi[s1] > rsi[s2]:  # regular_bullish
    if price[s1] > price[s2] and rsi[s1] < rsi[s2]:  # regular_bearish
    if price[s1] > price[s2] and rsi[s1] < rsi[s2]:  # hidden_bullish
    if price[s1] < price[s2] and rsi[s1] > rsi[s2]:  # hidden_bearish

# 5. Deduplicate: skip if < min_bars_between_signals since last signal
```

---

## Config (Recommended Overrides)

| Param | Original | Our Version |
|---|---|---|
| `rsi_period` | 14 | 14 |
| `swing_left` | 1 | 2–3 |
| `swing_right` | 1 | 2–3 |
| `lookback` | 100 | 200 |
| `min_bars_between_signals` | 1 | 8–10 |
| `min_swing_diff_pct` | 0.05% | 0.05% |
| `min_rsi_diff` | 1.0 | 2.0 |

---

## What to Keep
- All 4 divergence types — complete framework, don't drop any
- Swing-based comparison (not tick-level) — noise-resistant and meaningful
- `min_rsi_diff` filter — prevents false divergence from tiny RSI moves
- `min_swing_diff_pct` filter — percentage-based, works across instruments
- Separate regular vs hidden accuracy tracking — they have different reliability profiles

## What to Discard
- `min_bars_between_signals = 1` — too loose; use 8–10
- Single-timeframe only — need H1 divergence context + M15 entry alignment
- No SL/TP — signals only in original; we pair with zone and structural levels

## What to Improve
- Use as **zone quality filter**: demand zone + regular bullish divergence = bonus confidence (+20 to zone quality score)
- **Hidden divergence for retest setups**: when price retests a zone after BoS, hidden bullish divergence confirms the continuation
- **Divergence strength scoring**: bars between the two swings (wider = stronger) + RSI delta magnitude
- Require divergence confirmation **within zone proximity**: divergence that forms 50 bars before zone touch is less relevant

---

## Our Superior Version Design

### DivergenceDetector (pure function)
```python
@dataclass
class DivergenceSignal:
    type: str          # 'regular_bullish', 'regular_bearish', 'hidden_bullish', 'hidden_bearish'
    bar_idx: int
    price: float
    rsi_at_signal: float
    swing_gap_bars: int   # wider = stronger
    rsi_delta: float      # magnitude of RSI divergence
    strength_score: float # swing_gap * rsi_delta (composite)

def detect_divergences(
    rsi: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    config: DivergenceConfig
) -> List[DivergenceSignal]:
    swing_lows  = find_swings(lows,  config.left, config.right, config.min_swing_diff_pct, is_low=True)
    swing_highs = find_swings(highs, config.left, config.right, config.min_swing_diff_pct, is_low=False)
    signals = []
    # compare last two swing_lows → bullish types
    # compare last two swing_highs → bearish types
    return signals
```

### Integration with CreviaDeriv Gate Chain
```python
# In EntryEngine.scan_for_entries():
divergences = detect_divergences(rsi, highs, lows, div_config)
recent_divs = [d for d in divergences if abs(d.bar_idx - current_bar) <= 10]

# Zone quality upgrade:
if zone.type == 'DEMAND' and any(d.type == 'regular_bullish' for d in recent_divs):
    zone_quality_bonus = +20
if zone.type == 'DEMAND' and any(d.type == 'hidden_bullish' for d in recent_divs):
    zone_quality_bonus = +10   # continuation context

# Gate addition (optional high-conviction mode):
div_confirmed = any(d for d in recent_divs if d.type in ('regular_bullish','hidden_bullish'))
```

---

## Validation for CreviaDeriv
1. **Swing detection is already in StructureEngine** — our trendline-first fractal detection is the "proper implementation" the article points toward (article explicitly flags their swing detection as needing improvement)
2. **min_swing_diff_pct = 0.05%** validates percentage-based filtering (vs fixed pip) — consistent with ATR-normalized approach throughout our system
3. **Regular + hidden divergence together** cover both our reversal trades (zone touch reversals) AND continuation retests (zone retest after BoS) — complete divergence coverage for our trade types
4. **Hidden divergence confirms our HL identification**: when M15 makes a Higher Low and RSI shows lower low, this is exactly the "strong trend continuation" confirmation we want before a BUY

---

## CreviaDeriv Zone Quality Score Upgrade

Current:
```python
zone_strength = 80 if is_impulsive else 40  # from ZoneIdentifier
```

Proposed:
```python
zone_strength = base_strength  # 80 impulsive / 40 corrective
if recent_regular_divergence_matches_direction:   zone_strength += 20
if recent_hidden_divergence_matches_direction:    zone_strength += 10
if multi_tf_divergence_agrees:                    zone_strength += 15
# Max possible: 80 + 20 + 10 + 15 = 125 → normalize or use as ranking
```
