# Part 56 — Reading Session Acceptance and Rejection with CPI
**Type:** Indicator | **Verdict:** HIGH EXTRACT — 2-candle model for zone invalidation detection, CPI-based acceptance/rejection logic
**URL:** https://www.mql5.com/en/articles/20995

## What This Is
Defines exactly when a support/resistance level is 'accepted' (broken, zone invalid) vs 'rejected' (probe + reversal, zone strengthened). Uses 2-candle model with CPI confirmation. Directly maps to our zone invalidation logic in EntryEngine.

## The 2-Candle Model
Evaluation uses sh1 (newer bar = confirmation) and sh2 (older bar = initial break).
Session range boundary = the level being tested.

```python
def classify_zone_reaction(sh1_h, sh1_l, sh1_c, sh1_o,
                            sh2_h, sh2_l, sh2_c, sh2_o,
                            level: float, tolerance: float,
                            strong_thr=0.60, neutral_band=0.20) -> str:
    cpi1 = compute_cpi(sh1_h, sh1_l, sh1_c)
    cpi2 = compute_cpi(sh2_h, sh2_l, sh2_c)

    # BULLISH BREAKOUT (ACCEPTANCE at resistance = zone broken)
    # sh2 closes strongly above level + sh1 retests from above + sh1 also closes above
    bull_break = (
        sh2_c > level + tolerance and   # sh2 closed above level
        cpi2 >= strong_thr and           # sh2 closed with strong bullish pressure
        sh1_l < level + tolerance and    # sh1 retested the level
        sh1_c > level                    # sh1 also closed above
    )

    # BEARISH REJECTION at resistance (zone holds)
    # sh1 wicked above level but closed back below + strong CPI reversal
    bear_reject_hi = (
        sh1_h > level + tolerance and    # wick poked above level
        sh1_c < level and                # closed back below = rejection
        cpi1 <= -strong_thr and          # sh1 CPI very negative = bear pressure
        cpi2 >= -neutral_band            # sh2 was not already strongly negative
    )

    if bull_break:      return 'acceptance'    # zone broken, invalidate zone
    if bear_reject_hi:  return 'rejection'     # zone holds, strengthen zone
    return 'neutral'
```

## Zone Accept/Reject Application to CreviaDeriv
```python
# In ZoneIdentifier or EntryEngine zone invalidation check:
def check_zone_validity(zone, recent_bars, atr, point):
    tol = atr * 0.1  # tolerance = 10% ATR
    level = zone.top if zone.zone_type == 'supply' else zone.bottom
    if len(recent_bars) < 2:
        return zone  # not enough data

    sh1 = recent_bars[-1]  # newest closed bar
    sh2 = recent_bars[-2]  # bar before

    reaction = classify_zone_reaction(
        sh1.high, sh1.low, sh1.close, sh1.open,
        sh2.high, sh2.low, sh2.close, sh2.open,
        level=level, tolerance=tol
    )

    if reaction == 'acceptance':
        zone.is_valid = False    # zone broken
        zone.invalidation_reason = 'cpi_acceptance'
    elif reaction == 'rejection':
        zone.quality = min(100, zone.quality * 1.15)  # zone reinforced
        zone.rejection_count += 1
    return zone
```

## The Critical Rule: CPI + Close Is The Filter
A zone is NOT broken just because price closes beyond it.
Zone breaks ONLY when:
1. Close beyond level AND
2. CPI >= 0.20 in breakout direction (not just a spike through)

A zone is REINFORCED when:
1. Wick beyond level (price explored, discovered orders)
2. Close returned inside (sellers/buyers defended it)
3. CPI reverses strongly (> 0.60 absolute value, opposite direction)

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| InpStrongThreshold | 0.60 | CPI cutoff for strong acceptance |
| InpNeutralBand | 0.20 | CPI band for neutral classification |
| InpOncePerSessionPerSide | True | Prevents multiple classifications |

## Superior Version Improvements
1. Add rejection_count to ZoneState: supply zone rejected 3x = very strong supply
2. Acceptance with CPI in 0.20-0.60 = 'weak acceptance' — re-entry possible
3. Acceptance with CPI >= 0.60 = 'strong acceptance' — zone fully invalidated
4. Log acceptance/rejection events per zone for win rate analysis (Part 43 framework)
5. On Crash/Boom: spike candles have extreme CPI (close near low) — rejection at resistance
   almost always = CPI <= -0.80. Tighten InpStrongThreshold to 0.50 for synthetics.

## Connection to EntryEngine
Our current zone invalidation: price closes beyond zone_top/bottom.
Improvement: require CPI >= 0.20 for acceptance (same direction as break).
Impact: prevents false zone invalidations from wicks and reversals.