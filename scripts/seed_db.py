"""
Database seed script — creates all tables in PostgreSQL.
Run: python -m scripts.seed_db
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.database import engine, Base

# Import all models so they're registered with Base
from api.models.content import ContentPost, ThreadTweet, MarketSnapshot, AssetPrice  # noqa: F401
from api.models.user import User, ApiUsage, EmailSubscription  # noqa: F401


def main():
    print("Creating database tables...")
    print(f"Database: {engine.url}")

    Base.metadata.create_all(bind=engine)

    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables created ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")

    print("\nDatabase setup complete.")


if __name__ == '__main__':
    main()
