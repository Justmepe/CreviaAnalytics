#!/usr/bin/env python3
"""Check actual database properties"""

import os
import sys
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

API_KEY = os.getenv('NOTION_API_KEY')
DB_ID = os.getenv('NOTION_DATABASE_ID')

try:
    client = Client(auth=API_KEY)
    db = client.databases.retrieve(DB_ID)
    
    print("\n📊 YOUR NOTION DATABASE PROPERTIES")
    print("=" * 70)
    
    properties = db.get('properties', {})
    
    if not properties:
        print("❌ No properties found in database!")
        print("\nYour database might be empty or not properly shared with the integration.")
        print("\nTo create properties, add these columns in Notion:")
        print("  1. Title (type: Title)")
        print("  2. Content (type: rich_text)")
        print("  3. Type (type: select - options: Newsletter, News Post, Tweet Thread, Report)")
        print("  4. Platform (type: select - options: X, Substack, Web, Reddit)")
        print("  5. Status (type: select - options: Draft, Ready, Published, Archived)")
        print("  6. Tags (type: multi_select)")
        print("  7. Image URL (type: url)")
    else:
        print(f"Found {len(properties)} properties:\n")
        for name, prop_def in properties.items():
            prop_type = prop_def.get('type')
            print(f"  • {name}: {prop_type}")
            
            # Show select options if it's a select field
            if prop_type == 'select':
                options = prop_def.get('select', {}).get('options', [])
                if options:
                    print(f"      Options: {', '.join([opt.get('name', '') for opt in options])}")
    
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
