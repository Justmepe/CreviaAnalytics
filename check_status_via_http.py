#!/usr/bin/env python3
"""Check Status field configuration via HTTP"""

import os
import httpx
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv('NOTION_API_KEY')
DB_ID = os.getenv('NOTION_DATABASE_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Notion-Version': '2022-06-28'
}

with httpx.Client() as client:
    resp = client.get(f'https://api.notion.com/v1/databases/{DB_ID}', headers=headers)
    data = resp.json()
    props = data.get('properties', {})
    
    status_prop = props.get('Status', {})
    print('\n📌 STATUS PROPERTY:')
    print(f'Type: {status_prop.get("type")}')
    
    # Try both status and select config
    if status_prop.get('type') == 'status':
        config = status_prop.get('status', {})
        print('Configuration (status type):')
        print(json.dumps(config, indent=2))
    elif status_prop.get('type') == 'select':
        config = status_prop.get('select', {})
        print('Configuration (select type):')
        options = config.get('options', [])
        for opt in options:
            print(f'  - {opt.get("name")}')
            
    print('\n📌 TYPE PROPERTY:')
    type_prop = props.get('Type', {})
    print(f'Type: {type_prop.get("type")}')
    config = type_prop.get('select', {})
    options = config.get('options', [])
    for opt in options:
        print(f'  - {opt.get("name")}')
