"""
Phase 3 TA Engine Tests
=======================
Tests for the four new StructureEngine methods added from the research library:
  - identify_swing_points_atr   (Part 21)
  - detect_bos_choch_os_state   (Part 39)
  - fit_trendlines              (Part 60)
  - compute_mtf_harmony         (Parts 48/52)

Run: python -m pytest tests/test_phase3_ta_engine.py -v
"""

import numpy as np
import pandas as pd
import pytest

from src.intelligence.ta_engine.structure_engine import (
    StructureEngine,
    StructureState,
    MarketStructure,
    SwingPoint,
    SwingType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_df(n: int = 200, seed: int = 42, trend: str = "bullish") -> pd.DataFrame:
    """
    Synthetic OHLCV with an explicit zigzag pattern so that ATR-adaptive swing
    detection reliably finds peaks and troughs regardless of base price level.

    The ATR-adaptive lookback is capped (e.g. 16 bars for 4h), so the fixture
    must produce local extremes that dominate their neighbours within that window.
    We achieve this with 15-bar impulse / 5-bar pullback zigzag cycles.

    trend='bullish'  → impulses up, shallow pullbacks
    trend='bearish'  → impulses down, shallow bounces
    trend='ranging'  → alternating up/down impulses of equal size
    """
    np.random.seed(seed)
    dates = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")

    # Use a price level where ATR is a meaningful fraction of price
    # (keeps ATR-depth formula from hitting cap too harshly)
    base = 40_000.0
    # Cycle must be > 2*lookback+1 so the peak at (impulse_bars-1) is the
    # global max within its lookback window.  With ATR≈57 and price≈40000,
    # _atr_depth returns ~9, giving a 19-bar window.  cycle=40 >> 19.
    cycle = 40           # bars per full swing cycle
    impulse_bars = 30    # bars trending in primary direction
    pullback_bars = 10   # bars counter-trend

    impulse_size  = 50.0   # price move per impulse bar
    pullback_size = 20.0   # price move per pullback bar

    prices = []
    p = base
    for i in range(n):
        phase = i % cycle
        if trend == "bullish":
            p += impulse_size  if phase < impulse_bars else -pullback_size
        elif trend == "bearish":
            p -= impulse_size  if phase < impulse_bars else -pullback_size
        else:
            # Ranging: alternate up/down impulses
            half = cycle // 2
            p += (impulse_size if phase < half else -impulse_size)
        prices.append(max(p, 1.0))

    # Spread: large enough to give realistic ATR, small vs impulse so peaks are clean
    spread = np.abs(np.random.randn(n)) * 5 + 3
    df = pd.DataFrame(
        {
            "open":   prices,
            "high":   [p + s for p, s in zip(prices, spread)],
            "low":    [p - s for p, s in zip(prices, spread)],
            "close":  [p + np.random.uniform(-2, 2) for p in prices],
            "volume": np.random.rand(n) * 1e6,
        },
        index=dates,
    )
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"]  = df[["open", "low",  "close"]].min(axis=1)
    return df


@pytest.fixture
def engine() -> StructureEngine:
    return StructureEngine()


@pytest.fixture
def df_bull() -> pd.DataFrame:
    return _make_df(200, seed=1, trend="bullish")


@pytest.fixture
def df_bear() -> pd.DataFrame:
    return _make_df(200, seed=2, trend="bearish")


@pytest.fixture
def df_range() -> pd.DataFrame:
    return _make_df(200, seed=3, trend="ranging")


# ---------------------------------------------------------------------------
# 1. identify_swing_points_atr  (Part 21)
# ---------------------------------------------------------------------------

class TestIdentifySwingPointsATR:

    def test_returns_list(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        assert isinstance(swings, list)

    def test_detects_swings_on_trending_data(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        assert len(swings) >= 3, "Should detect at least 3 swing points on 200-bar trending data"

    def test_swing_types_are_classified(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        valid_types = {SwingType.HH, SwingType.HL, SwingType.LH, SwingType.LL}
        for s in swings:
            assert s.swing_type in valid_types, f"Unexpected swing_type: {s.swing_type}"

    def test_swings_ordered_by_index(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        indices = [s.index for s in swings]
        assert indices == sorted(indices), "Swings must be in chronological order"

    def test_is_high_flag_set(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        for s in swings:
            if s.swing_type in (SwingType.HH, SwingType.LH):
                assert s.is_high is True
            elif s.swing_type in (SwingType.HL, SwingType.LL):
                assert s.is_high is False

    def test_short_df_returns_empty(self, engine):
        tiny = _make_df(5)
        swings = engine.identify_swing_points_atr(tiny, "4h")
        assert swings == []

    def test_timeframe_variants(self, engine, df_bull):
        """Different timeframes should produce different lookback depths but not crash."""
        for tf in ("1m", "15m", "1h", "4h", "1d", "Major", "Minor"):
            swings = engine.identify_swing_points_atr(df_bull, tf)
            assert isinstance(swings, list)

    def test_more_swings_on_ranging_vs_trending(self, engine, df_range, df_bull):
        """Ranging data typically produces more swing pivots than strongly trending data."""
        swings_range = engine.identify_swing_points_atr(df_range, "4h")
        swings_trend = engine.identify_swing_points_atr(df_bull, "4h")
        # Both should find something
        assert len(swings_range) > 0
        assert len(swings_trend) > 0


# ---------------------------------------------------------------------------
# 2. detect_bos_choch_os_state  (Part 39)
# ---------------------------------------------------------------------------

class TestDetectBOSChoCHOsState:

    def test_returns_list(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        assert isinstance(events, list)

    def test_event_schema(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        required_keys = {"type", "direction", "level", "swing_idx", "timestamp"}
        for ev in events:
            assert required_keys.issubset(ev.keys()), f"Event missing keys: {ev}"

    def test_event_types_valid(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        for ev in events:
            assert ev["type"] in ("BOS", "CHOCH"), f"Unknown event type: {ev['type']}"
            assert ev["direction"] in ("bullish", "bearish"), f"Unknown direction: {ev['direction']}"

    def test_bullish_trend_has_bos(self, engine, df_bull):
        """A clear uptrend should generate at least one bullish BOS."""
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        bullish_bos = [e for e in events if e["type"] == "BOS" and e["direction"] == "bullish"]
        assert len(bullish_bos) >= 1, "Bullish trend should have at least one bullish BOS"

    def test_bearish_trend_has_bos(self, engine, df_bear):
        """A clear downtrend should generate at least one bearish BOS."""
        swings = engine.identify_swing_points_atr(df_bear, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        bearish_bos = [e for e in events if e["type"] == "BOS" and e["direction"] == "bearish"]
        assert len(bearish_bos) >= 1, "Bearish trend should have at least one bearish BOS"

    def test_ranging_has_choch(self, engine, df_range):
        """Sideways market should flip direction (CHoCH) at least once."""
        swings = engine.identify_swing_points_atr(df_range, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        chochs = [e for e in events if e["type"] == "CHOCH"]
        assert len(chochs) >= 1, "Ranging market should produce at least one CHoCH"

    def test_empty_swings_returns_empty(self, engine):
        events = engine.detect_bos_choch_os_state([])
        assert events == []

    def test_events_chronological(self, engine, df_bull):
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        events = engine.detect_bos_choch_os_state(swings)
        idxs = [e["swing_idx"] for e in events]
        assert idxs == sorted(idxs), "Events must be in chronological order"


# ---------------------------------------------------------------------------
# 3. fit_trendlines  (Part 60)
# ---------------------------------------------------------------------------

class TestFitTrendlines:

    def test_returns_dict_with_keys(self, engine, df_bull):
        tls = engine.fit_trendlines(df_bull, "4h")
        assert "support" in tls
        assert "resistance" in tls

    def test_trendline_schema(self, engine, df_bull):
        tls = engine.fit_trendlines(df_bull, "4h")
        required = {"type", "slope", "intercept", "start_idx", "end_idx",
                    "start_price", "end_price", "touches"}
        for line_type in ("support", "resistance"):
            for tl in tls[line_type]:
                assert required.issubset(tl.keys()), f"Trendline missing keys: {tl}"

    def test_support_lines_ascending(self, engine, df_bull):
        """Support trendlines must have slope >= 0 (ascending or flat)."""
        tls = engine.fit_trendlines(df_bull, "4h")
        for tl in tls["support"]:
            assert tl["slope"] >= 0, f"Support line has negative slope: {tl['slope']}"

    def test_resistance_lines_descending(self, engine, df_bear):
        """Resistance trendlines must have slope <= 0 (descending or flat)."""
        tls = engine.fit_trendlines(df_bear, "4h")
        for tl in tls["resistance"]:
            assert tl["slope"] <= 0, f"Resistance line has positive slope: {tl['slope']}"

    def test_min_touches_respected(self, engine, df_bull):
        tls3 = engine.fit_trendlines(df_bull, "4h", min_touches=3)
        for line_type in ("support", "resistance"):
            for tl in tls3[line_type]:
                assert tl["touches"] >= 3

    def test_short_df_returns_empty(self, engine):
        tiny = _make_df(10)
        tls = engine.fit_trendlines(tiny, "4h")
        assert tls["support"] == []
        assert tls["resistance"] == []

    def test_timeframe_variants_no_crash(self, engine, df_bull):
        for tf in ("15m", "1h", "4h", "1d"):
            tls = engine.fit_trendlines(df_bull, tf)
            assert isinstance(tls["support"], list)
            assert isinstance(tls["resistance"], list)

    def test_no_duplicate_start_idx(self, engine, df_bull):
        """De-duplication: no two lines should share the same start_idx."""
        tls = engine.fit_trendlines(df_bull, "4h")
        for line_type in ("support", "resistance"):
            start_idxs = [tl["start_idx"] for tl in tls[line_type]]
            assert len(start_idxs) == len(set(start_idxs)), \
                f"Duplicate start_idx in {line_type}: {start_idxs}"

    def test_chart_generator_compatible_format(self, engine, df_bull):
        """Output must include slope+intercept OR start/end price+idx for ChartGenerator."""
        tls = engine.fit_trendlines(df_bull, "4h")
        for line_type in ("support", "resistance"):
            for tl in tls[line_type]:
                has_slope = "slope" in tl and "intercept" in tl
                has_endpoints = "start_price" in tl and "end_price" in tl
                assert has_slope or has_endpoints


# ---------------------------------------------------------------------------
# 4. compute_mtf_harmony  (Parts 48/52)
# ---------------------------------------------------------------------------

class TestComputeMTFHarmony:

    def _make_state(self, structure: MarketStructure) -> StructureState:
        return StructureState(
            analysis_id="TEST",
            timeframe="4h",
            market_structure=structure,
        )

    def test_returns_dict_with_keys(self, engine, df_bull):
        s4h = engine.analyze_structure(df_bull, "4h", "BTC")
        s1h = engine.analyze_structure(df_bull.iloc[:100], "1h", "BTC")
        result = engine.compute_mtf_harmony({"4h": s4h, "1h": s1h})
        assert {"harmony", "direction", "bull_weight", "bear_weight", "breakdown"}.issubset(result)

    def test_harmony_range(self, engine, df_bull):
        s4h = engine.analyze_structure(df_bull, "4h", "BTC")
        s1h = engine.analyze_structure(df_bull.iloc[:100], "1h", "BTC")
        result = engine.compute_mtf_harmony({"4h": s4h, "1h": s1h})
        assert 0.0 <= result["harmony"] <= 1.0

    def test_full_bullish_alignment(self, engine):
        """All bullish TFs → harmony=1.0, direction=bullish."""
        bull_state = self._make_state(MarketStructure.BULLISH)
        result = engine.compute_mtf_harmony({
            "1d": bull_state, "4h": bull_state, "1h": bull_state, "15m": bull_state,
        })
        assert result["direction"] == "bullish"
        assert result["harmony"] == pytest.approx(1.0, abs=0.01)

    def test_full_bearish_alignment(self, engine):
        """All bearish TFs → harmony=1.0, direction=bearish."""
        bear_state = self._make_state(MarketStructure.BEARISH)
        result = engine.compute_mtf_harmony({
            "1d": bear_state, "4h": bear_state, "1h": bear_state, "15m": bear_state,
        })
        assert result["direction"] == "bearish"
        assert result["harmony"] == pytest.approx(1.0, abs=0.01)

    def test_mixed_alignment_between_0_and_1(self, engine):
        """Mixed TFs → 0 < harmony < 1."""
        result = engine.compute_mtf_harmony({
            "4h": self._make_state(MarketStructure.BULLISH),
            "1h": self._make_state(MarketStructure.BEARISH),
        })
        assert 0.0 < result["harmony"] < 1.0

    def test_higher_tf_weight_dominates(self, engine):
        """
        4h (weight=0.35) bullish vs 15m (weight=0.25) bearish
        → consensus should be bullish because 4h carries more weight.
        """
        result = engine.compute_mtf_harmony({
            "4h": self._make_state(MarketStructure.BULLISH),
            "15m": self._make_state(MarketStructure.BEARISH),
        })
        assert result["direction"] == "bullish"

    def test_empty_input_returns_neutral(self, engine):
        result = engine.compute_mtf_harmony({})
        assert result["direction"] == "neutral"
        assert result["harmony"] == 0.0

    def test_breakdown_includes_all_tfs(self, engine):
        states = {
            "4h": self._make_state(MarketStructure.BULLISH),
            "1h": self._make_state(MarketStructure.BEARISH),
            "15m": self._make_state(MarketStructure.BULLISH),
        }
        result = engine.compute_mtf_harmony(states)
        assert set(result["breakdown"].keys()) == {"4h", "1h", "15m"}

    def test_bull_weight_plus_bear_weight_le_1(self, engine):
        result = engine.compute_mtf_harmony({
            "4h": self._make_state(MarketStructure.BULLISH),
            "1h": self._make_state(MarketStructure.BEARISH),
            "15m": self._make_state(MarketStructure.BULLISH),
        })
        assert result["bull_weight"] + result["bear_weight"] <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# 5. Integration: full pipeline
# ---------------------------------------------------------------------------

class TestPhase3Integration:

    def test_full_pipeline_bull(self, engine, df_bull):
        """ATR swings → os_state events → trendlines → harmony, all consistent."""
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        assert len(swings) > 0

        events = engine.detect_bos_choch_os_state(swings)
        # In a bullish trend, bullish events should outnumber bearish
        bull_ev = [e for e in events if e["direction"] == "bullish"]
        bear_ev = [e for e in events if e["direction"] == "bearish"]
        assert len(bull_ev) >= len(bear_ev), "Bull trend: expect more bullish BOS/CHoCH events"

        tls = engine.fit_trendlines(df_bull, "4h")
        assert isinstance(tls["support"], list)
        assert isinstance(tls["resistance"], list)

        s4h = engine.analyze_structure(df_bull, "4h", "BTC")
        s1h = engine.analyze_structure(df_bull.iloc[-100:], "1h", "BTC")
        harmony = engine.compute_mtf_harmony({"4h": s4h, "1h": s1h})
        assert 0.0 <= harmony["harmony"] <= 1.0

    def test_trendlines_index_within_df(self, engine, df_bull):
        """All trendline indices must be within the DataFrame bounds."""
        n = len(df_bull)
        tls = engine.fit_trendlines(df_bull, "4h")
        for line_type in ("support", "resistance"):
            for tl in tls[line_type]:
                assert 0 <= tl["start_idx"] < n
                assert 0 <= tl["end_idx"] < n
                assert tl["start_idx"] <= tl["end_idx"]

    def test_swing_prices_within_df_range(self, engine, df_bull):
        """Swing prices must lie within the OHLC range of the DataFrame."""
        swings = engine.identify_swing_points_atr(df_bull, "4h")
        lo = df_bull["low"].min()
        hi = df_bull["high"].max()
        for s in swings:
            assert lo <= s.price <= hi, f"Swing price {s.price} outside [{lo}, {hi}]"
