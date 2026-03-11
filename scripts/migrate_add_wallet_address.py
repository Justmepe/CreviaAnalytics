#!/usr/bin/env python3
"""
Migration script — Add wallet_address column to users table.
Run on VPS: python scripts/migrate_add_wallet_address.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
import psycopg2

def migrate():
    """Add wallet_address column to users table if it doesn't exist."""
    
    db_config = {
        'host': DB_HOST,
        'port': int(DB_PORT),
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("Connected to database:", DB_NAME)
        
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
