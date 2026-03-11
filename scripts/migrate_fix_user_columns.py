#!/usr/bin/env python3
"""
Migration script — Add missing columns to users table
- wallet_address (already added, but we'll check)
- discord_webhook_url (missing)
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
    """Add missing columns to users table."""
    
    db_config = {
        'host': DB_HOST,
        'port': int(DB_PORT),
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'connect_timeout': 10,
    }
    
    conn = None
    cursor = None
    
    try:
        print(f"Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("✓ Connected to database:", DB_NAME)
        
        columns_to_add = {
            'wallet_address': "VARCHAR(42) DEFAULT NULL",
            'discord_webhook_url': "VARCHAR(500) DEFAULT NULL"
        }
        
        # Check which columns are missing
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users'
        """)
        
        existing_columns = {row[0] for row in cursor.fetchall()}
        missing_columns = {col: ddl for col, ddl in columns_to_add.items() if col not in existing_columns}
        
        if not missing_columns:
            print("✓ All required columns already exist")
            return 0
        
        # Add missing columns
        for column_name, column_def in missing_columns.items():
            print(f"Adding {column_name} column...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
        
        conn.commit()
        print(f"✓ Migration complete: {len(missing_columns)} column(s) added")
        return 0
        
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        if conn:
            conn.rollback()
        return 1
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        if conn:
            conn.rollback()
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    exit_code = migrate()
    sys.exit(exit_code)
