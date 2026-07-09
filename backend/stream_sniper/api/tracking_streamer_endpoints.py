"""
Tracked-streamer administration endpoints: CRUD plus the Twitch channel search
used by the add-streamer autocomplete.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from ..collector.twitch_api import TwitchAPI
from ..database.creator_table_gateway import insert_new_creator_db, select_creator_id_db
from ..database.tracked_streamers_table_gateway import (
    count_tracked_streamers_db,
    delete_tracked_streamer_db,
    insert_tracked_streamer_db,
    select_tracked_streamer_by_id_db,
    select_tracked_streamers_db,
    streamer_exists_db,
    update_tracked_streamer_db,
)
from ..logging_config import get_logger
from .auth import UserInDB, get_current_admin_user
from .cache import CacheTTL, get_cache
from .rate_limiter import limiter, rate_limits
from .tracking_models import (
    TrackedStreamerCreate,
    TrackedStreamerResponse,
    TrackedStreamersResponse,
    TrackedStreamerUpdate,
    TwitchChannelResult,
    convert_tracked_streamer_to_response,
)

logger = get_logger(__name__)

# Mounted under /admin/tracking by tracking_router.py.
router = APIRouter()


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
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_tracked_streamers(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    processing_enabled: Optional[bool] = Query(None, description="Filter by processing enabled"),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracked streamers (admin only)"""
    try:
        streamers_tuple = select_tracked_streamers_db(
            limit=limit,
            offset=offset,
            is_active=is_active,
            processing_enabled=processing_enabled
        )

        total = count_tracked_streamers_db(
            is_active=is_active,
            processing_enabled=processing_enabled
        )

        streamers = [convert_tracked_streamer_to_response(streamer_tuple)
                    for streamer_tuple in streamers_tuple]

        return TrackedStreamersResponse(
            streamers=streamers,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error fetching tracked streamers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
        400: {"description": "Invalid input data or streamer already exists"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def add_tracked_streamer(
    streamer_data: TrackedStreamerCreate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Add a new streamer to tracking (admin only)"""
    try:
        # Check if streamer already exists
        if streamer_exists_db(streamer_data.twitch_username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Streamer is already being tracked"
            )

        # Get or create creator
        creator_id = select_creator_id_db(streamer_data.twitch_username)

        if not creator_id:
            # Create new creator using Twitch API
            try:
                twitch_api = TwitchAPI.instance()
                await twitch_api.ensure_initialized()
                twitch_api.set_streamer_nickname(streamer_data.twitch_username)

                display_name, profile_image_url = await twitch_api.get_creator_info_async()
                twitch_creator_id = await twitch_api.get_creator_twitch_id_async()

                creator_id = insert_new_creator_db(
                    streamer_data.twitch_username,
                    display_name,
                    profile_image_url,
                    twitch_creator_id
                )

                if not creator_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create creator"
                    )

                display_name_for_tracking = display_name

            except Exception as e:
                logger.error(f"Error creating creator for {streamer_data.twitch_username}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get streamer information from Twitch"
                )
        else:
            # Use existing creator display name
            display_name_for_tracking = streamer_data.twitch_username

        # Create tracked streamer
        tracked_streamer_id = insert_tracked_streamer_db(
            creator_id=creator_id,
            twitch_username=streamer_data.twitch_username,
            display_name=display_name_for_tracking,
            created_by=current_user.id,
            notes=streamer_data.notes,
            is_active=streamer_data.is_active,
            processing_enabled=streamer_data.processing_enabled
        )

        if not tracked_streamer_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tracked streamer"
            )

        # Fetch created streamer
        streamer_tuple = select_tracked_streamer_by_id_db(tracked_streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created streamer"
            )

        logger.info(f"Tracked streamer created by admin {current_user.username}: {streamer_data.twitch_username}")
        return convert_tracked_streamer_to_response(streamer_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/twitch-search",
    response_model=List[TwitchChannelResult],
    summary="Search Twitch channels",
    description=f"""
    Search live Twitch channels by name, for the add-streamer autocomplete.
    Backed by the Twitch Helix search API (channels active in the last 6 months).

    Requires admin role.

    **Rate Limit**: {rate_limits.SEARCH}
    """,
    responses={
        200: {"description": "List of matching Twitch channels"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.SEARCH)
async def search_twitch_channels(
    request: Request,
    response: Response,
    q: str = Query(..., description="Channel name to search for"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of suggestions"),
    current_user: UserInDB = Depends(get_current_admin_user),
):
    """Search Twitch channels by name for the add-streamer typeahead (admin only)."""
    query = q.strip()
    if len(query) < 2:
        return []

    cache = get_cache()
    cache_key = cache._generate_key("twitch_search", query.lower(), limit)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_result

    try:
        twitch_api = TwitchAPI.instance()
        await twitch_api.ensure_initialized()
        channels = await twitch_api.search_channels_async(query, limit)
    except Exception as e:
        logger.error(f"Error searching Twitch channels for '{query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to search Twitch channels",
        )

    result = [
        {
            "login": channel.broadcaster_login,
            "display_name": channel.display_name,
            "profile_image_url": channel.thumbnail_url or "",
            "is_live": bool(channel.is_live),
        }
        for channel in channels
    ]

    cache.set(cache_key, result, CacheTTL.TWITCH_SEARCH)
    response.headers["X-Cache"] = "MISS"
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
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("60/minute")
def get_tracked_streamer(
    streamer_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracked streamer by ID (admin only)"""
    try:
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)

        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )

        return convert_tracked_streamer_to_response(streamer_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def update_tracked_streamer(
    streamer_id: int,
    streamer_update: TrackedStreamerUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Update tracked streamer (admin only)"""
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )

        # Build update data
        update_data = {}
        if streamer_update.is_active is not None:
            update_data['is_active'] = streamer_update.is_active
        if streamer_update.processing_enabled is not None:
            update_data['processing_enabled'] = streamer_update.processing_enabled
        if streamer_update.notes is not None:
            update_data['notes'] = streamer_update.notes

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Update streamer
        success = update_tracked_streamer_db(streamer_id, **update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update streamer"
            )

        # Fetch updated streamer
        updated_streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not updated_streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated streamer"
            )

        logger.info(f"Tracked streamer updated by admin {current_user.username}: streamer_id={streamer_id}")
        return convert_tracked_streamer_to_response(updated_streamer_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/streamers/{streamer_id}",
    summary="Remove tracked streamer",
    description="""
    Remove a streamer from tracking.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Streamer removed successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
def remove_tracked_streamer(
    streamer_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Remove tracked streamer (admin only)"""
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )

        # Delete streamer
        success = delete_tracked_streamer_db(streamer_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove streamer"
            )

        logger.info(f"Tracked streamer removed by admin {current_user.username}: streamer_id={streamer_id}")
        return {"message": "Streamer removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
