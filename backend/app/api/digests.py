import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select, func

from backend.app.config import settings
from backend.app.db.session import get_session
from backend.app.db.models import Digest
from backend.app.services.broadcaster import (
    markdown_to_telegram_html,
    broadcast_digest_async,
)

router = APIRouter(prefix="/digests", tags=["Digests"])


class DigestUpdate(BaseModel):
    summary_markdown: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)  # "draft" | "published" | "broadcasted"


class PaginatedDigests(BaseModel):
    items: List[Digest]
    total: int
    page: int
    pages: int
    limit: int


@router.get("", response_model=PaginatedDigests)
def list_digests(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> PaginatedDigests:
    """List digests with pagination sorted by date descending."""
    offset = (page - 1) * limit
    total = session.exec(select(func.count(Digest.id))).one()
    query = select(Digest).order_by(Digest.date.desc()).offset(offset).limit(limit)
    items = session.exec(query).all()
    pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedDigests(
        items=items,
        total=total,
        page=page,
        pages=pages,
        limit=limit,
    )


@router.get("/{digest_id}", response_model=Digest)
def get_digest(digest_id: int, session: Session = Depends(get_session)) -> Digest:
    """Get single digest details including markdown and HTML."""
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.put("/{digest_id}", response_model=Digest)
def update_digest_draft(
    digest_id: int,
    digest_in: DigestUpdate,
    session: Session = Depends(get_session),
) -> Digest:
    """
    FR-13: Edit digest summary draft before broadcasting.
    Re-generates HTML representation automatically if markdown is updated.
    """
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")

    if digest_in.summary_markdown is not None:
        digest.summary_markdown = digest_in.summary_markdown
        try:
            dt = datetime.strptime(digest.date, "%Y-%m-%d")
        except ValueError:
            dt = datetime.now()
        digest.summary_html = markdown_to_telegram_html(digest_in.summary_markdown, dt)

        # Update disk file as well
        date_file = settings.output_dir / f"digest-{digest.date}.md"
        try:
            with open(date_file, "w", encoding="utf-8") as f:
                f.write(digest.summary_markdown)
        except Exception:
            pass

    if digest_in.status is not None:
        digest.status = digest_in.status

    session.add(digest)
    session.commit()
    session.refresh(digest)
    return digest


@router.post("/{digest_id}/broadcast", response_model=Dict[str, Any])
async def broadcast_digest(
    digest_id: int,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    FR-14: Manual broadcast of digest to Telegram.
    """
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")

    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not bot_token or not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram credentials (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID) are not configured."
        )

    try:
        dt = datetime.strptime(digest.date, "%Y-%m-%d")
    except ValueError:
        dt = datetime.now()

    try:
        results = await broadcast_digest_async(
            token=bot_token,
            chat_id=chat_id,
            markdown_content=digest.summary_markdown,
            date_obj=dt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send to Telegram: {e}")

    # Mark as broadcasted
    now_utc = datetime.now(timezone.utc)
    digest.status = "broadcasted"
    digest.broadcasted_at = now_utc
    session.add(digest)
    session.commit()
    session.refresh(digest)

    return {
        "status": "ok",
        "message": f"Successfully broadcasted digest {digest_id} to Telegram.",
        "broadcasted_at": now_utc.isoformat(),
        "chunks_sent": len(results),
    }
