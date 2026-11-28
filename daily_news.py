#!/usr/bin/env python3
"""
Daily News Aggregator & Synthesizer with Cross-Feed Ranking
CLI / Cron entrypoint invoking modular domain services from backend.app.services.
Maintains 100% backward compatibility with existing command-line arguments (--dry-run, --test)
and file storage outputs (./digests/ and ./daily-summary.md).
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from backend.app.config import settings, Settings
from backend.app.services.crawler import fetch_feed, parse_feed_xml
from backend.app.services.clustering import cluster_articles
from backend.app.services.synthesizer import (
    synthesize_news,
    build_markdown_document,
)
from backend.app.services.broadcaster import (
    split_message_chunks,
    send_telegram_message,
    markdown_to_telegram_html,
    broadcast_digest_sync,
)

# Optional database persistence
try:
    from sqlmodel import Session, select
    from backend.app.db.session import engine, init_db
    from backend.app.db.models import Feed, Article, Digest, PipelineRun
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


def load_config():
    """Legacy helper returning dictionary representation of settings."""
    return {
        "gemini_api_key": settings.gemini_api_key,
        "telegram": {
            "bot_token": settings.telegram_bot_token,
            "chat_id": settings.telegram_chat_id,
        },
        "output_dir": str(settings.output_dir),
        "latest_summary_file": str(settings.latest_summary_file),
        "feeds": settings.default_feeds,
    }


def main():
    dry_run = "--dry-run" in sys.argv or "--test" in sys.argv
    started_at = datetime.now(timezone.utc)
    now_dt = datetime.now()
    today_str = now_dt.strftime("%A, %d %B %Y")
    date_str = now_dt.strftime("%Y-%m-%d")

    print(f"[{now_dt.isoformat()}] Starting Daily News Aggregator CLI (dry_run={dry_run})...")

    # Initialize DB if available
    db_session = None
    if DB_AVAILABLE:
        try:
            init_db()
            db_session = Session(engine)
        except Exception as e:
            print(f"[WARN] SQLite connection skipped: {e}", file=sys.stderr)
            db_session = None

    # Load feeds from DB or fallback to config
    feeds = []
    if db_session:
        try:
            db_feeds = db_session.exec(select(Feed).where(Feed.is_active == True)).all()
            if db_feeds:
                feeds = [{"name": f.name, "category": f.category, "url": f.url, "id": f.id} for f in db_feeds]
        except Exception as e:
            print(f"[WARN] Could not query feeds from DB: {e}", file=sys.stderr)

    if not feeds:
        feeds = settings.default_feeds

    cutoff = started_at - timedelta(hours=24)
    all_articles = []
    print(f"[{datetime.now().isoformat()}] Fetching news from {len(feeds)} sources...")

    for feed_info in feeds:
        name = feed_info.get("name", "News")
        category = feed_info.get("category", "General")
        url = feed_info.get("url")
        print(f" - {name}...")
        xml_bytes = fetch_feed(url, timeout=15)
        entries = parse_feed_xml(xml_bytes, feed_name=name, category=category)

        # Filter 24h
        recent = [e for e in entries if e.get("pub_date") and e["pub_date"] >= cutoff]
        if not recent:
            recent = entries[:5]
        else:
            recent = recent[:6]

        all_articles.extend(recent)

        # Update feed status in DB if available
        feed_id = feed_info.get("id")
        if db_session and feed_id:
            try:
                f_record = db_session.get(Feed, feed_id)
                if f_record:
                    f_record.last_fetched_at = datetime.now(timezone.utc)
                    f_record.last_status = "active" if xml_bytes else "error"
                    db_session.add(f_record)
                    db_session.commit()
            except Exception:
                pass

    print(f"Total articles retrieved: {len(all_articles)}. Clustering by topic...")
    clusters = cluster_articles(all_articles)
    print(f"Formed {len(clusters)} distinct topic clusters.")

    # Synthesis
    if settings.gemini_api_key:
        print("Using Gemini API for human-readable synthesis...")
    else:
        print("Using local ranking synthesizer (order by feed count)...")

    summary_body, model_used, total_clusters, total_sources = synthesize_news(
        all_articles=all_articles,
        clusters=clusters,
        gemini_api_key=settings.gemini_api_key,
    )
    print(f"Synthesis complete using: {model_used}")

    full_md = build_markdown_document(summary_body, now_dt)
    full_tg_html = markdown_to_telegram_html(summary_body, now_dt)

    # Save to Markdown files
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    date_file = settings.output_dir / f"digest-{date_str}.md"
    latest_file = settings.latest_summary_file

    with open(date_file, "w", encoding="utf-8") as f:
        f.write(full_md)
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(full_md)

    print(f"Saved digest to {latest_file} and {date_file}")

    # Persist in SQLite
    if db_session:
        try:
            existing_digest = db_session.exec(select(Digest).where(Digest.date == date_str)).first()
            if existing_digest:
                existing_digest.summary_markdown = full_md
                existing_digest.summary_html = full_tg_html
                existing_digest.model_used = model_used
                existing_digest.total_clusters = min(total_clusters, 5)
                existing_digest.total_sources = total_sources
                db_session.add(existing_digest)
            else:
                new_digest = Digest(
                    date=date_str,
                    summary_markdown=full_md,
                    summary_html=full_tg_html,
                    model_used=model_used,
                    total_clusters=min(total_clusters, 5),
                    total_sources=total_sources,
                    status="published",
                    created_at=datetime.now(timezone.utc),
                )
                db_session.add(new_digest)
            db_session.commit()
        except Exception as e:
            print(f"[WARN] Failed to record digest in SQLite: {e}", file=sys.stderr)

    if dry_run:
        print("[DRY RUN] Skipping Telegram send.")
        if db_session:
            db_session.close()
        return

    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if bot_token and chat_id:
        print("Sending formatted digest to Telegram...")
        chunks = split_message_chunks(full_tg_html)
        for i, chunk in enumerate(chunks):
            try:
                send_telegram_message(bot_token, chat_id, chunk)
                print(f"Delivered chunk {i+1}/{len(chunks)}")
            except Exception as e:
                print(f"[ERROR] Failed to send Telegram chunk {i+1}: {e}", file=sys.stderr)
        print("Telegram broadcast complete!")

        # Update broadcast status in DB
        if db_session:
            try:
                d_rec = db_session.exec(select(Digest).where(Digest.date == date_str)).first()
                if d_rec:
                    d_rec.status = "broadcasted"
                    d_rec.broadcasted_at = datetime.now(timezone.utc)
                    db_session.add(d_rec)
                    db_session.commit()
            except Exception:
                pass

    if db_session:
        db_session.close()


if __name__ == "__main__":
    main()
