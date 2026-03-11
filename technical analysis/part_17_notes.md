# Part 17 — TrendLoom EA Tool
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor (Analysis) | **Verdict:** PARTIAL EXTRACT — voting architecture, supermajority threshold concept
**Published:** 2025-03

---

## What It Does
Three timeframes each vote on directional bias based on close vs SMA(50). Sum votes. Supermajority (2-of-3) = signal. GUI panel with 7 preset strategy timeframe combinations.

---

## Voting Algorithm
```python
def multi_tf_vote(bars_by_tf: dict, sma_period: int = 50, threshold: int = 2) -> tuple:
    """
    bars_by_tf: {'M15': bars_array, 'H1': bars_array, 'H4': bars_array}
    Returns: (direction, score) where score = -3 to +3
    """
    total = 0
    for tf, bars in bars_by_tf.items():
        closes = [b.close for b in bars]
        sma = sum(closes[-sma_period:]) / sma_period
        current_close = closes[-2]  # last completed candle
        if current_close > sma:
            total += 1
        elif current_close < sma:
            total -= 1
        # else: neutral, no vote

    if total >= threshold:
        return 'BUY', total
    elif total <= -threshold:
        return 'SELL', total
    else:
        return 'NEUTRAL', total
```

---

## 7 Strategy TF Presets

| Strategy | TF1 | TF2 | TF3 |
|---|---|---|---|
| Short-Term | M1 | M5 | M15 |
| Scalping/Intraday | M5 | M15 | H1 |
| Swing | M15 | H1 | H4 |
| Trend | H1 | H4 | D1 |
| MTF Confirmation | H1 | H4 | W1 |
| Scalp/Mid | M5 | H1 | D1 |
| Long-Term | H1 | D1 | W1 |

---

## Key Architectural Insight: Gate Chain as Voter

Our current system uses hard AND logic:
```python
# Current: strict AND gate
if zone_touch AND ema_cross AND adx_rising AND vwv_strong AND departure:
    fire_signal()
```

Alternative architecture from TrendLoom:
```python
# Alternative: voting/scoring gate chain
score = 0
if zone_touch:    score += 2    # weighted — zone is most important
if ema_cross:     score += 1
if adx_rising:    score += 1
if vwv_strong:    score += 1
if departure:     score += 1

if score >= 5:    # all gates pass
    fire_signal(confidence='HIGH', size_multiplier=1.0)
elif score >= 4:  # one gate missing
    fire_signal(confidence='MEDIUM', size_multiplier=0.75)
# else: skip
```

**Why this matters**: Our current chain rejects a signal if ADX is at 19.9 instead of 20. Scoring allows "mostly aligned" signals with reduced position size.

---

## What to Keep
- Voting architecture (score-based, not binary)
- Supermajority threshold (2-of-3 for TF alignment)
- 7 preset TF groupings as a conceptual framework
- Score as confidence measure → position size scaling

## What to Discard
- SMA(50) as the vote trigger — too crude
- GUI button panel
- On-demand execution
- No SL/TP

## What to Improve
- Replace SMA with structural indicators in each vote
- Add weighted votes: higher TF = higher weight
- Apply scoring to gate chain for graduated confidence
- Map confidence score to position size multiplier

---

## Our Superior Version Design

### MultiTFVoter (pluggable indicator)
```python
class MultiTFVoter:
    """
    Generic multi-TF voter. Pass any indicator function.
    """
    def __init__(self, indicator_fn, timeframes: list, threshold: int = 2,
                 weights: dict = None):
        self.indicator_fn = indicator_fn
        self.timeframes = timeframes
        self.threshold = threshold
        self.weights = weights or {tf: 1 for tf in timeframes}

    def vote(self, data_by_tf: dict) -> tuple:
        total_score = 0
        max_score = sum(self.weights.values())
        for tf in self.timeframes:
            signal = self.indicator_fn(data_by_tf[tf])  # returns +1/-1/0
            total_score += signal * self.weights[tf]
        normalized = total_score / max_score   # -1.0 to +1.0
        direction = ('BUY' if total_score >= self.threshold else
                     'SELL' if total_score <= -self.threshold else 'NEUTRAL')
        return direction, total_score, normalized
```

### Gate Chain Confidence Scoring
```python
def compute_signal_confidence(gates: dict) -> float:
    """
    gates = {'zone': True, 'ema': True, 'adx': False, 'vwv': True, 'departure': True}
    Returns 0.0–1.0 confidence score.
    """
    weights = {'zone': 3, 'ema': 2, 'adx': 1, 'vwv': 1, 'departure': 2}
    max_score = sum(weights.values())
    actual = sum(weights[k] for k, v in gates.items() if v)
    return actual / max_score

# Example: all pass → 9/9 = 1.0; ADX fails → 8/9 = 0.89 (still fire at 0.75)
```

---

## Validation for CreviaDeriv
1. **Supermajority threshold is realistic**: In active trend transitions, one TF will lag. Requiring 2/3 agreement (not 3/3) captures more true signals while filtering noise.
2. **Scoring > binary**: Our hard AND gate creates cliff-effect rejections. A gate confidence score allows position sizing to reflect uncertainty.
3. **SMA(50) alone is weak validation**: The article confirms that SMA-only signals need supplemental confirmation (author says so explicitly). Our structural zone + indicator confluence is strictly better.
4. **7 presets confirm our TF architecture**: "Swing Trading" preset = M15+H1+H4 — validates our M15 as the primary structural timeframe.
