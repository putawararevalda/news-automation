import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.app.db.session import get_session
from backend.app.db.models import PipelineRun
from backend.app.services.pipeline import (
    execute_pipeline,
    subscribe_events,
    _active_run_id,
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


class PipelineRunRequest(BaseModel):
    dry_run: Optional[bool] = Field(default=False)
    auto_broadcast: Optional[bool] = Field(default=False)
    mode: Optional[str] = Field(default=None)  # "dry_run" | "full"


@router.post("/run", response_model=Dict[str, Any])
async def trigger_pipeline_run(
    req: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    FR-09: Trigger manual pipeline execution (full or dry-run).
    Runs asynchronously in background task and emits SSE progress.
    """
    # Check if a run is already currently executing
    if _active_run_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A pipeline execution is already in progress (run_id={_active_run_id})."
        )

    is_dry_run = bool(req.dry_run) or (req.mode == "dry_run")
    run_id = str(uuid.uuid4())

    # Schedule non-blocking execution in background
    background_tasks.add_task(
        execute_pipeline,
        dry_run=is_dry_run,
        trigger_type="manual",
        auto_broadcast=bool(req.auto_broadcast),
        custom_run_id=run_id,
    )

    return {
        "status": "started",
        "run_id": run_id,
        "dry_run": is_dry_run,
        "auto_broadcast": req.auto_broadcast,
        "mode": req.mode,
        "message": "Pipeline execution started in background.",
    }


@router.get("/stream")
@router.get("/stream/{run_id}")
async def stream_pipeline_progress(request: Request, run_id: Optional[str] = None):
    """
    FR-10: Server-Sent Events (SSE) endpoint streaming pipeline execution progress in real-time.
    Supports streaming for current pipeline or specific run_id.
    """
    async def event_generator():
        try:
            # Send initial connection acknowledgment
            init_msg = json.dumps({
                "event": "connected",
                "message": "SSE connection established.",
                "active_run_id": _active_run_id,
                "requested_run_id": run_id,
            })
            yield f"data: {init_msg}\n\n"

            async for event in subscribe_events():
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                # Filter if client specifically requested a single run_id
                event_run_id = event.get("run_id")
                if run_id and event_run_id and event_run_id != run_id:
                    continue

                event_name = event.get("event", "message")
                data_str = json.dumps(event)
                yield f"event: {event_name}\ndata: {data_str}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs", response_model=List[PipelineRun])
def list_pipeline_runs(
    limit: int = 15,
    session: Session = Depends(get_session),
) -> List[PipelineRun]:
    """List recent pipeline execution runs."""
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
    return session.exec(stmt).all()


@router.get("/runs/{run_id}", response_model=PipelineRun)
def get_pipeline_run(run_id: str, session: Session = Depends(get_session)) -> PipelineRun:
    """Get status and logs for a specific pipeline run."""
    run = session.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run
