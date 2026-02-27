"""
SQLAlchemy models for the social feed: user posts and per-user reactions
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func

from api.database import Base


class UserFeedPost(Base):
    __tablename__ = "user_feed_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = Column(String(100), nullable=False)
    body = Column(String(280), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    likes = Column(Integer, default=0)
    reposts = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_user_feed_posts_created', 'created_at'),
    )


class FeedReaction(Base):
    """Tracks per-user reactions to prevent duplicates and enable toggles."""
    __tablename__ = "feed_reactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('user_feed_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reaction_type = Column(String(20), nullable=False)  # "like" or "repost"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_feed_reaction_post', 'post_id'),
        UniqueConstraint('post_id', 'user_id', 'reaction_type', name='uq_feed_reaction'),
    )
