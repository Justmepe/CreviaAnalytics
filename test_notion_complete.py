#!/usr/bin/env python3
"""
Quick Notion Database Connection Test
"""

import os
import sys
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

print(f"\n📋 NOTION CONNECTION TEST")
print(f"=" * 60)
print(f"API Key: {NOTION_API_KEY[:20]}...✓" if NOTION_API_KEY else "❌ API Key missing")
print(f"Database ID: {NOTION_DATABASE_ID}")
print(f"=" * 60)

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    print("❌ Missing credentials!")
    sys.exit(1)

try:
    from notion_client import Client
    print("✓ notion-client installed\n")
except ImportError:
    print("❌ notion-client not installed\nRun: pip install notion-client")
    sys.exit(1)

try:
    # Initialize client
    client = Client(auth=NOTION_API_KEY)
    print("✓ Client initialized\n")
    
    # Try to get database info
    print(f"Fetching database info for: {NOTION_DATABASE_ID}")
    database = client.databases.retrieve(NOTION_DATABASE_ID)
    print(f"✅ Database found: {database.get('title', 'Untitled')}")
    
    # List properties
    print(f"\n📊 Database Properties:")
    props = database.get('properties', {})
    for prop_name, prop_info in props.items():
        prop_type = prop_info.get('type', 'unknown')
        print(f"  • {prop_name}: {prop_type}")
    
    # Try to query using direct HTTP request
    print(f"\n🔍 Testing query via direct HTTP...")
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    
    with httpx.Client() as http_client:
        resp = http_client.post(url, json={"page_size": 5}, headers=headers, timeout=30.0)
        resp.raise_for_status()
        response = resp.json()
    
    results = response.get('results', [])
    print(f"✅ Query successful! Found {len(results)} items")
    
    if results:
        print(f"\n📄 Sample items:")
        for i, page in enumerate(results[:3], 1):
            title = "Untitled"
            props = page.get('properties', {})
            for prop_name, prop_data in props.items():
                if prop_data.get('type') == 'title':
                    title_blocks = prop_data.get('title', [])
                    if title_blocks:
                        title = title_blocks[0].get('text', {}).get('content', 'Untitled')
                    break
            print(f"  {i}. {title}")
    
    print(f"\n✅ ALL TESTS PASSED - Notion is ready to use!\n")

except Exception as e:
    print(f"❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
