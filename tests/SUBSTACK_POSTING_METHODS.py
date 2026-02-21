"""
Additional Substack Posting Methods for Different Content Types

These methods should be added to the SubstackPoster class.
They handle:
- TEXT: Long-form articles/newsletters
- THREAD: X/Twitter thread format  
- CHAT: Discussion/chat format
- VIDEO/AUDIO: Special media formats
"""


def post_text(self, title: str, body_text: str, is_published: bool = False) -> Optional[str]:
    """
    Post a long-form TEXT article/newsletter to Substack.
    
    This is for substantive content like:
    - Research reports
    - Market analysis
    - In-depth guides
    - Newsletter articles
    
    Args:
        title: Article title (required for TEXT format)
        body_text: Full article body, can include formatting
        is_published: Publish immediately or save as draft
        
    Returns:
        article_id string or None on failure
    """
    if not self.enabled:
        return None
    
    if not self._check_rate_limit():
        return None
    
    if not self._ensure_authenticated():
        logger.error("[SubstackPoster] Not authenticated, cannot post TEXT")
        return None
    
    if not title or not title.strip():
        logger.error("[SubstackPoster] TEXT posts require a title")
        return None
    
    try:
        # Build ProseMirror document from plain text
        builder = NoteBuilder()
        paragraphs = body_text.split('\n\n')
        for para in paragraphs:
            lines = para.split('\n')
            if len(lines) == 1:
                builder.add_paragraph(lines[0])
            else:
                parts = []
                for i, line in enumerate(lines):
                    if line.strip():
                        parts.append({"text": line})
                if parts:
                    builder.add_rich_paragraph(parts)
        
        body_json = builder.build_json()
        
        # Post to Substack Posts API (different from notes)
        url = f'{self.BASE_URL}/api/v1/posts'
        payload = {
            'title': title,
            'body_html': body_json,  # Or use 'body' for markdown
            'publication_id': self.publication_id,
            'status': 'published' if is_published else 'draft',
            'post_type': 'article',
            'audience': 'all',  # or 'subscribers_only'
        }
        
        resp = self.session.post(url, json=payload, timeout=15)
        
        if resp.status_code in (200, 201):
            data = resp.json()
            post_id = str(data.get('id', ''))
            logger.info(f"[SubstackPoster] TEXT post created (ID: {post_id}, title: {title[:30]}...)")
            
            if is_published:
                self._notes_today.append(post_id)
                self._save_notes_log()
            
            return post_id
        
        elif resp.status_code == 401:
            logger.warning("[SubstackPoster] Session expired, re-authenticating...")
            self.authenticated = False
            if self._ensure_authenticated():
                resp2 = self.session.post(url, json=payload, timeout=15)
                if resp2.status_code in (200, 201):
                    data = resp2.json()
                    post_id = str(data.get('id', ''))
                    if is_published:
                        self._notes_today.append(post_id)
                        self._save_notes_log()
                    logger.info(f"[SubstackPoster] TEXT post created on retry (ID: {post_id})")
                    return post_id
            logger.error("[SubstackPoster] Re-auth failed, TEXT post not created")
            return None
        
        elif resp.status_code == 429:
            logger.warning("[SubstackPoster] Rate limited by Substack (429)")
            return None
        
        else:
            logger.error(f"[SubstackPoster] TEXT post failed: HTTP {resp.status_code} — {resp.text[:200]}")
            return None
    
    except Exception as e:
        logger.error(f"[SubstackPoster] TEXT post error: {e}")
        return None


def post_as_thread(self, thread_content: str) -> Optional[str]:
    """
    Post content as a THREAD (X/Twitter thread format).
    
    This is for content structured as a multi-part thread:
    - X/Twitter threads
    - Multi-tweet discussions
    - Sequential arguments
    
    The content should have parts separated by newlines/paragraph breaks.
    
    Args:
        thread_content: Full thread text (parts/tweets separated by newlines)
        
    Returns:
        thread_id string or None on failure
    """
    if not self.enabled:
        return None
    
    if not self._check_rate_limit():
        return None
    
    if not self._ensure_authenticated():
        logger.error("[SubstackPoster] Not authenticated, cannot post THREAD")
        return None
    
    try:
        # Split thread into individual parts
        parts = [p.strip() for p in thread_content.split('\n\n') if p.strip()]
        
        if len(parts) < 2:
            logger.warning("[SubstackPoster] THREAD format requires at least 2 parts, using NOTE instead")
            return self.post_note(thread_content)
        
        # Build ProseMirror document for each part
        builder = NoteBuilder()
        for part in parts:
            builder.add_paragraph(part)
        
        body_json = builder.build_json()
        
        # Post as thread type
        url = f'{self.BASE_URL}/api/v1/posts'
        payload = {
            'body': body_json,
            'publication_id': self.publication_id,
            'post_type': 'thread',
            'audience': 'all',
            'status': 'published',
        }
        
        resp = self.session.post(url, json=payload, timeout=15)
        
        if resp.status_code in (200, 201):
            data = resp.json()
            thread_id = str(data.get('id', ''))
            logger.info(f"[SubstackPoster] THREAD post created (ID: {thread_id}, parts: {len(parts)})")
            
            self._notes_today.append(thread_id)
            self._save_notes_log()
            
            return thread_id
        
        elif resp.status_code == 401:
            logger.warning("[SubstackPoster] Session expired, re-authenticating...")
            self.authenticated = False
            if self._ensure_authenticated():
                resp2 = self.session.post(url, json=payload, timeout=15)
                if resp2.status_code in (200, 201):
                    data = resp2.json()
                    thread_id = str(data.get('id', ''))
                    self._notes_today.append(thread_id)
                    self._save_notes_log()
                    logger.info(f"[SubstackPoster] THREAD post created on retry (ID: {thread_id})")
                    return thread_id
            return None
        
        elif resp.status_code == 429:
            logger.warning("[SubstackPoster] Rate limited (429)")
            return None
        
        else:
            logger.error(f"[SubstackPoster] THREAD post failed: HTTP {resp.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"[SubstackPoster] THREAD post error: {e}")
        return None


def post_as_chat(self, chat_content: str, title: str = "Discussion") -> Optional[str]:
    """
    Post content as a CHAT (discussion format).
    
    This is for interactive/discussion content:
    - Q&A sessions
    - Community discussions
    - Polls
    
    Args:
        chat_content: Chat/discussion content
        title: Chat title
        
    Returns:
        chat_id string or None on failure
    """
    if not self.enabled:
        return None
    
    if not self._check_rate_limit():
        return None
    
    if not self._ensure_authenticated():
        logger.error("[SubstackPoster] Not authenticated, cannot post CHAT")
        return None
    
    try:
        # Build ProseMirror document
        builder = NoteBuilder()
        paragraphs = chat_content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                builder.add_paragraph(para.strip())
        
        body_json = builder.build_json()
        
        # Post as chat type
        url = f'{self.BASE_URL}/api/v1/posts'
        payload = {
            'title': title,
            'body': body_json,
            'publication_id': self.publication_id,
            'post_type': 'chat',
            'audience': 'all',
            'status': 'published',
        }
        
        resp = self.session.post(url, json=payload, timeout=15)
        
        if resp.status_code in (200, 201):
            data = resp.json()
            chat_id = str(data.get('id', ''))
            logger.info(f"[SubstackPoster] CHAT post created (ID: {chat_id})")
            
            self._notes_today.append(chat_id)
            self._save_notes_log()
            
            return chat_id
        
        elif resp.status_code == 401:
            self.authenticated = False
            if self._ensure_authenticated():
                resp2 = self.session.post(url, json=payload, timeout=15)
                if resp2.status_code in (200, 201):
                    data = resp2.json()
                    chat_id = str(data.get('id', ''))
                    self._notes_today.append(chat_id)
                    self._save_notes_log()
                    return chat_id
            return None
        
        else:
            logger.error(f"[SubstackPoster] CHAT post failed: HTTP {resp.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"[SubstackPoster] CHAT post error: {e}")
        return None


def post_audio(self, audio_url: str, title: str = "", description: str = "") -> Optional[str]:
    """
    Post an AUDIO clip to Substack.
    
    Args:
        audio_url: URL to audio file
        title: Audio title
        description: Audio description
        
    Returns:
        audio_id string or None on failure (NOT YET FULLY IMPLEMENTED)
    """
    logger.info("[SubstackPoster] AUDIO posting not yet implemented (requires media upload)")
    return None


def post_video(self, video_url: str, title: str = "", description: str = "") -> Optional[str]:
    """
    Post a VIDEO to Substack.
    
    Args:
        video_url: URL to video or embed code
        title: Video title
        description: Video description
        
    Returns:
        video_id string or None on failure (NOT YET FULLY IMPLEMENTED)
    """
    logger.info("[SubstackPoster] VIDEO posting not yet implemented (requires media upload)")
    return None


def post_podcast(self, episode_url: str, title: str = "", description: str = "") -> Optional[str]:
    """
    Post a PODCAST episode.
    
    Args:
        episode_url: URL to podcast episode
        title: Episode title
        description: Episode description/notes
        
    Returns:
        podcast_id string or None on failure (NOT YET FULLY IMPLEMENTED)
    """
    logger.info("[SubstackPoster] PODCAST posting not yet implemented")
    return None


# Additional helper methods

def post_research_article(self, title: str, analysis: str, 
                         ticker: str = "", data_points: Optional[List[str]] = None) -> Optional[str]:
    """
    Post a research article with formatted data.
    
    Convenience method that formats research content and posts as TEXT.
    
    Args:
        title: Article title
        analysis: Main analysis text
        ticker: Optional crypto ticker
        data_points: Optional list of key data points
        
    Returns:
        article_id or None
    """
    # Format with data points if provided
    body = analysis
    
    if data_points:
        body += "\n\nKey Data Points:\n"
        for point in data_points:
            body += f"• {point}\n"
    
    return self.post_text(title=title, body_text=body, is_published=True)


def post_quick_alert(self, alert_text: str, ticker: str = "") -> Optional[str]:
    """
    Post a quick market alert as NOTE (short-form).
    
    Args:
        alert_text: Alert message
        ticker: Optional crypto ticker
        
    Returns:
        note_id or None
    """
    if ticker:
        full_text = f"🚨 {ticker} Alert:\n\n{alert_text}"
    else:
        full_text = alert_text
    
    return self.post_note(full_text)
