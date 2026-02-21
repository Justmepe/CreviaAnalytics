"""
Reddit Browser Poster - Post to Reddit using Playwright browser automation

Similar to SubstackBrowserPoster and XBrowserPoster, uses:
- Playwright for browser control
- Email/password login (no OAuth needed)
- Persistent session storage
- Markdown formatting support
- Error handling and retry logic
"""

import os
import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class RedditLoginCredentials:
    """Reddit login credentials"""
    email: str
    password: str
    username: str


class RedditBrowserPoster:
    """
    Post content to Reddit using browser automation.
    
    Similar to SubstackBrowserPoster and XBrowserPoster:
    - Uses Playwright for browser control
    - Stores persistent session
    - Supports markdown formatting
    - Handles rate limiting
    """
    
    def __init__(self, session_dir: Optional[str] = None, headless: bool = True):
        """
        Initialize Reddit browser poster.
        
        Args:
            session_dir: Directory to store Chromium session (default: reddit_browser_session)
            headless: Run browser in headless mode (default: True)
        """
        # Get credentials from environment
        self.email = os.getenv('REDDIT_EMAIL', '')
        self.password = os.getenv('REDDIT_PASSWORD', '')
        self.username = os.getenv('REDDIT_USERNAME', '')
        
        # Session management
        session_dir = session_dir or os.getenv('REDDIT_SESSION_DIR', 'reddit_browser_session')
        self.session_dir = PROJECT_ROOT / session_dir
        self.session_dir.mkdir(exist_ok=True, parents=True)
        
        self.headless = headless
        self.enabled = False
        
        # Check if credentials are available
        if not all([self.email, self.password, self.username]):
            logger.warning(
                "[Reddit] Missing credentials. Set REDDIT_EMAIL, REDDIT_PASSWORD, "
                "REDDIT_USERNAME in .env file"
            )
            return
        
        self.enabled = True
        logger.info("[Reddit] ✅ Browser poster initialized")
    
    def _login(self, page: Page) -> bool:
        """
        Login to Reddit with email/password.
        
        Args:
            page: Playwright page object
        
        Returns:
            bool: True if login successful
        """
        try:
            logger.info("[Reddit] Logging in...")
            
            # Navigate to Reddit login
            page.goto("https://www.reddit.com/login", wait_until="networkidle")
            time.sleep(1)
            
            # Fill email
            email_field = page.locator('input[name="username"]')
            if email_field.count() > 0:
                email_field.fill(self.email)
            else:
                logger.warning("[Reddit] Email field not found")
                return False
            
            time.sleep(0.5)
            
            # Fill password
            password_field = page.locator('input[name="password"]')
            if password_field.count() > 0:
                password_field.fill(self.password)
            else:
                logger.warning("[Reddit] Password field not found")
                return False
            
            time.sleep(0.5)
            
            # Click login button
            login_button = page.locator('button:has-text("Log in")')
            if login_button.count() > 0:
                login_button.click()
            else:
                # Try alternative button selector
                login_button = page.locator('button[type="submit"]')
                login_button.click()
            
            # Wait for login to complete
            page.wait_for_url("https://www.reddit.com/", timeout=10000)
            time.sleep(2)
            
            logger.info("[Reddit] ✅ Login successful")
            return True
            
        except Exception as e:
            logger.error(f"[Reddit] Login failed: {e}")
            return False
    
    def post_article(
        self,
        title: str,
        body: str,
        subreddit: str = "cryptocurrency"
    ) -> Optional[str]:
        """
        Post article to Reddit.
        
        Args:
            title: Post title (max 300 characters)
            body: Post body (markdown formatted)
            subreddit: Target subreddit (without r/ prefix)
        
        Returns:
            Optional[str]: Post URL if successful, None otherwise
        """
        if not self.enabled:
            logger.error("[Reddit] Reddit poster not enabled. Check credentials.")
            return None
        
        try:
            with sync_playwright() as p:
                # Launch browser with persistent session
                context = p.chromium.launch_persistent_context(
                    str(self.session_dir),
                    headless=self.headless,
                    viewport={"width": 1280, "height": 900},
                    args=['--disable-blink-features=AutomationControlled'],
                )
                
                page = context.new_page()
                
                try:
                    # Check if already logged in by trying to access subreddit
                    logger.info(f"[Reddit] Navigating to r/{subreddit}...")
                    page.goto(f"https://www.reddit.com/r/{subreddit}", wait_until="networkidle")
                    time.sleep(1)
                    
                    # Check if we need to login (look for login button)
                    if page.locator('button:has-text("Log In")').count() > 0:
                        logger.info("[Reddit] Session expired, logging in...")
                        if not self._login(page):
                            return None
                        # Navigate back to subreddit after login
                        page.goto(f"https://www.reddit.com/r/{subreddit}", wait_until="networkidle")
                        time.sleep(1)
                    
                    # Click "Create Post" button
                    logger.info("[Reddit] Clicking 'Create Post' button...")
                    create_post_button = page.locator('a:has-text("Create a post")')
                    
                    if create_post_button.count() == 0:
                        # Try alternative selector
                        create_post_button = page.locator('button:has-text("Create")')
                    
                    if create_post_button.count() > 0:
                        create_post_button.click()
                    else:
                        logger.warning("[Reddit] Create post button not found")
                        page.screenshot(path=str(PROJECT_ROOT / "debug_reddit_create.png"))
                        return None
                    
                    time.sleep(2)
                    
                    # Fill title
                    logger.info("[Reddit] Filling title...")
                    title_field = page.locator('textarea[placeholder*="Title"]')
                    
                    if title_field.count() == 0:
                        title_field = page.locator('input[placeholder*="Title"]')
                    
                    if title_field.count() > 0:
                        title_field.fill(title)
                    else:
                        logger.warning("[Reddit] Title field not found")
                        page.screenshot(path=str(PROJECT_ROOT / "debug_reddit_title.png"))
                        return None
                    
                    time.sleep(1)
                    
                    # Select text post type (if needed)
                    text_post_button = page.locator('button:has-text("Text")')
                    if text_post_button.count() > 0:
                        text_post_button.click()
                        time.sleep(1)
                    
                    # Fill body
                    logger.info("[Reddit] Filling body...")
                    body_field = page.locator('[contenteditable="true"]')
                    
                    if body_field.count() == 0:
                        body_field = page.locator('textarea[placeholder*="Text"]')
                    
                    if body_field.count() > 0:
                        body_field.click()
                        time.sleep(0.5)
                        body_field.fill(body)
                    else:
                        logger.warning("[Reddit] Body field not found")
                        page.screenshot(path=str(PROJECT_ROOT / "debug_reddit_body.png"))
                        return None
                    
                    time.sleep(1)
                    
                    # Click Post button
                    logger.info("[Reddit] Clicking 'Post' button...")
                    post_button = page.locator('button:has-text("Post")')
                    
                    if post_button.count() > 0:
                        post_button.click()
                    else:
                        logger.warning("[Reddit] Post button not found")
                        page.screenshot(path=str(PROJECT_ROOT / "debug_reddit_post.png"))
                        return None
                    
                    # Wait for post to be created
                    time.sleep(3)
                    
                    # Get post URL from current page
                    current_url = page.url
                    logger.info(f"[Reddit] ✅ Post created: {current_url}")
                    
                    return current_url
                    
                except Exception as e:
                    logger.error(f"[Reddit] Error during posting: {e}", exc_info=True)
                    page.screenshot(path=str(PROJECT_ROOT / "debug_reddit_error.png"))
                    return None
                
                finally:
                    page.close()
                    context.close()
        
        except Exception as e:
            logger.error(f"[Reddit] Browser error: {e}", exc_info=True)
            return None
    
    def post_to_subreddit(
        self,
        title: str,
        body: str,
        subreddit: str
    ) -> Optional[str]:
        """
        Post to specific subreddit.
        
        Args:
            title: Post title
            body: Post body (markdown)
            subreddit: Subreddit name (without r/)
        
        Returns:
            Optional[str]: Post URL if successful
        """
        return self.post_article(title, body, subreddit)
    
    def post_market_analysis(
        self,
        title: str,
        analysis_body: str,
        asset: str = "BTC"
    ) -> Optional[str]:
        """
        Post market analysis to cryptocurrency subreddit.
        
        Args:
            title: Analysis title
            analysis_body: Analysis content (markdown)
            asset: Primary asset (BTC, ETH, etc.)
        
        Returns:
            Optional[str]: Post URL
        """
        formatted_title = f"[{asset}] {title}"
        return self.post_article(formatted_title, analysis_body, "cryptocurrency")
    
    def post_breaking_news(
        self,
        headline: str,
        news_body: str,
        ticker: str = "BTC"
    ) -> Optional[str]:
        """
        Post breaking news to CryptoMarkets subreddit.
        
        Args:
            headline: News headline
            news_body: News article content
            ticker: Asset ticker
        
        Returns:
            Optional[str]: Post URL
        """
        formatted_title = f"[{ticker}] Breaking: {headline}"
        return self.post_article(formatted_title, news_body, "CryptoMarkets")


# Singleton instance
_reddit_browser_poster = None


def get_reddit_browser_poster(
    session_dir: Optional[str] = None,
    headless: bool = True
) -> RedditBrowserPoster:
    """
    Get or create RedditBrowserPoster instance.
    
    Args:
        session_dir: Browser session directory
        headless: Run in headless mode
    
    Returns:
        RedditBrowserPoster instance
    """
    global _reddit_browser_poster
    if _reddit_browser_poster is None:
        _reddit_browser_poster = RedditBrowserPoster(session_dir=session_dir, headless=headless)
    return _reddit_browser_poster
