"""Chronological scene-event feed and digest preview endpoints."""

from fastapi import APIRouter, Query, Request, Response

from ....analytics.operations.digest import build_digest
from ....database.gateways.content.scene_event_table_gateway import select_scene_events_db
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse
from .scene_event_models import SceneDigest, SceneEvent, ScenePulse

logger = get_logger(__name__)
router = APIRouter(tags=["Scene"])
_SCENE_PULSE_CACHE = ModelCachePolicy("scene_pulse", CacheTTL.STREAM_ANALYTICS, ScenePulse)


@router.get(
    "/scene/pulse",
    response_model=ScenePulse,
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_pulse(
    request: Request,
    response: Response,
    days: int = Query(7, ge=1, le=90),
    event_type: str = Query("", pattern="^(stream_report|personal_record|standout_moment|copypasta_spread|)$"),
    creator_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ScenePulse:
    with _SCENE_PULSE_CACHE.record_failures():
        cache = get_cache(request)
        key, cached = _SCENE_PULSE_CACHE.lookup(
            cache, response, days, event_type, creator_id, limit, offset, scene_rollup_version()
        )
        if cached is not None:
            return cached
        rows, total = select_scene_events_db(days, event_type or None, creator_id, limit, offset)
        items = [
            SceneEvent(
                id=row.id,
                event_type=row.event_type,
                occurred_at=row.occurred_at,
                creator_id=row.creator_id,
                creator_nick=row.creator_nick,
                creator_display_name=row.creator_display_name,
                stream_id=row.stream_id,
                message_text_id=row.message_text_id,
                title=row.title,
                summary=row.summary,
                metadata=row.metadata or {},
            )
            for row in rows
        ]
        result = ScenePulse(items=items, total=total, days=days, limit=limit, offset=offset)
        _SCENE_PULSE_CACHE.store(cache, response, key, result)
        return result


@router.get(
    "/scene/digest",
    response_model=SceneDigest,
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_digest(
    request: Request,
    response: Response,
    days: int = Query(7, ge=1, le=30),
) -> SceneDigest:
    return SceneDigest(days=days, markdown=build_digest(days))
