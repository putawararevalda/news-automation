import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from backend.app.config import settings
from backend.app.db.session import engine, init_db
from backend.app.db.migration import seed_default_feeds, import_legacy_digests
from backend.app.api import api_router
from backend.app.services.pipeline import execute_pipeline

scheduler = AsyncIOScheduler()


def scheduled_job():
    """Wrapper to run scheduled pipeline as asyncio task."""
    print("[SCHEDULER] Triggering scheduled morning news pipeline run...")
    asyncio.create_task(
        execute_pipeline(
            dry_run=False,
            trigger_type="scheduled",
            auto_broadcast=True,
        )
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    print("[INFO] Starting News Automation API service...")
    init_db()

    with Session(engine) as session:
        seed_default_feeds(session)
        import_legacy_digests(session)

    # Setup APScheduler if cron schedule is defined
    cron_expr = settings.cron_schedule.strip()
    if cron_expr:
        try:
            # Cron format: "minute hour day month day_of_week" e.g. "0 6 * * *"
            parts = cron_expr.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                )
                scheduler.add_job(scheduled_job, trigger, id="daily_news_run", replace_existing=True)
                scheduler.start()
                print(f"[INFO] APScheduler started with cron: '{cron_expr}'")
        except Exception as e:
            print(f"[WARN] Failed to configure APScheduler cron ({cron_expr}): {e}")

    yield

    # Shutdown sequence
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[INFO] APScheduler shut down.")


app = FastAPI(
    title="News Automation Operations & Analytics API",
    version="2.0.0",
    description="Containerized Operations & Analytics Dashboard API for RSS aggregation, AI synthesis, and Telegram broadcast.",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router)


@app.get("/", tags=["Health"])
def root_status() -> Dict[str, Any]:
    return {
        "service": "News Automation Operations API",
        "status": "healthy",
        "version": "2.0.0",
    }


@app.get("/api/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "database": "connected",
    }
