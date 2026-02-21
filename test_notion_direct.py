#!/usr/bin/env python3
"""
Direct Notion API test
"""

from notion_client import Client
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('NOTION_API_KEY')
db_id = os.getenv('NOTION_DATABASE_ID')

print(f"API Key: {'✓ Set' if api_key else '✗ Not set'}")
print(f"Database ID: {db_id}")

if not api_key:
    print("Error: NOTION_API_KEY not set")
    exit(1)

try:
    client = Client(auth=api_key)
    print("✓ Client created")
    
    # Test database retrieval
    try:
        db = client.databases.retrieve(db_id)
        print(f"✓ Database retrieved successfully")
        print(f"  Title: {db.get('title', 'N/A')}")
    except Exception as e:
        print(f"✗ Database retrieval failed: {e}")
    
    # Test querying (this is the issue)
    print("\nTesting query method...")
    try:
        result = client.databases.query(database_id=db_id)
        print(f"✓ Query successful, found {len(result.get('results', []))} items")
    except AttributeError as e:
        print(f"✗ Query method error: {e}")
        print("  Available methods:", dir(client.databases))
    except Exception as e:
        print(f"✗ Query failed: {e}")
        
except Exception as e:
    print(f"Connection error: {e}")
