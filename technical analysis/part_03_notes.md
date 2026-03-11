# Part 03 — Analytics Master EA
**Series:** Price Action Analysis Toolkit Development  
**Type:** Expert Advisor | **Verdict:** BUILD | **Depends on:** Parts 1 & 2

---

## What It Does
Part 3 is the live version of Part 2. It takes the same analytical data panel and converts it from a one-shot script into a continuously running EA that auto-refreshes every 2 hours. On top of that, it adds five entirely new data streams that Parts 1 and 2 never touched:

1. **ATR volatility** — H1 ATR(14) as a measure of intraday price range
2. **Account balance & equity** — live account status from the broker
3. **Market spread** — real-time Ask - Bid transaction cost
4. **Min/Max lot sizes** — broker position sizing limits
5. **Possible lot size** — risk-based position sizing suggestion

The dashboard now shows **17 metrics** in one panel, refreshing every 2 hours automatically.

---

## The Big Architectural Shift
This is the most important moment in the first three parts. Parts 1 and 2 were scripts — fire and forget. Part 3 is the first tool that runs *continuously*. It responds to market events, maintains state, and updates on its own.

This means from Part 3 onwards, our architecture needs to think in two modes:
- **On-demand tools** — called once by the user (Parts 1, 2 style)
- **Live services** — run continuously, self-updating (Part 3 style)

In our build, the "live service" model is handled by a `ScheduledRefreshManager` that fires on bar close or configurable interval — cleaner than the tick-gate approach the original uses.

---

## The S/R Change — Critical to Understand

Part 2 set support = prev_day_low, resistance = prev_day_high. That is raw level marking.

Part 3 changes this completely:
```
support    = prev_day_low  - (range * 0.382)
resistance = prev_day_high + (range * 0.382)
```
Where `range = prev_day_high - prev_day_low`.

This is a **Fibonacci extension** — it projects levels *beyond* the previous day's range. It is saying: if yesterday's range was 100 pips, the next meaningful support sits 38.2 pips *below* yesterday's low. This is a more aggressive projection — not marking where price was, but where it might go.

Neither approach is wrong. They serve different purposes:
- Raw H/L → mark where price has been (conservative reference)
- Fibonacci extension → project where price might go next (predictive)

**Our build exposes both as config options** via `FibonacciSRCalculator(mode='raw' | 'extension', ratio=0.382)`.

---

## The Lot Size Formula — Explained
```
stop_loss_distance = abs(support - resistance) * stop_loss_multiplier
risk_amount        = account_balance * (risk_percentage / 100)
lot_size           = risk_amount / (stop_loss_distance / tick_size)
```

Standard Kelly-adjacent risk formula. The logic: if you risk $100 on a trade and your stop is 50 ticks away, each tick must be worth $2 to justify the lot size.

**One issue:** The stop loss distance is using the Fibonacci *extended* S/R gap, which is larger than the actual daily range. This produces smaller lot sizes than intuition suggests. Not wrong — just important to understand. In our build, expose `use_raw_range_for_lot_sizing: true/false` as a config option.

---

## ATR — Why H1 and Why 14?
- **H1 timeframe** — captures hourly price movement. More responsive than D1 for intraday position sizing.
- **Period 14** — standard default from J. Welles Wilder (ATR's creator). 14 bars = ~14 hours of recent volatility.
- **What it tells you** — if ATR is 0.0015 on EURUSD, the average hourly range is 15 pips. Use this to judge whether a 10-pip stop is reasonable or too tight.

In our build: `ATRCalculator.get_atr(symbol, 'H1', 14)` — pure function, no broker coupling.

---

## The 2-Hour Refresh — What It Really Means
The original fires `UpdateMetrics()` on every single price tick. Inside that function it checks whether 2 hours have passed. If not, it returns immediately.

This is wasteful (calling a function thousands of times per hour to do nothing) but it works. Our cleaner equivalent:

```python
# Bar-close event handler (pseudocode)
def on_bar_close(bar):
    if scheduler.should_refresh(last_update, interval=7200):
        metrics = compute_all_metrics()
        renderer.update(metrics)
        last_update = now()
```

Better yet — fire on D1 bar close (once per day) since the data is daily anyway.

---

## The Direction Signal — Improved but Still Limited
Part 3 adds wick context to the Bullish/Bearish reading:

```
"Bullish with bullish pressure" = close > open AND high > both open and close
"Bearish with bearish pressure" = close < open AND low  < both open and close
```

The second condition ("pressure") checks whether the wick extended beyond the body in the direction of the move. A bullish candle where the high is above both open and close means buyers pushed price well above where it opened — confirming buying pressure.

Still no magnitude. We add it via ATR-relative range classification in our build.

---

## What to Keep
- The EA lifecycle pattern (OnInit/OnTick/OnDeinit) — maps cleanly to our service model
- ATR as volatility measure — standard, clean, reused in 30+ future parts
- Fibonacci S/R extension as an option — more nuanced than raw H/L
- Account balance & equity in the panel — essential live context
- Spread display — real transaction cost visibility
- Lot size calculation — risk% × balance ÷ stop is the right formula
- 17-metric comprehensive panel — good daily briefing format

## What to Discard
- Tick-based time gate — replace with event-driven scheduler
- `ObjectsDeleteAll(0)` — nukes all chart objects, not just ours
- Hard-coded 0.382 Fibonacci ratio — make configurable
- All MQL5 APIs

## What to Improve
- Scheduler: fire on bar close, not tick + time check
- Object management: namespace all created objects, delete only ours
- Fibonacci ratio: expose as config (0.236, 0.382, 0.5, 0.618, 1.0)
- Equity ratio alert: warn when equity < 95% of balance
- Spread alert: warn when spread > X% of ATR (unusually expensive)
- Volume: still needs time-normalisation (same flaw as Part 2)
- ATR: make timeframe and period configurable

---

## Architecture — New Components Introduced
```
ATRCalculator          → get_atr(symbol, tf, period) → float
AccountDataProvider    → get_account() → {balance, equity}
MarketDataProvider     → get_market_info(symbol) → {bid, ask, spread, lot_limits, tick_size}
LotSizeCalculator      → calculate(balance, risk_pct, sl_distance, tick_size, min_lot) → float
FibonacciSRCalculator  → calculate(high, low, mode, ratio) → {support, resistance}
ScheduledRefreshManager→ should_refresh(last_update, interval) → bool
```

`LotSizeCalculator` and `ATRCalculator` will be the most reused components in the entire toolkit — they appear in almost every EA part from here on. Get them right now.

---

## Forum Comments — What Users Actually Asked
Two important things from the discussion section:

1. A user asked if the tool **opens trades automatically** — the author confirmed it does NOT. It is analysis only. This is an important design principle: don't auto-trade until you have thoroughly validated.

2. A user asked for **audible alerts when sentiment changes** — this was not implemented. Our build adds: `AlertManager.notify(event_type, message)` with configurable channels (sound, push notification, webhook).
