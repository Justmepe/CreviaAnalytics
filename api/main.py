"""
FastAPI application — Crevia Analytics API
Serves content to the Next.js frontend and accepts content from the Python engine.
"""

import asyncio
import logging
import os
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.database import create_tables
from api.routers import content, market, intelligence, auth
from api.routers import journal
from api.routers import stream
from api.routers import waitlist
from api.routers import portfolio
from api.routers import feed
from api.routers import whale as whale_router
from api.routers import alerts as alerts_router
from api.routers import admin as admin_router
from api.routers import payments as payments_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title='Crevia Analytics API',
    description='Crypto market analysis content and data API',
    version='1.0.0',
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Register routers
app.include_router(content.router)
app.include_router(market.router)
app.include_router(intelligence.router)
app.include_router(auth.router)
app.include_router(journal.router)
app.include_router(stream.router)
app.include_router(waitlist.router)
app.include_router(portfolio.router)
app.include_router(feed.router)
app.include_router(whale_router.router)
app.include_router(alerts_router.router)
app.include_router(admin_router.router)
app.include_router(payments_router.router)


# ---------------------------------------------------------------------------
# Whale engine background thread
# ---------------------------------------------------------------------------

def _start_whale_engine() -> None:
    """
    Initialise DataAggregator with all available API keys, then
    run WhaleAnalyzer.refresh_all() every 5 minutes in a daemon thread.

    Uses the same env vars as main.py so no new config is needed.
    """
    try:
        from src.data.aggregator import DataAggregator
        from src.intelligence.whale_analyzer import WhaleAnalyzer

        aggregator = DataAggregator(
            binance_key     = os.getenv('BINANCE_API_KEY', ''),
            binance_secret  = os.getenv('BINANCE_SECRET_KEY', ''),
            coingecko_key   = os.getenv('COINGECKO_API_KEY', ''),
            etherscan_key   = os.getenv('ETHERSCAN_API_KEY', ''),
            glassnode_key   = os.getenv('GLASSNODE_API_KEY', ''),
            coinglass_key   = os.getenv('COINGLASS_API_KEY', ''),
        )

        analyzer = WhaleAnalyzer(aggregator=aggregator)
        whale_router.set_whale_engine(analyzer)
        logger.info('WhaleAnalyzer engine initialised — starting background refresh loop')

        def _loop():
            # First run immediately, then every 5 minutes
            while True:
                try:
                    analyzer.refresh_all(['BTC', 'ETH', 'SOL'])
                except Exception as e:
                    logger.error('WhaleAnalyzer refresh error: %s', e)
                time.sleep(300)   # 5 minutes

        t = threading.Thread(target=_loop, daemon=True, name='whale-engine')
        t.start()

        # Start WhaleCollector in a separate asyncio thread and drain its queue
        _start_whale_collector(analyzer)

    except Exception as e:
        logger.error('Failed to start whale engine: %s', e)


def _start_whale_collector(analyzer) -> None:
    """
    Start WhaleCollector in a dedicated asyncio thread.
    Drains its queue and injects transactions into WhaleAnalyzer every 10 s.
    """
    try:
        from src.data.whale_collector import WhaleCollector

        collector = WhaleCollector()

        def _run_collector():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _main():
                # Start collectors in background
                loop.create_task(collector.run())

                # Drain queue and push to analyzer every 10 s
                while True:
                    await asyncio.sleep(10)
                    batch: list = []
                    while not collector.queue.empty():
                        try:
                            batch.append(collector.queue.get_nowait())
                        except Exception:
                            break
                    if batch:
                        analyzer.inject_transactions(batch)
                        logger.debug('WhaleCollector drained %d txns', len(batch))

            loop.run_until_complete(_main())

        t = threading.Thread(target=_run_collector, daemon=True, name='whale-collector')
        t.start()
        logger.warning('WhaleCollector thread started')

    except Exception as e:
        logger.warning('WhaleCollector could not start: %s', e)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event('startup')
async def on_startup():
    """Create DB tables, start background engines."""
    create_tables()
    _start_whale_engine()
    # Alert checker runs on the main event loop
    from api.services.alert_checker import run_alert_checker
    asyncio.create_task(run_alert_checker())


@app.get('/api/health')
def health_check():
    return {'status': 'ok', 'service': 'crevia-analytics-api'}
