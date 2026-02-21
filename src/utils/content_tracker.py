"""
ContentTracker — Persistent content deduplication and channel tracking.

Connects directly to PostgreSQL (same DB as FastAPI) to:
1. Hash content before posting → skip duplicates across restarts
2. Record which channels each piece was posted to (X, Discord, Web, Substack)
3. Provide context of last post per ticker/type for the engine

Hash strategy: SHA-256 of normalized body text (prices/dates stripped)
so semantically identical content is caught even if regenerated with
slightly different price snapshots.
"""

import hashlib
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from urllib.parse import quote_plus
import os

logger = logging.getLogger(__name__)


class ContentTracker:
    """Persistent content deduplication tracker backed by PostgreSQL."""

    def __init__(self):
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'Gikonyo@2025!')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'creviastory')
        db_url = f"postgresql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

        self.engine = create_engine(db_url, pool_pre_ping=True, pool_size=2, max_overflow=3)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Ensure the table exists (idempotent)
        try:
            from api.models.content import ContentTracker as ContentTrackerModel
            ContentTrackerModel.__table__.create(bind=self.engine, checkfirst=True)
            self.enabled = True
            logger.info("[ContentTracker] Connected to database")
        except Exception as e:
            logger.warning(f"[ContentTracker] DB init failed, dedup disabled: {e}")
            self.enabled = False

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def generate_hash(body: str) -> str:
        """
        SHA-256 hash of normalized text.

        Normalization strips:
        - Dollar amounts ($97,234.56 → removed)
        - Percentages (+3.45% → removed)
        - Dates/timestamps
        - Extra whitespace
        This ensures semantically identical content matches even when
        regenerated with updated price data.
        """
        if not body:
            return hashlib.sha256(b'').hexdigest()

        text = body.lower()
        # Strip dollar amounts
        text = re.sub(r'\$[\d,]+\.?\d*[kmbt]?', '', text)
        # Strip percentages
        text = re.sub(r'[+-]?\d+\.?\d*%', '', text)
        # Strip dates (2025-01-15, Jan 15, etc.)
        text = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', text)
        text = re.sub(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}', '', text)
        # Strip timestamps
        text = re.sub(r'\d{1,2}:\d{2}(:\d{2})?\s*(am|pm|utc|est|pst)?', '', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    # ------------------------------------------------------------------
    # Dedup check
    # ------------------------------------------------------------------

    def is_duplicate(self, body: str) -> bool:
        """Check if content with this body text has already been posted."""
        if not self.enabled:
            return False

        content_hash = self.generate_hash(body)
        try:
            session = self.SessionLocal()
            from api.models.content import ContentTracker as CT
            exists = session.query(CT.id).filter(CT.content_hash == content_hash).first()
            session.close()
            if exists:
                logger.info(f"[ContentTracker] Duplicate detected (hash: {content_hash[:12]}...)")
                return True
            return False
        except Exception as e:
            logger.warning(f"[ContentTracker] Dedup check failed: {e}")
            return False  # On failure, allow posting (better to dup than block)

    # ------------------------------------------------------------------
    # Record a post
    # ------------------------------------------------------------------

    def record_post(self, body: str, content_type: str, ticker: str,
                    sector: str = None,
                    x_tweet_id: str = None,
                    x_thread_url: str = None,
                    discord_sent: bool = False,
                    web_slug: str = None,
                    substack_note_id: str = None,
                    content_post_id: int = None,
                    source_file: str = None) -> Optional[str]:
        """
        Record a piece of content after posting.

        Returns the content_hash or None on failure.
        """
        if not self.enabled:
            return None

        content_hash = self.generate_hash(body)
        body_preview = body[:300] if body else ''

        try:
            session = self.SessionLocal()
            from api.models.content import ContentTracker as CT

            # Check if hash already exists (upsert — update channel info)
            existing = session.query(CT).filter(CT.content_hash == content_hash).first()
            if existing:
                # Update channel info on the existing record
                if x_tweet_id and not existing.x_tweet_id:
                    existing.x_tweet_id = x_tweet_id
                if x_thread_url and not existing.x_thread_url:
                    existing.x_thread_url = x_thread_url
                if discord_sent:
                    existing.discord_sent = True
                if web_slug and not existing.web_slug:
                    existing.web_slug = web_slug
                if substack_note_id and not existing.substack_note_id:
                    existing.substack_note_id = substack_note_id
                if content_post_id and not existing.content_post_id:
                    existing.content_post_id = content_post_id
                session.commit()
                session.close()
                logger.info(f"[ContentTracker] Updated existing record (hash: {content_hash[:12]}...)")
                return content_hash

            # Insert new record
            record = CT(
                content_hash=content_hash,
                content_type=content_type,
                ticker=ticker,
                sector=sector,
                x_tweet_id=x_tweet_id,
                x_thread_url=x_thread_url,
                discord_sent=discord_sent,
                web_slug=web_slug,
                substack_note_id=substack_note_id,
                content_post_id=content_post_id,
                source_file=source_file,
                body_preview=body_preview,
            )
            session.add(record)
            session.commit()
            session.close()
            logger.info(f"[ContentTracker] Recorded {content_type} for {ticker} (hash: {content_hash[:12]}...)")
            return content_hash
        except Exception as e:
            logger.warning(f"[ContentTracker] Record failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Context queries
    # ------------------------------------------------------------------

    def get_last_post(self, ticker: str, content_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the most recent tracked post for a ticker.

        Returns dict with content_hash, content_type, ticker, posted_at, body_preview,
        or None if nothing found.
        """
        if not self.enabled:
            return None

        try:
            session = self.SessionLocal()
            from api.models.content import ContentTracker as CT

            query = session.query(CT).filter(CT.ticker == ticker)
            if content_type:
                query = query.filter(CT.content_type == content_type)
            record = query.order_by(desc(CT.posted_at)).first()
            session.close()

            if not record:
                return None

            return {
                'content_hash': record.content_hash,
                'content_type': record.content_type,
                'ticker': record.ticker,
                'posted_at': record.posted_at.isoformat() if record.posted_at else None,
                'body_preview': record.body_preview,
                'x_tweet_id': record.x_tweet_id,
                'web_slug': record.web_slug,
                'discord_sent': record.discord_sent,
                'substack_note_id': record.substack_note_id,
            }
        except Exception as e:
            logger.warning(f"[ContentTracker] get_last_post failed: {e}")
            return None

    def close(self):
        """Dispose of the engine connection pool."""
        self.engine.dispose()
