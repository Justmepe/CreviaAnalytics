"""
StructureEngine.py
==================
Market Structure Detection Engine (v12.0 - Dynamic Timeframe Labels)

CHANGES:
- FIXED: 'analyze_multi_timeframe' now labels data as 'Major'/'Minor' instead of hardcoded '15min'/'1min'.
  (This prevents confusion in logs when running Scalper Mode on M5).
- UPDATED: CHOCH Freshness logic to recognize 'Major' (M5/M15) and 'Minor' (M1) labels.
- RETAINED: Strict Candle Close Confirmation for Trends.
- RETAINED: Fractal Swing Detection & DNA Filtering.

Author: Trading System v12.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import csv
import os
import uuid  # Traceability Tickets


class MarketStructure(Enum):
    """Market structure types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"
    UNKNOWN = "unknown"


class LegType(Enum):
    """Leg classification types"""
    BULLISH_IMPULSIVE = "bullish_impulsive"
    BULLISH_CORRECTIVE = "bullish_corrective"
    BEARISH_IMPULSIVE = "bearish_impulsive"
    BEARISH_CORRECTIVE = "bearish_corrective"
    UNKNOWN = "unknown"


class SwingType(Enum):
    """Swing point types"""
    HH = "HH"  # Higher High
    HL = "HL"  # Higher Low
    LH = "LH"  # Lower High
    LL = "LL"  # Lower Low
    UNDEFINED = "UNK" # Initial state


@dataclass
class SwingPoint:
    """Represents a swing point in the market"""
    swing_type: SwingType
    price: float
    timestamp: datetime
    index: int  # Position in dataframe
    confirmed: bool = False
    structure_level: str = "external"  # "external" (major structure) or "internal" (within-leg moves)
    is_high: bool = True  # True = swing high, False = swing low (Phase 3 ATR methods)
    
    def __repr__(self):
        # Ensure timestamp is datetime before formatting
        ts = self.timestamp if isinstance(self.timestamp, datetime) else pd.Timestamp(self.timestamp)
        level_tag = f" [{self.structure_level}]" if self.structure_level == "internal" else ""
        return f"{self.swing_type.value} {self.price:.2f} @ {ts.strftime('%y/%m/%d %H:%M')}{level_tag}"


@dataclass
class MarketState:
    """Persistent market state for price position-based structure detection (v13.0)"""
    last_swing_high: Optional[float] = None        # Price of most recent high swing
    last_swing_low: Optional[float] = None         # Price of most recent low swing
    last_swing_high_time: Optional[datetime] = None # When it occurred
    last_swing_low_time: Optional[datetime] = None  # When it occurred
    recent_swings: List[SwingPoint] = field(default_factory=list)  # Last 6 swings
    
    # Current market state from price position
    current_market_structure: MarketStructure = MarketStructure.BULLISH
    
    # Break tracking
    last_broken_level: Optional[float] = None      # Where was structure last broken?
    last_break_direction: Optional[str] = None     # "UP" or "DOWN"
    break_confirmation_bars: int = 0               # How many bars since break was confirmed?
    
    def update_from_swing(self, swing: SwingPoint):
        """Update market state when a new swing is detected"""
        if swing.swing_type in [SwingType.HH, SwingType.LH]:
            self.last_swing_high = swing.price
            self.last_swing_high_time = swing.timestamp
        elif swing.swing_type in [SwingType.LL, SwingType.HL]:
            self.last_swing_low = swing.price
            self.last_swing_low_time = swing.timestamp
        
        # Keep recent swings list (max 6)
        self.recent_swings.append(swing)
        if len(self.recent_swings) > 6:
            self.recent_swings.pop(0)
    
    def get_current_price_structure(self, current_price: float) -> MarketStructure:
        """
        Determine market structure from current price position (v13.0).
        This is the key innovation - use PRICE POSITION relative to recent levels.
        """
        if self.last_swing_high is None or self.last_swing_low is None:
            return MarketStructure.BULLISH  # Default assumption
        
        # Check if price broke beyond recent levels
        if current_price > self.last_swing_high:
            return MarketStructure.BULLISH
        elif current_price < self.last_swing_low:
            return MarketStructure.BEARISH
        else:
            # Price is within range - check which is closer
            distance_to_high = self.last_swing_high - current_price
            distance_to_low = current_price - self.last_swing_low
            
            if distance_to_low < distance_to_high:
                return MarketStructure.BULLISH  # Closer to high = bullish
            else:
                return MarketStructure.BEARISH  # Closer to low = bearish


@dataclass
class Leg:
    """Represents a market leg (move from one swing to another)"""
    leg_id: int
    leg_type: LegType
    start_swing: SwingPoint
    end_swing: SwingPoint
    duration_candles: int = 0
    price_move: float = 0.0
    price_move_pct: float = 0.0
    
    # Minor structure within this leg
    minor_swings: List[SwingPoint] = field(default_factory=list)
    
    def __post_init__(self):
        self.duration_candles = self.end_swing.index - self.start_swing.index
        self.price_move = abs(self.end_swing.price - self.start_swing.price)
        if self.start_swing.price > 0:
            self.price_move_pct = (self.price_move / self.start_swing.price) * 100
    
    def __repr__(self):
        return f"Leg#{self.leg_id} {self.leg_type.value}: {self.start_swing} -> {self.end_swing}"


@dataclass
class StructureState:
    """Current market structure state"""
    # --- TRACEABILITY TICKET ---
    analysis_id: str  # Unique Ticket for this specific analysis run
    
    timeframe: str
    market_structure: MarketStructure
    current_leg: Optional[Leg] = None
    previous_legs: List[Leg] = field(default_factory=list)
    all_swings: List[SwingPoint] = field(default_factory=list)

    # Key levels
    last_HH: Optional[SwingPoint] = None
    last_HL: Optional[SwingPoint] = None
    last_LH: Optional[SwingPoint] = None
    last_LL: Optional[SwingPoint] = None

    # Structure break tracking
    last_choch: Optional[datetime] = None
    choch_index: Optional[int] = None            # bar index where CHoCH confirmed
    choch_swing: Optional['SwingPoint'] = None   # swing point that confirmed CHoCH (for debugging)

    # Two-timeframe CHOCH fields
    choch_detected: bool = False          # CHOCH happened (any age)
    choch_is_fresh: bool = False          # CHOCH is recent (timeframe-dependent)
    choch_bars_ago: Optional[int] = None  # How many bars since CHOCH

    # Legacy fields (kept for compatibility)
    structure_broken: bool = False        # Alias for choch_is_fresh
    choch_direction: Optional[str] = None  # 'bullish' or 'bearish' - direction of the CHoCH

    # Macro trend awareness
    macro_trend_direction: Optional[str] = None  # 'bullish', 'bearish', or None
    macro_trend_duration_hours: float = 0.0
    macro_trend_confidence: float = 0.0  # 0-1 confidence score
    
    # Source of Truth
    trend_source: str = "Swings"

    # === MOMENTUM DATA ===
    adx_value: float = 0.0
    atr_value: float = 0.0
    health_status: str = "UNKNOWN"


class StructureEngine:
    """
    Market Structure Detection Engine
    Identifies swings and classifies market structure
    """
    
    def __init__(self, config: Union[Dict, Any] = None):
        """Initialize StructureEngine"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Production flag: controls synthetic helpers and test-specific logic
        self.enable_test_helper = self._get_conf('enable_test_helper', False)

        # ==============================================================================
        # 1. DNA AMPLITUDE MAP (Derived from Market Profiler - STRICT MODE)
        # ==============================================================================
        # Logic: Minimum Swing Size = Approx Avg Impulse / 2 (or higher to filter noise)
        # We use strictly higher thresholds to ensure we capture MAJOR structure (~6 moves/day)
        self.AMPLITUDE_THRESHOLDS = {
            "Volatility 10 Index": 6,
            "Volatility 10 (1s) Index": 11,
            "Volatility 25 Index": 8,
            "Volatility 25 (1s) Index": 2153,
            "Volatility 50 (1s) Index": 1125,
            "Volatility 75 Index": 306,
            "Volatility 75 (1s) Index": 31,
            "Volatility 100 Index": 10,
            "Volatility 100 (1s) Index": 8
        }

        # 2. Detection: Lookback for fractal detection (default 5 for Major Swings)
        self.min_swing_points = self._get_conf('swing_lookback', 5)
        
        # 3. LOOKBACK MAP (FIX v13.1): Timeframe-aware fractal detection window
        # Prevents under-detection on M1 and over-strictness on H1
        self.LOOKBACK_MAP = {
            'M1': 3, '1min': 3, 'Minor': 3,
            'M5': 4, '5min': 4, '5m': 4,
            'M15': 5, '15min': 5, 'Major': 5, '15m': 5,
            'M30': 6, '30min': 6, '30m': 6,
            'H1': 7, '1h': 7,
            'H4': 8, '4h': 8,
            'D1': 10, '1d': 10,
        }
        
        # 4. Macro Threshold Multiplier (FIX v13.1): Configurable with safety cap
        # Prevents macro_threshold from being too large on high-volatility symbols
        self.macro_threshold_multiplier = self._get_conf('macro_threshold_multiplier', 3.0)

        # 5. History
        self.max_swings_history = 1000

        # Leg counter
        self.leg_counter = 0

        self.logger.info(f"StructureEngine initialized (Lookback={self.min_swing_points}, DNA Filtering Enabled)")

    def _get_conf(self, key, default):
        """Helper to handle both Dict and Object config formats"""
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)
    
    # ==================== NEW: EMA CALCULATION ====================
    def _add_ema(self, df: pd.DataFrame, period: int = 200):
        """Adds EMA 200 to dataframe for fallback logic"""
        if 'ema_200' not in df.columns:
            df['ema_200'] = df['close'].ewm(span=period, adjust=False).mean()
        return df


    # ==================== SWING POINT DETECTION ====================
    
    def identify_swing_points(self,
                             data: pd.DataFrame,
                             timeframe: str = '15min',
                             lookback: int = None,
                             min_size_pips: float = 0.0) -> List[SwingPoint]:
        """
        Identify swing points (highs and lows) in OHLC data.
        Uses Fractal Geometry with Proximity Cleaning and DNA Size Filtering.
        
        FIX (v13.1): Uses timeframe-aware LOOKBACK_MAP to scale detection window.
        - M1/Minor: 3-candle window (7 total candles)
        - M5: 4-candle window (9 total candles)
        - M15/Major: 5-candle window (11 total candles)
        - M30: 6-candle window (13 total candles)
        - H1: 7-candle window (15 total candles)
        """
        try:
            # Use timeframe-aware lookback from LOOKBACK_MAP (FIX v13.1)
            if lookback is None:
                lookback = self.LOOKBACK_MAP.get(timeframe, self.min_swing_points)

            # Need lookback bars on left + current + lookback bars on right
            if len(data) < lookback * 2 + 1:
                return []

            swings = []

            # Use NumPy for faster detection logic
            highs = data['high'].values
            lows = data['low'].values
            dates = data.index
            
            # Ensure dates are datetime objects (handle both datetime index and integer index)
            if not isinstance(dates, pd.DatetimeIndex):
                dates = pd.to_datetime(dates, errors='coerce')

            # --- PHASE 1: RAW DETECTION (N-Candle Fractals) ---
            for i in range(lookback, len(data) - lookback):
                current_high = highs[i]
                current_low_val = lows[i]

                # Fractal High: High > all bars in lookback window on both sides
                is_swing_high = True
                for j in range(1, lookback + 1):
                    if current_high <= highs[i - j] or current_high <= highs[i + j]:
                        is_swing_high = False
                        break

                if is_swing_high:
                    swings.append(SwingPoint(
                        swing_type=SwingType.HH,  # Temp type (High)
                        price=current_high,
                        timestamp=dates[i],
                        index=i,
                        confirmed=True
                    ))

                # Fractal Low: Low < all bars in lookback window on both sides
                is_swing_low = True
                for j in range(1, lookback + 1):
                    if current_low_val >= lows[i - j] or current_low_val >= lows[i + j]:
                        is_swing_low = False
                        break

                if is_swing_low:
                    swings.append(SwingPoint(
                        swing_type=SwingType.LL,  # Temp type (Low)
                        price=current_low_val,
                        timestamp=dates[i],
                        index=i,
                        confirmed=True
                    ))

            swings.sort(key=lambda x: x.index)

            # --- PHASE 2: DNA SIZE FILTERING (Remove micro-swings) ---
            # If min_size_pips is provided (from DNA map), use it.
            if min_size_pips > 0 and len(swings) >= 2:
                swings = self._filter_swings_by_size(swings, min_size_pips)

            # --- PHASE 3: SMART CLEANUP ---
            clean_swings = self._cleanup_swings(swings)

            # --- PHASE 4: CLASSIFY ---
            classified_swings = self._classify_swings(clean_swings)

            self.logger.info(f"Identified {len(classified_swings)} structural swings in {timeframe} (lookback={lookback}, min_size={min_size_pips:.2f})")

            return classified_swings

        except Exception as e:
            self.logger.error(f"Error identifying swing points: {str(e)}")
            return []

    def _filter_swings_by_size(self, swings: List[SwingPoint], min_size: float) -> List[SwingPoint]:
        """
        Filter and classify swings by structure level (external vs internal).
        
        SMART MONEY STRUCTURE (v13.2):
        - EXTERNAL: Major structural swings (for market structure classification & CHoCH)
        - INTERNAL: Swings within a leg (for entry timing, order blocks, fair value gaps)
        
        Instead of REJECTING shallow reversals, we TAG them as "internal".
        This preserves information for multi-timeframe analysis and entry precision.
        
        Example: High at 200, Low at 180, High at 185
        - Prior leg: 200 down to 180 = 20 points
        - Retracement to 185: 185-180 = 5 points
        - Retracement ratio: 5/20 = 25% < 33% threshold
        - ACTION: Tag 185 as [INTERNAL] instead of rejecting
        - USE: Major structure ignores 185 (uses only external), but entry logic can use 185 for precision
        """
        if len(swings) < 2:
            return swings

        # Minimum retracement ratio to qualify as EXTERNAL structure
        # (33% = one-third of the prior leg must be retraced for external classification)
        MIN_RETRACEMENT_RATIO = self._get_conf('min_retracement_ratio', 0.33)

        # Process all swings, classifying by level instead of rejecting
        filtered = [swings[0]]  # Always keep the first swing (mark as external)
        filtered[0].structure_level = "external"
        
        last_high = swings[0] if swings[0].swing_type in [SwingType.HH, SwingType.LH] else None
        last_low = swings[0] if swings[0].swing_type in [SwingType.LL, SwingType.HL] else None

        for curr in swings[1:]:
            is_high = curr.swing_type in [SwingType.HH, SwingType.LH]
            ref = last_high if is_high else last_low

            # --- CHECK 1: DNA SIZE (same kind comparison) ---
            if ref is not None and abs(curr.price - ref.price) < min_size:
                # Move is too small — tag as internal and continue
                curr.structure_level = "internal"
                filtered.append(curr)
                continue

            # --- CHECK 2: RETRACEMENT VALIDATION ---
            # Determine if this swing represents meaningful external structure
            is_external = True  # Assume external unless proven otherwise
            
            if is_high and last_high is not None and last_low is not None:
                prior_leg_size = abs(last_high.price - last_low.price)
                retracement_up = abs(curr.price - last_low.price)

                if prior_leg_size > 0:
                    retracement_ratio = retracement_up / prior_leg_size
                    if retracement_ratio < MIN_RETRACEMENT_RATIO:
                        is_external = False  # Shallow high — internal structure

            elif not is_high and last_low is not None and last_high is not None:
                prior_leg_size = abs(last_low.price - last_high.price)
                retracement_down = abs(curr.price - last_high.price)

                if prior_leg_size > 0:
                    retracement_ratio = retracement_down / prior_leg_size
                    if retracement_ratio < MIN_RETRACEMENT_RATIO:
                        is_external = False  # Shallow low — internal structure
            
            # Tag according to classification
            curr.structure_level = "external" if is_external else "internal"
            filtered.append(curr)
            
            # Update last_high and last_low for BOTH external and internal
            # (internal swings still affect price position tracking)
            if is_high:
                last_high = curr
            else:
                last_low = curr

        return filtered
    
    
    def _cleanup_swings(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """
        Smartly merges adjacent swings of the same type ONLY if they are close in time.
        """
        if not swings:
            return []
            
        cleaned = []
        current_group = [swings[0]]
        
        for i in range(1, len(swings)):
            s = swings[i]
            last_s = current_group[-1]
            
            # Check types: Highs with Highs, Lows with Lows
            # We assume initial types HH/LL from detection
            is_same_type_direction = (last_s.swing_type == s.swing_type) or \
                                     (last_s.swing_type in [SwingType.HH, SwingType.LH] and s.swing_type in [SwingType.HH, SwingType.LH]) or \
                                     (last_s.swing_type in [SwingType.LL, SwingType.HL] and s.swing_type in [SwingType.LL, SwingType.HL])
            
            # Check Proximity: Are they within 5 candles?
            is_close = (s.index - last_s.index) < 5
            
            if is_same_type_direction and is_close:
                # Merge into group (it's likely noise/flat top)
                current_group.append(s)
            else:
                # Resolve previous group
                best_swing = self._resolve_group(current_group)
                cleaned.append(best_swing)
                # Start new group
                current_group = [s]
        
        # Resolve final group
        if current_group:
            cleaned.append(self._resolve_group(current_group))
            
        return cleaned


    def _resolve_group(self, group: List[SwingPoint]) -> SwingPoint:
        """Find the extreme point in a group"""
        if not group: return None
        if len(group) == 1: return group[0]
        
        # If Highs, return max price
        if group[0].swing_type in [SwingType.HH, SwingType.LH]:
            return max(group, key=lambda x: x.price)
        # If Lows, return min price
        else:
            return min(group, key=lambda x: x.price)
    
    
    def _classify_swings(self, swings: List[SwingPoint], current_price: Optional[float] = None) -> List[SwingPoint]:
        """
        Classify swings as HH, HL, LH, or LL by comparing ONLY swings of the same type.
        
        CRITICAL FIX (v13.1): Maintain separate tracking for highs and lows.
        This prevents misclassification when alternating between peaks and troughs.
        - HH: High > previous high (compare high to high only)
        - HL: Low > previous low (compare low to low only)  
        - LH: High < previous high (compare high to high only)
        - LL: Low < previous low (compare low to low only)
        
        CHOCH correctly detects when structure changes from (HH/HL) to (LH/LL) or vice versa.
        """
        if len(swings) < 2:
            return swings

        classified = []
        last_high_swing = None
        last_low_swing = None

        for swing in swings:
            is_high = swing.swing_type in [SwingType.HH, SwingType.LH]

            if is_high:
                # Current swing is a HIGH - compare only to previous highs
                if last_high_swing is None:
                    swing.swing_type = SwingType.HH
                elif swing.price > last_high_swing.price:
                    swing.swing_type = SwingType.HH  # Higher High
                else:
                    swing.swing_type = SwingType.LH  # Lower High
                last_high_swing = swing
            else:
                # Current swing is a LOW - compare only to previous lows
                if last_low_swing is None:
                    swing.swing_type = SwingType.HL
                elif swing.price < last_low_swing.price:
                    swing.swing_type = SwingType.LL  # Lower Low
                else:
                    swing.swing_type = SwingType.HL  # Higher Low
                last_low_swing = swing

            classified.append(swing)

        return classified
    
    def detect_break_of_structure(self, current_price: float, close_price: float) -> Optional[Dict[str, Any]]:
        """
        Detect if price has broken a swing level, indicating a change in market structure.
        
        Returns:
            Dict with break info if detected, None otherwise
        """
        if not hasattr(self, '_market_state'):
            return None
        
        state = self._market_state
        
        # Check for break BELOW (forming LL in bearish context)
        if state.last_swing_low and close_price < state.last_swing_low:
            return {
                'break_type': 'BELOW',
                'broken_level': state.last_swing_low,
                'current_price': current_price,
                'close_price': close_price,
                'direction': 'DOWN',
                'new_structure': MarketStructure.BEARISH,
                'message': f'Break below {state.last_swing_low:.2f} - Forming LL'
            }
        
        # Check for break ABOVE (forming HH in bullish context)
        if state.last_swing_high and close_price > state.last_swing_high:
            return {
                'break_type': 'ABOVE',
                'broken_level': state.last_swing_high,
                'current_price': current_price,
                'close_price': close_price,
                'direction': 'UP',
                'new_structure': MarketStructure.BULLISH,
                'message': f'Break above {state.last_swing_high:.2f} - Forming HH'
            }
        
        return None
    
    
    # ==================== STRUCTURE CLASSIFICATION (UPDATED) ====================
    
    def classify_market_structure(self, swings: List[SwingPoint], df: pd.DataFrame) -> Tuple[MarketStructure, str]:
        """
        Classify overall market structure based on swing pattern.
        
        FIX (v13.1): Uses fixed recency count (last 8 swings) instead of percentage.
        FIX (v13.2): Uses EXTERNAL swings only for structure classification.
        This ensures consistent behavior and ignores internal micro-moves within legs.
        """
        # TIER 1: SWING ANALYSIS (The Gold Standard)
        if len(swings) >= 4:
            # FIX v13.2: Filter to EXTERNAL swings only (ignore internal moves within legs)
            all_swings = [s for s in swings if s.structure_level == "external"]
            
            # Calculate weighted counts using FIXED recency window (last 8 swings)
            RECENT_SWING_COUNT = 8
            weights = []
            for i, s in enumerate(all_swings):
                # Recent swings (last 8 always) get 2x weight
                weight = 2.0 if i >= len(all_swings) - RECENT_SWING_COUNT else 1.0
                weights.append(weight)
            
            # Count HH/HL vs LH/LL with weight
            hh_count = sum(weights[i] for i, s in enumerate(all_swings) if s.swing_type == SwingType.HH)
            hl_count = sum(weights[i] for i, s in enumerate(all_swings) if s.swing_type == SwingType.HL)
            lh_count = sum(weights[i] for i, s in enumerate(all_swings) if s.swing_type == SwingType.LH)
            ll_count = sum(weights[i] for i, s in enumerate(all_swings) if s.swing_type == SwingType.LL)
            
            bullish_signals = hh_count + hl_count
            bearish_signals = lh_count + ll_count
            
            # Debug: Log the counts for diagnosis
            self.logger.debug(f"Structure classification: HH={hh_count:.1f}, HL={hl_count:.1f}, LH={lh_count:.1f}, LL={ll_count:.1f} (total swings={len(all_swings)}, recent={RECENT_SWING_COUNT})")
            
            # Determine structure
            if bullish_signals > bearish_signals:
                return MarketStructure.BULLISH, "Swings"
            elif bearish_signals > bullish_signals:
                return MarketStructure.BEARISH, "Swings"
            else:
                pass 
        
        # TIER 2: EMA FALLBACK (The Fix for 'Unknown')
        has_ema_col = 'ema_200' in df.columns and not pd.isna(df.iloc[-1]['ema_200'])
        
        if has_ema_col or len(df) > 50: 
            current_price = df.iloc[-1]['close']
            ema_200 = df.iloc[-1]['ema_200'] if has_ema_col else df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
            
            if current_price > ema_200:
                return MarketStructure.BULLISH, "EMA_Fallback"
            else:
                return MarketStructure.BEARISH, "EMA_Fallback"
                
        return MarketStructure.UNKNOWN, "None"
    
    
    def classify_leg_type(self, 
                          start_swing: SwingPoint, 
                          end_swing: SwingPoint,
                          market_structure: MarketStructure) -> LegType:
        """Classify a leg as Impulsive or Corrective based on GEOMETRY"""
        # Logic Fix v11.1: Leg type is determined by price direction relative to trend
        is_up = end_swing.price > start_swing.price
        
        if market_structure == MarketStructure.BULLISH:
            return LegType.BULLISH_IMPULSIVE if is_up else LegType.BULLISH_CORRECTIVE
        elif market_structure == MarketStructure.BEARISH:
            return LegType.BEARISH_CORRECTIVE if is_up else LegType.BEARISH_IMPULSIVE
        else:
            # Fallback geometry
            return LegType.BULLISH_IMPULSIVE if is_up else LegType.BEARISH_IMPULSIVE
    
    
    # ==================== LEG CREATION (HISTORICAL REPLAY) ====================
    
    def create_legs_from_swings(self, 
                               swings: List[SwingPoint],
                               final_structure: MarketStructure) -> List[Leg]:
        """
        Create leg objects from consecutive swing points.
        UPDATED v11.2: Historical Replay Logic to assign correct trend state to past legs.
        """
        if len(swings) < 2:
            return []
        
        legs = []
        current_replay_trend = MarketStructure.UNKNOWN # Start neutral
        
        # We need to replay the structure formation to label past legs correctly
        # Instead of painting everything with the FINAL structure.
        
        self.leg_counter = 0
        
        for i in range(len(swings) - 1):
            start = swings[i]
            end = swings[i + 1]
            
            # 1. Update Trend State based on the swing that just formed (start)
            if start.swing_type == SwingType.HH:
                current_replay_trend = MarketStructure.BULLISH
            elif start.swing_type == SwingType.LL:
                current_replay_trend = MarketStructure.BEARISH
            elif start.swing_type == SwingType.HL and current_replay_trend == MarketStructure.UNKNOWN:
                current_replay_trend = MarketStructure.BULLISH # Optimistic assumption
            elif start.swing_type == SwingType.LH and current_replay_trend == MarketStructure.UNKNOWN:
                current_replay_trend = MarketStructure.BEARISH # Optimistic assumption
            
            # If still unknown, use geometry or fallback to final structure
            trend_context = current_replay_trend if current_replay_trend != MarketStructure.UNKNOWN else final_structure
            
            leg_type = self.classify_leg_type(start, end, trend_context)
            
            self.leg_counter += 1
            leg = Leg(
                leg_id=self.leg_counter,
                leg_type=leg_type,
                start_swing=start,
                end_swing=end
            )
            legs.append(leg)
        
        return legs
    
    
    # ==================== STRUCTURE BREAKS (CHOCH) ====================
    
    def detect_structure_break(self, 
                             swings: List[SwingPoint],
                             current_structure: MarketStructure) -> Tuple[bool, Optional[MarketStructure], Optional[SwingPoint]]:
        """
        Detect Change of Character (CHOCH) with improved robustness.
        
        FIX (v13.1): Returns the actual break swing, not just boolean.
        FIX (v13.2): Uses EXTERNAL swings only to detect major structure breaks.
        This ensures CHoCH detection is based on true structural moves, not internal noise.
        """
        if len(swings) < 4:
            return False, None, None
        
        # FIX v13.2: Filter to EXTERNAL swings only (ignore internal structure)
        external_swings = [s for s in swings if s.structure_level == "external"]
        if len(external_swings) < 4:
            return False, None, None
        
        # Use wider window for detection (not just last 4)
        recent = external_swings[-10:] if len(external_swings) >= 10 else external_swings[-4:]
        
        if current_structure == MarketStructure.BEARISH:
            # Bullish CHoCH: HH forms that breaks above the most recent prior LH
            hhs = [s for s in recent if s.swing_type == SwingType.HH]
            if not hhs:
                return False, None, None
            
            last_hh = hhs[-1]
            prior_lhs = [s for s in recent if s.swing_type == SwingType.LH and s.index < last_hh.index]
            if not prior_lhs:
                return False, None, None
            
            last_lh = prior_lhs[-1]
            if last_hh.price > last_lh.price:
                return True, MarketStructure.BULLISH, last_hh  # Return the break swing
        
        elif current_structure == MarketStructure.BULLISH:
            # Bearish CHoCH: LL forms that breaks below the most recent prior HL
            lls = [s for s in recent if s.swing_type == SwingType.LL]
            if not lls:
                return False, None, None
            
            last_ll = lls[-1]
            prior_hls = [s for s in recent if s.swing_type == SwingType.HL and s.index < last_ll.index]
            if not prior_hls:
                return False, None, None
            
            last_hl = prior_hls[-1]
            if last_ll.price < last_hl.price:
                return True, MarketStructure.BEARISH, last_ll  # Return the break swing
        
        return False, None, None

    def check_major_choch(self, state: StructureState) -> Tuple[bool, str]:
        """
        Check if major structure (15-min) has valid CHOCH for trend direction.
        CHOCH can be up to 100 bars old.

        Returns: (is_valid, message)
        """
        if not state.choch_detected:
            return False, "No major CHOCH detected"

        if state.choch_bars_ago is None:
            return False, "CHOCH age unknown"

        if state.choch_bars_ago > 100:
            return False, f"Major CHOCH too old ({state.choch_bars_ago} bars)"

        return True, f"Major CHOCH valid ({state.choch_direction}, {state.choch_bars_ago} bars ago)"

    def check_minor_choch(self, state: StructureState) -> Tuple[bool, str]:
        """
        Check if minor structure (1-min) has fresh CHOCH for entry timing.
        CHOCH must be within last 15 bars.

        Returns: (is_valid, message)
        """
        if not state.choch_is_fresh:
            return False, "No fresh minor CHOCH"

        if state.choch_bars_ago is None:
            return False, "CHOCH age unknown"

        if state.choch_bars_ago > 15:
            return False, f"Minor CHOCH not fresh ({state.choch_bars_ago} bars old)"

        return True, f"Minor CHOCH fresh ({state.choch_direction}, {state.choch_bars_ago} bars ago)"

    # ==================== AUTO-GENERATED TRAINING DATA ====================
    def log_structure_state(self, symbol: str, structure: StructureState):
        """No-op in crypto engine — CSV logging disabled."""
        pass


    # ==================== MOMENTUM & HEALTH CHECKS ====================

    def _calculate_momentum(self, df: pd.DataFrame, period: int = 14):
        """Calculates ADX and ATR for internal health checks"""
        df = df.copy()
        
        # Ensure float type to avoid pandas/numpy issues
        df['close'] = df['close'].astype(np.float64)
        df['high'] = df['high'].astype(np.float64)
        df['low'] = df['low'].astype(np.float64)
        
        # 1. ATR - use values to avoid index alignment issues
        h_l = (df['high'].values - df['low'].values).astype(np.float64)
        h_pc = np.abs(df['high'].values - np.roll(df['close'].values, 1)).astype(np.float64)
        l_pc = np.abs(df['low'].values - np.roll(df['close'].values, 1)).astype(np.float64)
        
        tr = np.maximum(np.maximum(h_l, h_pc), l_pc)
        df['tr'] = pd.Series(tr, index=df.index)
        df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()

        # 2. ADX - use values for calculation
        up = np.diff(df['high'].values, prepend=df['high'].values[0]).astype(np.float64)
        down = -np.diff(df['low'].values, prepend=df['low'].values[0]).astype(np.float64)
        
        dm_plus = np.where((up > down) & (up > 0), up, 0.0).astype(np.float64)
        dm_minus = np.where((down > up) & (down > 0), down, 0.0).astype(np.float64)
        
        df['+dm'] = pd.Series(dm_plus, index=df.index)
        df['-dm'] = pd.Series(dm_minus, index=df.index)
        
        alpha = 1 / period
        df['tr_s'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        df['+dm_s'] = df['+dm'].ewm(alpha=alpha, adjust=False).mean()
        df['-dm_s'] = df['-dm'].ewm(alpha=alpha, adjust=False).mean()
        
        # Avoid division by zero
        tr_s_safe = df['tr_s'].replace(0, 1e-10)
        df['+di'] = 100.0 * (df['+dm_s'] / tr_s_safe)
        df['-di'] = 100.0 * (df['-dm_s'] / tr_s_safe)
        
        sum_di = df['+di'] + df['-di']
        sum_di_safe = sum_di.replace(0, 1)
        df['dx'] = 100.0 * np.abs(df['+di'] - df['-di']) / sum_di_safe
        df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()
        
        return df

    def check_market_health(self, df: pd.DataFrame, structure_state: StructureState) -> str:
        """Returns the health status of the current trend"""
        if 'adx' in df.columns and df.iloc[-1]['adx'] > 0:
            adx = df.iloc[-1]['adx']
            return "SLEEPING" if adx < 20 else "HEALTHY"

        if len(df) < 20: return "UNKNOWN"
        
        df = self._calculate_momentum(df)
        current = df.iloc[-1]
        prev = df.iloc[-5] 
        
        adx = current['adx']
        adx_slope = adx - prev['adx']
        
        if adx < 20:
            return "SLEEPING"
            
        if structure_state.market_structure == MarketStructure.BULLISH:
            if structure_state.last_HH and structure_state.last_HH.index >= (len(df) - 5):
                if adx_slope < -2.0: 
                    return "EXHAUSTED"
                    
        elif structure_state.market_structure == MarketStructure.BEARISH:
            if structure_state.last_LL and structure_state.last_LL.index >= (len(df) - 5):
                if adx_slope < -2.0:
                    return "EXHAUSTED"
        
        return "HEALTHY"


    # ==================== MAIN ANALYSIS FUNCTION (UPDATED FOR SYMBOL) ====================
    
    def analyze_structure(self, 
                          data: pd.DataFrame, 
                          timeframe: str = '15min',
                          symbol: str = "Unknown") -> StructureState:
        """
        Complete structure analysis of OHLC data with TRACEABILITY TICKET.
        UPDATED: Accepts 'symbol' to apply DNA Filtering.
        """
        try:
            # 1. GENERATE TICKET
            # Ensure last index is datetime
            last_idx = data.index[-1]
            if not isinstance(last_idx, (pd.Timestamp, datetime)):
                last_idx = pd.Timestamp(last_idx)
            timestamp_str = last_idx.strftime('%Y%m%d_%H%M')
            short_uuid = str(uuid.uuid4())[:4]
            
            # Normalize symbol name if passed as None or default
            if symbol == "Unknown" and hasattr(data, "name") and data.name:
                symbol = str(data.name)
            
            ticket = f"ANA_{symbol.replace(' ', '')}_{timestamp_str}_{short_uuid}"
            
            # Step 0: Add EMA (For Fallback)
            data = self._add_ema(data)
            
            # --- CALCULATE MOMENTUM EARLY ---
            mom_df = self._calculate_momentum(data)
            current_adx = mom_df.iloc[-1]['adx'] if 'adx' in mom_df.columns else 0.0
            current_atr = mom_df.iloc[-1]['atr'] if 'atr' in mom_df.columns else 0.0
            
            health = "HEALTHY"
            if current_adx < 20: 
                health = "SLEEPING"
            
            # --- STEP 1: GET DNA THRESHOLD ---
            # Lookup the minimum pip size for this symbol
            min_pips = self.AMPLITUDE_THRESHOLDS.get(symbol, 0.0)
            if min_pips == 0.0:
                # Try partial match (e.g. "Volatility 75" matching "Volatility 75 Index")
                for key, val in self.AMPLITUDE_THRESHOLDS.items():
                    if symbol in key or key in symbol:
                        min_pips = val
                        break

            # --- ADAPTIVE FALLBACK 1: Unknown crypto symbols → derive from ATR
            # Crypto assets (BTC, ETH, etc.) are not in AMPLITUDE_THRESHOLDS.
            # Use 1.0x ATR as the minimum swing size — naturally scales to volatility.
            try:
                if min_pips == 0.0 and current_atr > 0:
                    min_pips = current_atr * 1.0  # 1 ATR minimum swing size
                    self.logger.info(f"DNA threshold not found for '{symbol}', using ATR-based: {min_pips:.4f}")
            except Exception:
                pass

            # --- ADAPTIVE FALLBACK 2: If DNA threshold is absurdly large for this dataset,
            # scale it down relative to recent ATR to avoid filtering out all swings
            try:
                if min_pips > 0 and current_atr > 0:
                    # If DNA threshold is more than 4x the recent ATR, it's likely
                    # too strict for this data (synthetic or small-scale). Lower it.
                    if min_pips > (current_atr * 4):
                        adjusted = max(current_atr * 1.5, min_pips * 0.1)
                        self.logger.info(f"DNA min_pips ({min_pips:.2f}) is very large vs ATR ({current_atr:.2f}), adjusting -> {adjusted:.2f}")
                        min_pips = adjusted
            except Exception:
                # If anything goes wrong, keep original min_pips (safe fallback)
                pass
            
            # Step 2: Identify swing points (WITH FILTER)
            swings = self.identify_swing_points(data, timeframe, min_size_pips=min_pips)
            
            # Step 3: Classify market structure
            market_structure, source = self.classify_market_structure(swings, data)
            
            # Step 4: Create legs (WITH HISTORICAL REPLAY)
            legs = self.create_legs_from_swings(swings, market_structure)
            
            # Step 5: Detect structure breaks (ENHANCED FOR TWO-TIMEFRAME)
            structure_broken_detected, new_structure, break_swing = self.detect_structure_break(swings, market_structure)

            # Initialize CHOCH tracking variables
            choch_direction = None
            choch_index = None
            last_choch_time = None
            choch_swing = None
            choch_detected = False
            choch_is_fresh = False
            choch_bars_ago = None

            if structure_broken_detected and new_structure:
                self.logger.info(f"[{ticket}] CHOCH detected: {market_structure.value} -> {new_structure.value}")
                choch_direction = new_structure.value  # 'bullish' or 'bearish'
                market_structure = new_structure

                # Use the actual break swing returned from detect_structure_break (FIX v13.1)
                if break_swing:
                    choch_swing = break_swing
                    choch_index = choch_swing.index
                    last_choch_time = choch_swing.timestamp

                    # Calculate CHOCH age with timeframe-aware freshness
                    choch_bars_ago = len(data) - choch_index
                    choch_detected = True  # CHOCH happened

                    # Timeframe-aware freshness check (UPDATED FOR SCALPER MODE)
                    if timeframe in ['Major', '15min', '5min']:
                        # Major structure: CHOCH can be old (up to 100 bars)
                        freshness_window = 100
                    elif timeframe in ['Minor', '1min']:
                        # Entry timing: CHOCH must be fresh (15 bars = 15 minutes)
                        freshness_window = 15
                    else:
                        # Default
                        freshness_window = 20

                    choch_is_fresh = (choch_bars_ago <= freshness_window)

                    self.logger.info(f"[{ticket}] CHOCH age: {choch_bars_ago} bars (fresh={choch_is_fresh}, window={freshness_window})")

            # Legacy compatibility
            structure_broken = choch_is_fresh
            
            # Step 6: Build structure state WITH ENHANCED CHOCH TRACKING
            state = StructureState(
                analysis_id=ticket,  # <--- TICKET ISSUED
                timeframe=timeframe,
                market_structure=market_structure,
                all_swings=swings,
                previous_legs=legs[:-1] if len(legs) > 1 else [],
                current_leg=legs[-1] if legs else None,

                # ENHANCED CHOCH TRACKING:
                choch_detected=choch_detected,      # Did CHOCH happen?
                choch_is_fresh=choch_is_fresh,      # Is it recent?
                choch_bars_ago=choch_bars_ago,      # How long ago?
                structure_broken=choch_is_fresh,    # Legacy compatibility
                choch_direction=choch_direction,

                last_choch=last_choch_time,
                choch_index=choch_index,
                choch_swing=choch_swing,

                trend_source=source,

                # SAVE THE MATH
                adx_value=current_adx,
                atr_value=current_atr,
                health_status=health
            )
            
            # Step 7: Update key levels
            for swing in swings:
                if swing.swing_type == SwingType.HH:
                    if state.last_HH is None or swing.price > state.last_HH.price: state.last_HH = swing
                elif swing.swing_type == SwingType.HL:
                    if state.last_HL is None or swing.timestamp > state.last_HL.timestamp: state.last_HL = swing
                elif swing.swing_type == SwingType.LH:
                    if state.last_LH is None or swing.timestamp > state.last_LH.timestamp: state.last_LH = swing
                elif swing.swing_type == SwingType.LL:
                    if state.last_LL is None or swing.price < state.last_LL.price: state.last_LL = swing
            
            # Step 8: Detect macro trend
            self._detect_macro_trend(state, data, swings)

            # Log state for self-validation
            self.log_structure_state(symbol, state)

            # [DIAGNOSTIC v11.0] Log structure event for continuous improvement tracking
            try:
                from filter_diagnostics import get_diagnostics as _get_diag
                _diag = _get_diag()
                _cur_leg = state.current_leg
                _leg_val = getattr(getattr(_cur_leg, 'leg_type', None), 'value', 'unknown') if _cur_leg else 'unknown'
                _prev_legs = state.previous_legs or []
                _prev_leg_val = (getattr(getattr(_prev_legs[-1], 'leg_type', None), 'value', 'unknown')
                                 if _prev_legs else 'none')
                _diag.log_structure_event(
                    symbol=symbol,
                    timeframe=timeframe,
                    event_type='analysis_complete',
                    market_structure=state.market_structure.value,
                    leg_type=_leg_val,
                    prev_leg_type=_prev_leg_val,
                    n_swings=len(swings),
                    last_hh=state.last_HH.price if state.last_HH else 0,
                    last_hl=state.last_HL.price if state.last_HL else 0,
                    last_lh=state.last_LH.price if state.last_LH else 0,
                    last_ll=state.last_LL.price if state.last_LL else 0,
                    choch_direction=state.choch_direction or '',
                    choch_bars_ago=state.choch_bars_ago if state.choch_bars_ago is not None else -1,
                    choch_fresh=state.choch_is_fresh,
                    details=f"adx={current_adx:.1f} atr={current_atr:.5f} src={source} health={health}"
                )
            except Exception:
                pass

            return state

        except Exception as e:
            self.logger.error(f"Error in structure analysis: {str(e)}")
            
            # EMERGENCY FALLBACK
            error_ticket = f"ERR_{uuid.uuid4()}"
            try:
                data = self._add_ema(data)
                trend = MarketStructure.BULLISH if data.iloc[-1]['close'] > data.iloc[-1]['ema_200'] else MarketStructure.BEARISH
                return StructureState(
                    analysis_id=error_ticket,
                    timeframe=timeframe,
                    market_structure=trend,
                    trend_source="Crash_EMA"
                )
            except:
                return StructureState(
                    analysis_id=error_ticket,
                    timeframe=timeframe,
                    market_structure=MarketStructure.UNKNOWN
                )


    def _detect_macro_trend(self, state: StructureState, data: pd.DataFrame, swings: List[SwingPoint]):
        """
        Detect macro trend (10-12 hour sustained direction) using DNA analysis methodology.
        
        FIX (v13.1): Configurable macro_threshold_multiplier with ATR cap.
        This prevents the threshold from being too large on V75/V100.
        """
        try:
            if len(data) < 100: 
                return

            lookback = min(200, len(data))
            recent_data = data.tail(lookback)  # Don't reset index - keep original timestamps
            
            # Get high/low values as numpy arrays to avoid pandas issues
            closes = recent_data['close'].values.astype(np.float64)
            highs = recent_data['high'].values.astype(np.float64)
            lows = recent_data['low'].values.astype(np.float64)
            timestamps = recent_data.index.tolist()  # Keep timestamps as list

            avg_range = np.mean(highs - lows)
            macro_threshold = avg_range * self.macro_threshold_multiplier  # Use configurable multiplier
            
            # FIX: Add safety cap relative to ATR to prevent threshold from being too large
            current_atr = getattr(state, 'atr_value', 0)
            if current_atr > 0:
                max_threshold = current_atr * 5
                macro_threshold = min(macro_threshold, max_threshold) 

            macro_swings = []
            current_direction = 0 
            extreme_price = closes[0]
            extreme_time = timestamps[0]
            extreme_idx = 0

            # Use direct array indexing instead of iterrows()
            for i in range(len(closes)):
                close = closes[i]
                timestamp = timestamps[i]

                if current_direction == 0:
                    change = close - extreme_price
                    if abs(change) >= macro_threshold:
                        current_direction = 1 if change > 0 else -1
                        extreme_price = close
                        extreme_time = timestamp
                        extreme_idx = i

                elif current_direction == 1:  # Macro uptrend
                    if close > extreme_price:
                        extreme_price = close
                        extreme_time = timestamp
                        extreme_idx = i
                    elif (extreme_price - close) >= macro_threshold:
                        macro_swings.append({'time': extreme_time, 'price': extreme_price, 'type': 'high', 'index': extreme_idx})
                        current_direction = -1
                        extreme_price = close
                        extreme_time = timestamp
                        extreme_idx = i

                elif current_direction == -1:  # Macro downtrend
                    if close < extreme_price:
                        extreme_price = close
                        extreme_time = timestamp
                        extreme_idx = i
                    elif (close - extreme_price) >= macro_threshold:
                        macro_swings.append({'time': extreme_time, 'price': extreme_price, 'type': 'low', 'index': extreme_idx})
                        current_direction = 1
                        extreme_price = close
                        extreme_time = timestamp
                        extreme_idx = i

            if len(macro_swings) == 0:
                state.macro_trend_direction = None
                return

            last_macro_swing = macro_swings[-1]
            current_price = closes[-1]
            current_time = timestamps[-1]

            # Calculate trend duration safely
            time_diff = current_time - last_macro_swing['time']
            if hasattr(time_diff, 'total_seconds'):
                trend_duration_hours = time_diff.total_seconds() / 3600
            else:
                trend_duration_hours = 0.0

            if last_macro_swing['type'] == 'low':
                trend_direction = 'bullish'
                move_size = current_price - last_macro_swing['price']
            else:
                trend_direction = 'bearish'
                move_size = last_macro_swing['price'] - current_price
                
            move_ratio = move_size / macro_threshold if macro_threshold > 0 else 0
            confidence = min(0.95, 0.5 + (move_ratio * 0.15))

            if trend_duration_hours >= 6.0:
                state.macro_trend_direction = trend_direction
                state.macro_trend_duration_hours = trend_duration_hours
                state.macro_trend_confidence = confidence
            else:
                state.macro_trend_direction = None

        except Exception as e:
            self.logger.debug(f"Macro trend detection failed ({str(e)[:50]}), skipping")
            state.macro_trend_direction = None


    # ==================== MULTI-TIMEFRAME ANALYSIS ====================
    
    def analyze_multi_timeframe(self,
                               data_major: pd.DataFrame,
                               data_minor: pd.DataFrame,
                               symbol: str = None) -> Dict[str, StructureState]:
        """
        Analyze both major (Configured Major) and minor (1min) structure.
        Both data parameters are now required as data is fetched in TradingOrchestrator.
        """
        
        # Get Symbol Name (prioritize parameter over data attribute)
        if symbol is None:
            symbol = "Unknown"
            if hasattr(data_major, "name"): 
                symbol = str(data_major.name)
            
        # 1. Analyze Major Structure (Use 'Major' label instead of '15min')
        self.major_structure = self.analyze_structure(data_major, 'Major', symbol)
        
        # 2. Analyze Minor Structure (Use 'Minor' label instead of '1min')
        self.minor_structure = self.analyze_structure(data_minor, 'Minor', symbol)
        
        # 3. Correlate minor swings to major leg (if both exist)
        if self.major_structure.current_leg and self.minor_structure.all_swings:
            leg_start_time = self.major_structure.current_leg.start_swing.timestamp
            leg_end_time = self.major_structure.current_leg.end_swing.timestamp
            
            minor_swings_in_leg = [
                s for s in self.minor_structure.all_swings
                if leg_start_time <= s.timestamp <= leg_end_time
            ]
            
            self.major_structure.current_leg.minor_swings = minor_swings_in_leg
        
        return {
            'major': self.major_structure,
            'minor': self.minor_structure
        }
    
    
    # ==================== PHASE 3: ATR-ADAPTIVE ALGORITHMS ====================
    # Sourced from research library: Part 21 (ATR swing), Part 39 (os_state), Part 60 (trendlines)

    # ATR multiplier per timeframe for swing lookback (Part 21)
    _ATR_LOOSEN: Dict[str, float] = {
        '1m': 0.3, '3m': 0.35, '5m': 0.4, '15m': 0.5,
        '30m': 0.55, '1h': 0.6, '4h': 0.65, '1d': 0.7,
        'Major': 0.5, 'Minor': 0.35,
    }
    # ATR multiplier for trendline touch validation (Part 60)
    _TL_ATR_MULT: Dict[str, float] = {
        '1m': 0.8, '3m': 0.75, '5m': 0.7, '15m': 0.5,
        '30m': 0.45, '1h': 0.4, '4h': 0.35, '1d': 0.3,
        'Major': 0.5, 'Minor': 0.7,
    }

    def _atr_depth(self, atr: float, price: float, tf: str, multiplier: float = 1.0) -> int:
        """
        Part 21: ATR-proportional swing lookback.
        Converts ATR into a candle lookback that scales with volatility.
        """
        if price <= 0 or atr <= 0:
            return 3
        symbol_point = price * 1e-4  # ~0.01% of price as unit
        loosen = self._ATR_LOOSEN.get(tf, 0.5)
        raw = (atr / symbol_point) * multiplier
        depth = max(2, int(raw * loosen))
        # Cap at 2× the fixed LOOKBACK_MAP value to avoid ridiculous windows
        cap = self.LOOKBACK_MAP.get(tf, 5) * 2
        return min(depth, cap)

    def identify_swing_points_atr(
        self,
        df: pd.DataFrame,
        timeframe: str = '4h',
    ) -> List[SwingPoint]:
        """
        Part 21: ATR-adaptive swing detection.
        Replaces the fixed LOOKBACK_MAP with a volatility-scaled lookback.
        Delegates classification to the existing _classify_swings() method.
        """
        if len(df) < 10:
            return []

        # Calculate ATR
        mom_df = self._calculate_momentum(df)
        atr = float(mom_df['atr'].iloc[-1]) if 'atr' in mom_df.columns else 0.0
        last_price = float(df['close'].iloc[-1])
        lookback = self._atr_depth(atr, last_price, timeframe)

        highs = df['high'].values
        lows = df['low'].values
        timestamps = df.index.tolist()

        raw_swings: List[SwingPoint] = []
        for i in range(lookback, len(df) - lookback):
            window_h = highs[i - lookback: i + lookback + 1]
            window_l = lows[i - lookback: i + lookback + 1]

            is_swing_high = highs[i] == window_h.max()
            is_swing_low = lows[i] == window_l.min()

            if is_swing_high and not is_swing_low:
                sp = SwingPoint(
                    swing_type=SwingType.HH,   # temp type; _classify_swings relies on HH/LH to identify highs
                    price=float(highs[i]),
                    timestamp=timestamps[i],
                    index=i,
                    structure_level='external',
                    is_high=True,
                )
                raw_swings.append(sp)
            elif is_swing_low and not is_swing_high:
                sp = SwingPoint(
                    swing_type=SwingType.LL,   # temp type; _classify_swings relies on LL/HL to identify lows
                    price=float(lows[i]),
                    timestamp=timestamps[i],
                    index=i,
                    structure_level='external',
                    is_high=False,
                )
                raw_swings.append(sp)

        # Re-use existing classification
        return self._classify_swings(raw_swings)

    # ── os_state BOS/CHoCH state machine (Part 39) ───────────────────────────

    def detect_bos_choch_os_state(
        self,
        swings: List[SwingPoint],
    ) -> List[Dict[str, Any]]:
        """
        Part 39: os_state (+1/-1) state machine for BOS/CHoCH detection.
        Cleaner than threshold-based logic:
          - Same direction break → BOS (continuation)
          - Opposite direction break → CHoCH (reversal)

        Returns list of break events: [{type, level, swing_idx, direction}]
        """
        events: List[Dict[str, Any]] = []
        os_state: int = 0  # 0 = uninitialised

        # Separate highs and lows in order
        highs = [s for s in swings if getattr(s, 'is_high', True) and s.swing_type in (SwingType.HH, SwingType.LH, SwingType.UNDEFINED)]
        lows  = [s for s in swings if not getattr(s, 'is_high', True) and s.swing_type in (SwingType.HL, SwingType.LL, SwingType.UNDEFINED)]

        # Walk swings in chronological order
        prev_high: Optional[SwingPoint] = None
        prev_low: Optional[SwingPoint] = None

        for s in sorted(swings, key=lambda x: x.index):
            is_high = getattr(s, 'is_high', s.swing_type in (SwingType.HH, SwingType.LH))

            if is_high:
                if prev_high is not None and s.price > prev_high.price:
                    # Bullish break
                    direction = +1
                    if os_state == 0:
                        os_state = direction
                        ev_type = 'NONE'
                    elif direction == os_state:
                        ev_type = 'BOS'
                    else:
                        ev_type = 'CHOCH'
                        os_state = direction
                    if ev_type != 'NONE':
                        events.append({
                            'type': ev_type,
                            'direction': 'bullish',
                            'level': prev_high.price,
                            'swing_idx': s.index,
                            'timestamp': s.timestamp,
                        })
                prev_high = s
            else:
                if prev_low is not None and s.price < prev_low.price:
                    # Bearish break
                    direction = -1
                    if os_state == 0:
                        os_state = direction
                        ev_type = 'NONE'
                    elif direction == os_state:
                        ev_type = 'BOS'
                    else:
                        ev_type = 'CHOCH'
                        os_state = direction
                    if ev_type != 'NONE':
                        events.append({
                            'type': ev_type,
                            'direction': 'bearish',
                            'level': prev_low.price,
                            'swing_idx': s.index,
                            'timestamp': s.timestamp,
                        })
                prev_low = s

        return events

    # ── Objective trendlines (Part 60) ────────────────────────────────────────

    def fit_trendlines(
        self,
        df: pd.DataFrame,
        timeframe: str = '4h',
        min_touches: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Part 60: Fit objective trendlines to swing highs (resistance) and swing
        lows (support) using ATR-validated touch counts.

        Returns:
            {
                'support':    [{'slope', 'intercept', 'start_idx', 'end_idx',
                                'start_price', 'end_price', 'touches', 'type'}, ...],
                'resistance': [...]
            }
        """
        if len(df) < 20:
            return {'support': [], 'resistance': []}

        mom_df = self._calculate_momentum(df)
        atr = float(mom_df['atr'].iloc[-1]) if 'atr' in mom_df.columns else 0.0
        tl_atr_mult = self._TL_ATR_MULT.get(timeframe, 0.5)
        touch_threshold = atr * tl_atr_mult

        # Use ATR-adaptive swings for anchor points
        swings = self.identify_swing_points_atr(df, timeframe)

        highs = [s for s in swings if getattr(s, 'is_high', s.swing_type in (SwingType.HH, SwingType.LH))]
        lows  = [s for s in swings if not getattr(s, 'is_high', s.swing_type in (SwingType.HL, SwingType.LL))]

        support_lines    = self._fit_trendline_set(df, lows,  'support',    touch_threshold, min_touches)
        resistance_lines = self._fit_trendline_set(df, highs, 'resistance', touch_threshold, min_touches)

        return {'support': support_lines, 'resistance': resistance_lines}

    def _fit_trendline_set(
        self,
        df: pd.DataFrame,
        anchors: List[SwingPoint],
        line_type: str,
        touch_threshold: float,
        min_touches: int,
    ) -> List[Dict[str, Any]]:
        """
        Internal: try each pair of anchor points as a trendline seed, count
        validated touches within ATR band, keep lines with >= min_touches.
        """
        if len(anchors) < 2:
            return []

        highs  = df['high'].values
        lows   = df['low'].values
        n      = len(df)
        lines: List[Dict[str, Any]] = []

        for i in range(len(anchors) - 1):
            for j in range(i + 1, len(anchors)):
                a, b = anchors[i], anchors[j]
                if a.index == b.index:
                    continue

                slope = (b.price - a.price) / (b.index - a.index)
                intercept = a.price - slope * a.index

                # Direction validation (Part 60 rule)
                if line_type == 'support' and slope < 0:
                    continue  # support must be ascending or flat
                if line_type == 'resistance' and slope > 0:
                    continue  # resistance must be descending or flat

                # Count touches between the two anchor indices (inclusive)
                touches = 0
                for k in range(a.index, min(b.index + 1, n)):
                    expected = slope * k + intercept
                    if line_type == 'support':
                        dist = abs(lows[k] - expected)
                    else:
                        dist = abs(highs[k] - expected)
                    if dist <= touch_threshold:
                        touches += 1

                if touches >= min_touches:
                    end_idx = min(b.index, n - 1)
                    lines.append({
                        'type': line_type,
                        'slope': round(slope, 6),
                        'intercept': round(intercept, 4),
                        'start_idx': a.index,
                        'end_idx': end_idx,
                        'start_price': round(a.price, 4),
                        'end_price': round(slope * end_idx + intercept, 4),
                        'touches': touches,
                    })

        # De-duplicate: keep highest-touch line per start anchor
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for tl in sorted(lines, key=lambda x: -x['touches']):
            key = tl['start_idx']
            if key not in seen:
                seen.add(key)
                unique.append(tl)

        return unique

    # ── MTF harmony index (Parts 48/52) ──────────────────────────────────────

    _MTF_WEIGHTS: Dict[str, float] = {
        '1d': 0.40, '4h': 0.35, '1h': 0.30, '15m': 0.25, '5m': 0.10,
        'Major': 0.35, 'Minor': 0.25,
    }

    def compute_mtf_harmony(
        self,
        tf_structures: Dict[str, 'StructureState'],
    ) -> Dict[str, Any]:
        """
        Parts 48/52: Weighted multi-TF harmony index.
        tf_structures: {timeframe_str → StructureState}
        Returns harmony score (0-1), consensus direction, and per-TF breakdown.
        """
        bull_score = 0.0
        bear_score = 0.0
        total_weight = 0.0
        breakdown: Dict[str, str] = {}

        for tf, state in tf_structures.items():
            w = self._MTF_WEIGHTS.get(tf, 0.2)
            direction = state.market_structure.value  # 'bullish' / 'bearish' / other
            if direction == 'bullish':
                bull_score += w
            elif direction == 'bearish':
                bear_score += w
            total_weight += w
            breakdown[tf] = direction

        if total_weight == 0:
            return {'harmony': 0.0, 'direction': 'neutral', 'breakdown': breakdown}

        bull_norm = bull_score / total_weight
        bear_norm = bear_score / total_weight

        if bull_norm > bear_norm:
            consensus = 'bullish'
            harmony = bull_norm
        elif bear_norm > bull_norm:
            consensus = 'bearish'
            harmony = bear_norm
        else:
            consensus = 'neutral'
            harmony = 0.5

        return {
            'harmony': round(harmony, 3),
            'direction': consensus,
            'bull_weight': round(bull_norm, 3),
            'bear_weight': round(bear_norm, 3),
            'breakdown': breakdown,
        }

    # ==================== UTILITY METHODS ====================

    def get_current_structure_state(self, timeframe: str = 'major') -> Optional[StructureState]:
        """Get current structure state for timeframe"""
        if timeframe == 'major':
            return self.major_structure
        elif timeframe == 'minor':
            return self.minor_structure
        return None
    
    
    def print_structure_summary(self, state: StructureState):
        """Print readable structure summary"""
        print("\n" + "="*70)
        print(f"STRUCTURE ANALYSIS [{state.analysis_id}] - {state.timeframe.upper()}")
        print("="*70)
        
        print(f"\nMarket Structure: {state.market_structure.value.upper()}")
        print(f"Trend Source: {state.trend_source}")
        
        if state.structure_broken:
            print("⚠ STRUCTURE BREAK DETECTED (CHOCH)")
        
        if state.macro_trend_direction:
             print(f"Macro Trend: {state.macro_trend_direction.upper()} ({state.macro_trend_duration_hours:.1f}h)")
        
        print(f"\nKey Levels:")
        if state.last_HH: print(f"  Last HH: {state.last_HH}")
        if state.last_HL: print(f"  Last HL: {state.last_HL}")
        if state.last_LH: print(f"  Last LH: {state.last_LH}")
        if state.last_LL: print(f"  Last LL: {state.last_LL}")
        
        print(f"\nTotal Swings: {len(state.all_swings)}")
        print(f"Total Legs: {len(state.previous_legs) + (1 if state.current_leg else 0)}")
        
        if state.current_leg:
            print(f"\nCurrent Leg:")
            print(f"  {state.current_leg}")
            print(f"  Duration: {state.current_leg.duration_candles} candles")
            print(f"  Move: {state.current_leg.price_move:.2f} ({state.current_leg.price_move_pct:.2f}%)")
        
        print("\n" + "="*70)


# ==================== TESTING FUNCTIONS ====================

def test_structure_engine():
    """Test StructureEngine with sample data"""
    print("=" * 70)
    print("TESTING STRUCTURE ENGINE (FULL DIAGNOSTIC)")
    print("=" * 70)
    
    from datetime import datetime, timedelta
    
    # Sample bullish market data
    dates = pd.date_range(start='2025-12-05', periods=500, freq='15min')
    
    np.random.seed(42)
    base_price = 5400
    prices = []
    current_price = base_price
    
    for i in range(500):
        if i % 50 < 30:  # Impulsive move up
            current_price += np.random.uniform(5, 15)
        else:  # Corrective move down
            current_price -= np.random.uniform(2, 8)
        prices.append(current_price)
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 10) for p in prices],
        'low': [p - np.random.uniform(0, 10) for p in prices],
        'close': [p + np.random.uniform(-5, 5) for p in prices],
        'volume': np.random.randint(100, 1000, 500)
    }, index=dates)
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    data.name = "Volatility 75 Index"  # Test specific symbol mapping
    
    print(f"\n✓ Created sample data: {len(data)} bars")
    
    # Initialize StructureEngine
    print("\nInitializing StructureEngine...")
    engine = StructureEngine()
    print("✓ StructureEngine initialized")
    
    # Analyze structure
    print("\nAnalyzing market structure...")
    state = engine.analyze_structure(data, '15min', str(data.name))
    
    # Print results
    engine.print_structure_summary(state)
    
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    if state.analysis_id.startswith("ANA_"):
        print(f"✓ Ticket Generated: {state.analysis_id}")
    else:
        print("✗ Traceability Ticket Missing")

    if state.market_structure != MarketStructure.UNKNOWN:
        print("✓ Market structure detected")
    else:
        print("✗ Failed to detect market structure")
    
    if len(state.all_swings) > 0:
        print(f"✓ Swings detected: {len(state.all_swings)}")
    else:
        print("✗ No swings detected")
        
    print("\n" + "="*70)
    print("STRUCTURE ENGINE TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_structure_engine()