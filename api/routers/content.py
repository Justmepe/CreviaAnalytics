"""
Content API router — publish and read content
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional

from api.database import get_db
from api.config import WEB_API_SECRET
from api.schemas.content import (
    PublishThreadRequest, PublishMemoRequest, PublishNewsTweetRequest, PublishArticleRequest,
    ContentPostResponse, ContentListResponse, TweetResponse,
)
from api.services.content_service import (
    create_thread_post, create_memo_post, create_news_tweet_post, create_article_post,
    get_content_feed, get_content_by_slug, get_content_tier,
)

router = APIRouter(prefix='/api/content', tags=['content'])


def _verify_internal(x_api_secret: str = Header(None)):
    """Verify internal API secret for publish endpoints."""
    if x_api_secret != WEB_API_SECRET:
        raise HTTPException(status_code=403, detail='Invalid API secret')


# --- Publish endpoints (engine → API) ---

@router.post('/publish/thread', response_model=ContentPostResponse)
def publish_thread(req: PublishThreadRequest, db: Session = Depends(get_db),
                   _=Depends(_verify_internal)):
    post = create_thread_post(
        db=db,
        tweets=req.tweets,
        tweet_count=req.tweet_count,
        tickers=req.tickers,
        sector=req.sector,
        image_url=req.image_url,
        market_snapshot=req.market_snapshot,
        source_file=req.source_file,
    )
    return post


@router.post('/publish/memo', response_model=ContentPostResponse)
def publish_memo(req: PublishMemoRequest, db: Session = Depends(get_db),
                 _=Depends(_verify_internal)):
    post = create_memo_post(
        db=db,
        ticker=req.ticker,
        body=req.body,
        current_price=req.current_price,
        sector=req.sector,
        tickers=req.tickers if req.tickers else [req.ticker],
        image_url=req.image_url,
        market_snapshot=req.market_snapshot,
        source_file=req.source_file,
    )
    return post


@router.post('/publish/article', response_model=ContentPostResponse)
def publish_article(req: PublishArticleRequest, db: Session = Depends(get_db),
                    _=Depends(_verify_internal)):
    post = create_article_post(
        db=db,
        title=req.title,
        body=req.body,
        sector=req.sector,
        tickers=req.tickers,
        image_url=req.image_url,
        market_snapshot=req.market_snapshot,
        source_file=req.source_file,
    )
    return post


@router.post('/publish/news', response_model=ContentPostResponse)
def publish_news_tweet(req: PublishNewsTweetRequest, db: Session = Depends(get_db),
                       _=Depends(_verify_internal)):
    post = create_news_tweet_post(
        db=db,
        ticker=req.ticker,
        body=req.body,
        current_price=req.current_price,
        sector=req.sector,
        tickers=req.tickers if req.tickers else [req.ticker],
    )
    return post


# --- Read endpoints (frontend → API) ---

@router.get('/feed', response_model=ContentListResponse)
def content_feed(
    content_type: Optional[str] = Query(None, description='thread, memo, news_tweet, risk_alert'),
    sector: Optional[str] = Query(None, description='majors, memecoins, privacy, defi, global'),
    ticker: Optional[str] = Query(None, description='BTC, ETH, SOL, etc.'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = get_content_feed(
        db=db, content_type=content_type, sector=sector,
        ticker=ticker, page=page, page_size=page_size,
    )
    return ContentListResponse(
        items=[ContentPostResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get('/post/{slug}', response_model=ContentPostResponse)
def get_post(slug: str, db: Session = Depends(get_db)):
    post = get_content_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')

    # Check tier access (for now, return all — frontend handles gating)
    response = ContentPostResponse.model_validate(post)
    # Annotate current effective tier for the frontend paywall logic
    response.tier = get_content_tier(post.published_at)
    return response
