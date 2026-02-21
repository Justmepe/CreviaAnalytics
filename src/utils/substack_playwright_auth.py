"""
Substack Authentication using Playwright Browser Automation

IMPROVED VERSION - Based on actual Substack flow:
1. Go to https://substack.com (homepage)
2. Click  "Sign in" link/button
3. Click "Sign in with password" option
4. Fill email field (human-like typing: 40ms per char)
5. Wait for password field to appear (1-6 seconds)
6. Fill password field
7. Click Continue button
8. Wait for login redirect
9. Extract session cookies

The key improvements:
- Starts from homepage, not /auth/login (Substack redirects)
- Waits for password field to appear after email entry
- Uses proper selectors for "Sign in" button navigation
- Includes comprehensive debugging with screenshots on failure
- Handles multi-step form properly
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    from playwright.async_api import async_playwright, Page, Browser
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / 'data'
COOKIE_FILE = DATA_DIR / 'substack_cookies.json'


async def authenticate_with_playwright(
    email: str,
    password: str,
    headless: bool = True,
    show_browser: bool = False
) -> Dict[str, str]:
    """
    Authenticate with Substack using Playwright.
    
    ACTUAL FLOW:
    1. Go to https://substack.com (homepage)
    2. Click "Sign in" link (top navigation)
    3. Get redirected to sign-in page with options
    4. Click "Sign in with password" option/button
    5. Email field becomes visible
    6. Type email slowly (human-like: 40ms per char)
    7. Password field appears after email is filled
    8. Type password
    9. Click Continue button
    10. Wait for redirect & extract cookies
    
    Args:
        email: Login email
        password: Login password
        headless: Run in headless mode
        show_browser: Show browser window for debugging
        
    Returns:
        Dict of cookies {name: value} or empty dict if failed
    """
    
    browser: Optional[Browser] = None
    
    try:
        logger.info("[SubstackAuth] ===== SUBSTACK LOGIN (IMPROVED FLOW) =====")
        logger.info(f"[SubstackAuth] Email: {email}")
        
        # Launch browser
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=headless and not show_browser,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        # ===== STEP 1: Homepage =====
        logger.info("[SubstackAuth] STEP 1: Navigate to https://substack.com")
        await page.goto('https://substack.com', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(2)
        
        # ===== STEP 2: Click "Sign in" =====
        logger.info("[SubstackAuth] STEP 2: Click 'Sign in' button")
        
        sign_in_found = False
        for selector in ["a:has-text('Sign in')", "button:has-text('Sign in')"]:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    await elements[0].click()
                    await asyncio.sleep(3)
                    sign_in_found = True
                    logger.info("[SubstackAuth] ✓ Clicked 'Sign in'")
                    break
            except:
                pass
        
        if not sign_in_found:
            logger.error("[SubstackAuth] 'Sign in' button not found")
            await browser.close()
            return {}
        
        # ===== STEP 3: Click "Sign in with password" =====
        logger.info("[SubstackAuth] STEP 3: Click 'Sign in with password'")
        
        pwd_signin_found = False
        for selector in ["button:has-text('Sign in with password')", "a:has-text('Sign in with password')"]:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    await elements[0].click()
                    await asyncio.sleep(2)
                    pwd_signin_found = True
                    logger.info("[SubstackAuth] ✓ Clicked 'Sign in with password'")
                    break
            except:
                pass
        
        if not pwd_signin_found:
            logger.warning("[SubstackAuth] 'Sign in with password' not found (might already be on form)")
        
        await asyncio.sleep(1)
        
        # ===== STEP 4: Fill Email =====
        logger.info("[SubstackAuth] STEP 4: Find and fill email field")
        
        email_field = None
        for selector in ["input[type='email']", "input[placeholder='Email']", "input[name='email']"]:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    visible = await elements[0].is_visible()
                    if visible:
                        email_field = elements[0]
                        logger.info(f"[SubstackAuth] Found email field: {selector}")
                        break
            except:
                pass
        
        if not email_field:
            logger.error("[SubstackAuth] EMAIL FIELD NOT FOUND")
            
            # Debug
            all_inputs = await page.query_selector_all('input')
            logger.error(f"[SubstackAuth] Page has {len(all_inputs)} input elements")
            for i, inp in enumerate(all_inputs[:10]):
                try:
                    itype = await inp.get_attribute('type')
                    iplac = await inp.get_attribute('placeholder')
                    logger.error(f"  [{i}] type={itype}, placeholder={iplac}")
                except:
                    pass
            
            try:
                await page.screenshot(path='substack_debug_email.png')
                logger.error("[SubstackAuth] Debug screenshot: substack_debug_email.png")
            except:
                pass
            
            await browser.close()
            return {}
        
        # Type email slowly
        logger.info(f"[SubstackAuth] Typing email: {email}")
        await email_field.click()
        await asyncio.sleep(0.5)
        
        for char in email:
            await email_field.type(char, delay=40)
            await asyncio.sleep(0.05)
        
        logger.info("[SubstackAuth] ✓ Email entered")
        await asyncio.sleep(1.5)  # Wait for form to process
        
        # ===== STEP 5: Password field appears after email =====
        logger.info("[SubstackAuth] STEP 5: Wait for password field to appear")
        
        password_field = None
        
        for attempt in range(6):  # Try for 6 seconds
            for selector in ["input[type='password']", "input[placeholder='Password']", "input[name='password']"]:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        if await elem.is_visible():
                            password_field = elem
                            logger.info(f"[SubstackAuth] Found password field: {selector}")
                            break
                    if password_field:
                        break
                except:
                    pass
            
            if password_field:
                break
            
            if attempt < 5:
                logger.info(f"[SubstackAuth] Password field not visible yet, waiting 1s...")
                await asyncio.sleep(1)
        
        if not password_field:
            logger.error("[SubstackAuth] PASSWORD FIELD NOT FOUND")
            
            # Debug
            all_inputs = await page.query_selector_all('input')
            logger.error(f"[SubstackAuth] Page has {len(all_inputs)} input elements")
            for i, inp in enumerate(all_inputs[:10]):
                try:
                    itype = await inp.get_attribute('type')
                    iplac = await inp.get_attribute('placeholder')
                    visible = await inp.is_visible()
                    logger.error(f"  [{i}] type={itype}, placeholder={iplac}, visible={visible}")
                except:
                    pass
            
            try:
                await page.screenshot(path='substack_debug_password.png')
                logger.error("[SubstackAuth] Debug screenshot: substack_debug_password.png")
            except:
                pass
            
            await browser.close()
            return {}
        
        # Type password slowly
        logger.info("[SubstackAuth] Typing password...")
        await password_field.click()
        await asyncio.sleep(0.5)
        
        for char in password:
            await password_field.type(char, delay=40)
            await asyncio.sleep(0.05)
        
        logger.info("[SubstackAuth] ✓ Password entered")
        await asyncio.sleep(1)
        
        # ===== STEP 6: Click Continue =====
        logger.info("[SubstackAuth] STEP 6: Click Continue button")
        
        continue_button = None
        for selector in ["button:has-text('Continue')", "input[type='submit']", "button[type='submit']"]:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    continue_button = elements[0]
                    logger.info(f"[SubstackAuth] Found Continue: {selector}")
                    break
            except:
                pass
        
        if not continue_button:
            logger.error("[SubstackAuth] CONTINUE BUTTON NOT FOUND")
            await browser.close()
            return {}
        
        logger.info("[SubstackAuth] Clicking Continue...")
        await continue_button.click()
        await asyncio.sleep(3)
        
        # ===== STEP 7: Wait for redirect =====
        logger.info("[SubstackAuth] STEP 7: Waiting for login to complete...")
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
        except:
            logger.warning("[SubstackAuth] Network idle timeout, continuing...")
        
        await asyncio.sleep(3)
        
        # Check if login was successful
        current_url = page.url
        logger.info(f"[SubstackAuth] Current URL: {current_url}")
        
        # If still on login page, something failed
        if 'auth' in current_url.lower() and 'sign' in current_url.lower():
            logger.error("[SubstackAuth] Still on login page after form submission!")
            await browser.close()
            return {}
        
        # ===== STEP 8: Extract cookies =====
        logger.info("[SubstackAuth] STEP 8: Extracting cookies...")
        
        cookies = await context.cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        
        # If no substack.sid yet, try navigating to a protected page
        if 'substack.sid' not in cookie_dict and cookie_dict:
            logger.info("[SubstackAuth] No substack.sid in initial cookies, checking account page...")
            try:
                await page.goto(f'https://substack.com/publication', wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(2)
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                logger.info(f"[SubstackAuth] After redirect: {list(cookie_dict.keys())}")
            except:
                logger.warning("[SubstackAuth] Could not navigate to check protected page")
        
        # Alternative: check localStorage for session token
        if 'substack.sid' not in cookie_dict:
            logger.warning("[SubstackAuth] Checking localStorage for session data...")
            try:
                local_data = await page.evaluate("() => localStorage")
                if local_data:
                    logger.info(f"[SubstackAuth] localStorage keys: {list(local_data.keys())}")
                    # Add localStorage items to cookie dict if they look like auth tokens
                    for key, val in local_data.items():
                        if isinstance(val, str) and (len(val) > 20 or 'sid' in key.lower()):
                            cookie_dict[f"localStorage_{key}"] = val
            except Exception as e:
                logger.debug(f"[SubstackAuth] Could not read localStorage: {e}")
        
        if not cookie_dict:
            logger.error("[SubstackAuth] No cookies found at all")
            await context.close()
            await browser.close()
            return {}
        
        logger.info(f"[SubstackAuth] ✓ Extracted {len(cookie_dict)} cookies")
        
        if 'substack.sid' in cookie_dict:
            logger.info(f"[SubstackAuth] ✓✓✓ SUCCESS! Found substack.sid")
            logger.info(f"[SubstackAuth] Cookie (first 60 chars): {cookie_dict['substack.sid'][:60]}...")
        else:
            logger.warning(f"[SubstackAuth] No substack.sid found (have: {list(cookie_dict.keys())[:5]}...)")
        
        await context.close()
        await browser.close()
        
        logger.info("[SubstackAuth] ===== AUTHENTICATION COMPLETE =====")
        return cookie_dict
        
    except Exception as e:
        logger.error(f"[SubstackAuth] FATAL ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if browser:
            try:
                await browser.close()
            except:
                pass
        return {}


def authenticate_substack(email: str, password: str, headless: bool = True) -> Dict[str, str]:
    """
    Synchronous wrapper for Playwright authentication.
    
    Args:
        email: Login email
        password: Login password
        headless: Run in headless mode
        
    Returns:
        Dict of cookies {name: value} or empty dict if failed
    """
    try:
        logger.info("[SubstackAuth] Starting synchronous wrapper")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            authenticate_with_playwright(email, password, headless)
        )
        loop.close()
        logger.info(f"[SubstackAuth] Wrapper finished: {len(result)} cookies")
        return result
    except Exception as e:
        logger.error(f"[SubstackAuth] Wrapper error: {e}")
        return {}
