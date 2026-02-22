"""
TA Engine Test
==============
Tests the full pipeline end-to-end:
  1. OHLCV fetcher  (Binance public API)
  2. Indicators     (EMA, VWAP, RSI, ATR, VWV)
  3. CryptoTAEngine (structure + zones + entry filters)
  4. TradeSetupGenerator with TA context (optional - requires ANTHROPIC_API_KEY)

Run:
    python test_ta_engine.py
    python test_ta_engine.py BTC 4h          # custom ticker/timeframe
    python test_ta_engine.py ETH 1h --setup  # include Claude setup generation
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sep(title: str = "") -> None:
    width = 70
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'-' * pad} {title} {'-' * pad}")
    else:
        print("-" * width)


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _err(msg: str) -> None:
    print(f"  [ERR]  {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 - OHLCV Fetcher
# ─────────────────────────────────────────────────────────────────────────────

async def test_ohlcv(ticker: str, interval: str) -> "pd.DataFrame | None":
    from src.intelligence.ta_engine.ohlcv_fetcher import fetch_ohlcv, get_ltf, get_structure_label

    _sep("1 - OHLCV Fetcher")
    ltf = get_ltf(interval)
    label = get_structure_label(interval)
    print(f"  Ticker : {ticker}")
    print(f"  HTF    : {interval}  ->  label={label}")
    print(f"  LTF    : {ltf}")

    try:
        df = await fetch_ohlcv(ticker, interval, exchange='binance', limit=300)
        _ok(f"HTF fetched: {len(df)} bars  ({df.index[0].date()} -> {df.index[-1].date()})")
        print(f"       last close = ${df.iloc[-1]['close']:,.4f}")
        print(f"       volume avg = {df['volume'].mean():,.0f}")
        return df
    except Exception as e:
        _err(f"Fetch failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 - Indicators
# ─────────────────────────────────────────────────────────────────────────────

def test_indicators(df) -> None:
    from src.intelligence.ta_engine.indicators import add_all_indicators, run_entry_filters

    _sep("2 - Indicators")
    df = add_all_indicators(df.copy())
    last = df.iloc[-1]

    cols = [c for c in ['ema_9', 'ema_20', 'ema_50', 'ema_200', 'rsi', 'atr', 'vwap', 'rvol', 'vwv'] if c in df.columns]
    for col in cols:
        val = last.get(col)
        if val is not None:
            print(f"  {col:10s}: {val:.4f}")

    _sep("  entry filters (LONG)")
    ef = run_entry_filters(df, 'LONG')
    print(f"  Filters passed : {ef['filters_passed']}/{ef['filters_total']}")
    print(f"  Alignment score: {ef['alignment_score']}%")
    print(f"  RSI            : {ef['rsi']}")
    print(f"  EMA aligned    : {ef['ema']['aligned']}  ({ef['ema']['note']})")
    print(f"  VWAP aligned   : {ef['vwap']['aligned']}  ({ef['vwap']['note']})")
    print(f"  Volume confirm : {ef['volume']['confirmed']}  rvol={ef['volume'].get('rvol')}")
    print(f"  VWV signal     : {ef['vwv']['signal']}  ({ef['vwv']['note']})")
    print(f"  ADX            : {ef['adx']['adx']}  ({ef['adx']['health']})")

    _ok("Indicators OK")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 - CryptoTAEngine (full analysis)
# ─────────────────────────────────────────────────────────────────────────────

async def test_ta_engine(ticker: str, htf: str) -> dict:
    from src.intelligence.ta_engine import CryptoTAEngine

    _sep("3 - CryptoTAEngine")
    engine = CryptoTAEngine()

    print(f"  Analyzing {ticker} on {htf} HTF ...")
    result = await engine.analyze(ticker=ticker, htf=htf, exchange='binance')

    if result.get('error'):
        _err(f"Analysis error: {result['error']}")
        return result

    _ok(f"Analysis complete")

    # Structure
    st = result['structure']
    print(f"\n  STRUCTURE ({result['htf']})")
    if st.get('available'):
        print(f"    Trend    : {st['trend']}")
        print(f"    Health   : {st['health']}  (ADX={st['adx']})")
        kl = st.get('key_levels', {})
        if kl.get('last_HH'):
            print(f"    HH=${kl['last_HH']:,.4f}  HL=${kl.get('last_HL') or 0:,.4f}"
                  f"  LH=${kl.get('last_LH') or 0:,.4f}  LL=${kl.get('last_LL') or 0:,.4f}")
        if st.get('choch_is_fresh'):
            print(f"    >>> FRESH CHoCH ({st['choch_direction']}) - {st['choch_bars_ago']} bars ago >>>")
        if st.get('macro_trend'):
            print(f"    Macro    : {st['macro_trend']} ({st.get('macro_confidence', 0)*100:.0f}% confidence)")
    else:
        _warn("Structure not available")

    # Zones
    zones = result['zones']
    print(f"\n  ZONES ({result['htf']})")
    print(f"    Active: {zones['active_count']}  Broken: {zones['broken_count']}")
    bd = zones.get('best_demand')
    bs = zones.get('best_supply')
    if bd:
        print(f"    Best DEMAND : ${bd['price_bottom']:,.4f}-${bd['price_top']:,.4f}"
              f"  Q={bd['quality_score']:.0f}/100  {bd['location_label']}  [{bd['status']}]")
    else:
        _warn("No demand zones found")
    if bs:
        print(f"    Best SUPPLY : ${bs['price_bottom']:,.4f}-${bs['price_top']:,.4f}"
              f"  Q={bs['quality_score']:.0f}/100  {bs['location_label']}  [{bs['status']}]")
    else:
        _warn("No supply zones found")

    # Entry filters
    ef = result['entry_filters']
    print(f"\n  ENTRY FILTERS ({result['ltf']})")
    print(f"    Direction  : {result['direction']}")
    print(f"    Passed     : {ef.get('filters_passed', 0)}/{ef.get('filters_total', 5)}")
    print(f"    Alignment  : {ef.get('alignment_score', 0)}%")
    print(f"    RSI        : {ef.get('rsi', 'n/a')}")

    # Quality
    print(f"\n  SETUP QUALITY : {result['setup_quality']}/100")
    print(f"  CURRENT PRICE : ${result['current_price']:,.4f}")
    print(f"  ATR           : {result['atr']:.4f}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 - TradeSetupGenerator with TA context
# ─────────────────────────────────────────────────────────────────────────────

def test_trade_setup(ticker: str, ta_result: dict) -> None:
    _sep("4 - TradeSetupGenerator + TA context")
    from src.intelligence.trade_setup_generator import TradeSetupGenerator

    gen = TradeSetupGenerator()
    if not gen._enabled:
        _warn("ANTHROPIC_API_KEY not set - skipping setup generation")
        return

    print(f"  Generating setup for {ticker} ...")
    price = ta_result.get('current_price', 0)
    price_data = {
        'price_usd': price,
        'price_change_24h': 0.0,
        'high_24h': price * 1.03,
        'low_24h': price * 0.97,
    }

    setup = gen.generate_setup(
        ticker=ticker,
        price_data=price_data,
        ta_context=ta_result,
    )

    if not setup:
        _err("Setup generation failed")
        return

    _ok("Setup generated")
    print(f"\n  Direction  : {setup.get('direction')}")
    print(f"  Type       : {setup.get('setup_type')}")
    print(f"  Confidence : {setup.get('confidence', 0)*100:.0f}%")
    print(f"  TA Quality : {setup.get('ta_quality', 'n/a')}/100")

    print("\n  Entry Zones:")
    for ez in setup.get('entry_zones', []):
        print(f"    ${ez.get('price', 0):,.4f}  [{ez.get('type')}]  {ez.get('reason', '')}")

    sl = setup.get('stop_loss', {})
    print(f"\n  Stop Loss  : ${sl.get('price', 0):,.4f}  ({sl.get('distance_pct', 0):.2f}%)")

    print("\n  Take Profits:")
    for tp in setup.get('take_profits', []):
        print(f"    ${tp.get('price', 0):,.4f}  R/R={tp.get('rr')}  ({tp.get('percentage')}%)  {tp.get('reason', '')}")

    print("\n  Reasoning:")
    for r in setup.get('reasoning', []):
        print(f"    - {r}")

    print("\n  Risk Factors:")
    for rf in setup.get('risk_factors', []):
        print(f"    ! {rf}")

    if setup.get('position_sizing'):
        ps = setup['position_sizing']
        print(f"\n  Position Sizing (units per $X risk):")
        print(f"    $100 risk -> {ps.get('risk_100', 'n/a')} units")
        print(f"    $200 risk -> {ps.get('risk_200', 'n/a')} units")
        print(f"    $500 risk -> {ps.get('risk_500', 'n/a')} units")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    args = sys.argv[1:]
    ticker = args[0].upper() if len(args) > 0 else 'BTC'
    htf = args[1].lower() if len(args) > 1 else '4h'
    run_setup = '--setup' in args

    print("=" * 70)
    print(f"  CREVIA ANALYTICS - TA ENGINE TEST")
    print(f"  Asset: {ticker}  |  HTF: {htf}  |  Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. OHLCV
    df = await test_ohlcv(ticker, htf)
    if df is None:
        print("\nAborted - OHLCV fetch failed.")
        return

    # 2. Indicators (on the HTF data)
    try:
        test_indicators(df)
    except Exception as e:
        _err(f"Indicators failed: {e}")
        import traceback; traceback.print_exc()

    # 3. Full TA engine
    ta_result = {}
    try:
        ta_result = await test_ta_engine(ticker, htf)
    except Exception as e:
        _err(f"TA engine failed: {e}")
        import traceback; traceback.print_exc()

    # 4. Trade setup (optional)
    if run_setup and ta_result:
        try:
            test_trade_setup(ticker, ta_result)
        except Exception as e:
            _err(f"Trade setup failed: {e}")
            import traceback; traceback.print_exc()
    elif not run_setup:
        _sep("")
        print("  Tip: add --setup flag to also run Claude trade setup generation")

    _sep("DONE")
    print()


if __name__ == '__main__':
    asyncio.run(main())
