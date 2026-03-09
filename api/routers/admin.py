"""
Admin Content Portal — write with Claude, publish to site
"""

import json
import os
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.config import ADMIN_EMAIL, WEB_API_SECRET, ADMIN_DISCORD_WEBHOOK
from api.middleware.auth import get_current_user
from api.models.user import User
from api.models.content import ContentPost
from api.models.admin_inbox import AdminInboxItem
from api.services.content_service import create_article_post

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/admin', tags=['admin'])

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not ADMIN_EMAIL or user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin access required')
    return user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str   # 'user' | 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class PublishRequest(BaseModel):
    title: str
    body: str
    content_type: str = 'article'   # article | memo | news_tweet
    sector: str = 'global'
    tickers: Optional[List[str]] = None
    tier: str = 'free'              # free | pro | enterprise

class PostResponse(BaseModel):
    id: int
    title: str
    content_type: str
    sector: str
    tickers: list
    tier: str
    slug: str
    published_at: datetime
    word_count: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Claude chat (streaming)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a professional crypto market analyst and writer for Crevia Analytics, "
    "a crypto intelligence platform. Write high-quality, insightful market analysis "
    "content in a clear, authoritative tone. Use markdown formatting. "
    "Focus on actionable insights, market context, and key data points. "
    "Keep analysis concise and relevant to traders and investors."
)


@router.post('/chat')
async def admin_chat(req: ChatRequest, _: User = Depends(require_admin)):
    """Stream Claude Sonnet 4.6 responses for content writing."""
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail='anthropic package not installed')

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))

    messages = [{'role': m.role, 'content': m.content} for m in req.messages]

    async def stream_response():
        try:
            with client.messages.stream(
                model='claude-sonnet-4-6',
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

@router.post('/publish', response_model=PostResponse)
def admin_publish(req: PublishRequest, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    """Publish an article/memo directly to the site."""
    post = create_article_post(
        db=db,
        title=req.title,
        body=req.body,
        sector=req.sector,
        tickers=req.tickers or ['BTC', 'ETH'],
        source_file='admin-portal',
    )
    # Override content_type and tier if requested
    post.content_type = req.content_type
    post.tier = req.tier
    db.commit()
    db.refresh(post)

    word_count = len(post.body.split()) if post.body else 0
    return PostResponse(
        id=post.id,
        title=post.title,
        content_type=post.content_type,
        sector=post.sector,
        tickers=post.tickers or [],
        tier=post.tier,
        slug=post.slug,
        published_at=post.published_at,
        word_count=word_count,
    )


# ---------------------------------------------------------------------------
# List & delete posts
# ---------------------------------------------------------------------------

@router.get('/posts', response_model=List[PostResponse])
def list_posts(limit: int = 20, db: Session = Depends(get_db),
               _: User = Depends(require_admin)):
    """List recent posts published through the admin portal."""
    posts = (
        db.query(ContentPost)
        .filter(ContentPost.source_file == 'admin-portal')
        .order_by(ContentPost.published_at.desc())
        .limit(limit)
        .all()
    )
    return [
        PostResponse(
            id=p.id,
            title=p.title,
            content_type=p.content_type,
            sector=p.sector,
            tickers=p.tickers or [],
            tier=p.tier,
            slug=p.slug,
            published_at=p.published_at,
            word_count=len(p.body.split()) if p.body else 0,
        )
        for p in posts
    ]


@router.delete('/posts/{post_id}')
def delete_post(post_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    """Delete a post by ID."""
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')
    db.delete(post)
    db.commit()
    return {'deleted': post_id}


# ---------------------------------------------------------------------------
# Admin Inbox — engine posts tasks here; admin writes with Claude and publishes
# ---------------------------------------------------------------------------

class InboxItemCreate(BaseModel):
    scan_type: str                      # morning_scan | breaking_news | mid_day | closing_bell
    headline: Optional[str] = None      # short description
    raw_data: Optional[dict] = None     # structured analysis data
    suggested_prompt: Optional[str] = None  # pre-filled Claude prompt

class InboxItemResponse(BaseModel):
    id: int
    scan_type: str
    headline: Optional[str]
    raw_data: Optional[dict]
    suggested_prompt: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


_SCAN_COLORS = {
    'morning_scan':  0x3fb950,   # green
    'mid_day':       0x79c0ff,   # blue
    'closing_bell':  0xe3b341,   # yellow
    'breaking_news': 0xf85149,   # red
}
_SCAN_EMOJI = {
    'morning_scan':  '🌅',
    'mid_day':       '☀️',
    'closing_bell':  '🌙',
    'breaking_news': '🚨',
}

def _notify_discord(scan_type: str, headline: str, item_id: int) -> None:
    """Fire-and-forget Discord embed to Peter's admin webhook."""
    if not ADMIN_DISCORD_WEBHOOK:
        return
    try:
        import httpx
        emoji = _SCAN_EMOJI.get(scan_type, '📋')
        color = _SCAN_COLORS.get(scan_type, 0x8b949e)
        embed = {
            'title': f'{emoji} {scan_type.replace("_", " ").title()} — Ready to Write',
            'description': headline,
            'color': color,
            'fields': [
                {
                    'name': 'Action',
                    'value': '[Open Admin Portal →](https://creviacockpit.com/admin)',
                    'inline': True,
                },
            ],
            'footer': {'text': 'Crevia Analytics · Admin Inbox'},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        with httpx.Client(timeout=5.0) as client:
            client.post(ADMIN_DISCORD_WEBHOOK, json={'embeds': [embed]})
    except Exception as e:
        logger.warning('Admin Discord notify failed: %s', e)


def _verify_engine(x_api_secret: str = None):
    if x_api_secret != WEB_API_SECRET:
        raise HTTPException(status_code=403, detail='Invalid API secret')


@router.post('/inbox', response_model=InboxItemResponse)
def create_inbox_item(
    req: InboxItemCreate,
    db: Session = Depends(get_db),
    x_api_secret: Optional[str] = None,
):
    """Engine posts analysis data here instead of calling Claude directly."""
    _verify_engine(x_api_secret)
    item = AdminInboxItem(
        scan_type=req.scan_type,
        headline=req.headline or f'{req.scan_type.replace("_", " ").title()} — {datetime.now(timezone.utc).strftime("%H:%M UTC")}',
        raw_data=req.raw_data,
        suggested_prompt=req.suggested_prompt,
        status='pending',
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Notify Peter via Discord
    _notify_discord(item.scan_type, item.headline or '', item.id)

    return item


@router.post('/inbox/test-notify')
def test_inbox_notify(_: User = Depends(require_admin)):
    """Send a test Discord notification to verify the webhook is configured."""
    if not ADMIN_DISCORD_WEBHOOK:
        raise HTTPException(status_code=400, detail='ADMIN_DISCORD_WEBHOOK not configured')
    _notify_discord('morning_scan', 'Test notification — Admin inbox webhook is working ✓', 0)
    return {'sent': True}


@router.get('/inbox', response_model=List[InboxItemResponse])
def list_inbox(status: Optional[str] = 'pending', db: Session = Depends(get_db),
               _: User = Depends(require_admin)):
    """List inbox items (default: pending only)."""
    q = db.query(AdminInboxItem)
    if status and status != 'all':
        q = q.filter(AdminInboxItem.status == status)
    return q.order_by(AdminInboxItem.created_at.desc()).limit(50).all()


@router.patch('/inbox/{item_id}')
def update_inbox_status(item_id: int, status: str, db: Session = Depends(get_db),
                        _: User = Depends(require_admin)):
    """Mark inbox item as done or dismissed."""
    item = db.query(AdminInboxItem).filter(AdminInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Inbox item not found')
    item.status = status
    db.commit()
    return {'id': item_id, 'status': status}


@router.delete('/inbox/{item_id}')
def delete_inbox_item(item_id: int, db: Session = Depends(get_db),
                      _: User = Depends(require_admin)):
    """Delete an inbox item."""
    item = db.query(AdminInboxItem).filter(AdminInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Inbox item not found')
    db.delete(item)
    db.commit()
    return {'deleted': item_id}
