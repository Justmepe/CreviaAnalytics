"""
Feed API router — live social feed combining user posts and engine content
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware.auth import get_current_user, get_optional_user
from api.models.feed import UserFeedPost, FeedReaction
from api.models.content import ContentPost
from api.models.user import User

router = APIRouter(prefix='/api/feed', tags=['feed'])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreatePostRequest(BaseModel):
    body: str


class FeedPostResponse(BaseModel):
    id: str
    is_cc: bool
    author: str
    handle: str
    body: str
    created_at: datetime
    likes: int
    reposts: int
    signal_card: Optional[dict] = None

    class Config:
        from_attributes = True


class FeedResponse(BaseModel):
    posts: List[FeedPostResponse]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _content_to_feed(post: ContentPost) -> dict:
    """Convert a ContentPost to the unified feed post shape."""
    # Prefer excerpt, fall back to truncated body
    raw = post.excerpt or (post.body[:280] if post.body else '')
    # Strip leading markdown headers and raw price lines
    import re
    raw = re.sub(r'^#+\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'Prices?:[^\n]*', '', raw, flags=re.IGNORECASE)
    body = raw.strip()
    if len(body) > 280:
        body = body[:277] + '...'

    # Build signal card if market_snapshot has regime data
    signal_card = None
    if post.market_snapshot and isinstance(post.market_snapshot, dict):
        regime = (
            post.market_snapshot.get('regime')
            or post.market_snapshot.get('regime_name')
        )
        confidence = post.market_snapshot.get('regime_confidence')
        if regime:
            signal_card = {'regime': regime, 'confidence': confidence}

    return {
        'id': f'cc-{post.id}',
        'is_cc': True,
        'author': 'CreviaCockpit',
        'handle': '@creviacockpit',
        'body': body,
        'created_at': post.published_at,
        'likes': 0,
        'reposts': 0,
        'signal_card': signal_card,
    }


def _user_to_feed(post: UserFeedPost) -> dict:
    """Convert a UserFeedPost to the unified feed post shape."""
    handle = '@' + post.username.lower().replace(' ', '')
    return {
        'id': f'user-{post.id}',
        'is_cc': False,
        'author': post.username,
        'handle': handle,
        'body': post.body,
        'created_at': post.created_at,
        'likes': post.likes or 0,
        'reposts': post.reposts or 0,
        'signal_card': None,
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get('/posts', response_model=FeedResponse)
def get_feed_posts(
    since: Optional[str] = Query(None, description='ISO timestamp — return only newer posts'),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return merged feed: user posts + engine content, sorted newest-first."""
    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            pass

    # User posts
    uq = db.query(UserFeedPost).order_by(UserFeedPost.created_at.desc())
    if since_dt:
        uq = uq.filter(UserFeedPost.created_at > since_dt)
    user_posts = uq.limit(limit).all()

    # Engine content posts
    cq = (
        db.query(ContentPost)
        .filter(ContentPost.is_published == True)  # noqa: E712
        .order_by(ContentPost.published_at.desc())
    )
    if since_dt:
        cq = cq.filter(ContentPost.published_at > since_dt)
    cc_posts = cq.limit(limit).all()

    # Merge and sort newest-first
    merged: List[dict] = []
    for p in user_posts:
        merged.append(_user_to_feed(p))
    for p in cc_posts:
        merged.append(_content_to_feed(p))

    merged.sort(
        key=lambda x: (x['created_at'] or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    merged = merged[:limit]

    return FeedResponse(posts=[FeedPostResponse(**p) for p in merged])


@router.post('/posts', response_model=FeedPostResponse, status_code=201)
def create_feed_post(
    req: CreatePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a user feed post. Requires a free account or higher."""
    body = req.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail='Post body cannot be empty')
    if len(body) > 280:
        raise HTTPException(status_code=400, detail='Post body exceeds 280 characters')

    username = current_user.name or current_user.email.split('@')[0]
    post = UserFeedPost(user_id=current_user.id, username=username, body=body)
    db.add(post)
    db.commit()
    db.refresh(post)

    return FeedPostResponse(**_user_to_feed(post))


@router.post('/posts/{post_id}/react', status_code=200)
def react_to_post(
    post_id: int,
    reaction_type: str = Query(..., description='"like" or "repost"'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle like or repost on a user feed post. Requires authentication.
    Returns updated counts and whether the reaction is now active."""
    if reaction_type not in ('like', 'repost'):
        raise HTTPException(status_code=400, detail='Invalid reaction type. Use "like" or "repost"')

    post = db.query(UserFeedPost).filter(UserFeedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')

    existing = db.query(FeedReaction).filter(
        FeedReaction.post_id == post_id,
        FeedReaction.user_id == current_user.id,
        FeedReaction.reaction_type == reaction_type,
    ).first()

    if existing:
        # Toggle off — remove and decrement
        db.delete(existing)
        if reaction_type == 'like':
            post.likes = max(0, (post.likes or 0) - 1)
        else:
            post.reposts = max(0, (post.reposts or 0) - 1)
        active = False
    else:
        # Toggle on — add and increment
        db.add(FeedReaction(post_id=post_id, user_id=current_user.id, reaction_type=reaction_type))
        if reaction_type == 'like':
            post.likes = (post.likes or 0) + 1
        else:
            post.reposts = (post.reposts or 0) + 1
        active = True

    db.commit()
    return {'id': post.id, 'reaction_type': reaction_type, 'active': active, 'likes': post.likes, 'reposts': post.reposts}
