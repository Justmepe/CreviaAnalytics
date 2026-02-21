#!/usr/bin/env python3
"""
Quick Setup Test Script

Tests if everything is configured correctly before running main.py
"""

import os
import sys

print("=" * 70)
print("CRYPTO ANALYSIS ENGINE - SETUP TEST")
print("=" * 70)

# Test 1: Check Python version
print("\n[1/5] Checking Python version...")
version = sys.version_info
if version.major >= 3 and version.minor >= 8:
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
else:
    print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Need 3.8+")
    sys.exit(1)

# Test 2: Check API key
print("\n[2/5] Checking ANTHROPIC_API_KEY...")
api_key = os.getenv('ANTHROPIC_API_KEY', '')
if api_key:
    print(f"   ✅ API key found (starts with: {api_key[:10]}...)")
else:
    print("   ❌ API key NOT found!")
    print("   Please set ANTHROPIC_API_KEY environment variable")
    print("\n   Windows PowerShell:")
    print('   $env:ANTHROPIC_API_KEY="sk-ant-your-key-here"')
    print("\n   Or create .env file:")
    print("   ANTHROPIC_API_KEY=sk-ant-your-key-here")
    sys.exit(1)

# Test 3: Import dependencies
print("\n[3/5] Checking dependencies...")
try:
    import anthropic
    print("   ✅ anthropic")
except ImportError:
    print("   ❌ anthropic - Run: pip install anthropic")
    sys.exit(1)

try:
    import requests
    print("   ✅ requests")
except ImportError:
    print("   ❌ requests - Run: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenv")
except ImportError:
    print("   ❌ python-dotenv - Run: pip install python-dotenv")
    sys.exit(1)

# Test 4: Test Anthropic API
print("\n[4/5] Testing Anthropic API connection...")
try:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=10,
        messages=[{"role": "user", "content": "test"}]
    )
    print("   ✅ API connection working!")
    try:
        print(f"   Response: {response.content[0].text}")
    except Exception:
        print("   Response received (raw object)")
except Exception as e:
    print(f"   ❌ API connection failed: {e}")
    sys.exit(1)

# Test 5: Check project structure
print("\n[5/5] Checking project structure...")
required_dirs = ['src', 'src/core', 'src/utils', 'src/pillars', 'src/analyzers', 'src/output']
for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(f"   ✅ {dir_path}/")
    else:
        print(f"   ❌ {dir_path}/ - Missing!")
        sys.exit(1)

# All tests passed!
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nYou're ready to run the engine!")
print("\nNext steps:")
print("1. Run main orchestrator:")
print("   python main.py")
print("\n2. Or generate a single thread:")
print("   python example_generate_x_thread.py")
print("\n3. Or test individual components:")
print("   python test_core.py")
print("=" * 70)
