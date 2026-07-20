"""
Tracked-streamer administration endpoints: CRUD plus the Twitch channel search
used by the add-streamer autocomplete.
"""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import RootModel

from stream_sniper.database.core.patches import UNSET

from ....application.identity.tracked_streamer_creation import (
    StreamerAlreadyTrackedError,
    StreamerNotFoundError,
    TrackedStreamerCreationError,
    TwitchProfileLookupError,
    create_tracked_streamer,
)
from ....collector.twitch_api import TwitchConfigurationError, TwitchUpstreamError
from ....database.gateways.streams.stream_table_gateway import select_creator_stream_summaries_db
from ....database.gateways.tracking.tracked_streamers_table_gateway import (
    count_tracked_streamers_db,
    delete_tracked_streamer_db,
    select_tracked_streamer_by_id_db,
    select_tracked_streamers_db,
    update_tracked_streamer_db,
)
from ....logging_config import get_logger, sanitize_log_value
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache, get_twitch_client
from ...security.auth import get_current_admin_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorResponse, RateLimitErrorResponse
from .tracking_models import (
    TrackedStreamerCreate,
    TrackedStreamerResponse,
    TrackedStreamersResponse,
    TrackedStreamerUpdate,
    TwitchChannelResult,
    TwitchProbeResponse,
    convert_tracked_streamer_to_response,
)

logger = get_logger(__name__)

# Mounted under /admin/tracking by tracking_router.py.
router = APIRouter()


class _TwitchSearchCache(RootModel[list[TwitchChannelResult]]):
    pass


_TWITCH_SEARCH_CACHE = ModelCachePolicy("twitch_search", CacheTTL.TWITCH_SEARCH, _TwitchSearchCache)


@router.get(
    "/streamers",
    response_model=TrackedStreamersResponse,
    summary="Get tracked streamers",
    description="""
    Get list of tracked streamers with optional filtering and pagination.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "List of tracked streamers"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        500: {"model": ErrorResponse, "description": "Tracked streamer persistence failed"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
def get_tracked_streamers(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    is_active: bool | None = Query(None, description="Filter by active status"),
    processing_enabled: bool | None = Query(None, description="Filter by processing enabled"),
) -> TrackedStreamersResponse:
    """Get tracked streamers (admin only)"""
    streamer_records = select_tracked_streamers_db(
        limit=limit, offset=offset, is_active=is_active, processing_enabled=processing_enabled
    )

    total = count_tracked_streamers_db(is_active=is_active, processing_enabled=processing_enabled)

    summaries = {
        row.creator_id: row
        for row in select_creator_stream_summaries_db([s.creator_id for s in streamer_records])
    }
    streamers = [
        convert_tracked_streamer_to_response(streamer, summaries.get(streamer.creator_id))
        for streamer in streamer_records
    ]

    return TrackedStreamersResponse(streamers=streamers, total=total, offset=offset, limit=limit)


@router.post(
    "/streamers",
    response_model=TrackedStreamerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tracked streamer",
    description="""
    Add a new streamer to tracking.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        201: {"description": "Streamer added successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data or streamer already exists"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        500: {"model": ErrorResponse, "description": "Tracked streamer persistence failed"},
        502: {"model": ErrorResponse, "description": "Twitch profile lookup failed"},
        503: {"model": ErrorResponse, "description": "Twitch integration is not configured"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
async def add_tracked_streamer(
    streamer_data: TrackedStreamerCreate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user),
) -> TrackedStreamerResponse:
    """Add a new streamer to tracking (admin only)"""
    try:
        streamer = await create_tracked_streamer(
            twitch_api=get_twitch_client(request),
            twitch_username=streamer_data.twitch_username,
            created_by=current_user.id,
            notes=streamer_data.notes,
            is_active=streamer_data.is_active,
            processing_enabled=streamer_data.processing_enabled,
        )
    except StreamerAlreadyTrackedError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Streamer is already being tracked")
    except StreamerNotFoundError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Streamer not found on Twitch")
    except TwitchConfigurationError as error:
        logger.exception("Twitch integration is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Twitch lookups aren't available right now because the server's Twitch access isn't configured. Contact the administrator."
        ) from error
    except (TwitchProfileLookupError, TwitchUpstreamError) as error:
        logger.exception("Twitch profile lookup failed for %s", sanitize_log_value(streamer_data.twitch_username))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not reach Twitch. Try again in a moment.") from error
    except TrackedStreamerCreationError as error:
        logger.exception("Tracked streamer creation failed for %s", sanitize_log_value(streamer_data.twitch_username))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add the streamer because of a server problem. Try again in a moment.",
        ) from error

    logger.info(
        "Tracked streamer created by admin %s: %s",
        sanitize_log_value(current_user.username),
        sanitize_log_value(streamer_data.twitch_username),
    )
    return convert_tracked_streamer_to_response(streamer)


@router.get(
    "/twitch-search",
    response_model=list[TwitchChannelResult],
    summary="Search Twitch channels",
    description="""
    Search live Twitch channels by name, for the add-streamer autocomplete.
    Backed by the Twitch Helix search API (channels active in the last 6 months).

    Requires admin role.

    **Rate Limit**: configured search policy
    """,
    responses={
        200: {"description": "List of matching Twitch channels"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "Twitch channel search failed"},
        503: {"model": ErrorResponse, "description": "Twitch integration is not configured"},
    },
)
@limiter.limit(rate_limits.SEARCH)
async def search_twitch_channels(
    request: Request,
    response: Response,
    q: str = Query(..., description="Channel name to search for"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of suggestions"),
) -> list[TwitchChannelResult]:
    """Search Twitch channels by name for the add-streamer typeahead (admin only)."""
    query = q.strip()
    if len(query) < 2:
        return []

    cache = get_cache(request)
    cache_key, cached_result = _TWITCH_SEARCH_CACHE.lookup(cache, response, query.lower(), limit)
    if cached_result is not None:
        return cached_result.root

    try:
        twitch_api = get_twitch_client(request)
        await twitch_api.ensure_initialized()
        channels = await twitch_api.search_channels(query, limit)
    except TwitchConfigurationError as error:
        logger.exception("Twitch integration is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Twitch lookups aren't available right now because the server's Twitch access isn't configured. Contact the administrator."
        ) from error
    except TwitchUpstreamError as error:
        logger.exception("Error searching Twitch channels for '%s'", sanitize_log_value(query))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not search Twitch right now. Try again in a moment.",
        ) from error

    result = [
        TwitchChannelResult(
            login=channel.broadcaster_login,
            display_name=channel.display_name,
            profile_image_url=channel.thumbnail_url or "",
            is_live=bool(channel.is_live),
        )
        for channel in channels
    ]

    _TWITCH_SEARCH_CACHE.store(cache, response, cache_key, _TwitchSearchCache(result))
    return result


@router.get(
    "/streamers/{streamer_id}",
    response_model=TrackedStreamerResponse,
    summary="Get tracked streamer by ID",
    description="""
    Get detailed information about a specific tracked streamer.

    Requires admin role.

    **Rate Limit**: 60 requests per minute
    """,
    responses={
        200: {"description": "Tracked streamer information"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Streamer not found"},
        500: {"model": ErrorResponse, "description": "Tracked streamer persistence failed"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
def get_tracked_streamer(streamer_id: int, request: Request, response: Response) -> TrackedStreamerResponse:
    """Get tracked streamer by ID (admin only)"""
    streamer = select_tracked_streamer_by_id_db(streamer_id)

    if not streamer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked streamer not found")

    summaries = select_creator_stream_summaries_db([streamer.creator_id])
    return convert_tracked_streamer_to_response(streamer, summaries[0] if summaries else None)


@router.put(
    "/streamers/{streamer_id}",
    response_model=TrackedStreamerResponse,
    summary="Update tracked streamer",
    description="""
    Update tracked streamer settings.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "Streamer updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Streamer not found"},
        500: {"model": ErrorResponse, "description": "Tracked streamer persistence failed"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
def update_tracked_streamer(
    streamer_id: int,
    streamer_update: TrackedStreamerUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user),
) -> TrackedStreamerResponse:
    """Update tracked streamer (admin only)"""
    streamer = select_tracked_streamer_by_id_db(streamer_id)
    if not streamer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked streamer not found")

    supplied_fields = streamer_update.model_fields_set
    if not supplied_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to save — change at least one field first.")

    success = update_tracked_streamer_db(
        streamer_id,
        is_active=streamer_update.is_active if streamer_update.is_active is not None else UNSET,
        processing_enabled=(
            streamer_update.processing_enabled if streamer_update.processing_enabled is not None else UNSET
        ),
        notes=streamer_update.notes if "notes" in supplied_fields else UNSET,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save the streamer changes because of a server problem. Try again in a moment.")

    updated_streamer = select_tracked_streamer_by_id_db(streamer_id)
    if not updated_streamer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The change may not have been saved because of a server problem. Refresh and try again."
        )

    logger.info(
        "Tracked streamer updated by admin %s: streamer_id=%s", sanitize_log_value(current_user.username), streamer_id
    )
    return convert_tracked_streamer_to_response(updated_streamer)


@router.delete(
    "/streamers/{streamer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tracked streamer",
    description="""
    Remove a streamer from tracking.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        204: {"description": "Streamer removed successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Streamer not found"},
        500: {"model": ErrorResponse, "description": "Tracked streamer persistence failed"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/minute")
def remove_tracked_streamer(
    streamer_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> None:
    """Remove tracked streamer (admin only)"""
    streamer = select_tracked_streamer_by_id_db(streamer_id)
    if not streamer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked streamer not found")

    success = delete_tracked_streamer_db(streamer_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not remove the streamer because of a server problem. Try again in a moment.")

    logger.info(
        "Tracked streamer removed by admin %s: streamer_id=%s", sanitize_log_value(current_user.username), streamer_id
    )
    return None


@router.post(
    "/streamers/{streamer_id}/probe",
    response_model=TwitchProbeResponse,
    summary="Probe a tracked streamer on Twitch",
    description="""
    On-demand Twitch snapshot for a tracked streamer: live status, archive VOD
    count, and the newest VOD's creation time. Lets an admin distinguish a
    dormant channel (nothing to collect) from broken ingestion.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Twitch snapshot for the streamer"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Streamer not found"},
        502: {"model": ErrorResponse, "description": "Twitch lookup failed"},
        503: {"model": ErrorResponse, "description": "Twitch integration is not configured"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/minute")
async def probe_twitch_channel(
    streamer_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> TwitchProbeResponse:
    streamer = await asyncio.to_thread(select_tracked_streamer_by_id_db, streamer_id)
    if not streamer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked streamer not found")

    login = streamer.twitch_username
    try:
        twitch_api = get_twitch_client(request)
        await twitch_api.ensure_initialized()
        live = await twitch_api.get_live_stream(login)
        videos = await twitch_api.get_archived_videos(login)
    except TwitchConfigurationError as error:
        logger.exception("Twitch integration is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twitch lookups aren't available right now because the server's Twitch access isn't configured. Contact the administrator.",
        ) from error
    except TwitchUpstreamError as error:
        logger.exception("Twitch probe failed for %s", sanitize_log_value(login))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Twitch for this channel. Try again in a moment.",
        ) from error

    last_vod = max(videos, key=lambda video: video.created_at) if videos else None
    logger.info(
        "Twitch probe by admin %s: streamer_id=%s live=%s vods=%s",
        sanitize_log_value(current_user.username),
        streamer_id,
        live is not None,
        len(videos),
    )
    return TwitchProbeResponse(
        is_live=live is not None,
        archive_vod_count=len(videos),
        last_vod_created_at=last_vod.created_at.isoformat() if last_vod else None,
        checked_at=datetime.now(UTC).isoformat(),
    )
