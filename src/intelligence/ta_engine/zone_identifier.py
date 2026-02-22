"""
ZoneIdentifier.py
=================
Structural Supply/Demand Detector (v7.14 - Price-Aware Zones)

UPDATES:
- LABELS: Changed default timeframe label from '15min' to 'Major'.
  (This aligns with the new M5/M1 Scalper config).
- LOGIC: Remains agnostic. It will correctly map M5 swings to M5 Zones.

Author: Trading System v7.14
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Union, Any, List, Dict, Tuple, Optional
import logging
from datetime import datetime, timedelta
import os

# --- VISUALIZATION IMPORTS ---
try:
    import mplfinance as mpf
    VISUALIZATION_ENABLED = True
except ImportError:
    VISUALIZATION_ENABLED = False

logger = logging.getLogger("ZoneIdentifier")

# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

class ZoneType(Enum):
    SUPPLY = "supply"
    DEMAND = "demand"

class ZoneStatus(Enum):
    FRESH = "fresh"
    TESTED = "tested"
    BROKEN = "broken"

@dataclass
class Zone:
    type: ZoneType
    price_top: float
    price_bottom: float
    protection_price: float
    analysis_id: str
    created_at: pd.Timestamp
    is_structural: bool = True
    strength: float = 50.0
    role: str = "impulsive"
    status: ZoneStatus = ZoneStatus.FRESH
    touch_count: int = 0
    timeframe: str = "Major"  # Updated default
    ema_aligned: bool = True
    has_accumulation: bool = True 
    is_major_structure: bool = True
    uid: str = field(default_factory=lambda: "")  # CRITICAL: Unique identifier per zone (FIX #1)
    
    # PHYSICS METRICS (v8.0 - Physics & Qualification Engine)
    basing_time: int = 0           # Number of candles price hesitated before creating zone
    velocity: float = 0.0          # Speed of departure (pips per bar)
    formation_rvol: float = 1.0    # Relative Volume at creation (1.0 = avg, 3.0 = high)
    
    # LOCATION LOGIC (v8.0 - Premium/Discount Scoring)
    range_position: float = 50.0   # 0% = Low (Discount), 100% = High (Premium)
    location_label: str = "Equilibrium" # "Premium", "Discount", etc.
    quality_score: float = 50.0    # Final calculated score (0-100)

    @property
    def mid_price(self) -> float:
        """Returns the 50% level of the zone."""
        return (self.price_top + self.price_bottom) / 2

    @property
    def height(self) -> float:
        """Returns the height of the zone in price units."""
        return abs(self.price_top - self.price_bottom)

    def contains(self, price: float) -> bool:
        return self.price_bottom <= price <= self.price_top
    
    def get_suggested_sl(self, current_ema: float = 0.0, buffer_pips: float = 0.0) -> float:
        """
        DIRECT MATH: Simply adds/subtracts the buffer_pips from protection price.
        """
        # If Demand: SL is BELOW the low
        if self.type == ZoneType.DEMAND:
            return self.protection_price - buffer_pips
        
        # If Supply: SL is ABOVE the high
        else: 
            return self.protection_price + buffer_pips

    def is_valid_for_entry(self, current_price: float, min_score: float = 0) -> bool:
        """
        Checks geometric validity and optional quality score threshold.
        """
        if self.status == ZoneStatus.BROKEN: 
            return False
        
        # Basic Price Geometry
        if self.type == ZoneType.DEMAND and current_price < self.protection_price: 
            return False
        if self.type == ZoneType.SUPPLY and current_price > self.protection_price: 
            return False
        
        # Quality Filter (v8.0)
        if min_score > 0 and self.quality_score < min_score:
            return False
            
        return True
    
    def __repr__(self):
        return f"Zone[{self.role}]({self.type.value}, {self.price_bottom:.2f}-{self.price_top:.2f})"


# ==============================================================================
# MAIN ENGINE CLASS
# ==============================================================================
# ZONE STATE - Price-Aware Zone Tracking (v7.14)
# ==============================================================================

@dataclass
class ZoneState:
    """Persistent zone state for price-position awareness (v7.14)"""
    active_zones: List[Zone] = field(default_factory=list)
    last_update_time: Optional[datetime] = None
    
    def get_price_zone_position(self, current_price: float) -> Dict[str, Any]:
        """
        Determine price position relative to all active zones (Price-Aware Detection).
        Returns structure indicating which zone(s) price is in/near/testing.
        """
        position = {
            'price': current_price,
            'inside_zones': [],      # Zones price is currently inside
            'above_all': True,        # Price above all zones
            'below_all': True,        # Price below all zones
            'nearest_above': None,    # Closest zone above price
            'nearest_below': None,    # Closest zone below price
            'distance_to_nearest': float('inf'),
            'zone_interactions': []   # Detailed interaction data
        }
        
        if not self.active_zones:
            return position
        
        zone_distances = []
        
        for zone in self.active_zones:
            # Check if price is inside zone
            if zone.contains(current_price):
                position['inside_zones'].append({
                    'zone': zone,
                    'type': zone.type.value,
                    'penetration_pct': ((current_price - zone.price_bottom) / (zone.price_top - zone.price_bottom)) * 100 if zone.price_top > zone.price_bottom else 0,
                    'distance_to_mid': abs(current_price - zone.mid_price)
                })
                position['above_all'] = False
                position['below_all'] = False
            
            # Check distance relationships
            if current_price < zone.price_bottom:
                # Price is below zone
                distance = zone.price_bottom - current_price
                zone_distances.append((distance, 'below', zone))
                position['below_all'] = False
            elif current_price > zone.price_top:
                # Price is above zone
                distance = current_price - zone.price_top
                zone_distances.append((distance, 'above', zone))
                position['above_all'] = False
        
        # Find nearest zones
        if zone_distances:
            zone_distances.sort(key=lambda x: x[0])
            nearest_distance, nearest_position, nearest_zone = zone_distances[0]
            position['distance_to_nearest'] = nearest_distance
            
            if nearest_position == 'above':
                position['nearest_below'] = {
                    'zone': nearest_zone,
                    'distance': nearest_distance,
                    'price_target': nearest_zone.price_top
                }
            else:  # below
                position['nearest_above'] = {
                    'zone': nearest_zone,
                    'distance': nearest_distance,
                    'price_target': nearest_zone.price_bottom
                }
        
        # Interaction summary
        position['zone_interactions'] = [
            {
                'zone_id': id(z),
                'type': z.type.value,
                'status': 'inside' if z.contains(current_price) else ('above' if current_price > z.price_top else 'below'),
                'distance': abs(current_price - z.mid_price)
            }
            for z in self.active_zones
        ]
        
        return position
    
    def detect_zone_breakout(self, current_price: float, close_price: float) -> Optional[Dict[str, Any]]:
        """
        Detect when price breaks OUT of a zone (similar to break_of_structure).
        Useful for invalidating zone entries.
        """
        if not self.active_zones:
            return None
        
        for zone in self.active_zones:
            # Was zone recently tested and is now broken?
            if zone.touch_count > 0:
                if zone.type == ZoneType.DEMAND:
                    # Demand zone broken if close goes below protection price
                    if close_price < zone.protection_price and zone.status == ZoneStatus.FRESH:
                        return {
                            'zone_broken': True,
                            'zone': zone,
                            'zone_type': 'demand',
                            'breakout_direction': 'down',
                            'breakout_price': close_price,
                            'breakdown_distance': zone.protection_price - close_price,
                            'timestamp': datetime.now()
                        }
                
                elif zone.type == ZoneType.SUPPLY:
                    # Supply zone broken if close goes above protection price
                    if close_price > zone.protection_price and zone.status == ZoneStatus.FRESH:
                        return {
                            'zone_broken': True,
                            'zone': zone,
                            'zone_type': 'supply',
                            'breakout_direction': 'up',
                            'breakout_price': close_price,
                            'breakout_distance': close_price - zone.protection_price,
                            'timestamp': datetime.now()
                        }
        
        return None


# ==============================================================================

class ZoneIdentifier:
    def __init__(self, config: Union[dict, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.plot_dir = "logs/plots"
        os.makedirs(self.plot_dir, exist_ok=True)
        # Production flag: controls synthetic zone injection and other test helpers
        self.enable_test_helper = self._get_conf('enable_test_helper', False)
        
        # Price-aware zone state (v7.14)
        self.zone_state = ZoneState()
        self.logger.info("[OK] ZoneIdentifier initialized with price-aware ZoneState (v7.14)")
    
    def _get_conf(self, key, default):
        """Helper to safely extract config values"""
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    def _add_indicators(self, df: pd.DataFrame):
        df = df.copy()
        if 'ema_3' not in df.columns:
            df['ema_3'] = df['close'].ewm(span=3, adjust=False).mean()
        return df

    def analyze_zone_physics(self, zone: Zone, df: pd.DataFrame) -> Zone:
        """
        Computes 'Physics' metrics: Basing Time, Velocity, and Formation Volume.
        This tells us HOW the zone was created (v8.0 - Enhanced).
        
        KEY: Only measures physics on COMPLETED breakouts (historical zones).
        For zones still forming (current_leg), returns zone with 0 basing.
        """
        if len(df) < 1:
            return zone
        
        # 1. Find the Breakout Moment (When price left the zone)
        if zone.type == ZoneType.SUPPLY:
            # For Supply, we look for candle breaking BELOW the zone
            breakout_mask = df['close'] < zone.price_bottom
        else:
            # For Demand, we look for candle breaking ABOVE the zone
            breakout_mask = df['close'] > zone.price_top
        
        # Get indices where breakout occurred
        breakout_indices = df[breakout_mask].index
        
        # CRITICAL (v8.0): Only count breakouts AFTER zone was created
        valid_breakouts = [idx for idx in breakout_indices if idx >= zone.created_at]
        
        # If price never left (still forming inside), return as is
        if not valid_breakouts:
            return zone
        
        first_breakout_time = valid_breakouts[0]
        try:
            break_loc = df.index.get_loc(first_breakout_time)
        except KeyError:
            return zone  # Safety catch
        
        # --- A. BASING TIME (Hesitation) ---
        # Look back 10 candles from breakout to see how many were "stuck" in the zone range
        lookback = 10
        start_loc = max(0, break_loc - lookback)
        segment = df.iloc[start_loc:break_loc]
        
        basing_count = 0
        for _, row in segment.iterrows():
            # Check intersection of candle with zone body
            candle_low = row['low']
            candle_high = row['high']
            # If candle overlaps with zone
            if (candle_high >= zone.price_bottom) and (candle_low <= zone.price_top):
                basing_count += 1
        
        zone.basing_time = basing_count
        
        # --- B. DEPARTURE VELOCITY (Explosiveness) ---
        # Measure net movement of next 3 candles after breakout
        future_segment = df.iloc[break_loc : break_loc + 3]
        if len(future_segment) > 0:
            start_price = future_segment.iloc[0]['open']
            end_price = future_segment.iloc[-1]['close']
            distance = abs(end_price - start_price)
            # Velocity = Pips per bar
            zone.velocity = distance / len(future_segment)
        else:
            zone.velocity = 0.0
        
        # --- C. FORMATION RELATIVE VOLUME (Participation) ---
        # Compare volume at breakout vs average volume of previous 20 candles
        avg_vol_window = df.iloc[max(0, break_loc-20):break_loc]
        breakout_vol = df.iloc[break_loc].get('tick_volume', 0) if 'tick_volume' in df.columns else 0
        
        if not avg_vol_window.empty and 'tick_volume' in df.columns:
            avg_vol = avg_vol_window['tick_volume'].mean()
            zone.formation_rvol = (breakout_vol / avg_vol) if avg_vol > 0 else 1.0
        else:
            zone.formation_rvol = 1.0
        
        return zone

    def _calculate_premium_discount(self, zone: Zone, range_high: float, range_low: float) -> Zone:
        """
        Calculates where the zone sits within the dealing range using Fibonacci retracement levels.
        
        FIBONACCI LEVELS (Professional Standard):
        0%    = Range Low (Recent Support)
        23.6% = Weak retracement level
        38.2% = Key support (Strong reversal point) 
        50%   = Equilibrium (Psychological mid-point)
        61.8% = Golden Ratio (Strongest support level)
        78.6% = Deep retracement
        100%  = Range High (Recent Resistance)
        
        ZONE CLASSIFICATION:
        < 38.2%    = Deep Discount (HIGH PROBABILITY BUY)
        38.2-50%   = Moderate Discount
        50-61.8%   = Moderate Premium
        > 61.8%    = Deep Premium (HIGH PROBABILITY SELL)
        """
        rng_size = range_high - range_low
        if rng_size <= 0:
            zone.range_position = 50.0
            zone.location_label = "Unknown"
            return zone
        
        mid_zone = zone.mid_price
        
        # Calculate percentage position (0% = Range Low, 100% = Range High)
        pct = ((mid_zone - range_low) / rng_size) * 100
        zone.range_position = pct
        
        # FIBONACCI-BASED LABELING (v9.0)
        if pct < 23.6:
            zone.location_label = "Deep Discount"  # Extreme low
        elif pct < 38.2:
            zone.location_label = "Discount"       # Below key support
        elif pct < 50.0:
            zone.location_label = "Moderate Discount"  # Between 38.2% and 50%
        elif pct < 61.8:
            zone.location_label = "Moderate Premium"   # Between 50% and 61.8%
        elif pct < 78.6:
            zone.location_label = "Premium"        # Above golden ratio
        else:
            zone.location_label = "Deep Premium"   # Extreme high
        
        return zone

    def calculate_zone_score(self, zone: Zone, current_price: float, atr: float) -> Zone:
        """
        Calculates a composite 0-100 score for the zone.
        Higher score = Higher Probability entry.
        
        Components:
        1. FRESHNESS (0-25): Fresh untested zones score high
        2. STRENGTH (0-15): Impulsive zones better than corrective
        3. BASING TIME (0-15): Short basing (explosive) > long basing (churning)
        4. VELOCITY (0-10): Relative to ATR - need moderate departure
        5. PREMIUM/DISCOUNT (±20): Smart Money aligns with location
        6. ZONE WIDTH (±10): Not too wide (unmanageable), not too tight (noise)
        """
        score = 50.0  # Base score
        
        # 1. FRESHNESS (+25)
        if zone.status == ZoneStatus.FRESH:
            score += 25
        elif zone.status == ZoneStatus.TESTED:
            # Penalty increases with touches
            score += 5 - (zone.touch_count * 5)
        
        # 2. STRENGTH / ROLE (+15)
        if zone.role == "impulsive":
            score += 15
        else:
            score -= 10  # Corrective zones are weak targets
        
        # 3. BASING TIME (+/- 15)
        # We want Short basing (explosive move). Long basing = churning.
        if zone.basing_time <= 2:
            score += 15  # "Rocket" departure
        elif zone.basing_time <= 4:
            score += 5
        elif zone.basing_time > 8:
            score -= 15  # Too much hesitation
        
        # 4. VELOCITY (+/- 10)
        # We need relative measure. If ATR available, use it.
        if atr > 0:
            velocity_ratio = zone.velocity / atr if zone.velocity > 0 else 0
            if velocity_ratio > 1.5:
                score += 10  # Good explosive move
            elif velocity_ratio < 0.5:
                score -= 10  # Slow drift away
        
        # 5. PREMIUM / DISCOUNT (+±25) [FIBONACCI-BASED v9.0]
        # Smart Money Sells High (Premium) and Buys Low (Discount)
        # Fibonacci levels provide natural support/resistance
        if zone.type == ZoneType.SUPPLY:
            # Supply zones (SELL) score highest at premium levels
            if zone.range_position > 61.8:
                score += 25  # Selling at golden ratio + (BEST)
            elif zone.range_position > 50:
                score += 10  # Selling above midpoint (good)
            elif zone.range_position > 38.2:
                score -= 5   # Selling below key support (weak)
            else:
                score -= 25  # Selling at discount (BAD)
        
        elif zone.type == ZoneType.DEMAND:
            # Demand zones (BUY) score highest at discount levels
            if zone.range_position < 38.2:
                score += 25  # Buying at key support level (BEST)
            elif zone.range_position < 50:
                score += 10  # Buying below midpoint (good)
            elif zone.range_position < 61.8:
                score -= 5   # Buying above 50% level (weak)
            else:
                score -= 25  # Buying at premium (BAD)
        
        # 6. ZONE WIDTH (Precision) (±10)
        # Too wide = hard to manage risk. Too tight = likely noise.
        zone_h = zone.height
        if atr > 0:
            if zone_h > (3.0 * atr):
                score -= 10  # Barn door zone
            elif zone_h < (0.2 * atr):
                score -= 5  # Micro zone (likely noise)
        
        # Clamp Score 0-100
        zone.quality_score = min(100.0, max(0.0, score))
        return zone

    def calculate_location_score(self, zone: Zone, structure_high: float, structure_low: float) -> int:
        """
        PREMIUM/DISCOUNT ANALYZER (v2.0)
        Returns a score based on zone location within major structure.
        
        CONTEXT:
        - Bullish trends: We want to BUY DEMAND in DISCOUNT (low in range) ✓ Good
        - Bullish trends: We don't want to BUY DEMAND in PREMIUM (high in range) ✗ Bad
        - Bearish trends: We want to SELL SUPPLY in PREMIUM (high in range) ✓ Good
        - Bearish trends: We don't want to SELL SUPPLY in DISCOUNT (low in range) ✗ Bad
        
        Score Interpretation:
        - +20: Deep position (best)
        - +10: Good position
        -  0: Neutral
        - -20: Bad position (should skip)
        
        Args:
            zone: Zone object to score
            structure_high: Highest point of major structure
            structure_low: Lowest point of major structure
            
        Returns:
            int: Score indicating quality of zone location
        """
        rng = structure_high - structure_low
        if rng == 0: 
            return 0
        
        # Calculate % position in range (0 = Low, 100 = High)
        mid_price = (zone.price_top + zone.price_bottom) / 2
        pct = ((mid_price - structure_low) / rng) * 100
        
        # Store for debugging
        zone.range_position = pct
        
        score = 0
        
        # BEARISH TREND: We want to SELL in PREMIUM (>50%)
        if zone.type == ZoneType.SUPPLY:
            if pct > 62: 
                score += 20    # Deep Premium (Best)
                self.logger.debug(f"[Location] SUPPLY at {pct:.1f}% (DEEP PREMIUM) ✓ Score: +20")
            elif pct > 50: 
                score += 10  # Premium (Good)
                self.logger.debug(f"[Location] SUPPLY at {pct:.1f}% (PREMIUM) ✓ Score: +10")
            else: 
                score -= 20           # Discount (Bad - Chasing down)
                self.logger.debug(f"[Location] SUPPLY at {pct:.1f}% (DISCOUNT) ✗ Score: -20")
            
        # BULLISH TREND: We want to BUY in DISCOUNT (<50%)
        elif zone.type == ZoneType.DEMAND:
            if pct < 38: 
                score += 20    # Deep Discount (Best)
                self.logger.debug(f"[Location] DEMAND at {pct:.1f}% (DEEP DISCOUNT) ✓ Score: +20")
            elif pct < 50: 
                score += 10  # Discount (Good)
                self.logger.debug(f"[Location] DEMAND at {pct:.1f}% (DISCOUNT) ✓ Score: +10")
            else: 
                score -= 20           # Premium (Bad - Chasing up)
                self.logger.debug(f"[Location] DEMAND at {pct:.1f}% (PREMIUM) ✗ Score: -20")
        
        return score

    def identify_zones(self, df: pd.DataFrame, structure, timeframe="Major", symbol="", **kwargs) -> Dict[str, List[Zone]]:
        # Validate Inputs
        if len(df) < 50: return {'active': [], 'broken': []}
        if structure is None or not hasattr(structure, 'previous_legs'):
            return {'active': [], 'broken': []}
        
        try:
            ticket = getattr(structure, 'analysis_id', "UNKNOWN")
            df = self._add_indicators(df)
            
            # A. Map Legs to Zones
            # This maps both "Left" (previous_legs) and "Right" (current_leg) zones
            structural_zones = self._map_legs_to_zones(df, structure, ticket, timeframe)
            
            # B. Deduplicate
            merged_zones = self._deduplicate_zones(structural_zones)

            # C. Update Status (Capture both lists)
            active_zones, broken_zones = self._update_zone_status(df, merged_zones)
            
            # [NEW] D. PHYSICS & QUALIFICATION ANALYSIS (v8.0) - Grade the "Resume" of every zone
            # Calculate structure range for Premium/Discount logic
            struct_high = getattr(structure, 'last_HH', None)
            struct_low = getattr(structure, 'last_LL', None)
            
            # Fallback if structure object doesn't have explicit high/low
            range_high = struct_high.price if struct_high else df['high'].max()
            range_low = struct_low.price if struct_low else df['low'].min()
            
            # Estimate ATR for width checks (Simple avg range of last 20 candles)
            avg_range = (df['high'] - df['low']).tail(20).mean()
            
            enhanced_zones = []
            for z in active_zones:
                # 1. Calculate Physics (Velocity, Basing, Relative Volume)
                z = self.analyze_zone_physics(z, df)
                
                # 2. Calculate Location (Premium/Discount)
                z = self._calculate_premium_discount(z, range_high, range_low)
                
                # 3. Final Scoring (Composite 0-100)
                z = self.calculate_zone_score(z, df['close'].iloc[-1], avg_range)
                
                enhanced_zones.append(z)
            
            # [DIAGNOSTIC v11.0] Log zone creation events for continuous improvement
            try:
                from filter_diagnostics import get_diagnostics as _get_diag
                _diag = _get_diag()
                for _z in enhanced_zones:
                    _diag.log_zone_event(
                        symbol=symbol,
                        event_type='zone_active',
                        zone_type=_z.type.value,
                        zone_bottom=_z.price_bottom,
                        zone_top=_z.price_top,
                        zone_uid=getattr(_z, 'uid', ''),
                        strength=getattr(_z, 'strength', 0),
                        quality_score=getattr(_z, 'quality_score', 0),
                        touch_count=_z.touch_count,
                        basing_time=getattr(_z, 'basing_time', 0),
                        velocity_atr=round(getattr(_z, 'velocity', 0) / avg_range, 3) if avg_range > 0 else 0,
                        reason=getattr(_z, 'role', '')
                    )
            except Exception:
                pass

            # Update ZoneState with enhanced zones
            self.zone_state.active_zones = enhanced_zones
            self.zone_state.last_update_time = datetime.now()
            
            # E. Visualization (Optional)
            if VISUALIZATION_ENABLED and len(enhanced_zones) > 0:
                self._save_validation_chart(df, enhanced_zones, symbol, timeframe)
            elif len(enhanced_zones) == 0:
                self.logger.debug(f"No active zones to visualize for {symbol}")
            
            return {'active': enhanced_zones, 'broken': broken_zones}
            
        except Exception as e:
            self.logger.error(f"Error identifying zones: {e}")
            return {'active': [], 'broken': []}

    def _map_legs_to_zones(self, df: pd.DataFrame, structure, ticket: str, timeframe: str = "Major") -> List[Zone]:
        zones = []
        
        # 1. Historical Legs (The "Left Side")
        legs = structure.previous_legs.copy() if isinstance(structure.previous_legs, list) else []
        
        # 2. Current Leg (The "Right Side" - forming corrective/impulsive moves)
        if structure.current_leg and hasattr(structure.current_leg, 'start_swing'):
            legs.append(structure.current_leg)
            
        # Map zones directly from each leg's classified leg_type
        for leg in legs:
            if not hasattr(leg, 'start_swing') or leg.start_swing is None: continue
            if leg.start_swing.index >= len(df): continue

            idx = leg.start_swing.index
            candle = df.iloc[idx]

            leg_type = str(leg.leg_type.value).lower() if hasattr(leg.leg_type, 'value') else str(leg.leg_type).lower()

            # FIX #1: Generate unique UID per zone to prevent cooldown collisions across multiple zones in same analysis
            zone_uid = f"{ticket}_{int(leg.start_swing.timestamp.timestamp())}_{leg_type}"

            # bullish_impulsive -> DEMAND (impulsive, strong)
            if "bullish_impulsive" in leg_type:
                zones.append(Zone(
                    type=ZoneType.DEMAND,
                    price_top=max(candle['open'], candle['close']),
                    price_bottom=leg.start_swing.price,
                    protection_price=min(candle['low'], leg.start_swing.price),
                    analysis_id=ticket,
                    created_at=leg.start_swing.timestamp,
                    strength=80.0,
                    role="impulsive",
                    timeframe=timeframe,
                    uid=zone_uid
                ))

            # bullish_corrective -> SUPPLY (corrective, weak/target)
            elif "bullish_corrective" in leg_type:
                zones.append(Zone(
                    type=ZoneType.SUPPLY,
                    price_top=leg.start_swing.price,
                    price_bottom=min(candle['open'], candle['close']),
                    protection_price=max(candle['high'], leg.start_swing.price),
                    analysis_id=ticket,
                    created_at=leg.start_swing.timestamp,
                    strength=40.0,
                    role="corrective",
                    timeframe=timeframe,
                    uid=zone_uid
                ))

            # bearish_impulsive -> SUPPLY (impulsive, strong)
            elif "bearish_impulsive" in leg_type:
                zones.append(Zone(
                    type=ZoneType.SUPPLY,
                    price_top=leg.start_swing.price,
                    price_bottom=min(candle['open'], candle['close']),
                    protection_price=max(candle['high'], leg.start_swing.price),
                    analysis_id=ticket,
                    created_at=leg.start_swing.timestamp,
                    strength=80.0,
                    role="impulsive",
                    timeframe=timeframe,
                    uid=zone_uid
                ))

            # bearish_corrective -> DEMAND (corrective, weak/target)
            elif "bearish_corrective" in leg_type:
                zones.append(Zone(
                    type=ZoneType.DEMAND,
                    price_top=max(candle['open'], candle['close']),
                    price_bottom=leg.start_swing.price,
                    protection_price=min(candle['low'], leg.start_swing.price),
                    analysis_id=ticket,
                    created_at=leg.start_swing.timestamp,
                    strength=40.0,
                    role="corrective",
                    timeframe=timeframe,
                    uid=zone_uid
                ))

            # Add a small recent zone around the last closed candle to improve integration test coverage (test helper only)
            if self.enable_test_helper:
                try:
                    last_closed = df.iloc[-2]
                    wick = float(last_closed['high'] - last_closed['low'])
                    buff = max(1.0, wick)
                    struct = getattr(structure, 'market_structure', None)
                    struct_val = getattr(struct, 'value', struct)
                    if struct_val == 'bearish':
                        ztype = ZoneType.SUPPLY
                    else:
                        ztype = ZoneType.DEMAND

                    test_uid = f"{ticket}_helper_{int(last_closed.name.timestamp())}"
                    z = Zone(
                        type=ztype,
                        price_top=last_closed['high'] + buff,
                        price_bottom=last_closed['low'] - buff,
                        protection_price=last_closed['low'] if ztype == ZoneType.DEMAND else last_closed['high'],
                        analysis_id=ticket,
                        created_at=last_closed.name,
                        strength=30.0,
                        role="impulsive",
                        timeframe=timeframe,
                        uid=test_uid
                    )
                    zones.append(z)
                except Exception:
                    pass

        return zones

    def _deduplicate_zones(self, zones: List[Zone]) -> List[Zone]:
        if not zones: return []
        # Sort by price to easily find overlaps
        sorted_zones = sorted(zones, key=lambda z: z.price_bottom)
        merged = []
        current = sorted_zones[0]
        
        for i in range(1, len(sorted_zones)):
            next_z = sorted_zones[i]
            # Overlap check: If next bottom is inside current top range
            if next_z.price_bottom <= current.price_top and next_z.type == current.type:
                # Merge Logic: Expand bounds to cover both
                new_top = max(current.price_top, next_z.price_top)
                new_bottom = min(current.price_bottom, next_z.price_bottom)
                
                # Protection price: Min Low for Demand, Max High for Supply
                new_prot = min(current.protection_price, next_z.protection_price) if current.type == ZoneType.DEMAND else max(current.protection_price, next_z.protection_price)
                
                # Preserve metadata
                merged_role = "impulsive" if ("impulsive" in [current.role, next_z.role]) else "corrective"
                
                current = Zone(
                    type=current.type,
                    price_top=new_top,
                    price_bottom=new_bottom,
                    protection_price=new_prot,
                    analysis_id=current.analysis_id,
                    created_at=max(current.created_at, next_z.created_at),
                    is_structural=current.is_structural and next_z.is_structural,
                    strength=max(current.strength, next_z.strength),
                    role=merged_role,
                    status=current.status,
                    touch_count=max(current.touch_count, next_z.touch_count),
                    timeframe=current.timeframe,
                    ema_aligned=current.ema_aligned and next_z.ema_aligned,
                    has_accumulation=current.has_accumulation or next_z.has_accumulation,
                    is_major_structure=current.is_major_structure or next_z.is_major_structure
                )
            else:
                merged.append(current)
                current = next_z
        merged.append(current)
        return merged

    def _update_zone_status(self, df: pd.DataFrame, zones: List[Zone]) -> Tuple[List[Zone], List[Zone]]:
        active_zones = []
        broken_zones = []
        
        for zone in zones:
            # Skip zones created in the future (safety check) or too old
            if zone.created_at > df.index[-1]: 
                 active_zones.append(zone)
                 continue

            age = df.index[-1] - zone.created_at
            if age > timedelta(days=30): continue  # Extended from 48 hours to 30 days
            
            # Slice data AFTER zone creation
            mask = df.index > zone.created_at
            future = df.loc[mask]
            
            is_broken = False
            if not future.empty:
                if zone.type == ZoneType.DEMAND:
                    # Broken if a Candle CLOSE is below protection (wick allowed in sweep logic, but close kills zone)
                    if (future['close'] < zone.protection_price).any(): is_broken = True
                else:
                    if (future['close'] > zone.protection_price).any(): is_broken = True
            
            if not is_broken:
                if not future.empty:
                    if zone.type == ZoneType.DEMAND:
                        zone.touch_count = (future['low'] <= zone.price_top).sum()
                    else:
                        zone.touch_count = (future['high'] >= zone.price_bottom).sum()
                    zone.status = ZoneStatus.TESTED if zone.touch_count > 0 else ZoneStatus.FRESH
                active_zones.append(zone)
            else:
                zone.status = ZoneStatus.BROKEN
                broken_zones.append(zone)
                # [DIAGNOSTIC v11.0] Log zone invalidation
                try:
                    from filter_diagnostics import get_diagnostics as _get_diag
                    _get_diag().log_zone_event(
                        symbol=getattr(zone, 'analysis_id', '').split('_')[1] if '_' in getattr(zone, 'analysis_id', '') else '',
                        event_type='zone_broken',
                        zone_type=zone.type.value,
                        zone_bottom=zone.price_bottom,
                        zone_top=zone.price_top,
                        zone_uid=getattr(zone, 'uid', ''),
                        strength=getattr(zone, 'strength', 0),
                        quality_score=getattr(zone, 'quality_score', 0),
                        touch_count=zone.touch_count,
                        reason='close_beyond_protection'
                    )
                except Exception:
                    pass

        return active_zones, broken_zones

    # =========================================================================
    # PRICE-AWARE ZONE METHODS (v7.14) - Similar to MarketState in StructureEngine
    # =========================================================================
    
    def get_price_zone_position(self, current_price: float) -> Dict[str, Any]:
        """
        Get detailed price position relative to all active zones.
        Returns: Which zones price is inside/near/testing.
        
        Example output:
        {
            'price': 9100.0,
            'inside_zones': [{'zone': Zone(...), 'penetration_pct': 45.2, ...}],
            'above_all': False,
            'below_all': False,
            'nearest_above': {'zone': Zone(...), 'distance': 15.3},
            'nearest_below': {'zone': Zone(...), 'distance': 8.7},
            'distance_to_nearest': 8.7,
            'zone_interactions': [...]
        }
        """
        return self.zone_state.get_price_zone_position(current_price)
    
    def detect_zone_breakout(self, current_price: float, close_price: float) -> Optional[Dict[str, Any]]:
        """
        Detect when price breaks OUT of a zone (similar to detect_break_of_structure).
        Useful for invalidating zone-based entries.
        
        Example output:
        {
            'zone_broken': True,
            'zone': Zone(...),
            'zone_type': 'demand',
            'breakout_direction': 'down',
            'breakout_price': 9087.5,
            'breakdown_distance': 12.3,
            'timestamp': datetime.now()
        }
        """
        return self.zone_state.detect_zone_breakout(current_price, close_price)
    
    def get_zone_status_summary(self) -> Dict[str, Any]:
        """
        Get high-level summary of all active zones and their current status.
        
        Returns: Statistics about zones (count, types, touches, etc)
        """
        if not self.zone_state.active_zones:
            return {
                'zone_count': 0,
                'demand_zones': 0,
                'supply_zones': 0,
                'fresh_zones': 0,
                'tested_zones': 0,
                'broken_zones': 0,
                'total_touches': 0,
                'avg_strength': 0.0
            }
        
        zones = self.zone_state.active_zones
        return {
            'zone_count': len(zones),
            'demand_zones': sum(1 for z in zones if z.type == ZoneType.DEMAND),
            'supply_zones': sum(1 for z in zones if z.type == ZoneType.SUPPLY),
            'fresh_zones': sum(1 for z in zones if z.status == ZoneStatus.FRESH),
            'tested_zones': sum(1 for z in zones if z.status == ZoneStatus.TESTED),
            'broken_zones': sum(1 for z in zones if z.status == ZoneStatus.BROKEN),
            'total_touches': sum(z.touch_count for z in zones),
            'avg_strength': sum(z.strength for z in zones) / len(zones) if zones else 0.0,
            'last_update': self.zone_state.last_update_time
        }

    def _cleanup_old_plots(self):
        try:
            current = datetime.now()
            if not os.path.exists(self.plot_dir): return
            for f in os.listdir(self.plot_dir):
                if not f.endswith(".png"): continue
                try:
                    if current - datetime.fromtimestamp(os.path.getmtime(os.path.join(self.plot_dir, f))) > timedelta(hours=1):
                        os.remove(os.path.join(self.plot_dir, f))
                except: continue
        except: pass

    def _save_validation_chart(self, df: pd.DataFrame, zones: List[Zone], symbol: str, timeframe: str):
        try:
            self._cleanup_old_plots()
            plot_df = df.tail(150).copy()
            if plot_df.empty:
                self.logger.debug(f"No data to plot for {symbol}")
                return
            
            # Styles
            mc = mpf.make_marketcolors(up='green', down='red', edge='i', wick='i', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
            
            h_lines = []
            h_colors = []
            dotted_lines = [] # For midlines
            
            view_min = plot_df['low'].min()
            view_max = plot_df['high'].max()
            
            for z in zones:
                if z.price_bottom > view_max or z.price_top < view_min: continue
                
                # Solid Borders
                h_lines.append(z.price_top)
                h_lines.append(z.price_bottom)
                c = 'darkgreen' if z.type == ZoneType.DEMAND else 'darkred'
                h_colors.append(c); h_colors.append(c)
                
                # Dotted Midline (Using alines for arbitrary lines)
                # Draw from first bar to last bar visible
                start_dt = plot_df.index[0]
                end_dt = plot_df.index[-1]
                dotted_lines.append([(start_dt, z.mid_price), (end_dt, z.mid_price)])

            if h_lines:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"{self.plot_dir}/{symbol}_{ts}_zones.png"
                
                # Draw borders
                kwargs = dict(
                    type='candle', 
                    style=s, 
                    hlines=dict(hlines=h_lines, colors=h_colors, linewidths=1, alpha=0.6),
                    title=f"{symbol} | Zones: {len(zones)}",
                    savefig=fname, 
                    volume=False
                )
                
                # Add Dotted Midlines if any
                if dotted_lines:
                    kwargs['alines'] = dict(alines=dotted_lines, colors='gray', linestyle=':', linewidths=0.8, alpha=0.8)
                    
                mpf.plot(plot_df, **kwargs)
                self.logger.info(f"✓ Zone plot saved: {fname}")
            else:
                self.logger.debug(f"No zone boundaries to plot for {symbol}")
        except Exception as e:
            self.logger.error(f"Zone plot error: {e}", exc_info=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("ZoneIdentifier v7.13 Loaded")