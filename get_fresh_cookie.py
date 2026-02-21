#!/usr/bin/env python3
"""
Get fresh Substack.sid cookie using Playwright by extracting from HTTP headers
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def get_fresh_substack_sid():
    """Get a fresh substack.sid by monitoring network responses during login"""
    
    email = os.getenv('SUBSTACK_EMAIL')
    password = os.getenv('SUBSTACK_PASSWORD')
    
    print(f"Getting fresh Substack.sid for {email}...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        context = await browser.new_context()
        page = await context.new_page()
        
        # Intercept responses to find Set-Cookie headers
        sid_value = None
        
        async def handle_response(response):
            nonlocal sid_value
            headers = response.headers
            if 'set-cookie' in headers:
                cookies_header = headers.get('set-cookie', '')
                if 'substack.sid' in cookies_header:
                    # Extract the cookie value
                    # Format: substack.sid=VALUE; Path=/; Domain=.substack.com; HttpOnly; Secure; SameSite=Strict
                    parts = cookies_header.split(';')[0]  # Get first part before semicolon
                    if '=' in parts:
                        sid_value = parts.split('=', 1)[1]
                        print(f"\n✓ Found substack.sid in response headers!")
                        print(f"Cookie value (first 50 chars): {sid_value[:50]}...")
        
        page.on('response', handle_response)
        
        # Navigate and login
        print("STEP 1: Navigate to homepage...")
        await page.goto('https://substack.com', wait_until='domcontentloaded', timeout=30000)
        
        print("STEP 2: Click Sign in...")
        await page.click('button:has-text("Sign in")')
        await page.wait_for_timeout(1000)
        
        print("STEP 3: Click Sign in with password...")
        await page.click('button:has-text("Sign in with password")')
        await page.wait_for_timeout(1000)
        
        print("STEP 4: Fill email...")
        await page.fill('input[type="email"]', email)
        await page.wait_for_timeout(1000)
        
        print("STEP 5: Find and fill password...")
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        await page.fill('input[type="password"]', password)
        await page.wait_for_timeout(500)
        
        print("STEP 6: Click Continue...")
        await page.click('button:has-text("Continue")')
        await page.wait_for_load_state('domcontentloaded', timeout=10000)
        
        print(f"STEP 7: Logged in, current URL: {page.url}")
        
        # If we got the sid from headers, great!
        if sid_value:
            print(f"\n✓✓✓ SUCCESS! Got substack.sid: {sid_value[:60]}...\n")
            
            # Save to .env
            update_env_with_cookie(sid_value)
            
            await context.close()
            await browser.close()
            return sid_value
        
        # If not, check cookies directly
        cookies = await context.cookies()
        print(f"\nAll cookies: {[c['name'] for c in cookies]}")
        
        for cookie in cookies:
            if 'sid' in cookie['name'].lower():
                print(f"Found potential auth cookie: {cookie['name']}")
        
        await context.close()
        await browser.close()
        
        if not sid_value:
            print("\n✗ Could not extract substack.sid from headers")
            print("Try manually:")
            print("  1. Open browser developer tools (F12)")
            print("  2. Go to Network tab")
            print("  3. Log in again")
            print("  4. Find a response with Set-Cookie: substack.sid=...")
            print("  5. Copy the cookie value")
        
        return sid_value

def update_env_with_cookie(cookie_value):
    """Update .env file with fresh cookie"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("✗ .env file not found!")
        return
    
    lines = env_file.read_text().split('\n')
    updated = []
    found = False
    
    for line in lines:
        if line.startswith('SUBSTACK_SID='):
            updated.append(f'SUBSTACK_SID={cookie_value}')
            found = True
        else:
            updated.append(line)
    
    if found:
        env_file.write_text('\n'.join(updated))
        print(f"\n✓ Updated .env with new cookie")
        print(f"New .env line: SUBSTACK_SID={cookie_value[:60]}...")
    else:
        print("✗ SUBSTACK_SID not found in .env")

if __name__ == '__main__':
    sid = asyncio.run(get_fresh_substack_sid())
    
    if sid:
        print("\n" + "="*80)
        print("SUCCESS! Fresh cookie is now in .env")
        print("Next: Run test_complete_workflow.py or quick_test.py")
        print("="*80)
