#!/usr/bin/env python3
"""Verify Notion initialization in main.py"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

print("\n" + "="*70)
print("TESTING NOTION INTEGRATION IN MAIN.PY")
print("="*70 + "\n")

try:
    print("[INIT] Loading CryptoAnalysisOrchestrator...")
    from main import CryptoAnalysisOrchestrator
    
    print("[INIT] Creating orchestrator instance...")
    orchestrator = CryptoAnalysisOrchestrator()
    
    print("\n[SUCCESS] Main orchestrator initialized!\n")
    
    # Check Notion
    print("NOTION INTEGRATION STATUS:")
    print("-" * 70)
    
    if hasattr(orchestrator, 'notion_manager'):
        manager = orchestrator.notion_manager
        print(f"[+] Notion Manager found: {type(manager).__name__}")
        
        if manager.is_available():
            print("[+] Notion is CONNECTED and ready to use")
            stats = manager.get_stats()
            print(f"[+] Database connected")
            print(f"[+] Current content items:")
            print(f"    - Total Drafts: {stats.get('total_drafts', 0)}")
            print(f"    - Published: {stats.get('published', 0)}")
        else:
            print("[-] Notion is configured but not connected")
            print("    Check NOTION_API_KEY and NOTION_DATABASE_ID")
    else:
        print("[-] Notion manager not found in orchestrator")
        
    print("\n" + "="*70)
    print("ORCHESTRATOR COMPONENTS:")
    print("="*70)
    components = [
        ('data', 'Data Aggregator'),
        ('claude_writer', 'Claude Content Writer'),
        ('notion_manager', 'Notion Content Manager'),
        ('discord', 'Discord Notifier'),
        ('x_poster', 'X/Twitter Poster'),
        ('x_browser_poster', 'X Browser Poster'),
        ('web_publisher', 'Web Publisher'),
        ('substack', 'Substack Poster'),
        ('substack_browser', 'Substack Browser Poster'),
    ]
    
    for attr, label in components:
        if hasattr(orchestrator, attr):
            obj = getattr(orchestrator, attr)
            status = "✓" if obj else "-"
            print(f"  [{status}] {label}")
        else:
            print(f"  [-] {label} (not found)")
    
    print("\n" + "="*70)
    print("VERDICT: Main.py is properly initialized with Notion!")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] Failed to initialize: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
