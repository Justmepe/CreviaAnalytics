"""
Database engine and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from api.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables (for initial setup)."""
    from api.models import content, user  # noqa: F401 — ensure models are registered
    from api.models import journal  # noqa: F401
    from api.models import feed  # noqa: F401
    from api.models import alerts  # noqa: F401
    from api.models import admin_inbox  # noqa: F401
    from api.models import payment  # noqa: F401
    Base.metadata.create_all(bind=engine)
