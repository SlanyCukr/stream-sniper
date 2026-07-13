"""Window-over-window creator audience participation reports."""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.audience_movement_table_gateway import select_creator_audience_movement_db
from ..logging_config import get_logger
from .audience_models import AudienceAssociation, AudienceMovement
from .cache import CacheTTL, get_cache
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)
router = APIRouter(tags=["Community"])


@router.get("/creator/{creator_id}/audience-movement", response_model=AudienceMovement)
@limiter.limit(rate_limits.HEAVY)
def get_audience_movement(
    request: Request,
    response: Response,
    creator_id: int = Path(..., ge=1),
    days: int = Query(30, ge=7, le=90),
    limit: int = Query(8, ge=1, le=20),
) -> AudienceMovement:
    """Compare distinct participating chatters across adjacent equal windows."""
    try:
        cache = get_cache()
        key = cache._generate_key("audience_movement", creator_id, days, limit)
        cached = cache.get(key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return AudienceMovement(**cached)
        summary, source_rows, destination_rows = select_creator_audience_movement_db(
            creator_id, days, limit
        )
        current, previous, retained, gained, lapsed = summary
        def association(row):
            return AudienceAssociation(
                creator_id=row[0], nick=row[1], display_name=row[2], chatter_count=row[3]
            )
        result = AudienceMovement(
            creator_id=creator_id,
            window_days=days,
            current_audience=current,
            previous_audience=previous,
            retained=retained,
            gained=gained,
            lapsed=lapsed,
            retention_rate=round(retained / previous, 4) if previous else None,
            gain_rate=round(gained / current, 4) if current else None,
            prior_channels_for_gained=[association(row) for row in source_rows],
            current_channels_for_lapsed=[association(row) for row in destination_rows],
        )
        cache.set(key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching audience movement: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
