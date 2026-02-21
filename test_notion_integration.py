#!/usr/bin/env python3
"""
Test Notion Integration Setup
Verifies that your Notion connection is properly configured
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.utils.notion_client import get_notion_client
from src.utils.notion_content_manager import get_content_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_notion_integration():
    """Test Notion integration setup."""
    
    print("\n" + "="*60)
    print("🔧 NOTION INTEGRATION TEST")
    print("="*60 + "\n")
    
    load_dotenv()
    
    # Test 1: Check environment variables
    print("Step 1️⃣ : Checking environment variables...")
    api_key = os.getenv('NOTION_API_KEY')
    db_id = os.getenv('NOTION_DATABASE_ID')
    
    if not api_key:
        print("  ❌ NOTION_API_KEY not found in .env")
        print("     → Add it following the setup guide")
        return False
    
    if not db_id:
        print("  ❌ NOTION_DATABASE_ID not found in .env")
        print("     → Add it following the setup guide")
        return False
    
    print(f"  ✅ NOTION_API_KEY configured")
    print(f"  ✅ NOTION_DATABASE_ID configured")
    
    # Test 2: Check notion-client package
    print("\nStep 2️⃣: Checking notion-client package...")
    try:
        from notion_client import Client
        print("  ✅ notion-client is installed")
    except ImportError:
        print("  ❌ notion-client not installed")
        print("     → Install with: pip install notion-client")
        return False
    
    # Test 3: Initialize client
    print("\nStep 3️⃣: Initializing Notion client...")
    try:
        client = get_notion_client()
        if not client.is_available():
            print("  ❌ Failed to initialize Notion client")
            print("     → Check your API key and database ID")
            return False
        print("  ✅ Notion client initialized successfully")
    except Exception as e:
        print(f"  ❌ Error initializing client: {e}")
        return False
    
    # Test 4: Test database connection
    print("\nStep 4️⃣: Testing database connection...")
    try:
        # Try to query the database
        drafts = client.list_drafts(limit=1)
        print(f"  ✅ Database connection successful")
        print(f"     Found {len(drafts)} existing item(s)")
    except Exception as e:
        print(f"  ⚠️  Database query failed: {e}")
        print("     → Ensure your integration has database access")
        print("     → Go to Notion → Share → Add your integration")
        return False
    
    # Test 5: Content manager
    print("\nStep 5️⃣: Initializing content manager...")
    try:
        manager = get_content_manager()
        if not manager.is_available():
            print("  ❌ Content manager not available")
            return False
        print("  ✅ Content manager initialized")
    except Exception as e:
        print(f"  ❌ Error initializing content manager: {e}")
        return False
    
    # Test 6: Optional - Create test draft
    print("\nStep 6️⃣: Creating test draft...")
    try:
        test_page_id = manager.save_news_post(
            title="🧪 Notion Integration Test",
            content="This is a test post created by the integration test script. You can delete this.",
            tags=["Test", "Integration"],
            image_url=None
        )
        
        if test_page_id:
            print(f"  ✅ Test draft created successfully")
            print(f"     Page ID: {test_page_id}")
            print("     → Visit your Notion database to see it")
            print("     → You can delete this test post")
        else:
            print("  ⚠️  Could not create test draft")
            print("     → Check database permissions")
    except Exception as e:
        print(f"  ⚠️  Test draft creation failed: {e}")
    
    # Test 7: Show stats
    print("\nStep 7️⃣: Content statistics...")
    try:
        manager.print_stats()
    except Exception as e:
        print(f"  ⚠️  Could not retrieve stats: {e}")
    
    return True


def main():
    """Run all tests."""
    success = test_notion_integration()
    
    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED!")
        print("\nYour Notion integration is ready to use!")
        print("\nNext steps:")
        print("  1. Review the setup guide: doc/NOTION_SETUP_GUIDE.md")
        print("  2. Start using in your code with:")
        print("     from src.utils.notion_content_manager import get_content_manager")
        print("  3. See usage examples in the setup guide")
    else:
        print("❌ TESTS FAILED")
        print("\nPlease fix the issues above and try again.")
        print("See doc/NOTION_SETUP_GUIDE.md for detailed instructions.")
    print("="*60 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
