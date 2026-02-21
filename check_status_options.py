#!/usr/bin/env python3
"""Check Status field options"""

import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NOTION_API_KEY')
DB_ID = os.getenv('NOTION_DATABASE_ID')

try:
    client = Client(auth=API_KEY)
    db = client.databases.retrieve(DB_ID)
    
    status_prop = db.get('properties', {}).get('Status', {})
    
    print("\n📊 Status Field Configuration:")
    print(f"Type: {status_prop.get('type')}")
    
    status_config = status_prop.get('status', {})
    print(f"Options: {status_config}")
    
    options = status_config.get('options', [])
    print(f"\nAvailable Status Values:")
    for opt in options:
        print(f"  • {opt.get('name')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
