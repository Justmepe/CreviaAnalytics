"""
ChartGenerator
==============
Renders publication-quality candlestick charts with TA overlays to PNG.

Outputs:
  - Candlestick chart (4h or 1d timeframe)
  - EMA overlays (20, 50, 200)
  - VWAP line
  - Supply / demand zones (shaded rectangles)
  - Trendlines (support + resistance)
  - Entry / SL / TP levels (from trade setup)
  - RSI subplot
  - Volume bars (colour-coded)

Usage:
    from src.intelligence.ta_engine.chart_generator import ChartGenerator
    path = ChartGenerator.generate(ticker='BTC', interval='4h', output_dir='output/charts')
    # → 'output/charts/BTC_4h_20260308_1200.png'

    # With trade setup overlay:
    path = ChartGenerator.generate(
        ticker='BTC', interval='4h',
        setup={'direction': 'LONG', 'entry_zones': [...], 'stop_loss': {...}, 'take_profits': [...]},
        ta_context={'best_demand_zone': {...}, 'best_supply_zone': {...}, 'trendlines': {...}},
        output_dir='output/charts',
    )
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────────────────────────────
_BG       = '#0d1117'
_PANEL    = '#111520'
_BULL     = '#00d68f'
_BEAR     = '#f03e5a'
_NEUTRAL  = '#e8eaf0'
_DIM      = '#3d4562'
_EMA20    = '#3b82f6'
_EMA50    = '#f59e0b'
_EMA200   = '#8b5cf6'
_VWAP     = '#ec4899'
_DEMAND   = '#00d68f'
_SUPPLY   = '#f03e5a'
_ENTRY    = '#facc15'
_SL       = '#f03e5a'
_TP       = '#00d68f'
_TREND_S  = '#00d68f'
_TREND_R  = '#f03e5a'


def _try_import_matplotlib():
    """Import matplotlib with non-interactive backend (safe for server/VPS)."""
    import matplotlib
    matplotlib.use('Agg')  # must be before pyplot import
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.gridspec as gridspec
    return plt, mpatches, gridspec


class ChartGenerator:
    """
    Static factory — call ChartGenerator.generate() or ChartGenerator.generate_sync().
    No state; all logic is pure functions.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    async def generate(
        cls,
        ticker: str,
        interval: str = '4h',
        setup: Optional[Dict[str, Any]] = None,
        ta_context: Optional[Dict[str, Any]] = None,
        output_dir: str = 'output/charts',
        candle_count: int = 120,
    ) -> Optional[str]:
        """
        Async entry point. Fetches OHLCV, computes indicators, renders chart.
        Returns absolute path to the saved PNG, or None on failure.
        """
        try:
            from src.intelligence.ta_engine.ohlcv_fetcher import fetch_binance_ohlcv
            from src.intelligence.ta_engine.indicators import add_all_indicators

            df = await fetch_binance_ohlcv(ticker, interval=interval, limit=candle_count)
            df = add_all_indicators(df)
            return cls._render(ticker, interval, df, setup, ta_context, output_dir)
        except Exception as e:
            logger.warning(f"[ChartGenerator] Failed for {ticker} {interval}: {e}")
            return None

    @classmethod
    def generate_sync(
        cls,
        ticker: str,
        interval: str = '4h',
        df: Optional[pd.DataFrame] = None,
        setup: Optional[Dict[str, Any]] = None,
        ta_context: Optional[Dict[str, Any]] = None,
        output_dir: str = 'output/charts',
        candle_count: int = 120,
    ) -> Optional[str]:
        """
        Sync entry point — pass a pre-fetched DataFrame or let it fetch via asyncio.run().
        """
        try:
            if df is None:
                df = asyncio.run(cls._fetch_and_enrich(ticker, interval, candle_count))
            return cls._render(ticker, interval, df, setup, ta_context, output_dir)
        except Exception as e:
            logger.warning(f"[ChartGenerator] Sync render failed for {ticker} {interval}: {e}")
            return None

    # ── Internal ──────────────────────────────────────────────────────────────

    @classmethod
    async def _fetch_and_enrich(cls, ticker: str, interval: str, limit: int) -> pd.DataFrame:
        from src.intelligence.ta_engine.ohlcv_fetcher import fetch_binance_ohlcv
        from src.intelligence.ta_engine.indicators import add_all_indicators
        df = await fetch_binance_ohlcv(ticker, interval=interval, limit=limit)
        return add_all_indicators(df)

    @classmethod
    def _render(
        cls,
        ticker: str,
        interval: str,
        df: pd.DataFrame,
        setup: Optional[Dict],
        ta_context: Optional[Dict],
        output_dir: str,
    ) -> Optional[str]:
        plt, mpatches, gridspec = _try_import_matplotlib()

        try:
            # ── Layout ──────────────────────────────────────────────────────
            fig = plt.figure(figsize=(14, 8), facecolor=_BG)
            gs  = gridspec.GridSpec(
                3, 1, height_ratios=[4, 1, 1],
                hspace=0.04, top=0.93, bottom=0.06, left=0.07, right=0.97,
            )
            ax_price  = fig.add_subplot(gs[0])
            ax_volume = fig.add_subplot(gs[1], sharex=ax_price)
            ax_rsi    = fig.add_subplot(gs[2], sharex=ax_price)

            for ax in (ax_price, ax_volume, ax_rsi):
                ax.set_facecolor(_PANEL)
                ax.tick_params(colors=_DIM, labelsize=7)
                ax.spines[['top', 'right', 'left', 'bottom']].set_color('#1c2235')
                ax.yaxis.set_tick_params(labelright=True, labelleft=False)

            n = len(df)
            x = np.arange(n)

            # ── Candlesticks ─────────────────────────────────────────────────
            cls._draw_candles(ax_price, df, x)

            # ── EMA lines ────────────────────────────────────────────────────
            for col, color, lw, label in [
                ('ema_20',  _EMA20,  1.0, 'EMA20'),
                ('ema_50',  _EMA50,  1.2, 'EMA50'),
                ('ema_200', _EMA200, 1.4, 'EMA200'),
            ]:
                if col in df.columns:
                    vals = df[col].values
                    mask = ~np.isnan(vals)
                    if mask.any():
                        ax_price.plot(x[mask], vals[mask], color=color,
                                      linewidth=lw, alpha=0.85, label=label, zorder=2)

            # ── VWAP ─────────────────────────────────────────────────────────
            if 'vwap' in df.columns:
                vals = df['vwap'].values
                mask = ~np.isnan(vals)
                if mask.any():
                    ax_price.plot(x[mask], vals[mask], color=_VWAP, linewidth=1.0,
                                  linestyle='--', alpha=0.75, label='VWAP', zorder=2)

            # ── Supply / demand zones from ta_context ─────────────────────────
            if ta_context:
                cls._draw_zones(ax_price, ta_context, n)
                cls._draw_trendlines(ax_price, ta_context, df, x)

            # ── Trade setup levels ────────────────────────────────────────────
            if setup:
                cls._draw_setup_levels(ax_price, setup, x[-1])

            # ── Volume bars ───────────────────────────────────────────────────
            cls._draw_volume(ax_volume, df, x)

            # ── RSI ───────────────────────────────────────────────────────────
            cls._draw_rsi(ax_rsi, df, x)

            # ── X-axis labels (every ~20 candles) ────────────────────────────
            step = max(1, n // 8)
            tick_positions = x[::step]
            tick_labels = [
                df.index[i].strftime('%m/%d %H:%M') if isinstance(df.index[i], pd.Timestamp)
                else str(df.index[i])
                for i in range(0, n, step)
            ]
            ax_rsi.set_xticks(tick_positions)
            ax_rsi.set_xticklabels(tick_labels, rotation=30, ha='right', fontsize=6, color=_DIM)
            plt.setp(ax_price.get_xticklabels(), visible=False)
            plt.setp(ax_volume.get_xticklabels(), visible=False)

            # ── Title + legend ────────────────────────────────────────────────
            last_close = df['close'].iloc[-1]
            change_pct = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100 if n >= 2 else 0
            color_chg  = _BULL if change_pct >= 0 else _BEAR
            sign       = '+' if change_pct >= 0 else ''

            fig.suptitle(
                f"{ticker}/USDT  ·  {interval}  ·  ${last_close:,.2f}  ({sign}{change_pct:.2f}%)",
                color=_NEUTRAL, fontsize=11, fontweight='bold', x=0.07, ha='left',
            )

            # Colour the price number
            title_obj = fig.texts[-1]
            title_obj.set_color(_NEUTRAL)

            # Legend (price panel only)
            handles, labels = ax_price.get_legend_handles_labels()
            if handles:
                ax_price.legend(
                    handles, labels, loc='upper left',
                    fontsize=6.5, framealpha=0.25,
                    facecolor=_PANEL, edgecolor='#1c2235', labelcolor=_DIM,
                )

            # Timestamp watermark
            ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            fig.text(0.97, 0.01, f'creviacockpit.com  ·  {ts}',
                     ha='right', va='bottom', fontsize=6, color=_DIM, alpha=0.6)

            # ── Save ──────────────────────────────────────────────────────────
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            fname = f"{ticker}_{interval}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.png"
            fpath = os.path.join(output_dir, fname)
            fig.savefig(fpath, dpi=150, bbox_inches='tight', facecolor=_BG)
            plt.close(fig)
            logger.info(f"[ChartGenerator] Saved: {fpath}")
            return fpath

        except Exception as e:
            logger.error(f"[ChartGenerator] Render error: {e}", exc_info=True)
            try:
                plt.close('all')
            except Exception:
                pass
            return None

    # ── Drawing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _draw_candles(ax, df: pd.DataFrame, x: np.ndarray) -> None:
        """Draw OHLC candlesticks."""
        opens  = df['open'].values
        highs  = df['high'].values
        lows   = df['low'].values
        closes = df['close'].values

        width  = 0.6
        width2 = 0.08

        for i in range(len(x)):
            bull = closes[i] >= opens[i]
            color = _BULL if bull else _BEAR
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i]) or (highs[i] - lows[i]) * 0.001

            # Body
            ax.bar(x[i], body_height, width, bottom=body_bottom,
                   color=color, alpha=0.85, zorder=3)
            # Wick
            ax.plot([x[i], x[i]], [lows[i], highs[i]],
                    color=color, linewidth=width2 * 6, alpha=0.7, zorder=2)

    @staticmethod
    def _draw_volume(ax, df: pd.DataFrame, x: np.ndarray) -> None:
        """Draw volume bars coloured by candle direction."""
        opens  = df['open'].values
        closes = df['close'].values
        vols   = df['volume'].values

        colors = [_BULL if c >= o else _BEAR for o, c in zip(opens, closes)]
        ax.bar(x, vols, 0.7, color=colors, alpha=0.55, zorder=2)

        # Rolling average line
        if len(vols) >= 20:
            vol_ma = pd.Series(vols).rolling(20).mean().values
            mask = ~np.isnan(vol_ma)
            ax.plot(x[mask], vol_ma[mask], color=_DIM, linewidth=0.8, alpha=0.7)

        ax.set_ylabel('Vol', color=_DIM, fontsize=6, labelpad=2)
        ax.yaxis.set_major_formatter(
            lambda v, _: f'{v/1e6:.1f}M' if v >= 1e6 else f'{v/1e3:.0f}K'
        )

    @staticmethod
    def _draw_rsi(ax, df: pd.DataFrame, x: np.ndarray) -> None:
        """Draw RSI with overbought / oversold bands."""
        if 'rsi' not in df.columns:
            ax.set_visible(False)
            return

        rsi = df['rsi'].values
        mask = ~np.isnan(rsi)
        if not mask.any():
            ax.set_visible(False)
            return

        ax.plot(x[mask], rsi[mask], color='#a78bfa', linewidth=1.0, alpha=0.9)
        ax.axhline(70, color=_BEAR,   linewidth=0.5, linestyle='--', alpha=0.5)
        ax.axhline(30, color=_BULL,   linewidth=0.5, linestyle='--', alpha=0.5)
        ax.axhline(50, color=_DIM,    linewidth=0.4, linestyle=':', alpha=0.35)
        ax.fill_between(x[mask], rsi[mask], 70,
                        where=(rsi[mask] > 70), color=_BEAR, alpha=0.15)
        ax.fill_between(x[mask], rsi[mask], 30,
                        where=(rsi[mask] < 30), color=_BULL, alpha=0.15)
        ax.set_ylim(0, 100)
        ax.set_yticks([30, 50, 70])
        ax.set_ylabel('RSI', color=_DIM, fontsize=6, labelpad=2)

    @staticmethod
    def _draw_zones(ax, ta_context: Dict, n_candles: int) -> None:
        """Draw supply and demand zones as shaded rectangles."""
        demand = ta_context.get('best_demand_zone') or ta_context.get('demand_zone')
        supply = ta_context.get('best_supply_zone') or ta_context.get('supply_zone')

        for zone, color, label in [
            (demand, _DEMAND, 'Demand'),
            (supply, _SUPPLY, 'Supply'),
        ]:
            if not zone:
                continue
            try:
                bottom = float(zone.get('price_bottom') or zone.get('low', 0))
                top    = float(zone.get('price_top')    or zone.get('high', 0))
                if bottom <= 0 or top <= 0 or top <= bottom:
                    continue
                ax.axhspan(bottom, top, alpha=0.12, color=color, zorder=1)
                ax.axhline(bottom, color=color, linewidth=0.6, alpha=0.5, linestyle='-', zorder=2)
                ax.axhline(top,    color=color, linewidth=0.6, alpha=0.5, linestyle='-', zorder=2)
                mid = (bottom + top) / 2
                ax.text(n_candles * 0.98, mid, label,
                        color=color, fontsize=6.5, alpha=0.75,
                        ha='right', va='center', zorder=4,
                        bbox=dict(facecolor=_PANEL, edgecolor='none', alpha=0.6, pad=1))
            except (TypeError, ValueError):
                continue

    @staticmethod
    def _draw_trendlines(ax, ta_context: Dict, df: pd.DataFrame, x: np.ndarray) -> None:
        """Draw support and resistance trendlines."""
        trendlines = ta_context.get('trendlines') or {}
        support    = trendlines.get('support')
        resistance = trendlines.get('resistance')

        n = len(x)

        for line, color, label in [
            (support,    _TREND_S, 'Support TL'),
            (resistance, _TREND_R, 'Resistance TL'),
        ]:
            if not line:
                continue
            try:
                # line may be {slope, intercept} or {start_price, end_price, start_idx, end_idx}
                if 'slope' in line and 'intercept' in line:
                    slope     = float(line['slope'])
                    intercept = float(line['intercept'])
                    y_vals = slope * x + intercept
                elif 'start_price' in line and 'end_price' in line:
                    x0 = int(line.get('start_idx', 0))
                    x1 = int(line.get('end_idx', n - 1))
                    y0 = float(line['start_price'])
                    y1 = float(line['end_price'])
                    if x1 == x0:
                        continue
                    slope     = (y1 - y0) / (x1 - x0)
                    intercept = y0 - slope * x0
                    y_vals = slope * x + intercept
                else:
                    continue

                ax.plot(x, y_vals, color=color, linewidth=1.0,
                        linestyle='--', alpha=0.7, label=label, zorder=3)
            except (TypeError, ValueError, KeyError):
                continue

    @staticmethod
    def _draw_setup_levels(ax, setup: Dict, last_x: int) -> None:
        """Draw entry zones, stop loss, and take profit levels."""
        direction = setup.get('direction', 'LONG').upper()

        # ── Entry zones ────────────────────────────────────────────────────
        for ez in (setup.get('entry_zones') or []):
            try:
                price = float(ez.get('price', 0))
                if price <= 0:
                    continue
                ez_type = ez.get('type', 'entry')
                alpha   = 0.9 if ez_type == 'conservative' else 0.6
                ax.axhline(price, color=_ENTRY, linewidth=0.9,
                           linestyle='-.', alpha=alpha, zorder=5)
                ax.text(last_x, price, f" Entry ({ez_type[:3].upper()}) ${price:,.2f}",
                        color=_ENTRY, fontsize=6, va='bottom', zorder=6,
                        bbox=dict(facecolor=_PANEL, edgecolor='none', alpha=0.7, pad=1))
            except (TypeError, ValueError):
                continue

        # ── Stop loss ──────────────────────────────────────────────────────
        sl = setup.get('stop_loss') or {}
        try:
            sl_price = float(sl.get('price', 0))
            if sl_price > 0:
                ax.axhline(sl_price, color=_SL, linewidth=1.1,
                           linestyle='--', alpha=0.9, zorder=5)
                ax.text(last_x, sl_price, f" SL ${sl_price:,.2f}",
                        color=_SL, fontsize=6, va='top', zorder=6,
                        bbox=dict(facecolor=_PANEL, edgecolor='none', alpha=0.7, pad=1))
        except (TypeError, ValueError):
            pass

        # ── Take profits ───────────────────────────────────────────────────
        for i, tp in enumerate(setup.get('take_profits') or []):
            try:
                tp_price = float(tp.get('price', 0))
                rr       = tp.get('rr', '')
                if tp_price <= 0:
                    continue
                ax.axhline(tp_price, color=_TP, linewidth=0.9,
                           linestyle='--', alpha=0.75 - i * 0.1, zorder=5)
                rr_str = f"  R/R {rr:.1f}" if rr else ''
                ax.text(last_x, tp_price, f" TP{i+1} ${tp_price:,.2f}{rr_str}",
                        color=_TP, fontsize=6, va='bottom', zorder=6,
                        bbox=dict(facecolor=_PANEL, edgecolor='none', alpha=0.7, pad=1))
            except (TypeError, ValueError):
                continue

        # ── Direction arrow ────────────────────────────────────────────────
        arrow_color = _BULL if direction == 'LONG' else _BEAR
        ax.annotate(
            f'{"▲ LONG" if direction == "LONG" else "▼ SHORT"}',
            xy=(last_x * 0.02, ax.get_ylim()[1]),
            xycoords='data', fontsize=8, fontweight='bold',
            color=arrow_color, alpha=0.85, zorder=7,
        )


# ── Convenience wrapper ────────────────────────────────────────────────────────

async def generate_chart(
    ticker: str,
    interval: str = '4h',
    setup: Optional[Dict] = None,
    ta_context: Optional[Dict] = None,
    output_dir: str = 'output/charts',
    candle_count: int = 120,
) -> Optional[str]:
    """Top-level async helper — preferred interface for main.py."""
    return await ChartGenerator.generate(
        ticker=ticker,
        interval=interval,
        setup=setup,
        ta_context=ta_context,
        output_dir=output_dir,
        candle_count=candle_count,
    )
