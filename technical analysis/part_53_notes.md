# Part 53 — Pattern Density Heatmap (Zone Quality with Recency Decay)
**Type:** Indicator | **Verdict:** HIGH EXTRACT — Recency decay for zone quality, HTF 1.4x boost, BinCount density aggregation
**URL:** https://www.mql5.com/en/articles/20390

## What This Is
Aggregates candlestick pattern detections into price bins. Zones with more recent pattern detections score higher. HTF-confirmed zones get 1.4x boost. Score 1-100 maps to zone quality. Half-life decay = 250 bars.

## Recency Decay Formula
The article uses a half-life decay model (DecayHalfLife=250 bars):
```python
def recency_decay(age_bars: int, half_life: float = 250.0) -> float:
    """Exponential decay: detection 250 bars ago = 50% weight."""
    return 2.0 ** (-age_bars / half_life)
# age=0   -> weight=1.00 (current bar)
# age=250 -> weight=0.50 (half-life)
# age=500 -> weight=0.25
# age=1000-> weight=0.0625
```

## Zone Score Formula
```python
def compute_zone_score(hits: list, current_bar_idx: int,
                        htf_confirmed: bool = False,
                        half_life: float = 250.0) -> float:
    """
    hits: list of bar indices where pattern was detected at this price level
    Returns: score 0-100, boosted by HTF confirmation
    """
    if not hits:
        return 0.0
    # Weight each hit by recency decay
    weighted_hits = sum(recency_decay(current_bar_idx - h, half_life) for h in hits)
    # Normalize to 0-100 (max_hits is calibrated across all bins)
    # In practice: normalize against the most active bin
    htf_factor = 1.4 if htf_confirmed else 1.0
    return weighted_hits * htf_factor  # caller normalizes to 100
```

## Density Bin Algorithm
```python
def build_density_heatmap(patterns: list, price_high: float, price_low: float,
                           bin_count: int = 40, lookback: int = 2000) -> dict:
    """
    patterns: list of (bar_idx, price_anchor, is_bullish) tuples
    Returns: dict of bin_idx -> weighted_score
    """
    bin_size = (price_high - price_low) / bin_count
    bins = {}
    for bar_idx, anchor_price, is_bullish in patterns[-lookback:]:
        bin_idx = int((anchor_price - price_low) / bin_size)
        bin_idx = max(0, min(bin_count-1, bin_idx))
        age = lookback - bar_idx  # approximate age in bars
        weight = recency_decay(age)
        bins[bin_idx] = bins.get(bin_idx, 0) + weight
    # Normalize to 0-100
    max_val = max(bins.values()) if bins else 1.0
    return {k: (v/max_val)*100 for k, v in bins.items()}
```

## ZoneIdentifier Integration
```python
class ZoneQualityDecay:
    """Mixin for ZoneIdentifier: apply recency decay to existing zone scores."""

    @staticmethod
    def apply_decay(zone_quality: float, zone_age_bars: int,
                    half_life: float = 250.0) -> float:
        """
        Decay zone quality over time. Zone formed 250 bars ago = 50% original quality.
        Minimum floor: 20% (zone never fully disappears until price tests it).
        """
        decay_factor = 2.0 ** (-zone_age_bars / half_life)
        # Floor at 20% to retain zone as weak level even if old
        decayed = zone_quality * (0.20 + 0.80 * decay_factor)
        return max(0.0, decayed)

# In ZoneIdentifier.update_zone_quality():
for zone in self.demand_zones + self.supply_zones:
    age = current_bar - zone.created_bar
    zone.quality = ZoneQualityDecay.apply_decay(zone.quality_original, age)
    if zone.quality < MIN_ZONE_QUALITY:
        self.remove_zone(zone)
```

## Parameter Defaults
| Parameter | Default | Purpose |
|-----------|---------|---------|
| LookbackBars | 2000 | Historical scan depth |
| BinCount | 40 | Price range divisions |
| MinHitsToShow | 2 | Zone visibility threshold |
| DecayHalfLife | 250.0 | Recency half-life in bars |
| ApproachThresholdPips | 8 | Alert proximity distance |

## CreviaDeriv Improvements
1. Add  timestamp to ZoneState dataclass
2. Run decay update every N bars (not every tick) for performance
3. HTF boost: if M15 zone coincides with H1 zone in same price bin -> quality *= 1.4
4. Zone score 100 = multiple fresh patterns at this level = high-quality demand/supply
5. Use zone density score to modulate : denser zones need lower threshold

## Superior Version vs Original
- Original: flat scoring (old and new patterns equally weighted)
- Ours: exponential decay means only recent reactions drive zone quality
- Better: zones that price tested 2+ months ago automatically demote unless retested
- Add: when zone is retested (price returns to zone), reset decay clock (zone freshened)
```python
def on_zone_retest(zone):
    zone.created_bar = current_bar   # reset age
    zone.quality = min(100, zone.quality * 1.2)  # slight boost for re-confirmation
```
