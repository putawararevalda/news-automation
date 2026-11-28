import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Feed(SQLModel, table=True):
    __tablename__ = "feed"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str = Field(index=True, unique=True)
    category: str = Field(default="General", index=True)
    is_active: bool = Field(default=True, index=True)
    last_status: str = Field(default="idle")  # "idle", "active", "error"
    last_fetched_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Article(SQLModel, table=True):
    __tablename__ = "article"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: Optional[int] = Field(default=None, foreign_key="feed.id", index=True)
    title: str
    url: str = Field(index=True)
    snippet: Optional[str] = Field(default=None)
    published_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Digest(SQLModel, table=True):
    __tablename__ = "digest"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True, unique=True)  # YYYY-MM-DD
    summary_markdown: str
    summary_html: str
    model_used: str = Field(default="local-nlp")
    total_clusters: int = Field(default=0)
    total_sources: int = Field(default=0)
    status: str = Field(default="draft", index=True)  # "draft" | "published" | "broadcasted"
    broadcasted_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_run"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trigger_type: str = Field(default="manual", index=True)  # "scheduled" | "manual"
    status: str = Field(default="running", index=True)  # "running" | "completed" | "failed"
    logs: Optional[str] = Field(default=None)  # JSON serialized logs
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
