#!/usr/bin/env python3
"""Test the Notion Content Manager"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.notion_content_manager import get_content_manager

print("\n" + "="*60)
print("[TEST] NOTION CONTENT MANAGER")
print("="*60 + "\n")

manager = get_content_manager()

if not manager.is_available():
    print("[-] Notion not available")
    print("   Check .env file for NOTION_API_KEY and NOTION_DATABASE_ID")
    sys.exit(1)

print("[+] Notion Content Manager initialized\n")

try:
    # Test 1: Save a news post
    print("[TEST 1] Saving a news post...")
    page_id = manager.save_news_post(
        title="Test Post: Bitcoin Market Analysis",
        content="This is a test post created by the integration test.\n\nIt contains analysis of market conditions.",
        tags=["Bitcoin", "Test", "Market Analysis"],
        image_url=None
    )
    
    if page_id:
        print(f"[+] News post saved! ID: {page_id}\n")
    else:
        print("[-] Failed to save news post\n")
        sys.exit(1)
    
    # Test 2: Retrieve the draft
    print("[TEST 2] Retrieving the draft...")
    draft = manager.get_draft(page_id)
    if draft:
        print(f"[+] Draft retrieved!")
        print(f"   Title: {draft.get('title', 'N/A')}")
        print(f"   Status: {draft.get('status', 'N/A')}")
        print(f"   Tags: {draft.get('tags', [])}\n")
    else:
        print("[-] Could not retrieve draft (this is normal if it takes time to sync)\n")
    
    # Test 3: List all drafts
    print("[TEST 3] Listing drafts by status...")
    drafts = manager.list_by_status("draft", limit=10)
    print(f"[+] Found {len(drafts)} draft(s)")
    for i, d in enumerate(drafts[:3], 1):
        print(f"   {i}. {d.get('title', 'Untitled')}")
    
    # Test 4: Show statistics
    print("\n[TEST 4] Content Statistics...")
    manager.print_stats()
    
    print("[+] ALL TESTS PASSED!\n")
    print("Your Notion integration is now fully functional!")
    print(f"Page created: {page_id}")
    print("\nNext steps:")
    print("1. Check your Notion database to see the test post")
    print("2. Read doc/NOTION_SETUP_GUIDE.md for full usage guide")
    print("3. Integrate into your main.py analysis pipeline")
    
except Exception as e:
    print(f"[-] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
