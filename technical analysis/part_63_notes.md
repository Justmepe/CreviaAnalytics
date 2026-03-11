# Part 63 — Automating Rising and Falling Wedge Detection
**Type:** Indicator | **Verdict:** MEDIUM-HIGH — Wedge = zone context classifier. Rising wedge at supply = double bearish signal. Slope comparison formula reusable for all pattern type detection.
**URL:** https://www.mql5.com/en/articles/21518

## What This Is
Detects rising and falling wedges (converging trendlines). A rising wedge is bearish (upward coiling
into resistance). A falling wedge is bullish (downward coiling into support). The convergence check
ensures the apex (intersection) is still in the future — otherwise the wedge has already resolved.

## Slope Calculation and Wedge Classification
```python
def compute_trendline_slope(p1_idx, p1_price, p2_idx, p2_price) -> float:
    denom = (p2_idx - p1_idx) + 1e-10
    return (p2_price - p1_price) / denom

def classify_wedge(upper_slope, lower_slope) -> str:
    if upper_slope > 0 and lower_slope > 0 and lower_slope > upper_slope:
        return 'rising_wedge'   # both up, lower rising FASTER = converging
    if upper_slope < 0 and lower_slope < 0 and upper_slope < lower_slope:
        return 'falling_wedge' # both down, upper falling FASTER = converging
    if abs(upper_slope - lower_slope) <= 0.1:
        return 'channel'        # parallel = channel (Part 62)
    return 'triangle'          # one flat, one slanted
```

## Convergence Check (Apex Validation)
```python
def compute_apex_index(p1h_idx, p1h_price, upper_slope,
                        p1l_idx, p1l_price, lower_slope) -> float:
    numer = p1l_price - p1h_price + upper_slope*p1h_idx - lower_slope*p1l_idx
    denom = upper_slope - lower_slope + 1e-10
    return numer / denom

def is_valid_wedge(upper_p1, upper_slope, lower_p1, lower_slope, current_bar_idx: int) -> bool:
    apex = compute_apex_index(
        upper_p1[0], upper_p1[1], upper_slope,
        lower_p1[0], lower_p1[1], lower_slope
    )
    return int(round(apex)) > current_bar_idx  # apex must be in the FUTURE
```

## Anti-Repainting: PivotRight=5
```python
def detect_pivot_high(highs, i, pivot_left=5, pivot_right=5) -> bool:
    if i < pivot_left or i > len(highs) - pivot_right - 1:
        return False  # not enough confirmation bars yet
    center = highs[i]
    left_ok  = all(center > highs[i-j] for j in range(1, pivot_left+1))
    right_ok = all(center > highs[i+j] for j in range(1, pivot_right+1))
    return left_ok and right_ok
# PivotRight=5 means we wait 5 bars AFTER the pivot to confirm it
# This introduces 5-bar delay but eliminates repainting
```

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| PivotLeft | 5 | Bars left of pivot |
| PivotRight | 5 | Bars right of pivot (delay = anti-repainting) |
| MinTouches | 3 | Min pivot touches per boundary |
| LineExtensionBars | 30 | Forward projection |
| BreakoutBuffer | 3 | Point*3 beyond line |

## Wedge as Zone Context Classifier
```python
def zone_wedge_context(zone, m15_structure) -> str:
    upper_sl = m15_structure.resistance_trendline.get('slope', 0) if m15_structure.resistance_trendline else 0
    lower_sl = m15_structure.support_trendline.get('slope', 0) if m15_structure.support_trendline else 0

    wedge = classify_wedge(upper_sl, lower_sl)

    if wedge == 'rising_wedge' and zone.zone_type == 'supply':
        return 'high_priority'   # price coiling into supply = double bearish
    if wedge == 'rising_wedge' and zone.zone_type == 'demand':
        return 'avoid'           # rising wedge usually breaks DOWN = against demand
    if wedge == 'falling_wedge' and zone.zone_type == 'demand':
        return 'high_priority'   # price coiling into demand = double bullish
    if wedge == 'falling_wedge' and zone.zone_type == 'supply':
        return 'avoid'
    return 'standard'
```

## Breakout Direction Mapping
| Pattern | Expected Break | Best Entry |
|---------|---------------|-----------|
| Rising wedge | Downside | SELL at supply inside wedge |
| Falling wedge | Upside | BUY at demand inside wedge |
| Channel | Either side | Trade zone nearest boundary |

## CreviaDeriv Integration
```python
# In EntryEngine._check_zone_context():
context = zone_wedge_context(zone, m15_structure)
if context == 'high_priority':
    departure_strength = min(4, departure_strength + 1)  # boost for wedge convergence
elif context == 'avoid':
    return None  # skip this zone entirely
```

## Superior Version
1. Wedge detection on M15 = strategic context; zone entry on M1 = tactical execution
2. Rising wedge on M15 + supply zone on M1 = highest-confidence SELL setup in our system
3. Convergence check critical: apex must be > 0 future bars (otherwise wedge already resolved)
4. Store wedge type in StructureState: `wedge_type: Optional[str] = None` for EntryEngine use
5. Minimum 3 touches per boundary — validates Part 61 requirement of 3-swing confirmation