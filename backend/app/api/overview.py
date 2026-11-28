from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from backend.app.db.session import get_session
from backend.app.db.models import Feed, Article, Digest, PipelineRun

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("", response_model=Dict[str, Any])
def get_overview_metrics(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Retrieve high-level KPI metrics for the dashboard."""
    # Feeds count
    total_feeds = session.exec(select(func.count(Feed.id))).one()
    active_feeds = session.exec(select(func.count(Feed.id)).where(Feed.is_active == True)).one()

    # Articles today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    articles_today = session.exec(
        select(func.count(Article.id)).where(Article.created_at >= today_start)
    ).one()

    # Total digests
    total_digests = session.exec(select(func.count(Digest.id))).one()

    # Last pipeline run
    last_run_stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
    last_run = session.exec(last_run_stmt).first()

    # Latest digest
    latest_digest_stmt = select(Digest).order_by(Digest.date.desc()).limit(1)
    latest_digest = session.exec(latest_digest_stmt).first()

    return {
        "active_feeds_count": active_feeds,
        "total_feeds_count": total_feeds,
        "articles_today_count": articles_today,
        "total_digests_count": total_digests,
        "last_run": {
            "id": last_run.id if last_run else None,
            "status": last_run.status if last_run else "idle",
            "trigger_type": last_run.trigger_type if last_run else None,
            "started_at": last_run.started_at.isoformat() if last_run else None,
            "completed_at": last_run.completed_at.isoformat() if (last_run and last_run.completed_at) else None,
        } if last_run else None,
        "latest_digest": {
            "id": latest_digest.id if latest_digest else None,
            "date": latest_digest.date if latest_digest else None,
            "status": latest_digest.status if latest_digest else None,
            "total_clusters": latest_digest.total_clusters if latest_digest else 0,
            "total_sources": latest_digest.total_sources if latest_digest else 0,
            "model_used": latest_digest.model_used if latest_digest else None,
            "broadcasted_at": latest_digest.broadcasted_at.isoformat() if (latest_digest and latest_digest.broadcasted_at) else None,
        } if latest_digest else None,
    }
