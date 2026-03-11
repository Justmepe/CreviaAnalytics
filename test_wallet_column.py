#!/usr/bin/env python3
"""
Test script — Verify wallet_address column exists in database
"""

import os
from dotenv import load_dotenv

load_dotenv()

from api.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
import psycopg2

try:
    print(f"Testing database connection to {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    
    db_config = {
        'host': DB_HOST,
        'port': int(DB_PORT),
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'connect_timeout': 10,
    }
    
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    print("✓ Connected successfully")
    
    # Get all columns from users table
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users'
        ORDER BY ordinal_position
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    
    print(f"\nUsers table columns ({len(columns)} total):")
    for i, col in enumerate(columns, 1):
        marker = "✓" if col == "wallet_address" else " "
        print(f"  {marker} {i:2d}. {col}")
    
    if "wallet_address" in columns:
        print("\n✅ SUCCESS: wallet_address column exists!")
    else:
        print("\n❌ FAILED: wallet_address column NOT FOUND")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
