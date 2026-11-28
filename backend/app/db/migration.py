import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import Session, select

from backend.app.config import settings
from backend.app.db.models import Feed, Digest
from backend.app.services.broadcaster import markdown_to_telegram_html


def seed_default_feeds(session: Session) -> int:
    """Seed default RSS feeds from config.json if the feed table is empty."""
    existing = session.exec(select(Feed)).first()
    if existing:
        return 0

    inserted_count = 0
    for item in settings.default_feeds:
        url = item.get("url")
        if not url:
            continue
        feed = Feed(
            name=item.get("name", "News Source"),
            url=url,
            category=item.get("category", "General"),
            is_active=True,
            last_status="idle",
            created_at=datetime.now(timezone.utc),
        )
        session.add(feed)
        inserted_count += 1

    if inserted_count > 0:
        session.commit()
        print(f"[INFO] Seeded {inserted_count} default feeds into database.", file=sys.stdout)
    return inserted_count


def import_legacy_digests(session: Session, digests_dir: Optional[Path] = None) -> int:
    """
    FR-15: Scan markdown files in ./digests/digest-YYYY-MM-DD.md and import into SQLite.
    Idempotent operation: skips any digest whose date is already stored.
    """
    target_dir = digests_dir or settings.output_dir
    if not target_dir.exists():
        return 0

    imported_count = 0
    date_regex = re.compile(r"digest-(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE)

    for file_path in sorted(target_dir.glob("digest-*.md")):
        match = date_regex.search(file_path.name)
        if not match:
            continue

        digest_date = match.group(1)

        # Check if date already present
        existing = session.exec(select(Digest).where(Digest.date == digest_date)).first()
        if existing:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[WARN] Failed to read legacy digest {file_path}: {e}", file=sys.stderr)
            continue

        if not content.strip():
            continue

        # Estimate cluster count from numbered emojis or headers
        cluster_emojis = len(re.findall(r"[1-9]️⃣", content))
        if cluster_emojis == 0:
            cluster_emojis = len(re.findall(r"\n---\n", content)) + 1
        cluster_emojis = max(cluster_emojis, 1)

        # Count sources mentioned
        sources_match = re.findall(r"sumber:\s*([^)]+)\)", content, re.IGNORECASE)
        distinct_sources = set()
        for src_group in sources_match:
            for s in src_group.split(","):
                clean = s.strip()
                if clean:
                    distinct_sources.add(clean)
        total_sources = len(distinct_sources) if distinct_sources else cluster_emojis

        # Convert markdown to HTML representation
        try:
            dt = datetime.strptime(digest_date, "%Y-%m-%d")
        except ValueError:
            dt = datetime.now()

        summary_html = markdown_to_telegram_html(content, dt)

        digest = Digest(
            date=digest_date,
            summary_markdown=content,
            summary_html=summary_html,
            model_used="legacy-archive",
            total_clusters=cluster_emojis,
            total_sources=total_sources,
            status="broadcasted",
            broadcasted_at=datetime.combine(dt.date(), datetime.min.time(), tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        session.add(digest)
        imported_count += 1

    if imported_count > 0:
        session.commit()
        print(f"[INFO] Imported {imported_count} legacy digests into SQLite database.", file=sys.stdout)

    return imported_count
