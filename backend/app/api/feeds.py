from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl, Field
from sqlmodel import Session, select

from backend.app.db.session import get_session
from backend.app.db.models import Feed
from backend.app.services.crawler import test_feed_url_async

router = APIRouter(prefix="/feeds", tags=["Feeds"])


class FeedCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=5)
    category: Optional[str] = Field(default="General")
    is_active: Optional[bool] = Field(default=True)


class FeedUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    url: Optional[str] = Field(default=None, min_length=5)
    category: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class FeedTestRequest(BaseModel):
    url: str = Field(..., min_length=5)
    limit: Optional[int] = Field(default=3, ge=1, le=10)


@router.get("", response_model=List[Feed])
def list_feeds(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session),
) -> List[Feed]:
    """List all configured RSS feeds with optional filtering."""
    query = select(Feed)
    if category is not None:
        query = query.where(Feed.category == category)
    if is_active is not None:
        query = query.where(Feed.is_active == is_active)
    query = query.order_by(Feed.id.asc())
    return session.exec(query).all()


@router.post("", response_model=Feed, status_code=201)
def create_feed(feed_in: FeedCreate, session: Session = Depends(get_session)) -> Feed:
    """Create a new RSS feed configuration."""
    existing = session.exec(select(Feed).where(Feed.url == feed_in.url)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A feed with this URL already exists.")

    feed = Feed(
        name=feed_in.name,
        url=feed_in.url,
        category=feed_in.category or "General",
        is_active=feed_in.is_active if feed_in.is_active is not None else True,
        last_status="idle",
        created_at=datetime.now(timezone.utc),
    )
    session.add(feed)
    session.commit()
    session.refresh(feed)
    return feed


@router.post("/test", response_model=Dict[str, Any])
async def test_feed(req: FeedTestRequest) -> Dict[str, Any]:
    """
    FR-06 Live Feed Tester: Probe RSS feed URL, return status and preview articles.
    """
    result = await test_feed_url_async(url=req.url, limit=req.limit or 3)
    return result


@router.get("/{feed_id}", response_model=Feed)
def get_feed(feed_id: int, session: Session = Depends(get_session)) -> Feed:
    """Get single feed by ID."""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.put("/{feed_id}", response_model=Feed)
def update_feed(feed_id: int, feed_in: FeedUpdate, session: Session = Depends(get_session)) -> Feed:
    """Update feed details."""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if feed_in.url and feed_in.url != feed.url:
        existing = session.exec(select(Feed).where(Feed.url == feed_in.url)).first()
        if existing and existing.id != feed_id:
            raise HTTPException(status_code=400, detail="Another feed with this URL already exists.")
        feed.url = feed_in.url

    if feed_in.name is not None:
        feed.name = feed_in.name
    if feed_in.category is not None:
        feed.category = feed_in.category
    if feed_in.is_active is not None:
        feed.is_active = feed_in.is_active

    session.add(feed)
    session.commit()
    session.refresh(feed)
    return feed


@router.patch("/{feed_id}/toggle", response_model=Feed)
def toggle_feed(feed_id: int, session: Session = Depends(get_session)) -> Feed:
    """Toggle feed active/inactive state."""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed.is_active = not feed.is_active
    session.add(feed)
    session.commit()
    session.refresh(feed)
    return feed


@router.delete("/{feed_id}", response_model=Dict[str, Any])
def delete_feed(feed_id: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Delete a feed by ID."""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    session.delete(feed)
    session.commit()
    return {"status": "ok", "message": f"Feed {feed_id} deleted"}
