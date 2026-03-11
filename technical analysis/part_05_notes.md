# Part 05 — Volatility Navigator EA
**Series:** Price Action Analysis Toolkit Development
**Type:** Expert Advisor | **Verdict:** EXTRACT — ATR SL/TP pattern + confluence gate architecture
**Published:** 2024-12-16 | **Depends on:** Parts 1-4 (uses BrokerDataAdapter, ATRCalculator)

---

## What It Does
Generates buy/sell signals when RSI, Bollinger Bands, and ATR all simultaneously confirm the same direction. On a signal, draws three horizontal lines on the chart: entry (green), stop loss (red), take profit (blue). Plays an audio alert.

Does NOT execute trades — signals only.

---

## The Core Insight
**Three-indicator confluence = noise filter.** Require all three independent measurements (momentum via RSI, statistical extreme via BB, volatility sufficiency via ATR) to agree before acting. Any two agreeing is not enough.

This is the conceptual foundation of CreviaDeriv's entry gate chain: zone touch → EMA3 cross → ADX rising → VWV → departure. Same pattern, better indicators for structure-based trading.

---

## The Series Pivot Point
Parts 1-4 were analytical/display tools. **Part 5 is the first tool in the series that generates actual trading signals with entry, SL, and TP levels.** The series shifts here from "understand the market" to "tell me when and where to trade."

---

## Signal Logic

### Buy
```
close < bb_lower   AND   rsi < 30   AND   atr > threshold
entry = close
sl    = entry - (atr × 1.5)
tp    = entry + (atr × 1.5 × 2)   ← 2:1 RR
```

### Sell
```
close > bb_upper   AND   rsi > 70   AND   atr > threshold
entry = close
sl    = entry + (atr × 1.5)
tp    = entry - (atr × 1.5 × 2)   ← 2:1 RR
```

---

## The 8 Config Parameters
| Param | Default | Our Equivalent |
|---|---|---|
| `rsi_period` | 14 | `rsi_period: 14` in IndicatorConfig |
| `overbought_level` | 70.0 | Gate threshold (we use 60/40 instead) |
| `oversold_level` | 30.0 | Gate threshold |
| `bb_period` | 20 | Not used (we use EMA3 not BB) |
| `bb_deviation` | 2.0 | Not used |
| `atr_period` | 14 | `atr_period: 14` in ENTRY_CONFIG |
| `atr_multiplier` | 1.5 | Our floor: `min_sl = 2 × ATR` |
| `signal_sound` | alert.wav | NotificationService.send() |

---

## What to Keep
- **Three-indicator confluence gate** — correct architecture for entry filtering
- **ATR-based SL formula** — `SL = entry ± (ATR × multiplier)` is the right approach
- **2:1 minimum RR constraint** — we use MIN_RRR=1.5, same philosophy
- **Signals-only design** — no auto-execution, human/system decides
- **Green/Red/Blue colour convention** for Entry/SL/TP

## What to Discard
- RSI + BB as entry triggers — we use zone touch instead
- Fixed ATR×1.5 SL — we use structural swing anchor with ATR floor
- Fixed 2:1 TP — we use 4 TP targets
- MQL5 rendering APIs — replaced by matplotlib/ChartRenderer
- Audio alert.wav — replaced by NotificationService

## What to Improve
- Replace RSI+BB trigger with supply/demand zone interaction
- Replace fixed ATR SL with structural SL (nearest external swing), ATR as floor only
- Replace single TP with P1=opposing zone, P2=swing, P3=leg×1.5, P4=2:1 RR
- Add M15 structure context before M1 entry
- Add VWV (velocity) gate — no volume confirmation in this tool
- Add position management: trail SL after P1, partial close at each target

---

## Architecture This Tool Reveals
```
RSICalculator         ← rsi(prices, period) → series
BollingerBands        ← bb(prices, period, deviation) → {upper, mid, lower}
SignalEngine          ← evaluate(rsi, bb, atr, close, config) → Signal | None
LevelDrawer           ← draw_entry_sl_tp(entry, sl, tp, direction) → chart
NotificationService   ← already defined in Part 4, reused here
```

---

## Validation for CreviaDeriv Design
1. **ATR SL floor confirmed**: Industry standard is `SL = entry ± (ATR × N)`. Our `min_sl = 2×ATR` floor in `_calculate_precision_sl()` aligns perfectly.
2. **Confluence gate confirmed**: 3-condition AND gate before entry is correct. Our 5-gate chain (zone, EMA, ADX, VWV, departure) is more rigorous — the right direction.
3. **2:1 RR validated**: Standard minimum. Our `MIN_RRR=1.5` is slightly more permissive — still safe because our structural TPs often achieve 2:1+ naturally.
4. **Structural SL is strictly better**: This tool's raw ATR SL has no structural anchor. Our approach: find nearest external swing, then verify it's ≥2×ATR away. Best of both worlds.

---

## Notes
- Tested on Crash 900 and Volatility 500 synthetic indices (Deriv/Boom-Crash family)
- Author calls it "Tool Number 6 in the Lynnchris Tool Chest" — the "Tool Chest" numbering doesn't always match the article part number
- The 2:1 RR (TP = 2 × SL distance) is hardcoded — not configurable in the original. Our system should always make RR_ratio configurable (MIN_RRR in ENTRY_CONFIG).
