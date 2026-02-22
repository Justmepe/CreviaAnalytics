"""
Indicators Module
=================
EMA, VWAP, RSI, ATR, VWV (Volume-Weighted Velocity), and entry alignment checks.
All functions accept a pandas DataFrame with OHLCV columns and return it enriched.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Core indicator calculations
# ---------------------------------------------------------------------------

def add_emas(df: pd.DataFrame, periods: list[int] = [3, 9, 20, 50, 200]) -> pd.DataFrame:
    """Add EMA columns for each period."""
    df = df.copy()
    for p in periods:
        if len(df) >= p:
            df[f'ema_{p}'] = df['close'].ewm(span=p, adjust=False).mean()
        else:
            df[f'ema_{p}'] = np.nan
    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add VWAP anchored to UTC calendar day.
    For crypto (24/7), resets every midnight UTC.
    """
    df = df.copy()
    tp = (df['high'] + df['low'] + df['close']) / 3

    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.normalize()  # truncate to day
    else:
        dates = pd.to_datetime(df.index, utc=True).normalize()

    tp_vol = tp * df['volume']
    cum_tpvol = tp_vol.groupby(dates).cumsum()
    cum_vol = df['volume'].groupby(dates).cumsum()
    df['vwap'] = cum_tpvol / cum_vol.replace(0, np.nan)
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add RSI column."""
    df = df.copy()
    if len(df) < period + 1:
        df['rsi'] = np.nan
        return df
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR column."""
    df = df.copy()
    h_l = df['high'] - df['low']
    h_pc = (df['high'] - df['close'].shift(1)).abs()
    l_pc = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1 / period, adjust=False).mean()
    return df


def add_volume_profile(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Add relative volume (current bar vs rolling average).
    rvol > 1.2 = above average volume (confirms momentum).
    """
    df = df.copy()
    df['vol_avg'] = df['volume'].rolling(window).mean()
    df['rvol'] = df['volume'] / df['vol_avg'].replace(0, np.nan)
    return df


def add_vwv(df: pd.DataFrame, atr_col: str = 'atr') -> pd.DataFrame:
    """
    Volume-Weighted Velocity (VWV) — adapted for real crypto volume.
    Measures momentum conviction: direction × energy weight.

    Signal Matrix:
      vel↓ + vol↓ → Exhaustion  ✅ Entry zone
      vel↓ + vol↑ → Absorption  ⏳ Wait
      vel↑ + vol↑ → Expansion   ❌ Skip (chasing)
      vel↑ + vol↓ → Weak push   ❌ Skip
    """
    df = df.copy()
    if atr_col not in df.columns:
        df = add_atr(df)

    safe_atr = df[atr_col].replace(0, np.nan)
    candle_range = (df['high'] - df['low']).abs()

    velocity = (df['close'] - df['open']) / safe_atr  # direction in ATR units
    vol_weight = candle_range / safe_atr               # energy weight

    df['vwv'] = velocity * vol_weight
    df['vwv_5'] = df['vwv'].rolling(5).mean()         # 5-bar VWV signal
    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience: add all indicators in one call."""
    df = add_emas(df, [3, 9, 20, 50, 200])
    df = add_atr(df)
    df = add_vwap(df)
    df = add_rsi(df)
    df = add_volume_profile(df)
    df = add_vwv(df)
    return df


# ---------------------------------------------------------------------------
# Entry alignment filters
# ---------------------------------------------------------------------------

def check_ema_alignment(df: pd.DataFrame, direction: str) -> dict:
    """
    Check if EMA stack is aligned for the given direction.

    LONG alignment:  close > EMA20 > EMA50
    SHORT alignment: close < EMA20 < EMA50

    Returns dict with alignment status and values.
    """
    last = df.iloc[-1]
    close = last['close']
    e20 = last.get('ema_20', np.nan)
    e50 = last.get('ema_50', np.nan)
    e200 = last.get('ema_200', np.nan)

    if direction.upper() == 'LONG':
        aligned = (
            not pd.isna(e20) and not pd.isna(e50) and
            close > e20 > e50
        )
        bias_note = 'above EMA20 and EMA50' if aligned else 'not aligned for LONG'
    else:
        aligned = (
            not pd.isna(e20) and not pd.isna(e50) and
            close < e20 < e50
        )
        bias_note = 'below EMA20 and EMA50' if aligned else 'not aligned for SHORT'

    return {
        'aligned': aligned,
        'note': bias_note,
        'close': close,
        'ema_20': None if pd.isna(e20) else round(e20, 4),
        'ema_50': None if pd.isna(e50) else round(e50, 4),
        'ema_200': None if pd.isna(e200) else round(e200, 4),
    }


def check_vwap_alignment(df: pd.DataFrame, direction: str) -> dict:
    """
    Check if price is on the correct side of VWAP.
    LONG: price above VWAP (buy-side bias)
    SHORT: price below VWAP (sell-side bias)
    """
    last = df.iloc[-1]
    close = last['close']
    vwap = last.get('vwap', np.nan)

    if pd.isna(vwap):
        return {'aligned': False, 'note': 'VWAP not available', 'vwap': None, 'close': close}

    if direction.upper() == 'LONG':
        aligned = close > vwap
        note = 'above VWAP' if aligned else 'below VWAP (unfavorable for LONG)'
    else:
        aligned = close < vwap
        note = 'below VWAP' if aligned else 'above VWAP (unfavorable for SHORT)'

    return {
        'aligned': aligned,
        'note': note,
        'vwap': round(vwap, 4),
        'close': close,
        'distance_pct': round((close - vwap) / vwap * 100, 3),
    }


def check_volume_confirmation(df: pd.DataFrame, threshold: float = 1.1) -> dict:
    """
    Check if recent volume confirms the move (above average).
    threshold: multiplier above avg vol to consider confirmed.
    """
    if 'rvol' not in df.columns:
        return {'confirmed': False, 'note': 'No volume data', 'rvol': None}

    last_rvol = df.iloc[-1].get('rvol', np.nan)
    if pd.isna(last_rvol):
        return {'confirmed': False, 'note': 'No volume data', 'rvol': None}

    confirmed = last_rvol >= threshold
    return {
        'confirmed': confirmed,
        'rvol': round(last_rvol, 2),
        'note': f'Volume {last_rvol:.1f}x avg ({("above" if confirmed else "below")} {threshold}x threshold)',
    }


def check_vwv_signal(df: pd.DataFrame, direction: str) -> dict:
    """
    Check VWV for exhaustion signal (good entry condition).
    Exhaustion (vel slowing + vol slowing) = momentum running out → reversal likely.
    """
    if 'vwv' not in df.columns or len(df) < 5:
        return {'signal': 'UNKNOWN', 'vwv': None, 'note': 'Insufficient data'}

    last = df.iloc[-1]
    vwv = last.get('vwv', np.nan)
    vwv_5 = last.get('vwv_5', np.nan)
    rvol = last.get('rvol', np.nan)

    if pd.isna(vwv) or pd.isna(rvol):
        return {'signal': 'UNKNOWN', 'vwv': None, 'note': 'No VWV data'}

    # Momentum is decelerating
    vel_decelerating = (vwv_5 > 0 > vwv) if direction.upper() == 'SHORT' else (vwv_5 < 0 < vwv)

    if vel_decelerating and rvol < 0.9:
        signal = 'EXHAUSTION'
        note = 'Velocity reversing + below-avg volume = exhaustion entry'
    elif vel_decelerating and rvol >= 1.5:
        signal = 'ABSORPTION'
        note = 'Velocity reversing but high volume = absorption, wait'
    elif not vel_decelerating and rvol >= 1.2:
        signal = 'EXPANSION'
        note = 'Momentum building, wait for pullback'
    else:
        signal = 'NEUTRAL'
        note = 'No strong VWV signal'

    return {
        'signal': signal,
        'vwv': round(vwv, 4),
        'vwv_5': round(vwv_5, 4) if not pd.isna(vwv_5) else None,
        'rvol': round(rvol, 2),
        'note': note,
        'favorable': signal in ('EXHAUSTION', 'NEUTRAL'),
    }


def check_adx_strength(df: pd.DataFrame) -> dict:
    """
    Check ADX trend strength.
    Uses StructureEngine's _calculate_momentum if ADX not pre-computed.
    """
    if 'adx' not in df.columns:
        # Compute inline
        try:
            period = 14
            df = df.copy()
            h_l = (df['high'] - df['low']).values
            h_pc = np.abs(df['high'].values - np.roll(df['close'].values, 1))
            l_pc = np.abs(df['low'].values - np.roll(df['close'].values, 1))
            tr = np.maximum(np.maximum(h_l, h_pc), l_pc)
            up = np.diff(df['high'].values, prepend=df['high'].values[0])
            down = -np.diff(df['low'].values, prepend=df['low'].values[0])
            dm_plus = np.where((up > down) & (up > 0), up, 0.0)
            dm_minus = np.where((down > up) & (down > 0), down, 0.0)
            alpha = 1 / period
            tr_s = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean()
            dmp_s = pd.Series(dm_plus).ewm(alpha=alpha, adjust=False).mean()
            dmm_s = pd.Series(dm_minus).ewm(alpha=alpha, adjust=False).mean()
            di_plus = 100 * dmp_s / tr_s.replace(0, 1e-10)
            di_minus = 100 * dmm_s / tr_s.replace(0, 1e-10)
            dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus).replace(0, 1)
            adx_val = float(dx.ewm(alpha=alpha, adjust=False).mean().iloc[-1])
        except Exception:
            adx_val = 0.0
    else:
        adx_val = float(df.iloc[-1]['adx'])

    return {
        'adx': round(adx_val, 1),
        'trending': adx_val > 20,
        'strong': adx_val > 25,
        'health': 'SLEEPING' if adx_val < 20 else ('STRONG' if adx_val > 25 else 'MODERATE'),
    }


def run_entry_filters(df: pd.DataFrame, direction: str) -> dict:
    """
    Run all entry filters and return combined result.
    Returns dict with per-filter results and an aggregate pass/fail.
    """
    df = add_all_indicators(df)

    ema = check_ema_alignment(df, direction)
    vwap = check_vwap_alignment(df, direction)
    vol = check_volume_confirmation(df)
    vwv = check_vwv_signal(df, direction)
    adx = check_adx_strength(df)

    last = df.iloc[-1]

    # Score each filter
    filters_passed = sum([
        ema['aligned'],
        vwap['aligned'],
        vol['confirmed'],
        vwv.get('favorable', False),
        adx['trending'],
    ])

    return {
        'direction': direction,
        'ema': ema,
        'vwap': vwap,
        'volume': vol,
        'vwv': vwv,
        'adx': adx,
        'rsi': round(last.get('rsi', 50), 1),
        'filters_passed': filters_passed,
        'filters_total': 5,
        'alignment_score': round(filters_passed / 5 * 100),  # 0-100
        'current_price': float(last['close']),
        'atr': round(float(last.get('atr', 0)), 4),
    }
