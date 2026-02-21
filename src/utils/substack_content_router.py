"""
Enhanced Substack Content Type System

Supports all Substack post types:
- TEXT: Long-form articles/newsletters
- NOTE: Short-form quick updates
- THREAD: X/Twitter thread format
- CHAT: Discussion format
- VIDEO/AUDIO: Special formats
"""

from enum import Enum
from typing import Optional, Dict, Any, List


class SubstackContentType(Enum):
    """Enum for Substack content types (3 formats supported)"""
    TEXT = "text"           # Newsletter/long-form article
    NOTE = "note"           # Short-form note/update
    THREAD = "thread"       # X/Twitter thread format
    

class ContentTypeDetector:
    """Detect appropriate Substack content type based on metadata"""
    
    @staticmethod
    def detect_from_source(
        source: str,
        content_length: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SubstackContentType:
        """
        Detect content type based on source and characteristics.
        
        Supports 3 formats:
        - TEXT: Long-form articles/research
        - NOTE: Quick updates/alerts
        - THREAD: X/Twitter thread format
        
        Args:
            source: Source of content (e.g., 'twitter', 'research', 'news', 'memo')
            content_length: Character count of content
            metadata: Additional metadata dict
            
        Returns:
            Appropriate SubstackContentType
        """
        
        metadata = metadata or {}
        source = source.lower().strip()
        
        # ===== THREAD DETECTION =====
        # X/Twitter threads should use THREAD format
        if source in ('x', 'twitter', 'x_thread', 'twitter_thread', 'thread'):
            return SubstackContentType.THREAD
        
        # ===== TEXT/LONG-FORM DETECTION =====
        # Research and analysis = TEXT format (long-form)
        if source in ('research', 'analysis', 'report', 'article'):
            return SubstackContentType.TEXT
        
        # If explicitly marked as long-form
        if metadata.get('is_longform') or metadata.get('is_article'):
            return SubstackContentType.TEXT
        
        # If content is substantial (>500 chars), use TEXT
        if content_length > 500:
            return SubstackContentType.TEXT
        
        # ===== NOTE DETECTION =====
        # Quick memos, alerts, news → NOTE format (default)
        if source in ('memo', 'alert', 'news', 'update', 'note'):
            return SubstackContentType.NOTE
        
        # If explicitly marked as short-form
        if metadata.get('is_shortform') or metadata.get('is_note'):
            return SubstackContentType.NOTE
        
        # ===== DEFAULT =====
        # Default to NOTE (safest option for unknown content)
        return SubstackContentType.NOTE
    
    @staticmethod
    def get_posting_method(content_type: SubstackContentType) -> str:
        """
        Get the poster method name for a content type.
        
        Supports: text, note, thread
        
        Returns:
            Method name on SubstackPoster class
        """
        mapping = {
            SubstackContentType.TEXT: "post_text",
            SubstackContentType.NOTE: "post_note",
            SubstackContentType.THREAD: "post_as_thread",
        }
        return mapping.get(content_type, "post_note")
    
    @staticmethod
    def validate_for_type(content_type: SubstackContentType, content: str) -> bool:
        """
        Validate if content is suitable for the given type.
        
        Args:
            content_type: Target content type
            content: Content text to validate
            
        Returns:
            True if content is suitable
        """
        if not content or not content.strip():
            return False
        
        # NOTE: Quick updates, any length OK
        if content_type == SubstackContentType.NOTE:
            return len(content.strip()) > 0
        
        # TEXT: Should be substantial (100+ chars)
        if content_type == SubstackContentType.TEXT:
            return len(content) >= 100
        
        # THREAD: Needs multiple parts (2+)
        if content_type == SubstackContentType.THREAD:
            lines = content.split('\n')
            non_empty = [l for l in lines if l.strip()]
            return len(non_empty) >= 2
        
        return True


class ContentTypeRouter:
    """Route content to appropriate posting method"""
    
    def __init__(self, poster):
        """
        Initialize router with a SubstackPoster instance.
        
        Args:
            poster: SubstackPoster instance
        """
        self.poster = poster
    
    def post(
        self,
        content: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
        force_type: Optional[SubstackContentType] = None
    ) -> Optional[str]:
        """
        Post content, automatically selecting the best format.
        
        Args:
            content: Content text to post
            source: Source identifier (e.g., 'twitter', 'research', 'memo')
            metadata: Additional metadata for detection
            force_type: Override automatic detection with explicit type
            
        Returns:
            Post ID if successful, None if failed
        """
        
        # Determine content type
        if force_type:
            content_type = force_type
        else:
            content_type = ContentTypeDetector.detect_from_source(
                source=source,
                content_length=len(content),
                metadata=metadata
            )
        
        # Validate content
        if not ContentTypeDetector.validate_for_type(content_type, content):
            return None
        
        # Get appropriate method
        method_name = ContentTypeDetector.get_posting_method(content_type)
        
        if not hasattr(self.poster, method_name):
            return None
        
        method = getattr(self.poster, method_name)
        
        # Call the method with appropriate parameters
        try:
            if method_name == "post_text":
                # TEXT usually needs a title
                title = metadata.get('title', '') if metadata else ''
                return method(title=title, body_text=content)
            elif method_name == "post_as_thread":
                # THREAD format
                return method(content)
            else:
                # All others take just content
                return method(content)
        except Exception as e:
            return None


# Example usage documentation:
"""
USAGE EXAMPLES:

1. Auto-detect and post Twitter thread:
   router.post(
       content="Tweet 1\\nTweet 2\\nTweet 3",
       source="twitter_thread"
   )
   → Uses post_as_thread()

2. Auto-detect and post market memo:
   router.post(
       content="Quick market update",
       source="memo"
   )
   → Uses post_note() (short-form)

3. Force long-form newsletter:
   router.post(
       content="Long analysis article",
       source="unknown",
       force_type=SubstackContentType.TEXT
   )
   → Uses post_text()

4. Auto-detect with metadata:
   router.post(
       content="Market analysis",
       source="research",
       metadata={
           "title": "Weekly Market Update",
           "is_longform": True
       }
   )
   → Uses post_text() (research detected as text)

5. News update (auto selects NOTE):
   router.post(
       content="Breaking: New regulation announced",
       source="news"
   )
   → Uses post_note()
"""
