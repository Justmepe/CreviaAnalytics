"""
Background service: checks price alerts every 60 s and fires Discord embeds.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.alerts import PriceAlert
from api.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CoinGecko asset → ID map
# ---------------------------------------------------------------------------

_CG_IDS: dict[str, str] = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano',
    'DOGE': 'dogecoin', 'AVAX': 'avalanche-2', 'DOT': 'polkadot',
    'MATIC': 'matic-network', 'LINK': 'chainlink', 'UNI': 'uniswap',
    'ATOM': 'cosmos', 'LTC': 'litecoin', 'BCH': 'bitcoin-cash',
    'ARB': 'arbitrum', 'OP': 'optimism', 'SUI': 'sui',
    'INJ': 'injective-protocol', 'TIA': 'celestia', 'TON': 'the-open-network',
}

# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

async def _fetch_prices(assets: list[str]) -> dict[str, dict]:
    """Return {TICKER: {price, pct_change_24h}} from CoinGecko."""
    ids = [_CG_IDS[a] for a in assets if a in _CG_IDS]
    if not ids:
        return {}

    url = (
        'https://api.coingecko.com/api/v3/simple/price'
        f'?ids={",".join(ids)}&vs_currencies=usd&include_24hr_change=true'
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()
    except Exception as e:
        logger.warning('CoinGecko fetch failed: %s', e)
        return {}

    # Reverse map: cg_id → asset ticker
    id_to_ticker = {v: k for k, v in _CG_IDS.items()}
    result: dict[str, dict] = {}
    for cg_id, vals in raw.items():
        ticker = id_to_ticker.get(cg_id)
        if ticker and ticker in assets:
            result[ticker] = {
                'price': vals.get('usd', 0.0),
                'pct_change_24h': vals.get('usd_24h_change', 0.0),
            }
    return result


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def _condition_met(alert: PriceAlert, price_data: dict) -> bool:
    price = price_data.get('price', 0.0)
    pct = price_data.get('pct_change_24h', 0.0)
    t = alert.threshold_value

    if alert.alert_type == 'price_above':
        return price >= t
    if alert.alert_type == 'price_below':
        return price <= t
    if alert.alert_type == 'pct_change_up':
        return pct >= t
    if alert.alert_type == 'pct_change_down':
        return pct <= -abs(t)
    return False


def _can_fire(alert: PriceAlert, now: datetime) -> bool:
    if alert.status != 'active':
        return False
    if not alert.last_triggered:
        return True
    elapsed = (now - alert.last_triggered).total_seconds()
    if alert.frequency == 'once':
        return False  # already fired
    if alert.frequency == 'daily':
        return elapsed >= 86_400
    if alert.frequency == 'always':
        return elapsed >= 300  # 5 min cooldown
    return False


# ---------------------------------------------------------------------------
# Discord embed
# ---------------------------------------------------------------------------

_TYPE_LABEL = {
    'price_above':    'crossed above',
    'price_below':    'dropped below',
    'pct_change_up':  'is up',
    'pct_change_down': 'is down',
}


def _build_embed(alert: PriceAlert, price: float, pct: float) -> dict:
    verb = _TYPE_LABEL.get(alert.alert_type, 'triggered for')
    if alert.alert_type in ('price_above', 'price_below'):
        desc = f'**{alert.asset}** {verb} **${alert.threshold_value:,.2f}**'
    else:
        desc = f'**{alert.asset}** {verb} **{alert.threshold_value:.1f}%** in 24 h'

    fields = [
        {'name': 'Current Price', 'value': f'${price:,.4f}', 'inline': True},
        {'name': '24h Change',    'value': f'{pct:+.2f}%',    'inline': True},
        {'name': 'Frequency',     'value': alert.frequency.title(), 'inline': True},
    ]
    if alert.note:
        fields.append({'name': 'Note', 'value': alert.note, 'inline': False})

    return {
        'embeds': [{
            'title': '🔔 Crevia Alert Triggered',
            'description': desc,
            'color': 0x00D4AA,
            'fields': fields,
            'footer': {'text': 'Crevia Analytics · creviacockpit.com'},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }]
    }


async def _send_discord(url: str, payload: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code in (200, 204)
    except Exception as e:
        logger.error('Discord POST error: %s', e)
        return False


# ---------------------------------------------------------------------------
# Main checker loop
# ---------------------------------------------------------------------------

async def _check_once() -> None:
    db: Session = SessionLocal()
    try:
        alerts: list[PriceAlert] = (
            db.query(PriceAlert).filter(PriceAlert.status == 'active').all()
        )
        if not alerts:
            return

        assets = list({a.asset.upper() for a in alerts})
        prices = await _fetch_prices(assets)
        if not prices:
            return

        now = datetime.now(timezone.utc)

        for alert in alerts:
            asset = alert.asset.upper()
            if asset not in prices:
                continue
            if not _can_fire(alert, now):
                continue
            if not _condition_met(alert, prices[asset]):
                continue

            user: User | None = db.query(User).filter(User.id == alert.user_id).first()
            if not user or not user.discord_webhook_url:
                continue

            payload = _build_embed(alert, prices[asset]['price'], prices[asset]['pct_change_24h'])
            ok = await _send_discord(user.discord_webhook_url, payload)
            if ok:
                alert.last_triggered = now
                if alert.frequency == 'once':
                    alert.status = 'triggered'
                db.commit()
                logger.info(
                    'Alert %d fired → user %d (%s %s)',
                    alert.id, alert.user_id, asset, alert.alert_type,
                )
    finally:
        db.close()


async def run_alert_checker() -> None:
    """Endless loop — call via asyncio.create_task() at startup."""
    logger.info('Alert checker started (60 s interval)')
    while True:
        try:
            await _check_once()
        except Exception as e:
            logger.error('Alert checker loop error: %s', e)
        await asyncio.sleep(60)
