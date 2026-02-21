#!/usr/bin/env python3
"""Quick test of Notion connection"""
from notion_client import Client
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('NOTION_API_KEY')
db_id = os.getenv('NOTION_DATABASE_ID')

print(f'API Key: {api_key[:20]}...' if api_key else 'No API key found')
print(f'Database ID: {db_id}' if db_id else 'No database ID found')

try:
    client = Client(auth=api_key)
    db = client.databases.retrieve(db_id)
    
    print('✓ Connected to Notion')
    
    # Get database title
    title = ''
    if 'title' in db:
        title_blocks = db.get('title', [])
        if title_blocks:
            title = title_blocks[0].get('plain_text', 'Unknown')
    
    print(f'Database: {title}')
    print(f'Properties: {list(db.get("properties", {}).keys())}')
    
    # Try to query the database
    response = client.databases.query(db_id, page_size=1)
    print(f'Query successful - found {response.get("result_type", "unknown")} result')
    
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
