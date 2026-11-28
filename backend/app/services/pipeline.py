import asyncio
import json
import traceback
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Dict, Any, Optional, List, Callable
from sqlmodel import Session, select

from backend.app.config import settings
from backend.app.db.session import engine
from backend.app.db.models import Feed, Article, Digest, PipelineRun
from backend.app.services.crawler import async_fetch_feed, parse_feed_xml
from backend.app.services.clustering import cluster_articles
from backend.app.services.synthesizer import synthesize_news, build_markdown_document
from backend.app.services.broadcaster import markdown_to_telegram_html, broadcast_digest_async

# Global broadcaster queue for active SSE listeners
_subscribers: List[asyncio.Queue] = []
_active_run_id: Optional[str] = None
_run_lock = asyncio.Lock()


async def subscribe_events() -> AsyncGenerator[Dict[str, Any], None]:
    """Register an SSE subscriber queue and yield events."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    try:
        while True:
            event = await q.get()
            yield event
    finally:
        if q in _subscribers:
            _subscribers.remove(q)


async def emit_event(event_type: str, stage: str, progress: int, message: str, **kwargs) -> None:
    """Broadcast an event to all active SSE subscribers."""
    payload = {
        "event": event_type,
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except (asyncio.QueueFull, Exception):
            pass


async def execute_pipeline(
    dry_run: bool = False,
    trigger_type: str = "manual",
    auto_broadcast: bool = False,
    custom_run_id: Optional[str] = None,
) -> PipelineRun:
    """
    Executes the full news aggregation and synthesis pipeline.
    Yields events via emit_event for SSE subscribers.
    """
    global _active_run_id
    started_at = datetime.now(timezone.utc)
    logs_buffer: List[Dict[str, Any]] = []

    def log(stage: str, msg: str, level: str = "INFO"):
        logs_buffer.append({
            "stage": stage,
            "message": msg,
            "level": level,
            "time": datetime.now(timezone.utc).isoformat(),
        })

    with Session(engine) as session:
        run = PipelineRun(
            id=custom_run_id or None,
            trigger_type=trigger_type,
            status="running",
            logs=None,
            started_at=started_at,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    _active_run_id = run_id

    try:
        # Stage 1: Starting
        await emit_event("status", "Starting", 5, f"Initializing pipeline run ({trigger_type})", run_id=run_id)
        log("Starting", f"Pipeline initiated with run_id={run_id}, dry_run={dry_run}")

        # Stage 2: Fetching
        await emit_event("status", "Fetching", 15, "Retrieving active RSS feeds", run_id=run_id)
        with Session(engine) as session:
            feeds = session.exec(select(Feed).where(Feed.is_active == True)).all()

        if not feeds:
            log("Fetching", "No active feeds configured in database", level="WARN")
            await emit_event("warning", "Fetching", 25, "No active feeds found in database", run_id=run_id)

        all_articles: List[Dict[str, Any]] = []
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=24)

        for idx, feed in enumerate(feeds):
            feed_name = feed.name
            feed_url = feed.url
            feed_cat = feed.category
            pct = 15 + int((idx + 1) / max(len(feeds), 1) * 20)
            await emit_event("progress", "Fetching", pct, f"Fetching feed {feed_name}", feed=feed_name, run_id=run_id)
            log("Fetching", f"Fetching feed '{feed_name}' from {feed_url}")

            xml_bytes = await async_fetch_feed(feed_url, timeout=12)
            feed_status = "active" if xml_bytes else "error"

            with Session(engine) as session:
                f_db = session.get(Feed, feed.id)
                if f_db:
                    f_db.last_fetched_at = datetime.now(timezone.utc)
                    f_db.last_status = feed_status
                    session.add(f_db)
                    session.commit()

            if not xml_bytes:
                log("Fetching", f"Failed to retrieve XML for feed '{feed_name}'", level="WARN")
                continue

            entries = parse_feed_xml(xml_bytes, feed_name=feed_name, category=feed_cat)
            recent = [e for e in entries if e.get("pub_date") and e["pub_date"] >= cutoff]
            selected = recent[:6] if recent else entries[:5]

            # Save articles to DB
            with Session(engine) as session:
                for art in selected:
                    existing_art = session.exec(select(Article).where(Article.url == art["link"])).first()
                    if not existing_art:
                        new_art = Article(
                            feed_id=feed.id,
                            title=art["title"],
                            url=art["link"],
                            snippet=art.get("description", "")[:400],
                            published_at=art.get("pub_date"),
                            created_at=datetime.now(timezone.utc),
                        )
                        session.add(new_art)
                session.commit()

            all_articles.extend(selected)

        log("Fetching", f"Retrieved total of {len(all_articles)} articles across {len(feeds)} feeds")

        # Stage 3: Clustering
        await emit_event("status", "Clustering", 45, f"Clustering {len(all_articles)} articles by semantic topic", run_id=run_id)
        log("Clustering", f"Starting token-overlap clustering on {len(all_articles)} articles")
        clusters = cluster_articles(all_articles)
        log("Clustering", f"Formed {len(clusters)} distinct topic clusters")
        await emit_event("progress", "Clustering", 55, f"Identified {len(clusters)} topic clusters", total_clusters=len(clusters), run_id=run_id)

        # Stage 4: Synthesizing
        await emit_event("status", "Synthesizing", 65, "Synthesizing news stories via AI / NLP", run_id=run_id)
        log("Synthesizing", "Generating daily summary writeup")
        raw_summary, model_used, total_clusters, total_sources = synthesize_news(
            all_articles=all_articles,
            clusters=clusters,
            gemini_api_key=settings.gemini_api_key,
        )
        log("Synthesizing", f"Synthesis complete using model: {model_used}")
        await emit_event("progress", "Synthesizing", 80, f"Synthesis finished ({model_used})", model=model_used, run_id=run_id)

        # Stage 5: Storing
        await emit_event("status", "Storing", 85, "Persisting markdown digest and database records", run_id=run_id)
        now_dt = datetime.now()
        date_str = now_dt.strftime("%Y-%m-%d")
        full_md = build_markdown_document(raw_summary, now_dt)
        full_html = markdown_to_telegram_html(raw_summary, now_dt)

        # Write to files for backward compatibility
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        date_file = settings.output_dir / f"digest-{date_str}.md"
        with open(date_file, "w", encoding="utf-8") as f:
            f.write(full_md)
        with open(settings.latest_summary_file, "w", encoding="utf-8") as f:
            f.write(full_md)

        # Store or update in DB
        with Session(engine) as session:
            existing_digest = session.exec(select(Digest).where(Digest.date == date_str)).first()
            if existing_digest:
                existing_digest.summary_markdown = full_md
                existing_digest.summary_html = full_html
                existing_digest.model_used = model_used
                existing_digest.total_clusters = min(total_clusters, 5)
                existing_digest.total_sources = total_sources
                if trigger_type == "scheduled":
                    existing_digest.status = "published"
                session.add(existing_digest)
                digest_id = existing_digest.id
            else:
                new_digest = Digest(
                    date=date_str,
                    summary_markdown=full_md,
                    summary_html=full_html,
                    model_used=model_used,
                    total_clusters=min(total_clusters, 5),
                    total_sources=total_sources,
                    status="published" if trigger_type == "scheduled" else "draft",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(new_digest)
                session.commit()
                session.refresh(new_digest)
                digest_id = new_digest.id
            session.commit()

        log("Storing", f"Saved digest for date {date_str} (id={digest_id})")

        # Stage 6: Broadcast (if applicable)
        should_broadcast = (not dry_run) and (
            auto_broadcast or (trigger_type == "scheduled" and settings.telegram_bot_token and settings.telegram_chat_id)
        )
        if should_broadcast and settings.telegram_bot_token and settings.telegram_chat_id:
            await emit_event("status", "Broadcast", 92, "Broadcasting formatted digest to Telegram", run_id=run_id)
            log("Broadcast", "Delivering digest to Telegram bot")
            try:
                await broadcast_digest_async(
                    token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id,
                    markdown_content=raw_summary,
                    date_obj=now_dt,
                )
                with Session(engine) as session:
                    d_record = session.get(Digest, digest_id)
                    if d_record:
                        d_record.status = "broadcasted"
                        d_record.broadcasted_at = datetime.now(timezone.utc)
                        session.add(d_record)
                        session.commit()
                log("Broadcast", "Telegram broadcast delivered successfully")
            except Exception as e:
                log("Broadcast", f"Telegram broadcast failed: {e}", level="ERROR")
                await emit_event("error", "Broadcast", 95, f"Telegram delivery error: {e}", run_id=run_id)
        elif dry_run:
            log("Broadcast", "Dry run enabled: skipped Telegram broadcast")

        # Stage 7: Complete
        completed_at = datetime.now(timezone.utc)
        with Session(engine) as session:
            run_db = session.get(PipelineRun, run_id)
            if run_db:
                run_db.status = "completed"
                run_db.completed_at = completed_at
                run_db.logs = json.dumps(logs_buffer, ensure_ascii=False)
                session.add(run_db)
                session.commit()
                session.refresh(run_db)
                final_run = run_db

        await emit_event(
            "complete",
            "Complete",
            100,
            "Pipeline finished successfully",
            run_id=run_id,
            digest_id=digest_id,
            date=date_str,
        )
        return final_run

    except Exception as exc:
        err_msg = str(exc)
        stack = traceback.format_exc()
        log("Error", f"Pipeline failed: {err_msg}\n{stack}", level="ERROR")
        completed_at = datetime.now(timezone.utc)
        with Session(engine) as session:
            run_db = session.get(PipelineRun, run_id)
            if run_db:
                run_db.status = "failed"
                run_db.completed_at = completed_at
                run_db.logs = json.dumps(logs_buffer, ensure_ascii=False)
                session.add(run_db)
                session.commit()
                session.refresh(run_db)
                final_run = run_db
        await emit_event("error", "Failed", 100, f"Pipeline error: {err_msg}", run_id=run_id)
        return final_run
    finally:
        _active_run_id = None
