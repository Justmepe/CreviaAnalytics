"""
Chart Generator — Candlestick PNGs from Binance OHLCV data

Saves PNGs to web/public/charts/ so Next.js serves them as static files.
Returns a public URL: https://creviacockpit.com/charts/<filename>

Usage:
    from src.utils.chart_generator import generate_chart_image
    url = generate_chart_image('BTC', '4h')  # -> '/charts/btc_4h_20260303_1200.png'
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — required for server/threaded environments

import os
import logging
import httpx
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Charts saved here — Next.js serves /public/** as static assets
CHARTS_DIR = Path(__file__).parent.parent.parent / 'web' / 'public' / 'charts'
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Keep at most this many chart files to avoid filling disk
MAX_CHART_FILES = 200

# Binance SPOT symbol map — only pairs available on api.binance.com/api/v3/klines
# XAU and TSLA are futures-only on Binance; exclude to avoid silent 400 errors.
_SYMBOL_MAP = {
    'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT', 'XRP': 'XRPUSDT',
    'BNB': 'BNBUSDT', 'AVAX': 'AVAXUSDT', 'SUI': 'SUIUSDT', 'LINK': 'LINKUSDT',
    'DOGE': 'DOGEUSDT', 'SHIB': 'SHIBUSDT', 'PEPE': 'PEPEUSDT', 'FLOKI': 'FLOKIUSDT',
    'XMR': 'XMRUSDT', 'ZEC': 'ZECUSDT', 'DASH': 'DASHUSDT',
    'AAVE': 'AAVEUSDT', 'UNI': 'UNIUSDT', 'CRV': 'CRVUSDT', 'LDO': 'LDOUSDT',
}

# Priority order for picking a representative chart from a list of tickers.
# When a post covers multiple assets, prefer the most liquid/well-known one.
_CHART_PRIORITY = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'AVAX', 'LINK', 'SUI',
    'DOGE', 'SHIB', 'PEPE', 'FLOKI',
    'AAVE', 'UNI', 'CRV', 'LDO',
    'XMR', 'ZEC', 'DASH',
]


def pick_chart_ticker(tickers: list[str], fallback: str = 'BTC') -> str:
    """
    From a list of asset tickers, return the best one to use as a chart.

    Rules:
    - Only considers tickers that exist in _SYMBOL_MAP (chartable on Binance spot)
    - Among chartable tickers, picks the highest-priority one (_CHART_PRIORITY)
    - Falls back to `fallback` (default BTC) if none are chartable
    """
    chartable = [t.upper() for t in tickers if t.upper() in _SYMBOL_MAP]
    if not chartable:
        return fallback
    # Sort by priority index (lower = higher priority); unrecognised tickers go last
    chartable.sort(key=lambda t: _CHART_PRIORITY.index(t) if t in _CHART_PRIORITY else 999)
    return chartable[0]

# Dark theme matching the CreviaCockpit UI
_STYLE = mpf.make_mpf_style(
    base_mpf_style='nightclouds',
    marketcolors=mpf.make_marketcolors(
        up='#00d68f',
        down='#f03e5a',
        edge={'up': '#00d68f', 'down': '#f03e5a'},
        wick={'up': '#00d68f', 'down': '#f03e5a'},
        volume={'up': '#00d68f44', 'down': '#f03e5a44'},
    ),
    facecolor='#0d1117',
    edgecolor='#1c2235',
    figcolor='#08090c',
    gridcolor='#161b28',
    gridstyle='-',
    gridaxis='both',
    y_on_right=True,
    rc={
        'axes.labelcolor': '#6b7494',
        'axes.edgecolor': '#1c2235',
        'xtick.color': '#3d4562',
        'ytick.color': '#3d4562',
        'font.family': 'monospace',
        'font.size': 8,
        'figure.facecolor': '#08090c',
    },
)

# Timeframe → candle count (keep charts readable)
_TF_LIMITS = {
    '1h': 120, '4h': 100, '1d': 90, '1w': 52,
}

# Label shown in chart title
_TF_LABELS = {
    '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W',
}


def _fetch_klines(ticker: str, interval: str, limit: int) -> pd.DataFrame:
    """Fetch OHLCV from Binance synchronously. Returns DataFrame."""
    symbol = _SYMBOL_MAP.get(ticker.upper(), f'{ticker.upper()}USDT')
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

    if not raw:
        raise ValueError(f'Binance returned empty klines for {symbol} {interval}')

    df = pd.DataFrame(raw, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'num_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore',
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    df.set_index('open_time', inplace=True)
    for col in ('open', 'high', 'low', 'close', 'volume'):
        df[col] = df[col].astype(float)
    return df[['open', 'high', 'low', 'close', 'volume']]


def _prune_old_charts():
    """Delete oldest chart files if we exceed MAX_CHART_FILES."""
    files = sorted(CHARTS_DIR.glob('*.png'), key=lambda f: f.stat().st_mtime)
    while len(files) > MAX_CHART_FILES:
        files.pop(0).unlink(missing_ok=True)


def generate_chart_image(
    ticker: str,
    interval: str = '4h',
    limit: int | None = None,
) -> str | None:
    """
    Generate a candlestick chart PNG for the given ticker and timeframe.

    Returns the public URL path (/charts/<filename>) suitable for storing
    as image_url on a ContentPost, or None on failure.
    """
    try:
        tf = interval.lower()
        candle_limit = limit or _TF_LIMITS.get(tf, 100)
        tf_label = _TF_LABELS.get(tf, tf.upper())

        df = _fetch_klines(ticker, tf, candle_limit)

        now_utc = datetime.now(timezone.utc)
        filename = f"{ticker.lower()}_{tf}_{now_utc.strftime('%Y%m%d_%H%M%S')}.png"
        out_path = CHARTS_DIR / filename

        # Current price for title
        last_close = df['close'].iloc[-1]
        price_str = f'${last_close:,.2f}' if last_close >= 1 else f'${last_close:.6f}'

        title = f'{ticker}/USDT · {tf_label}  {price_str}'

        # ── Build additional plot: 20-EMA overlay ────────────────────────────
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ap = [mpf.make_addplot(ema20, color='#f0a030', width=1.2, linestyle='--')]

        fig, axes = mpf.plot(
            df,
            type='candle',
            style=_STYLE,
            title=f'\n{title}',
            ylabel='',
            ylabel_lower='Volume',
            volume=True,
            addplot=ap,
            figsize=(12, 6.75),
            tight_layout=True,
            returnfig=True,
            warn_too_much_data=99999,
        )

        # ── Watermark — centred diagonal ghost over the main chart axis ────────
        main_ax = axes[0]
        main_ax.text(
            0.5, 0.5,
            'CREVIACOCKPIT',
            transform=main_ax.transAxes,
            ha='center', va='center',
            fontsize=42,
            fontweight='bold',
            color='#00d68f',
            alpha=0.045,
            fontfamily='monospace',
            rotation=30,
            zorder=0,
        )
        main_ax.text(
            0.5, 0.38,
            'creviacockpit.com',
            transform=main_ax.transAxes,
            ha='center', va='center',
            fontsize=14,
            color='#00d68f',
            alpha=0.045,
            fontfamily='monospace',
            rotation=30,
            zorder=0,
        )

        fig.savefig(out_path, dpi=120, bbox_inches='tight', facecolor='#08090c')
        plt.close(fig)

        _prune_old_charts()

        logger.info(f'[ChartGen] Saved {filename} ({len(df)} candles, {tf_label})')
        return f'/charts/{filename}'

    except Exception as e:
        logger.warning(f'[ChartGen] Failed for {ticker} {interval}: {e}')
        return None
