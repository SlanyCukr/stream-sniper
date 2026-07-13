"""Chronological scene-event feed and digest preview endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..analytics.digest import build_digest
from ..database.scene_event_table_gateway import select_scene_events_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .rate_limiter import limiter, rate_limits
from .scene_event_models import SceneDigest, SceneEvent, ScenePulse

logger = get_logger(__name__)
router = APIRouter(tags=["Scene"])


@router.get("/scene/pulse", response_model=ScenePulse)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_pulse(
    request: Request,
    response: Response,
    days: int = Query(7, ge=1, le=90),
    event_type: str = Query("", pattern="^(stream_report|personal_record|standout_moment|copypasta_spread|)$"),
    creator_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ScenePulse:
    try:
        cache = get_cache()
        key = cache._generate_key("scene_pulse", days, event_type, creator_id, limit, offset)
        cached = cache.get(key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return ScenePulse(**cached)
        rows, total = select_scene_events_db(days, event_type or None, creator_id, limit, offset)
        items = [
            SceneEvent(
                id=row[0], event_type=row[1], occurred_at=row[2], creator_id=row[3],
                creator_nick=row[4], creator_display_name=row[5], stream_id=row[6],
                message_text_id=row[7], title=row[8], summary=row[9], metadata=row[10] or {},
            )
            for row in rows
        ]
        result = ScenePulse(items=items, total=total, days=days, limit=limit, offset=offset)
        cache.set(key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching scene pulse: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/scene/digest", response_model=SceneDigest)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_digest(
    request: Request,
    response: Response,
    days: int = Query(7, ge=1, le=30),
) -> SceneDigest:
    try:
        return SceneDigest(days=days, markdown=build_digest(days))
    except Exception as exc:
        logger.error(f"Error building scene digest: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
