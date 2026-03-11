# Part 08 — Metrics Board
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor (Interactive Dashboard) | **Verdict:** REFERENCE — extract the 6 metrics as a data contract
**Published:** 2025-01-23

---

## What It Does
Creates an on-chart interactive panel with 6 clickable buttons. Each button fetches and displays specific market metrics for the H1 timeframe on demand. No signals, no trades — pure analytical display tool.

---

## The Core Insight
**On-demand vs. always-on**: Instead of a dashboard that constantly streams data, the trader asks for what they need when they need it. Reduces noise, reduces cognitive load. The 6 metrics chosen are the fundamental analytical pillars every price action trader needs:

1. **High/Low** — price structure boundary
2. **Volume** — participation level
3. **Trend MA** (14-period) — short-term direction
4. **Volatility ATR** (14-period) — range expansion/contraction
5. **Moving Average** (50-period) — medium-term trend
6. **Support/Resistance** — previous bar's high/low as near-term levels

---

## What the 6 Metrics Tell Us (and What They Miss)

| Metric | What it tells you | What it misses |
|--------|-------------------|----------------|
| H1 High/Low | Current bar range | Multi-session context |
| Volume | Activity level | Whether volume is high or low vs. average |
| 14-period MA | Short momentum direction | Slope and acceleration |
| ATR(14) | Volatility magnitude | Direction of volatility change |
| 50-period MA | Trend direction | Trend strength (needs ADX) |
| Prev H/L as S/R | Nearest structural levels | Zone quality, confluence with other timeframes |

---

## Config
- Dialog position: x=10, y=10 (pixels from chart corner)
- Panel: 350px × 500px
- 7 buttons (6 analysis + close): 300px wide, 30px high, 15px gap

---

## Our Superior Version Design
The Metrics Board concept is right but limited by:
1. Only H1 — we need M1, M15, H1 hierarchy
2. No averaging — ATR current bar vs. 5-day average is far more useful
3. No alerts — just silent display
4. Single symbol — we need multi-symbol scan

### Our MetricsSnapshot Object
```python
@dataclass
class MetricsSnapshot:
    symbol: str
    timestamp: datetime
    # Structure
    h1_high: float
    h1_low: float
    m15_high: float
    m15_low: float
    # Trend
    sma_50_h1: float           # medium-term trend direction
    sma_14_m15: float          # short-term bias
    market_structure: str      # BULLISH/BEARISH/RANGING (from StructureEngine)
    # Volatility
    atr_14_m15: float          # our SL floor reference
    atr_14_h1: float           # macro volatility context
    atr_5d_avg: float          # is today's ATR high or low vs. history?
    # Volume/Velocity
    vwv_score: float           # VWV from our VelocityEngine
    session_volume_pct: float  # how far through session volume-wise
    # S/R
    prev_h1_high: float        # resistance
    prev_h1_low: float         # support
    demand_zones: List[Zone]   # from ZoneIdentifier
    supply_zones: List[Zone]   # from ZoneIdentifier
    # Risk
    lot_size: float            # pre-calculated for 1% risk at current ATR SL
```

### Improvement Priorities (in order)
1. Add StructureEngine market_structure — tells you BULLISH/BEARISH/RANGING, more useful than SMA direction
2. Add ATR vs. 5-day average — "ATR is 2.3x its 5-day average" is far more actionable than "ATR=0.00245"
3. Add VWV score — our velocity metric. Is there energy for a move right now?
4. Add Zone context — are we near a demand or supply zone? Distance in pips and ATR multiples
5. Add multi-symbol scan — run MetricsSnapshot across all configured symbols every 15 minutes

---

## Architecture
```
MetricsCalculator
    get_metrics(symbol, timeframes=['M15', 'H1']) -> MetricsSnapshot
    ├── BrokerDataAdapter.get_ohlc()       # raw bars
    ├── ATRCalculator.compute()            # volatility
    ├── StructureEngine.analyze()          # market structure
    ├── ZoneIdentifier.find_zones()        # S/R zones
    └── VelocityEngine.analyze()          # VWV score
```

---

## Validation for CreviaDeriv
- Confirms the 6 metric pillars are standard: High/Low, Volume, Trend, Volatility, S/R, MA
- Confirms H1 as the right timeframe for macro context
- Confirms ATR(14) as the industry standard volatility measure
- Our version adds structure + zones + VWV — strictly superior
