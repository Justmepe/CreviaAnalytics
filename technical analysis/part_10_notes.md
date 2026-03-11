# Part 10 — External Flow (II) VWAP
**Series:** Price Action Analysis Toolkit Development
**Type:** MQL5 EA + Python Flask | **Verdict:** EXTRACT — VWAP formula, two-tier S/R, confirmation interval
**Published:** 2025-01-30

---

## What It Does
Extends the bridge from Part 9 with a proper VWAP calculation replacing the naive average. Collects 150 H1 bars, calculates VWAP in Python via Pandas, returns signal (BUY/SELL if close above/below VWAP) plus major and minor S/R levels.

---

## The VWAP Formula (Keep This Exactly)
```python
df['typical'] = (df['high'] + df['low'] + df['close']) / 3
df['vwap']    = (df['typical'] * df['volume']).cumsum() / df['volume'].cumsum()
current_vwap  = df['vwap'].iloc[-1]

# Signal
if close > current_vwap:  signal = 'BUY'
elif close < current_vwap: signal = 'SELL'
else:                      signal = 'NEUTRAL'
```

---

## Two-Tier S/R (Simple but Useful Framework)
```python
# Major (absolute window boundaries)
major_support    = df['low'].min()
major_resistance = df['high'].max()

# Minor (recent rolling average)
minor_support    = df['low'].rolling(3).mean().iloc[-1]
minor_resistance = df['high'].rolling(3).mean().iloc[-1]
```
**Our improvement**: replace minor S/R (rolling average of 3 bars) with zone-based S/R from ZoneIdentifier. More structurally meaningful.

---

## Confirmation Interval (Important Pattern)
```
signal must appear for N consecutive periods before alerting
```
This is the same concept as our departure candle gate — require the signal condition to persist, not just flash once. Prevents acting on transient touches.

---

## VWAP vs. Our VWV

| | VWAP | Our VWV |
|---|---|---|
| **What it measures** | Where price traded weighted by volume | How much velocity per bar weighted by volume |
| **Purpose** | Fair value reference (WHERE) | Energy for a move (HOW FAST) |
| **Scale** | Price level | Normalized score |
| **Synthetic index support** | Poor (tick volume ≠ real volume) | Yes (range_atr energy source) |
| **Use case** | Directional filter | Entry gate |

**Best of both worlds**: VWAP as directional filter (is price above/below fair value?) + VWV as energy gate (is there enough momentum?).

---

## Our Superior Version Design

### VWAP as a Filter, Not a Signal
```python
# Wrong (what Part 10 does): VWAP alone = signal
signal = 'BUY' if close > vwap else 'SELL'

# Right (what we do): VWAP as one filter in a chain
if close > vwap:     allow_buy_setups = True   # directional context
if zone_interaction: gate_b_pass = True         # structural trigger
if ema_cross:        gate_c_pass = True         # momentum confirmation
if adx_rising:       gate_d_pass = True         # trend energy
if vwv_score > 0.3:  gate_f_pass = True         # velocity confirmation
if departure_candle: gate_g_pass = True         # entry timing
# All gates → signal with SL/TP
```

### Session-Anchored VWAP (Better Than Rolling Window)
Reset VWAP at each session open:
```python
def session_vwap(df, session_open_time):
    session_data = df[df.index >= session_open_time].copy()
    session_data['typical'] = (session_data['high']+session_data['low']+session_data['close'])/3
    return (session_data['typical']*session_data['volume']).cumsum() / session_data['volume'].cumsum()
```

---

## Validation for CreviaDeriv
1. **VWAP formula is correct**: `(H+L+C)/3 × Volume` cumulative sum — industry standard. Our VWV extends this concept.
2. **Two-tier S/R is the right framework**: Major + Minor hierarchy. We do this with supply/demand zones (major) and session H/L (minor).
3. **Confirmation interval = departure candle**: Both enforce that a condition must PERSIST before acting, not just flash momentarily.
4. **150-bar lookback is adequate**: We use 672-bar window for M15 structure, which is 168 hours. Their 150 H1 bars = 150 hours. Similar order of magnitude.
