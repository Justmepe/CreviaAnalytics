"""
Notion Client Integration
Manages content storage, drafts, and publishing through Notion API
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

try:
    from notion_client import Client
    import httpx
except ImportError:
    Client = None
    httpx = None

logger = logging.getLogger(__name__)
load_dotenv()


class NotionClient:
    """
    Handles all Notion API interactions for content management.
    
    Requires:
    - NOTION_API_KEY: Notion integration token
    - NOTION_DATABASE_ID: Database ID for content storage
    """
    
    def __init__(self):
        """Initialize Notion client with API credentials."""
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not self.api_key:
            logger.warning("NOTION_API_KEY not set. Notion integration disabled.")
            self.client = None
            return
        
        if not Client:
            logger.error("notion-client not installed. Install with: pip install notion-client")
            self.client = None
            return
        
        try:
            self.client = Client(auth=self.api_key)
            logger.info("✓ Notion client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Notion client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Notion client is properly configured."""
        if self.client is None or self.database_id is None:
            return False
        if httpx is None:
            logger.warning("httpx not available for Notion queries")
            return False
        return True
    
    def create_draft(
        self,
        title: str,
        content: str,
        content_type: str = "Newsletter",
        platform: str = "X",
        status: str = "Drafting",
        tags: List[str] = None,
        image_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new draft in Notion.
        
        Args:
            title: Post title
            content: Post content
            content_type: Type of content (Newsletter, Tweet Thread, News Post, Report)
            platform: Target platform (X, Substack, Web, Reddit)
            status: Content status (Draft, Ready, Published, Archived)
            tags: List of tags/categories
            image_url: URL of featured image
        
        Returns:
            Page ID if successful, None otherwise
        """
        if not self.is_available():
            logger.warning("Notion client not available")
            return None
        
        try:
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Content": {
                    "rich_text": [
                        {
                            "text": {
                                "content": content
                            }
                        }
                    ]
                },
                "Type": {
                    "select": {
                        "name": content_type
                    }
                },
                "Platform": {
                    "select": {
                        "name": platform
                    }
                },
                "Status": {
                    "status": {
                        "name": status
                    }
                },
                "Created": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }
            
            # Add tags if provided
            if tags:
                properties["Tags"] = {
                    "multi_select": [
                        {"name": tag} for tag in tags
                    ]
                }
            
            # Add image if provided
            if image_url:
                properties["Image URL"] = {
                    "url": image_url
                }
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response.get("id")
            logger.info(f"✓ Created Notion draft: {title} (ID: {page_id})")
            return page_id
            
        except Exception as e:
            logger.error(f"Failed to create Notion draft: {e}")
            return None
    
    def update_draft(
        self,
        page_id: str,
        **updates
    ) -> bool:
        """
        Update an existing draft in Notion.
        
        Args:
            page_id: Notion page ID
            **updates: Fields to update (title, content, status, tags, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Notion client not available")
            return False
        
        try:
            properties = {}
            
            if "title" in updates:
                properties["Name"] = {
                    "title": [{"text": {"content": updates["title"]}}]
                }
            
            if "content" in updates:
                properties["Content"] = {
                    "rich_text": [{"text": {"content": updates["content"]}}]
                }
            
            if "status" in updates:
                properties["Status"] = {
                    "status": {"name": updates["status"]}
                }
            
            if "tags" in updates:
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in updates["tags"]]
                }
            
            if "platform" in updates:
                properties["Platform"] = {
                    "select": {"name": updates["platform"]}
                }
            
            if "image_url" in updates:
                properties["Image URL"] = {
                    "url": updates["image_url"]
                }
            
            self.client.pages.update(page_id, properties=properties)
            logger.info(f"✓ Updated Notion draft: {page_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Notion draft: {e}")
            return False
    
    def get_draft(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a draft from Notion.
        
        Args:
            page_id: Notion page ID
        
        Returns:
            Draft data if found, None otherwise
        """
        if not self.is_available():
            logger.warning("Notion client not available")
            return None
        
        try:
            page = self.client.pages.retrieve(page_id)
            return self._parse_page(page)
        except Exception as e:
            logger.error(f"Failed to retrieve Notion draft: {e}")
            return None
    
    def list_drafts(
        self,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List drafts from Notion with optional filters.
        
        Args:
            status: Filter by status (Draft, Ready, Published)
            content_type: Filter by type (Newsletter, Tweet Thread, News Post, Report)
            platform: Filter by platform (X, Substack, Web, Reddit)
            limit: Maximum number of results
        
        Returns:
            List of draft data
        """
        if not self.is_available():
            logger.warning("Notion client not available")
            return []
        
        try:
            filters = []
            
            if status:
                filters.append({
                    "property": "Status",
                    "status": {"equals": status}
                })
            
            if content_type:
                filters.append({
                    "property": "Type",
                    "select": {"equals": content_type}
                })
            
            if platform:
                filters.append({
                    "property": "Platform",
                    "select": {"equals": platform}
                })
            
            # Combine filters with AND
            query_filter = None
            if filters:
                if len(filters) == 1:
                    query_filter = filters[0]
                else:
                    query_filter = {
                        "and": filters
                    }
            
            # Query using direct HTTP request to Notion API
            try:
                # Build request payload
                payload = {
                    "page_size": min(limit, 100)
                }
                if query_filter:
                    payload["filter"] = query_filter
                
                # Make direct HTTP request to Notion API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                
                url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
                
                with httpx.Client() as http_client:
                    resp = http_client.post(url, json=payload, headers=headers, timeout=30.0)
                    resp.raise_for_status()
                    response = resp.json()
                
            except Exception as query_error:
                logger.error(f"Query error: {query_error}")
                return []
            
            drafts = [self._parse_page(page) for page in response.get("results", [])]
            return drafts
            
        except Exception as e:
            logger.error(f"Failed to list Notion drafts: {e}")
            return []
    
    def publish_draft(self, page_id: str, published_url: str = None) -> bool:
        """
        Mark a draft as published in Notion.
        
        Args:
            page_id: Notion page ID
            published_url: URL where content was published
        
        Returns:
            True if successful, False otherwise
        """
        updates = {"status": "Published"}
        if published_url:
            updates["published_url"] = published_url
        
        return self.update_draft(page_id, **updates)
    
    def archive_draft(self, page_id: str) -> bool:
        """Archive a draft in Notion."""
        return self.update_draft(page_id, status="Archived")
    
    def _parse_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Notion page into readable format."""
        props = page.get("properties", {})
        
        parsed = {
            "id": page.get("id"),
            "url": page.get("url"),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
        }
        
        # Extract property values
        # Try common title property names
        title = ""
        for title_prop in ["Title", "Name", "title", "name"]:
            if title_prop in props:
                prop_data = props.get(title_prop, {})
                if prop_data.get("type") == "title":
                    title_array = prop_data.get("title", [])
                    title = "".join([t.get("text", {}).get("content", "") for t in title_array])
                    break
        parsed["title"] = title
        
        if "Content" in props:
            content_array = props.get("Content", {}).get("rich_text", [])
            parsed["content"] = "".join([t.get("text", {}).get("content", "") for t in content_array])
        
        # Try common status property names
        for status_prop in ["Status", "status"]:
            if status_prop in props:
                prop_data = props.get(status_prop, {})
                # Handle both "select" and "status" property types
                select_data = prop_data.get("select", {}) or prop_data.get("status", {})
                if select_data:
                    parsed["status"] = select_data.get("name", "")
                    break
        
        for platform_prop in ["Platform", "platform"]:
            if platform_prop in props:
                select_data = props.get(platform_prop, {}).get("select", {})
                if select_data:
                    parsed["platform"] = select_data.get("name", "")
                    break
        
        for type_prop in ["Type", "type"]:
            if type_prop in props:
                select_data = props.get(type_prop, {}).get("select", {})
                if select_data:
                    parsed["type"] = select_data.get("name", "")
                    break
        
        # Tags
        for tags_prop in ["Tags", "tags"]:
            if tags_prop in props:
                tags = props.get(tags_prop, {}).get("multi_select", [])
                parsed["tags"] = [tag.get("name") for tag in tags]
                break
        
        # Image URL
        for image_prop in ["Image URL", "image_url", "Image"]:
            if image_prop in props:
                parsed["image_url"] = props.get(image_prop, {}).get("url", "")
                break
        
        return parsed
    
    def add_image_to_page(self, page_id: str, image_url: str) -> bool:
        """
        Add or update image in page blocks.
        
        Args:
            page_id: Notion page ID
            image_url: URL of image to add
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Notion client not available")
            return False
        
        try:
            # Add image as a block in the page
            self.client.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {
                                "url": image_url
                            }
                        }
                    }
                ]
            )
            logger.info(f"✓ Added image to Notion page: {page_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add image to Notion page: {e}")
            return False


# Singleton instance
_notion_client: Optional[NotionClient] = None


def get_notion_client() -> NotionClient:
    """Get or create singleton Notion client."""
    global _notion_client
    if _notion_client is None:
        _notion_client = NotionClient()
    return _notion_client
