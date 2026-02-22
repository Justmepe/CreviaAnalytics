"""
FastAPI application — Crevia Analytics API
Serves content to the Next.js frontend and accepts content from the Python engine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.database import create_tables
from api.routers import content, market, intelligence, auth
from api.routers import journal
from api.routers import stream
from api.routers import waitlist
from api.routers import portfolio

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


@app.on_event('startup')
def on_startup():
    """Create tables on first run if they don't exist."""
    create_tables()


@app.get('/api/health')
def health_check():
    return {'status': 'ok', 'service': 'crevia-analytics-api'}
