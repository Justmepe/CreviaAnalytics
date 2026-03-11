#!/usr/bin/env python3
"""
Migration script — Add wallet_address column to users table.
Run on VPS: python scripts/migrate_add_wallet_address.py
"""

import sys
import os
import psycopg2
from psycopg2 import sql

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.config import DATABASE_URL

def migrate():
    """Add wallet_address column to users table if it doesn't exist."""
    
    # Parse database URL
    # Format: postgresql://user:password@host:port/dbname
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    
    db_config = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("Connected to database:", db_config['database'])
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='wallet_address'
        """)
        
        if cursor.fetchone():
            print("✓ wallet_address column already exists")
            cursor.close()
            conn.close()
            return
        
        # Add the column
        print("Adding wallet_address column to users table...")
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN wallet_address VARCHAR(42) DEFAULT NULL
        """)
        
        conn.commit()
        print("✓ Migration complete: wallet_address column added")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    migrate()
