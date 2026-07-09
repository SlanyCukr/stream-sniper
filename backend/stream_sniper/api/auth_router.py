"""
Composite router for the authentication API.

The prefix and OpenAPI tag for the whole ``/auth`` surface are declared once
here; the endpoint modules register plain routers so a rename or router-level
dependency has a single place to change.
"""

from fastapi import APIRouter

from .auth_endpoints import router as self_service_router
from .user_admin_endpoints import router as user_admin_router

router = APIRouter(prefix="/auth", tags=["Authentication"])
router.include_router(self_service_router)
router.include_router(user_admin_router)
