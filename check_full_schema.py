#!/usr/bin/env python3
"""Check full database properties"""

import os
import json
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NOTION_API_KEY')
DB_ID = os.getenv('NOTION_DATABASE_ID')

try:
    client = Client(auth=API_KEY)
    db = client.databases.retrieve(DB_ID)
    
    print("\n📊 FULL DATABASE SCHEMA")
    print("=" * 70)
    
    props = db.get('properties', {})
    
    for prop_name, prop_def in props.items():
        prop_type = prop_def.get('type')
        print(f"\n{prop_name} ({prop_type})")
        
        if prop_type == 'select' or prop_type == 'status':
            config_key = prop_type  # Could be 'select' or 'status'
            config = prop_def.get(config_key, {})
            options = config.get('options', [])
            if options:
                print(f"  Options:")
                for opt in options:
                    print(f"    - {opt.get('name')}")
            else:
                print(f"  (No options configured)")
        elif prop_type == 'multi_select':
            config = prop_def.get('multi_select', {})
            options = config.get('options', [])
            if options:
                print(f"  Options:")
                for opt in options:
                    print(f"    - {opt.get('name')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
