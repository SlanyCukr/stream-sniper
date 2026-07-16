"""
Composite router for the tracking administration API.

The prefix and OpenAPI tag for the whole ``/admin/tracking`` surface are
declared once here; the endpoint modules register plain routers so a rename
or router-level dependency has a single place to change.
"""

from fastapi import APIRouter, Depends

from ...security.auth import get_current_admin_user
from .tracking_job_endpoints import router as job_router
from .tracking_service_endpoints import router as service_router
from .tracking_streamer_endpoints import router as streamer_router

router = APIRouter(
    prefix="/admin/tracking",
    tags=["Tracking"],
    dependencies=[Depends(get_current_admin_user)],
)
router.include_router(streamer_router)
router.include_router(job_router)
router.include_router(service_router)
