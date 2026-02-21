"""
Multi-Platform Content Distribution

Unified interface for posting content to:
- X Articles
- Substack Articles
- Reddit posts

Handles retry logic, error handling, and platform-agnostic publishing.
"""

import logging
from typing import Dict, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported distribution platforms"""
    X_ARTICLE = "x_article"
    SUBSTACK_ARTICLE = "substack_article"
    REDDIT = "reddit"


class DistributionResult:
    """Result of a distribution attempt"""
    
    def __init__(self, platform: Platform, success: bool, post_id: Optional[str] = None, error: Optional[str] = None):
        self.platform = platform
        self.success = success
        self.post_id = post_id
        self.error = error
    
    def __repr__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.platform.value}: {self.post_id or self.error}"


class MultiPlatformDistributor:
    """
    Distribute content to multiple platforms simultaneously.
    
    Usage:
        distributor = MultiPlatformDistributor(
            x_poster=x_browser_poster,
            substack_poster=substack_browser,
            reddit_poster=reddit_poster
        )
        
        results = distributor.distribute_article(
            title="Market Analysis",
            body="...",
            platforms=[Platform.X_ARTICLE, Platform.SUBSTACK_ARTICLE, Platform.REDDIT],
            reddit_subreddit="cryptocurrency"
        )
    """
    
    def __init__(self, x_poster=None, substack_poster=None, reddit_poster=None):
        """
        Initialize distributor with platform posters.
        
        Args:
            x_poster: XBrowserPoster instance
            substack_poster: SubstackBrowserPoster instance
            reddit_poster: RedditPoster instance
        """
        self.x_poster = x_poster
        self.substack_poster = substack_poster
        self.reddit_poster = reddit_poster
    
    def distribute_article(
        self,
        title: str,
        body: str,
        platforms: List[Platform] = None,
        reddit_subreddit: str = "cryptocurrency",
        retry_count: int = 1
    ) -> Dict[Platform, DistributionResult]:
        """
        Distribute article to specified platforms.
        
        Args:
            title: Article title
            body: Article body (markdown formatted)
            platforms: List of platforms to post to (default: all available)
            reddit_subreddit: Target subreddit for Reddit posts
            retry_count: Number of retry attempts per platform
        
        Returns:
            Dict mapping Platform to DistributionResult
        """
        if platforms is None:
            platforms = [Platform.X_ARTICLE, Platform.SUBSTACK_ARTICLE, Platform.REDDIT]
        
        results = {}
        
        for platform in platforms:
            if platform == Platform.X_ARTICLE:
                results[platform] = self._distribute_to_x(title, body, retry_count)
            elif platform == Platform.SUBSTACK_ARTICLE:
                results[platform] = self._distribute_to_substack(title, body, retry_count)
            elif platform == Platform.REDDIT:
                results[platform] = self._distribute_to_reddit(title, body, reddit_subreddit, retry_count)
        
        return results
    
    def _distribute_to_x(self, title: str, body: str, retry_count: int) -> DistributionResult:
        """Post article to X"""
        if not self.x_poster or not hasattr(self.x_poster, 'enabled') or not self.x_poster.enabled:
            return DistributionResult(
                Platform.X_ARTICLE,
                False,
                error="X poster not available or disabled"
            )
        
        try:
            logger.info("📤 Posting to X Articles...")
            for attempt in range(retry_count):
                try:
                    post_id = self.x_poster.post_article(title, body)
                    if post_id:
                        logger.info(f"   ✅ X Article posted (ID: {post_id})")
                        return DistributionResult(Platform.X_ARTICLE, True, post_id=post_id)
                except Exception as e:
                    if attempt < retry_count - 1:
                        logger.warning(f"   ⚠️  X attempt {attempt + 1} failed: {e}, retrying...")
                    else:
                        raise
            
            return DistributionResult(
                Platform.X_ARTICLE,
                False,
                error="X posting returned False after retries"
            )
        except Exception as e:
            logger.error(f"   ❌ X Article exception: {e}")
            return DistributionResult(
                Platform.X_ARTICLE,
                False,
                error=str(e)
            )
    
    def _distribute_to_substack(self, title: str, body: str, retry_count: int) -> DistributionResult:
        """Post article to Substack"""
        if not self.substack_poster or not hasattr(self.substack_poster, 'enabled') or not self.substack_poster.enabled:
            return DistributionResult(
                Platform.SUBSTACK_ARTICLE,
                False,
                error="Substack poster not available or disabled"
            )
        
        try:
            logger.info("📤 Posting to Substack Articles...")
            for attempt in range(retry_count):
                try:
                    post_id = self.substack_poster.post_article(title, body)
                    if post_id:
                        logger.info(f"   ✅ Substack Article posted (ID: {post_id})")
                        return DistributionResult(Platform.SUBSTACK_ARTICLE, True, post_id=post_id)
                except Exception as e:
                    if attempt < retry_count - 1:
                        logger.warning(f"   ⚠️  Substack attempt {attempt + 1} failed: {e}, retrying...")
                    else:
                        raise
            
            return DistributionResult(
                Platform.SUBSTACK_ARTICLE,
                False,
                error="Substack posting returned False after retries"
            )
        except Exception as e:
            logger.error(f"   ❌ Substack Article exception: {e}")
            return DistributionResult(
                Platform.SUBSTACK_ARTICLE,
                False,
                error=str(e)
            )
    
    def _distribute_to_reddit(
        self,
        title: str,
        body: str,
        subreddit: str,
        retry_count: int
    ) -> DistributionResult:
        """Post article to Reddit (supports both browser and OAuth posters)"""
        if not self.reddit_poster:
            return DistributionResult(
                Platform.REDDIT,
                False,
                error="Reddit poster not available"
            )
        
        try:
            logger.info(f"📤 Posting to Reddit (r/{subreddit})...")
            for attempt in range(retry_count):
                try:
                    # Check if it's a browser poster (has .post_article method returning URL)
                    if hasattr(self.reddit_poster, 'enabled') and not self.reddit_poster.enabled:
                        return DistributionResult(
                            Platform.REDDIT,
                            False,
                            error="Reddit poster disabled - check credentials"
                        )
                    
                    # Try browser poster method (returns URL or None)
                    if hasattr(self.reddit_poster, 'post_article') and not hasattr(self.reddit_poster, 'is_authenticated'):
                        post_url = self.reddit_poster.post_article(
                            title=title,
                            body=body,
                            subreddit=subreddit
                        )
                        
                        if post_url:
                            logger.info(f"   ✅ Reddit post created: {post_url}")
                            return DistributionResult(Platform.REDDIT, True, post_id=post_url)
                        else:
                            if attempt < retry_count - 1:
                                logger.warning(f"   ⚠️  Reddit attempt {attempt + 1} failed, retrying...")
                            else:
                                raise Exception("Post returned None")
                    
                    # Try OAuth poster method (returns tuple)
                    elif hasattr(self.reddit_poster, 'is_authenticated'):
                        if not self.reddit_poster.is_authenticated:
                            return DistributionResult(
                                Platform.REDDIT,
                                False,
                                error="Reddit poster not authenticated"
                            )
                        
                        success, result = self.reddit_poster.post_analysis(
                            title=title,
                            content=body,
                            subreddit=subreddit
                        )
                        
                        if success:
                            logger.info(f"   ✅ Reddit post created (ID: {result})")
                            return DistributionResult(Platform.REDDIT, True, post_id=result)
                        else:
                            if attempt < retry_count - 1:
                                logger.warning(f"   ⚠️  Reddit attempt {attempt + 1} failed: {result}, retrying...")
                            else:
                                raise Exception(result)
                    
                except Exception as e:
                    if attempt < retry_count - 1:
                        logger.warning(f"   ⚠️  Reddit attempt {attempt + 1} failed: {e}, retrying...")
                    else:
                        raise
            
            return DistributionResult(
                Platform.REDDIT,
                False,
                error="Reddit posting failed after retries"
            )
        except Exception as e:
            logger.error(f"   ❌ Reddit exception: {e}")
            return DistributionResult(
                Platform.REDDIT,
                False,
                error=str(e)
            )
    
    def print_summary(self, results: Dict[Platform, DistributionResult]):
        """Print distribution results summary"""
        logger.info("\n" + "="*80)
        logger.info("📊 DISTRIBUTION SUMMARY")
        logger.info("="*80)
        
        for platform, result in results.items():
            logger.info(f"   {result}")
        
        success_count = sum(1 for r in results.values() if r.success)
        total_count = len(results)
        
        logger.info(f"\n   Result: {success_count}/{total_count} platforms successful")
        logger.info("="*80 + "\n")


def get_multi_platform_distributor(
    x_poster=None,
    substack_poster=None,
    reddit_poster=None
) -> MultiPlatformDistributor:
    """
    Factory function to create distributor with available posters.
    
    Args:
        x_poster: XBrowserPoster instance (optional)
        substack_poster: SubstackBrowserPoster instance (optional)
        reddit_poster: RedditPoster instance (optional)
    
    Returns:
        MultiPlatformDistributor instance
    """
    return MultiPlatformDistributor(
        x_poster=x_poster,
        substack_poster=substack_poster,
        reddit_poster=reddit_poster
    )
