# Part 47 -- Tracking Forex Sessions and Breakouts
**URL:** https://www.mql5.com/en/articles/19944

Session range high/low = key S/R for next session. London session high/low are the most important for NY session trades.

## Session Range
Session bars -> max(high), min(low). Close > session_high = bullish breakout. Close < session_low = bearish breakout.
Add London range to ZoneIdentifier as SESSION_RANGE zone type. Confirm BUY signals with price > London session high.
