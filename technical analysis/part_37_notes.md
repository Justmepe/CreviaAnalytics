# Part 37 — Sentiment Tilt Meter
**Type:** Indicator | **Verdict:** HIGH EXTRACT — CBR/CPP/VAD formula, CPP for departure timing
**URL:** https://www.mql5.com/en/articles/19137

## Three Core Features + Composite Score
```python
def compute_stm_score(o, h, l, c, atr: float, prev_c_dir: int = 1) -> float:
    """
    o,h,l,c = current bar OHLC
    atr = ATR(14)
    prev_c_dir = +1 if prev bar bullish, -1 if bearish (confidence factor)
    Returns: sentiment score in [-100, +100]
    """
    body  = abs(c - o)
    rng   = h - l or 1e-10
    dirn  = 1 if c > o else -1

    cbr = (body / rng) * dirn                           # body ratio × direction
    cpp = ((c - l) / rng - 0.5) * 2                    # close position [-1, +1]
    vad = (rng / atr - 1.0) * dirn if atr > 0 else 0  # range vs ATR × direction

    mini = np.clip(cbr * 0.4 + cpp * 0.3 + vad * 0.3, -1, 1)

    # Confidence factors
    same_dir = (dirn == prev_c_dir)
    mini *= 1.0 if same_dir else 0.6

    return mini * 100   # scale to [-100, +100]
```

## CPP (Close Position Percent) — Standalone Entry Filter
```python
def close_position_pct(h, l, c) -> float:
    """Where did the bar close within its range? -1.0=at low, +1.0=at high"""
    if h == l: return 0.0
    return ((c - l) / (h - l) - 0.5) * 2

# Departure gate upgrade:
cpp = close_position_pct(h, l, c)
departure_ok = cpp > 0.3 if signal.direction == 'BUY' else cpp < -0.3
```

## Why CPP is Valuable
CPP tells us WHERE in the candle the bar closed — a BUY departure that closes in the bottom 30% of its range is a weak departure, even if close > open. CPP > 0.5 means the bar closed in the top 25% of range = strong bullish commitment.

## Smoothed STM for Gate Use
```python
class SentimentTiltMeter:
    def __init__(self, lookback=20, alpha=0.28):
        self.lookback = lookback
        self.alpha    = alpha
        self._scores  = []
        self._smoothed = 0.0

    def update(self, score: float) -> float:
        self._scores.append(score)
        if len(self._scores) > self.lookback:
            self._scores.pop(0)
        raw = np.mean(self._scores)
        self._smoothed = self.alpha * raw + (1 - self.alpha) * self._smoothed
        return self._smoothed   # -100 to +100 after first bars

    def bullish(self) -> bool: return self._smoothed > 30
    def bearish(self) -> bool: return self._smoothed < -30
```

## Validation
- Tested on Crash 300 and Crash 1000 — both are instruments we trade on Deriv
- VAD (range vs ATR) overlaps with our departure candle LR check from Part 33 — but adds direction context
- CBR (body ratio) is similar to our (close-open)/ATR but normalized to candle range instead of ATR — captures within-candle momentum
