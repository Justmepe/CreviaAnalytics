#!/usr/bin/env python3
"""
Find your Notion databases and their IDs
Run this to see all databases currently accessible to your integration
"""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
api_key = os.getenv('NOTION_API_KEY')

if not api_key:
    print("❌ NOTION_API_KEY not found in .env")
    exit(1)

try:
    client = Client(auth=api_key)
    
    # Search for all databases (we'll get what's accessible)
    response = client.databases.list()
    
    print("\n" + "="*60)
    print("📚 ACCESSIBLE NOTION DATABASES")
    print("="*60)
    
    databases = response.get('results', [])
    
    if not databases:
        print("\n❌ No databases found!")
        print("Make sure to:")
        print("  1. Share your database with CreviaAnalytics integration")
        print("  2. Go to Database → Share → Add CreviaAnalytics")
        print("\nIf you just shared it, wait a moment and try again.")
    else:
        print(f"\n✓ Found {len(databases)} database(s):\n")
        
        for db in databases:
            # Get title
            title = ''
            if 'title' in db:
                title_blocks = db.get('title', [])
                if title_blocks:
                    title = title_blocks[0].get('plain_text', 'Untitled')
            
            db_id = db.get('id', 'unknown')
            
            # Format the ID with dashes for readability
            formatted_id = db_id.replace('-', '')
            if len(formatted_id) == 32:
                formatted_id = f"{formatted_id[:8]}-{formatted_id[8:12]}-{formatted_id[12:16]}-{formatted_id[16:20]}-{formatted_id[20:]}"
            
            print(f"Database: {title}")
            print(f"ID: {formatted_id}")
            print(f"Use in .env: NOTION_DATABASE_ID={db_id}")
            
            # Show properties
            props = db.get('properties', {})
            if props:
                print(f"Properties: {list(props.keys())}")
            print()
    
    print("="*60)
    print("\n📝 NEXT STEPS:")
    print("1. Find your database in the list above")
    print("2. Copy the ID (without dashes)")
    print("3. Update your .env file with the correct ID")
    print("4. If your database isn't listed:")
    print("   → Go to Notion")
    print("   → Open your database")
    print("   → Click Share button")
    print("   → Add 'CreviaAnalytics' integration")
    print("   → Wait 30 seconds and run this script again")
    print("\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure:")
    print("  • NOTION_API_KEY is set in .env")
    print("  • Your integration has access to at least one database")
    print("  • Run: pip install notion-client")
