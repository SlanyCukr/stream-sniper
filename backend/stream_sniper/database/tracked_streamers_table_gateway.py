"""
Database gateway for tracked_streamers table operations.
"""

from typing import Optional, List, Tuple
from datetime import datetime

from .connection_pool import get_pool
from .decorators import log_database_operation
from ..logging_config import get_logger

logger = get_logger(__name__)


@log_database_operation
def insert_tracked_streamer_db(
    creator_id: int,
    twitch_username: str,
    display_name: str,
    created_by: int,
    notes: Optional[str] = None,
    is_active: bool = True,
    processing_enabled: bool = True
) -> Optional[int]:
    """
    Insert a new tracked streamer into the database.
    
    Args:
        creator_id: ID of the creator to track
        twitch_username: Twitch username
        display_name: Display name
        created_by: ID of the user who created this tracking
        notes: Optional notes
        is_active: Whether tracking is active
        processing_enabled: Whether processing is enabled
    
    Returns:
        Tracked streamer ID if successful, None otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO stream_sniper.tracked_streamers 
                (creator_id, twitch_username, display_name, created_by, notes, is_active, processing_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (creator_id, twitch_username, display_name, created_by, notes, is_active, processing_enabled)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error inserting tracked streamer: {e}")
        return None


@log_database_operation
def select_tracked_streamers_db(
    limit: int = 100,
    offset: int = 0,
    is_active: Optional[bool] = None,
    processing_enabled: Optional[bool] = None
) -> List[Tuple]:
    """
    Select tracked streamers with optional filtering.
    
    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        is_active: Filter by active status
        processing_enabled: Filter by processing enabled status
    
    Returns:
        List of tracked streamer tuples
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            where_clauses = []
            params = []
            
            if is_active is not None:
                where_clauses.append("ts.is_active = %s")
                params.append(is_active)
            
            if processing_enabled is not None:
                where_clauses.append("ts.processing_enabled = %s")
                params.append(processing_enabled)
            
            where_clause = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_clause}" if where_clause else ""
            
            params.extend([limit, offset])
            
            query = f"""
                SELECT ts.id, ts.creator_id, ts.twitch_username, ts.display_name, ts.is_active,
                       ts.last_stream_check, ts.last_processed_stream_id, ts.processing_enabled,
                       ts.created_at, ts.updated_at, ts.created_by, ts.notes,
                       c.display_name as creator_display_name, c.profile_image_url,
                       u.username as created_by_username
                FROM stream_sniper.tracked_streamers ts
                JOIN stream_sniper.creator c ON ts.creator_id = c.id
                LEFT JOIN stream_sniper.users u ON ts.created_by = u.id
                {where_clause}
                ORDER BY ts.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error selecting tracked streamers: {e}")
        return []


@log_database_operation
def select_tracked_streamer_by_id_db(tracked_streamer_id: int) -> Optional[Tuple]:
    """
    Select a tracked streamer by ID.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
    
    Returns:
        Tracked streamer tuple or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT ts.id, ts.creator_id, ts.twitch_username, ts.display_name, ts.is_active,
                       ts.last_stream_check, ts.last_processed_stream_id, ts.processing_enabled,
                       ts.created_at, ts.updated_at, ts.created_by, ts.notes,
                       c.display_name as creator_display_name, c.profile_image_url,
                       u.username as created_by_username
                FROM stream_sniper.tracked_streamers ts
                JOIN stream_sniper.creator c ON ts.creator_id = c.id
                LEFT JOIN stream_sniper.users u ON ts.created_by = u.id
                WHERE ts.id = %s
                """,
                (tracked_streamer_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting tracked streamer by ID: {e}")
        return None


@log_database_operation
def select_tracked_streamer_by_username_db(twitch_username: str) -> Optional[Tuple]:
    """
    Select a tracked streamer by Twitch username.
    
    Args:
        twitch_username: Twitch username
    
    Returns:
        Tracked streamer tuple or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT ts.id, ts.creator_id, ts.twitch_username, ts.display_name, ts.is_active,
                       ts.last_stream_check, ts.last_processed_stream_id, ts.processing_enabled,
                       ts.created_at, ts.updated_at, ts.created_by, ts.notes,
                       c.display_name as creator_display_name, c.profile_image_url,
                       u.username as created_by_username
                FROM stream_sniper.tracked_streamers ts
                JOIN stream_sniper.creator c ON ts.creator_id = c.id
                LEFT JOIN stream_sniper.users u ON ts.created_by = u.id
                WHERE ts.twitch_username = %s
                """,
                (twitch_username,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting tracked streamer by username: {e}")
        return None


@log_database_operation
def update_tracked_streamer_db(tracked_streamer_id: int, **kwargs) -> bool:
    """
    Update tracked streamer information.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    pool = get_pool()
    
    if not kwargs:
        return False
    
    # Build dynamic update query
    set_clauses = []
    params = []
    
    allowed_fields = [
        'twitch_username', 'display_name', 'is_active', 'last_stream_check',
        'last_processed_stream_id', 'processing_enabled', 'notes'
    ]
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = %s")
            params.append(value)
    
    if not set_clauses:
        return False
    
    # Always update the updated_at field
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(tracked_streamer_id)
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            query = f"""
                UPDATE stream_sniper.tracked_streamers 
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            cursor.execute(query, params)
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating tracked streamer: {e}")
        return False


@log_database_operation
def delete_tracked_streamer_db(tracked_streamer_id: int) -> bool:
    """
    Delete a tracked streamer from the database.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
    
    Returns:
        True if successful, False otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM stream_sniper.tracked_streamers WHERE id = %s",
                (tracked_streamer_id,)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting tracked streamer: {e}")
        return False


@log_database_operation
def count_tracked_streamers_db(
    is_active: Optional[bool] = None,
    processing_enabled: Optional[bool] = None
) -> int:
    """
    Count tracked streamers with optional filtering.
    
    Args:
        is_active: Filter by active status
        processing_enabled: Filter by processing enabled status
    
    Returns:
        Number of tracked streamers
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            where_clauses = []
            params = []
            
            if is_active is not None:
                where_clauses.append("is_active = %s")
                params.append(is_active)
            
            if processing_enabled is not None:
                where_clauses.append("processing_enabled = %s")
                params.append(processing_enabled)
            
            where_clause = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_clause}" if where_clause else ""
            
            query = f"SELECT COUNT(*) FROM stream_sniper.tracked_streamers {where_clause}"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error counting tracked streamers: {e}")
        return 0


@log_database_operation
def update_stream_check_time_db(tracked_streamer_id: int, check_time: datetime) -> bool:
    """
    Update the last stream check time for a tracked streamer.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
        check_time: Time of the check
    
    Returns:
        True if successful, False otherwise
    """
    return update_tracked_streamer_db(tracked_streamer_id, last_stream_check=check_time)


@log_database_operation
def update_last_processed_stream_db(tracked_streamer_id: int, stream_id: int) -> bool:
    """
    Update the last processed stream ID for a tracked streamer.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
        stream_id: ID of the last processed stream
    
    Returns:
        True if successful, False otherwise
    """
    return update_tracked_streamer_db(tracked_streamer_id, last_processed_stream_id=stream_id)


@log_database_operation
def select_active_tracked_streamers_db() -> List[Tuple]:
    """
    Select all active tracked streamers for monitoring.
    
    Returns:
        List of active tracked streamer tuples
    """
    return select_tracked_streamers_db(
        limit=1000,  # Large limit to get all active streamers
        offset=0,
        is_active=True,
        processing_enabled=True
    )


@log_database_operation
def streamer_exists_db(twitch_username: str) -> bool:
    """
    Check if a streamer is already being tracked.
    
    Args:
        twitch_username: Twitch username to check
    
    Returns:
        True if streamer exists, False otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM stream_sniper.tracked_streamers WHERE twitch_username = %s",
                (twitch_username,)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking streamer existence: {e}")
        return False