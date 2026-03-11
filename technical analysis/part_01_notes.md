# Part 01 — Chart Projector
**Series:** Price Action Analysis Toolkit Development  
**Type:** Script | **Verdict:** BUILD | **Depends on:** Nothing (foundation layer)

---

## What It Does
Takes every candlestick from yesterday's session and redraws it on today's chart in ghost form — same price values, today's timestamps. Optionally draws horizontal lines at yesterday's daily High and Low.

The goal is zero-effort context. Instead of scrolling left and mentally comparing two areas of the chart, yesterday sits right behind today. Price respecting yesterday's levels becomes immediately visible.

---

## The Core Insight
Markets have memory. Yesterday's High is where sellers dominated. Yesterday's Low is where buyers stepped in. When today's price revisits those zones, the same crowd faces the same decision again. The ghost overlay makes that dynamic visible at a glance without any indicators.

---

## What Data It Needs
1. **Yesterday's intraday bars** — OHLC per bar, on the active chart timeframe
2. **Today's bar timestamps** — just the `time` field, to know where to plot
3. **Yesterday's D1 bar** — single High and Low for the horizontal S/R lines
4. **Timeframe in seconds** — to calculate each candle body width on the x-axis

---

## Key Logic (One Paragraph)
Loop through today's bars. For each position `i`, grab `yesterday_bars[i % len(yesterday_bars)]` (modulo so it cycles if today has more bars than yesterday). Take that bar's OHLC but plot it at today's timestamp. Draw a wick line from Low to High, and a rectangle from Open to Close. Repeat for every bar. Then draw two horizontal lines at yesterday's daily High and Low across the full chart width.

---

## The 6 Config Parameters
| Param | Default | Our Equivalent |
|---|---|---|
| `GhostColor` | Grey | `ghost_color: rgba(128,128,128,0.4)` |
| `LineStyle` | Dotted | `line_style: "dotted"` |
| `LineWidth` | 2 | `line_width: 2` |
| `ShowHighLow` | true | `show_high_low: true` |
| `ShiftBars` | 0 | `shift_bars: 0` — we handle timezone at data layer instead |
| `ProjectForwardBars` | 100 | `lookback_days: 1` — we extend this to N days |

---

## What to Keep
- The ghost overlay concept — genuinely useful, not gimmicky
- The H/L horizontal lines — arguably the most useful output of this whole tool
- The modulo cycling logic — elegantly handles sessions of unequal length
- All 6 config params (adapted to our schema)

## What to Discard
- All MQL5-specific rendering APIs (ObjectCreate, OBJ_TREND, OBJ_HLINE etc.)
- All MQL5 data APIs (iBarShift, iTime, iOpen, iHigh, iLow, iClose)
- The single-run script model (we build live refresh instead)

## What to Improve
- **Transparency** — original has no alpha. Add `rgba` support to ghost colour.
- **Live refresh** — original runs once. Ours refreshes on each new bar close.
- **Multi-day lookback** — original is hardcoded to 1 day. Make it configurable (1–5).
- **Labelled H/L lines** — original draws unlabelled lines. Add price text directly on line.
- **Timezone handling** — original uses `ShiftBars` as a manual workaround. We fix this at the data layer by normalising all sessions to UTC before the tool sees the data.

---

## Architecture This Tool Reveals We Need
This is Part 1 of 65 and it tells us immediately what the foundation must be:

```
BrokerDataAdapter   ← get_ohlc(symbol, timeframe, from, to) — EVERY tool needs this
SessionManager      ← what is "yesterday"? handles timezones, gaps, holidays
ChartProjector      ← pure logic, no rendering
ChartRenderer       ← draw candles, lines, labels — broker & library agnostic
ToolConfig          ← shared config schema all 65 tools extend
```

Build the **BrokerDataAdapter** first. Start with a `CSVAdapter` that reads local OHLC files so you can test every tool without a live broker connection. All 65 parts feed from this one interface.

---

## Notes
- The article's animated GIF (Fig 4) is the clearest way to understand what this looks like in practice: https://c.mql5.com/2/100/chart_projector_gif.gif
- `ShiftBars` is secretly a timezone offset parameter. The author needed it because different MT5 brokers open the daily candle at different times. We make this a first-class concern in SessionManager instead.
- The original warns: *"use for educational purposes only, do not experiment with real money"* — sensible disclaimer for the whole series.
