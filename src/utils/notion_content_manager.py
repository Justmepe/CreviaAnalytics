"""
Notion Content Manager
Manages all content types: newsletters, news posts, tweet threads, reports
Integrates with the crypto analysis engine
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from src.utils.notion_client import get_notion_client

logger = logging.getLogger(__name__)


class NotionContentManager:
    """
    Manages content storage and organization in Notion.
    Supports:
    - Drafts (before publishing)
    - Active content (published)
    - Templates and insights
    """
    
    # Content type definitions
    CONTENT_TYPES = {
        "newsletter": "Newsletter",
        "news_post": "News Post",
        "tweet_thread": "Tweet Thread",
        "report": "Report",
        "insight": "Market Insight"
    }
    
    # Platform definitions
    PLATFORMS = {
        "x": "X (Twitter)",
        "substack": "Substack",
        "web": "Web",
        "reddit": "Reddit",
        "discord": "Discord"
    }
    
    # Status definitions
    STATUSES = {
        "draft": "Drafting",
        "idea": "Idea",
        "review": "Editing",
        "ready": "Editing",
        "published": "Published",
        "scheduled": "Scheduled",
        "archived": "Idea"  # Map archived back to Idea (conceptually)
    }
    
    def __init__(self):
        """Initialize content manager with Notion client."""
        self.notion = get_notion_client()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def is_available(self) -> bool:
        """Check if Notion integration is available."""
        return self.notion.is_available()
    
    # ================== DRAFT MANAGEMENT ==================
    
    def save_draft(
        self,
        title: str,
        content: str,
        content_type: str,
        platform: str,
        tags: List[str] = None,
        image_url: str = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Save content as a draft in Notion.
        
        Args:
            title: Content title
            content: Full content/body
            content_type: Type of content (from CONTENT_TYPES)
            platform: Target platform (from PLATFORMS)
            tags: List of tags (e.g., ["Bitcoin", "DeFi", "Analysis"])
            image_url: URL of featured image
            metadata: Additional metadata to store
        
        Returns:
            Page ID if successful, None otherwise
        
        Example:
            page_id = manager.save_draft(
                title="Bitcoin Rally: What Caused It?",
                content="Market analysis content...",
                content_type="news_post",
                platform="web",
                tags=["Bitcoin", "Market Analysis"],
                image_url="https://example.com/image.png"
            )
        """
        if not self.is_available():
            self.logger.warning("Notion not available. Draft not saved.")
            return None
        
        # Normalize content type
        normalized_type = self.CONTENT_TYPES.get(
            content_type.lower(),
            self.CONTENT_TYPES["news_post"]
        )
        
        # Normalize platform
        normalized_platform = self.PLATFORMS.get(
            platform.lower(),
            self.PLATFORMS["x"]
        )
        
        page_id = self.notion.create_draft(
            title=title,
            content=content,
            content_type=normalized_type,
            platform=normalized_platform,
            status=self.STATUSES["draft"],
            tags=tags or [],
            image_url=image_url
        )
        
        if page_id and metadata:
            self._save_metadata(page_id, metadata)
        
        return page_id
    
    def update_draft(
        self,
        page_id: str,
        title: str = None,
        content: str = None,
        status: str = None,
        tags: List[str] = None,
        image_url: str = None
    ) -> bool:
        """
        Update an existing draft.
        
        Args:
            page_id: Notion page ID
            title: New title (optional)
            content: New content (optional)
            status: New status (optional)
            tags: New tags (optional)
            image_url: New image URL (optional)
        
        Returns:
            True if successful, False otherwise
        
        Example:
            manager.update_draft(
                page_id="abc123",
                status="review",
                tags=["Bitcoin", "Updated"]
            )
        """
        if not self.is_available():
            return False
        
        updates = {}
        if title:
            updates["title"] = title
        if content:
            updates["content"] = content
        if status:
            updates["status"] = self.STATUSES.get(status.lower(), status)
        if tags:
            updates["tags"] = tags
        if image_url:
            updates["image_url"] = image_url
        
        return self.notion.update_draft(page_id, **updates)
    
    def get_draft(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a draft from Notion.
        
        Args:
            page_id: Notion page ID
        
        Returns:
            Draft data or None
        
        Example:
            draft = manager.get_draft("abc123")
            print(draft["title"], draft["content"])
        """
        if not self.is_available():
            return None
        
        draft = self.notion.get_draft(page_id)
        if draft:
            metadata = self._load_metadata(page_id)
            if metadata:
                draft["_metadata"] = metadata
        return draft
    
    # ================== DRAFT LISTING & FILTERING ==================
    
    def list_drafts(
        self,
        status: str = None,
        content_type: str = None,
        platform: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List drafts with optional filtering.
        
        Args:
            status: Filter by status (draft, review, ready, published, etc.)
            content_type: Filter by type (newsletter, news_post, tweet_thread, report, insight)
            platform: Filter by platform (x, substack, web, reddit, discord)
            limit: Maximum number of results
        
        Returns:
            List of drafts
        
        Example:
            # Get all pending drafts for X
            pending = manager.list_drafts(
                status="ready",
                platform="x",
                limit=20
            )
            
            # Get all newsletters
            newsletters = manager.list_drafts(
                content_type="newsletter",
                limit=100
            )
        """
        if not self.is_available():
            return []
        
        # Normalize inputs
        normalized_status = self.STATUSES.get(status.lower()) if status else None
        normalized_type = self.CONTENT_TYPES.get(content_type.lower()) if content_type else None
        normalized_platform = self.PLATFORMS.get(platform.lower()) if platform else None
        
        return self.notion.list_drafts(
            status=normalized_status,
            content_type=normalized_type,
            platform=normalized_platform,
            limit=limit
        )
    
    def list_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all content by status."""
        return self.list_drafts(status=status, limit=limit)
    
    def list_by_platform(self, platform: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all content for a specific platform."""
        return self.list_drafts(platform=platform, limit=limit)
    
    def list_by_type(self, content_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all content of a specific type."""
        return self.list_drafts(content_type=content_type, limit=limit)
    
    # ================== STATUS MANAGEMENT ==================
    
    def mark_as_ready(self, page_id: str) -> bool:
        """Mark a draft as ready to publish."""
        return self.update_draft(page_id, status="ready")
    
    def mark_as_published(self, page_id: str, published_url: str = None) -> bool:
        """Mark a draft as published."""
        success = self.update_draft(page_id, status="published")
        if success and published_url:
            self._save_metadata(page_id, {"published_url": published_url})
        return success
    
    def mark_for_review(self, page_id: str) -> bool:
        """Mark a draft for review."""
        return self.update_draft(page_id, status="review")
    
    def archive_draft(self, page_id: str) -> bool:
        """Archive a draft."""
        return self.notion.archive_draft(page_id)
    
    # ================== SPECIAL CONTENT OPERATIONS ==================
    
    def save_newsletter(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        image_url: str = None
    ) -> Optional[str]:
        """
        Save a newsletter draft.
        
        Example:
            page_id = manager.save_newsletter(
                title="Crypto Weekly Digest - Feb 19",
                content="Market roundup...",
                tags=["Weekly", "Roundup"],
                image_url="https://..."
            )
        """
        return self.save_draft(
            title=title,
            content=content,
            content_type="newsletter",
            platform="substack",
            tags=tags,
            image_url=image_url
        )
    
    def save_news_post(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        image_url: str = None
    ) -> Optional[str]:
        """
        Save a news analysis post.
        
        Example:
            page_id = manager.save_news_post(
                title="Bitcoin Breaks $100K: Here's Why",
                content="Analysis content...",
                tags=["Bitcoin", "Market Analysis"],
                image_url="https://..."
            )
        """
        return self.save_draft(
            title=title,
            content=content,
            content_type="news_post",
            platform="web",
            tags=tags,
            image_url=image_url
        )
    
    def save_tweet_thread(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        image_url: str = None
    ) -> Optional[str]:
        """
        Save a tweet thread draft.
        
        Example:
            page_id = manager.save_tweet_thread(
                title="Daily Market Update",
                content="1/ Market in flux...",
                tags=["Daily", "X"],
                image_url="https://..."
            )
        """
        return self.save_draft(
            title=title,
            content=content,
            content_type="tweet_thread",
            platform="x",
            tags=tags,
            image_url=image_url
        )
    
    def save_report(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        image_url: str = None
    ) -> Optional[str]:
        """
        Save a detailed market report.
        
        Example:
            page_id = manager.save_report(
                title="Q1 Crypto Market Analysis",
                content="Detailed analysis...",
                tags=["Report", "Quarterly"],
                image_url="https://..."
            )
        """
        return self.save_draft(
            title=title,
            content=content,
            content_type="report",
            platform="web",
            tags=tags,
            image_url=image_url
        )
    
    # ================== IMAGE MANAGEMENT ==================
    
    def add_image(self, page_id: str, image_url: str) -> bool:
        """
        Add an image to a draft.
        
        Args:
            page_id: Notion page ID
            image_url: URL of image to add
        
        Returns:
            True if successful, False otherwise
        
        Example:
            manager.add_image(page_id, "https://example.com/chart.png")
        """
        return self.notion.add_image_to_page(page_id, image_url)
    
    # ================== METADATA MANAGEMENT ==================
    
    def _save_metadata(self, page_id: str, metadata: Dict[str, Any]) -> bool:
        """Save additional metadata to a file cache."""
        try:
            metadata_dir = Path("data/notion_metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_file = metadata_dir / f"{page_id}.json"
            
            # Load existing metadata if it exists
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    existing = json.load(f)
                    existing.update(metadata)
                    metadata = existing
            
            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            return False
    
    def _load_metadata(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata for a page."""
        try:
            metadata_file = Path("data/notion_metadata") / f"{page_id}.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
        return None
    
    # ================== STATS & ANALYTICS ==================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get content statistics."""
        if not self.is_available():
            return {}
        
        stats = {
            "total_drafts": len(self.list_drafts(status="draft")),
            "ready_to_publish": len(self.list_drafts(status="ready")),
            "published": len(self.list_drafts(status="published")),
            "in_review": len(self.list_drafts(status="review")),
        }
        
        # By type
        for content_type in self.CONTENT_TYPES.keys():
            stats[f"type_{content_type}"] = len(self.list_by_type(content_type))
        
        # By platform
        for platform in self.PLATFORMS.keys():
            stats[f"platform_{platform}"] = len(self.list_by_platform(platform))
        
        return stats
    
    def print_stats(self):
        """Print content statistics."""
        stats = self.get_stats()
        if not stats:
            print("❌ Notion integration not available")
            return
        
        print("\n" + "="*50)
        print("📊 NOTION CONTENT STATISTICS")
        print("="*50)
        
        print(f"\n📝 STATUS:")
        print(f"  • Drafts: {stats.get('total_drafts', 0)}")
        print(f"  • Ready: {stats.get('ready_to_publish', 0)}")
        print(f"  • Published: {stats.get('published', 0)}")
        print(f"  • In Review: {stats.get('in_review', 0)}")
        
        print(f"\n📚 CONTENT TYPES:")
        for content_type in self.CONTENT_TYPES.keys():
            count = stats.get(f"type_{content_type}", 0)
            print(f"  • {content_type.title()}: {count}")
        
        print(f"\n🌐 PLATFORMS:")
        for platform in self.PLATFORMS.keys():
            count = stats.get(f"platform_{platform}", 0)
            print(f"  • {platform.upper()}: {count}")
        
        print("\n" + "="*50 + "\n")


# Singleton instance
_content_manager: Optional[NotionContentManager] = None


def get_content_manager() -> NotionContentManager:
    """Get or create singleton content manager."""
    global _content_manager
    if _content_manager is None:
        _content_manager = NotionContentManager()
    return _content_manager
