#!/usr/bin/env python3
"""
Setup Notion Database with All Required Properties
This will add all necessary fields to your existing database
"""

import os
import sys
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NOTION_API_KEY')
DB_ID = os.getenv('NOTION_DATABASE_ID')

print("\n" + "="*70)
print("🔧 NOTION DATABASE SETUP - Adding Required Properties")
print("="*70 + "\n")

if not API_KEY or not DB_ID:
    print("❌ Missing NOTION_API_KEY or NOTION_DATABASE_ID in .env")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Define all properties we need
# Note: "Name" is the title property in your database
properties_to_add = {
    "Content": {
        "rich_text": {}
    },
    "Type": {
        "select": {
            "options": [
                {"name": "Newsletter", "color": "blue"},
                {"name": "News Post", "color": "green"},
                {"name": "Tweet Thread", "color": "purple"},
                {"name": "Report", "color": "orange"},
                {"name": "Market Insight", "color": "red"}
            ]
        }
    },
    "Platform": {
        "select": {
            "options": [
                {"name": "X (Twitter)", "color": "gray"},
                {"name": "Substack", "color": "yellow"},
                {"name": "Web", "color": "green"},
                {"name": "Reddit", "color": "orange"},
                {"name": "Discord", "color": "blue"}
            ]
        }
    },
    "Tags": {
        "multi_select": {
            "options": [
                {"name": "Bitcoin", "color": "orange"},
                {"name": "Ethereum", "color": "purple"},
                {"name": "DeFi", "color": "blue"},
                {"name": "NFTs", "color": "pink"},
                {"name": "Altcoins", "color": "green"},
                {"name": "Market Analysis", "color": "red"},
                {"name": "News", "color": "yellow"},
                {"name": "Weekly", "color": "gray"},
                {"name": "Daily", "color": "brown"},
                {"name": "Analysis", "color": "purple"}
            ]
        }
    },
    "Image URL": {
        "url": {}
    }
}

try:
    # Get current database info
    url = f"https://api.notion.com/v1/databases/{DB_ID}"
    
    with httpx.Client() as client:
        # Get current database
        resp = client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        current_db = resp.json()
        
        print("📊 Current database properties:")
        current_props = current_db.get('properties', {})
        for prop_name in current_props.keys():
            print(f"   ✓ {prop_name}")
        
        print(f"\n📝 Adding new properties...")
        
        # Add missing properties
        properties_to_update = {}
        for prop_name, prop_def in properties_to_add.items():
            if prop_name not in current_props:
                properties_to_update[prop_name] = prop_def
                print(f"   + {prop_name}")
            else:
                print(f"   ✓ {prop_name} (already exists)")
        
        if properties_to_update:
            # Update database with new properties
            update_payload = {
                "properties": properties_to_update
            }
            
            resp = client.patch(url, json=update_payload, headers=headers, timeout=30.0)
            if resp.status_code != 200:
                print(f"❌ Error response: {resp.status_code}")
                print(f"Response: {resp.text}")
            resp.raise_for_status()
            
            print(f"\n✅ Database updated successfully!")
            print(f"\nAdded {len(properties_to_update)} new properties:")
            for prop_name in properties_to_update.keys():
                print(f"   • {prop_name}")
        else:
            print(f"\n✓ All properties already exist!")
        
        print(f"\n✅ Setup complete! Your database is ready to use.\n")
        print("Next steps:")
        print("1. Go to your Notion database")
        print("2. You should see all the new columns")
        print("3. Run: python test_notion_content_manager.py")
        print("4. Start saving content with the manager!\n")

except Exception as e:
    print(f"❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
