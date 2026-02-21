"""
Reddit Poster - Post market analysis and news to Reddit

Supports posting to:
- r/cryptocurrency (general market analysis)
- r/CryptoMarkets (trading insights)
- Custom subreddits

Uses PRAW (Python Reddit API Wrapper) for Reddit OAuth authentication.
"""

import os
import logging
from typing import Dict, Optional, Tuple
import praw
from datetime import datetime

logger = logging.getLogger(__name__)


class RedditPoster:
    """Post content to Reddit using PRAW OAuth"""
    
    def __init__(self):
        """Initialize Reddit client with OAuth credentials"""
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'CreviaAnalytics/1.0 by CreviaAnalytics')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        
        self.reddit = None
        self._authenticated = False
        
        # Check if credentials are configured
        if not all([self.client_id, self.client_secret, self.username, self.password]):
            logger.warning(
                "[Reddit] Missing OAuth credentials. Configure REDDIT_CLIENT_ID, "
                "REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD in .env"
            )
            return
        
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """
        Authenticate with Reddit API using OAuth.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                username=self.username,
                password=self.password
            )
            
            # Test authentication
            test_user = self.reddit.user.me()
            logger.info(f"[Reddit] Authenticated as: {test_user.name}")
            self._authenticated = True
            return True
            
        except praw.exceptions.InvalidPassword:
            logger.error("[Reddit] Invalid username or password")
            return False
        except praw.exceptions.ResponseException as e:
            logger.error(f"[Reddit] Authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"[Reddit] Unexpected error during authentication: {e}")
            return False
    
    def post_analysis(
        self,
        title: str,
        content: str,
        subreddit: str = "cryptocurrency",
        asset_tag: Optional[str] = None,
        market_data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Post market analysis to Reddit.
        
        Args:
            title: Post title (max 300 chars)
            content: Post body (markdown formatted)
            subreddit: Target subreddit (default: cryptocurrency)
            asset_tag: Asset tag for flair (BTC, ETH, etc.)
            market_data: Additional market data for post formatting
        
        Returns:
            Tuple of (success: bool, post_id: str or error_message: str)
        """
        if not self._authenticated:
            return False, "[Reddit] Not authenticated. Cannot post."
        
        try:
            # Validate title length
            if len(title) > 300:
                logger.warning(f"[Reddit] Title too long ({len(title)} > 300), truncating")
                title = title[:297] + "..."
            
            # Add timestamp to avoid duplicates
            header = f"**{datetime.now().strftime('%B %d, %Y at %H:%M UTC')}**\n\n"
            full_content = header + content
            
            # Limit total length to avoid Reddit's 40,000 char limit
            if len(full_content) > 35000:
                logger.warning(f"[Reddit] Content too long ({len(full_content)} chars), truncating")
                full_content = full_content[:34900] + "\n\n*[Content truncated due to length]*"
            
            # Get subreddit
            sub = self.reddit.subreddit(subreddit)
            
            logger.info(
                f"[Reddit] Posting to r/{subreddit}: '{title[:60]}...'"
            )
            
            # Submit post
            submission = sub.submit(
                title=title,
                selftext=full_content
            )
            
            logger.info(f"[Reddit] ✅ Posted successfully: {submission.url}")
            
            return True, submission.id
            
        except praw.exceptions.InvalidSubreddit:
            error_msg = f"[Reddit] Subreddit r/{subreddit} not found or inaccessible"
            logger.error(error_msg)
            return False, error_msg
        except praw.exceptions.InvalidURL:
            error_msg = "[Reddit] Invalid content format"
            logger.error(error_msg)
            return False, error_msg
        except praw.exceptions.ResponseException as e:
            error_msg = f"[Reddit] API error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"[Reddit] Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def post_newsletter(
        self,
        newsletter_title: str,
        newsletter_body: str,
        asset: str = "BTC"
    ) -> Tuple[bool, str]:
        """
        Post daily/weekly newsletter to Reddit.
        
        Args:
            newsletter_title: Newsletter title
            newsletter_body: Full newsletter markdown
            asset: Primary asset analyzed
        
        Returns:
            Tuple of (success: bool, post_id or error)
        """
        # Format for Reddit with asset tag
        formatted_title = f"{newsletter_title} | {asset}"
        
        return self.post_analysis(
            title=formatted_title,
            content=newsletter_body,
            subreddit="cryptocurrency",
            asset_tag=asset
        )
    
    def post_breaking_news(
        self,
        headline: str,
        article_body: str,
        ticker: str = "BTC"
    ) -> Tuple[bool, str]:
        """
        Post breaking news article to Reddit.
        
        Args:
            headline: News headline
            article_body: Full article markdown
            ticker: Asset ticker
        
        Returns:
            Tuple of (success: bool, post_id or error)
        """
        # Add source attribution
        title = f"[{ticker}] {headline}"
        
        # Add cross-posting notice
        footer = "\n\n---\n\n*This analysis was also published on [Substack](https://petergikonyo.substack.com) and [X (Twitter)](https://x.com/Peter_N_Gikonyo). Follow for real-time market updates.*"
        full_body = article_body + footer
        
        return self.post_analysis(
            title=title,
            content=full_body,
            subreddit="CryptoMarkets",
            asset_tag=ticker
        )
    
    def post_to_custom_subreddit(
        self,
        title: str,
        content: str,
        subreddit: str
    ) -> Tuple[bool, str]:
        """
        Post to custom subreddit.
        
        Args:
            title: Post title
            content: Post content
            subreddit: Target subreddit (without r/)
        
        Returns:
            Tuple of (success: bool, post_id or error)
        """
        return self.post_analysis(
            title=title,
            content=content,
            subreddit=subreddit
        )
    
    def get_submission_stats(self, submission_id: str) -> Dict:
        """
        Get stats for a posted submission.
        
        Args:
            submission_id: Reddit submission ID
        
        Returns:
            Dict with submission stats
        """
        if not self._authenticated:
            return {"error": "Not authenticated"}
        
        try:
            submission = self.reddit.submission(id=submission_id)
            
            return {
                "title": submission.title,
                "score": submission.score,
                "upvotes": submission.ups,
                "downvotes": submission.downs,
                "comments": submission.num_comments,
                "url": submission.url,
                "created_utc": submission.created_utc,
                "author": str(submission.author)
            }
        except Exception as e:
            logger.error(f"[Reddit] Error fetching submission stats: {e}")
            return {"error": str(e)}
    
    @property
    def is_authenticated(self) -> bool:
        """Check if Reddit API is authenticated"""
        return self._authenticated


# Singleton instance
_reddit_poster = None


def get_reddit_poster() -> RedditPoster:
    """Get or create Reddit poster instance"""
    global _reddit_poster
    if _reddit_poster is None:
        _reddit_poster = RedditPoster()
    return _reddit_poster


def post_to_reddit(
    title: str,
    content: str,
    subreddit: str = "cryptocurrency",
    post_type: str = "analysis"
) -> Tuple[bool, str]:
    """
    Convenience function to post to Reddit.
    
    Args:
        title: Post title
        content: Post content (markdown)
        subreddit: Target subreddit
        post_type: Type of post (analysis, news, etc.)
    
    Returns:
        Tuple of (success, post_id or error message)
    """
    poster = get_reddit_poster()
    
    if not poster.is_authenticated:
        return False, "Reddit not configured. Missing OAuth credentials in .env"
    
    return poster.post_analysis(
        title=title,
        content=content,
        subreddit=subreddit
    )
