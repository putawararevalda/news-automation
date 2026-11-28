from fastapi import APIRouter

from backend.app.api.overview import router as overview_router
from backend.app.api.feeds import router as feeds_router
from backend.app.api.digests import router as digests_router
from backend.app.api.pipeline import router as pipeline_router

api_router = APIRouter(prefix="/api")

api_router.include_router(overview_router)
api_router.include_router(feeds_router)
api_router.include_router(digests_router)
api_router.include_router(pipeline_router)

__all__ = ["api_router"]
