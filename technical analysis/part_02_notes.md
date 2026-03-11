# Part 02 — Analytical Comment Script
**Series:** Price Action Analysis Toolkit Development  
**Type:** Script | **Verdict:** BUILD | **Depends on:** Part 1

---

## What It Does
Fetches yesterday's full OHLCV from the D1 bar and today's partial volume, then produces two things simultaneously:

1. **Two horizontal lines on the chart** — green at yesterday's Low (support), red at yesterday's High (resistance)
2. **A text data panel on the chart** — a vertical table showing Open, Close, High, Low, both volumes, support, resistance, and three lines of written commentary about market direction

The commentary engine is simple but useful: it reads yesterday's close vs open (Bullish / Bearish / Neutral), compares today's volume to yesterday's, and outputs a plain-English sentence for each.

---

## How This Connects to Part 1

This is the second layer on the same foundation. Part 1 gave us the *visual* — ghost candles and H/L lines. Part 2 gives us the *analytical text layer* — structured data and commentary sitting beside that visual. Together they form a complete daily briefing system.

The S/R lines in Part 2 are **identical** to Part 1's `ShowHighLow=true` output. Both parts draw horizontal lines at the same two prices. This is the first sign of duplicated logic in the series — and the signal that we need a shared `DailyContextProvider` module that both tools draw from.

---

## What Data It Needs
1. **Yesterday's D1 bar** — Open, High, Low, Close, Volume (adds Volume to what Part 1 needed)
2. **Today's D1 bar** — Volume only (partial, grows during the session)

That's it. Simplest data requirement in the series.

---

## The Classification Logic

### Market Nature (from close vs open)
```
close > open  →  "Bullish"
close < open  →  "Bearish"
close == open →  "Neutral"
```
Straightforward but limited — no magnitude, no context. A 1-pip bullish close and a 200-pip one both say "Bullish".

### Volume Sentiment
```
today_vol > prev_vol  →  "Bullish sentiment may continue"
today_vol < prev_vol  →  "Bearish sentiment may follow"
today_vol == prev_vol →  "Sentiment uncertain"
```
**Critical flaw:** This comparison is time-dependent. At 9am, today's volume will almost always be less than yesterday's *full day* volume — the script will read "Bearish" for almost every morning session regardless of actual market direction.

**Our fix:** Normalise volume before comparing:
```
elapsed_pct    = elapsed_session_minutes / total_session_minutes
volume_pace    = current_day_volume / elapsed_pct
signal         = volume_pace vs prev_day_volume
```
Now the comparison is apples-to-apples at any time of day.

---

## The 5 Config Parameters
| Param | Default | Purpose |
|---|---|---|
| `table_text_color` | Blue | Colour of the data panel text |
| `table_x_offset` | 10px | Distance from chart left edge |
| `table_y_offset` | 50px | Distance from chart top |
| `support_color` | Green | Colour of support H-line |
| `resistance_color` | Red | Colour of resistance H-line |

Note: the `Trade.mqh` library is included in the original but never actually used anywhere in the script. Author oversight — we do not need a trade management import for a pure analysis tool.

---

## What the Screenshots Show

- **Fig 1** (`trendlines1.png`) — The clearest image in the article. Shows a live chart with the green support line and red resistance line drawn at prev day Low and High. Price clearly reacts to both levels. This is the visual proof the concept works.
- **Fig 2** (`text_summary.png`) — The data panel on the chart. Vertical list of key-value pairs. Simple, clean, immediately readable.
- **Figs 5–7** (animated GIFs) — Three different instruments (USDSEK, Crash 900, USDCNH) all showing the tool's bullish/bearish reading being confirmed by subsequent price action. Useful validation that the basic classification is directionally correct even if rough.

---

## What to Keep
- The 7-field data table format — OHLCV + S/R in one place
- Bullish/Bearish/Neutral classification — simple and directionally useful
- Green/red colour convention for S/R lines — intuitive, will use across all parts
- Volume comparison structure — correct idea, fix the time-normalisation
- Plain-English commentary output — valuable for logging, alerts, and UI

## What to Discard
- Raw volume comparison without normalisation — misleading before market midpoint
- MQL5-specific rendering (Comment(), ObjectCreate, iVolume etc.)
- The unused `Trade.mqh` import

## What to Improve
- **Volume normalisation** — compare pace, not raw count
- **Range magnitude** — classify yesterday's candle as small/normal/large relative to ATR
- **Price distance** — how far is current price from support/resistance in pips and ATR units
- **Live update** — original runs once; ours refreshes on each bar close
- **Merge S/R with Part 1** — shared `DailyContextProvider` eliminates duplicated logic

---

## Architecture Note — The Overlap Problem

Part 1 and Part 2 both fetch `prev_day_high` and `prev_day_low` and both draw horizontal lines at those levels. As we go through all 65 parts we will likely find many more of these overlaps.

The right response is not to build 65 separate data-fetching routines. It is to build one shared module:

```
DailyContextProvider.get(symbol, date) -> {
    open, high, low, close, volume,
    support, resistance,
    market_nature, atr, range_magnitude
}
```

Every tool that needs daily context calls this once. The data is cached and shared. This is the most important architectural decision for the whole project.
