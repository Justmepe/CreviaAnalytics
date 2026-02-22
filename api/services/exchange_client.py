"""
Exchange REST API clients for portfolio sync (read-only).
Supports Binance, Bybit, and OKX using HMAC-SHA256 signed requests.
"""

import hashlib
import hmac
import time
from typing import Optional
import httpx


BINANCE_BASE = "https://api.binance.com"
BYBIT_BASE = "https://api.bybit.com"
OKX_BASE = "https://www.okx.com"

# Assets with ~$0 value we skip (too many dust positions clutter the view)
DUST_THRESHOLD_USD = 0.5


def _binance_sign(params: dict, secret: str) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _bybit_sign(params: str, secret: str, timestamp: str, recv_window: str) -> str:
    pre_hash = timestamp + secret + recv_window + params  # Bybit v5 signature
    return hmac.new(secret.encode(), pre_hash.encode(), hashlib.sha256).hexdigest()


async def fetch_binance_portfolio(api_key: str, api_secret: str) -> list[dict]:
    """
    Fetch spot account balances from Binance.
    Returns list of {asset, free, locked, total}.
    """
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp, "recvWindow": 5000}
    params["signature"] = _binance_sign(params, api_secret)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BINANCE_BASE}/api/v3/account",
            params=params,
            headers={"X-MBX-APIKEY": api_key},
        )
        resp.raise_for_status()
        data = resp.json()

    balances = []
    for b in data.get("balances", []):
        free = float(b["free"])
        locked = float(b["locked"])
        total = free + locked
        if total > 0:
            balances.append({
                "asset": b["asset"],
                "free": free,
                "locked": locked,
                "total": total,
            })
    return balances


async def fetch_bybit_portfolio(api_key: str, api_secret: str) -> list[dict]:
    """
    Fetch unified account balances from Bybit v5.
    Returns list of {asset, free, locked, total}.
    """
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    query = "accountType=UNIFIED"
    sig = _bybit_sign(query, api_secret, timestamp, recv_window)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BYBIT_BASE}/v5/account/wallet-balance",
            params={"accountType": "UNIFIED"},
            headers={
                "X-BAPI-API-KEY": api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "X-BAPI-SIGN": sig,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    balances = []
    for account in data.get("result", {}).get("list", []):
        for coin in account.get("coin", []):
            total = float(coin.get("walletBalance", 0))
            available = float(coin.get("availableToWithdraw", 0))
            if total > 0:
                balances.append({
                    "asset": coin["coin"],
                    "free": available,
                    "locked": total - available,
                    "total": total,
                })
    return balances


async def enrich_with_usd_values(
    balances: list[dict],
    prices: Optional[dict[str, float]] = None,
) -> list[dict]:
    """
    Add usd_value to each balance using CoinGecko simple price endpoint.
    Skips dust positions below DUST_THRESHOLD_USD.
    prices: optional {symbol: price_usd} map (avoids extra API call if caller provides data)
    """
    if not balances:
        return []

    # Build list of symbols to price
    symbols = list({b["asset"] for b in balances})

    if prices is None:
        prices = await _fetch_prices(symbols)

    result = []
    for b in balances:
        asset = b["asset"]
        price = prices.get(asset, 0.0)
        usd_value = b["total"] * price
        if usd_value >= DUST_THRESHOLD_USD or price == 0.0:
            result.append({**b, "price_usd": price, "usd_value": usd_value})

    result.sort(key=lambda x: x["usd_value"], reverse=True)
    return result


async def _fetch_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetch USD prices from Binance ticker (free, no auth).
    Falls back to 0 for unknown assets (stablecoins handled separately).
    """
    prices: dict[str, float] = {}

    # Common stablecoins — peg to 1
    stables = {"USDT", "USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDP"}
    for s in stables:
        if s in symbols:
            prices[s] = 1.0

    symbols_to_fetch = [s for s in symbols if s not in prices]
    if not symbols_to_fetch:
        return prices

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{BINANCE_BASE}/api/v3/ticker/price")
            resp.raise_for_status()
            tickers = {t["symbol"]: float(t["price"]) for t in resp.json()}

        for sym in symbols_to_fetch:
            # Try USDT pair first, then BUSD
            for quote in ("USDT", "BUSD", "USDC"):
                pair = f"{sym}{quote}"
                if pair in tickers:
                    prices[sym] = tickers[pair]
                    break
            else:
                prices[sym] = 0.0
    except Exception:
        for sym in symbols_to_fetch:
            prices[sym] = 0.0

    return prices
