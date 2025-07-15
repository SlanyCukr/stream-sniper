"""
Database gateway for processing_jobs table operations.
"""

from typing import Optional, List, Tuple
from datetime import datetime

from .connection_pool import get_pool
from .decorators import log_database_operation
from ..logging_config import get_logger

logger = get_logger(__name__)

# Job status constants
JOB_STATUS_PENDING = "pending"
JOB_STATUS_IN_PROGRESS = "in_progress"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


@log_database_operation
def insert_processing_job_db(
    tracked_streamer_id: int,
    twitch_stream_id: int,
    status: str = JOB_STATUS_PENDING
) -> Optional[int]:
    """
    Insert a new processing job into the database.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
        twitch_stream_id: Twitch stream ID to process
        status: Initial job status
    
    Returns:
        Processing job ID if successful, None otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO stream_sniper.processing_jobs 
                (tracked_streamer_id, twitch_stream_id, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (tracked_streamer_id, twitch_stream_id, status)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error inserting processing job: {e}")
        return None


@log_database_operation
def select_processing_jobs_db(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    tracked_streamer_id: Optional[int] = None
) -> List[Tuple]:
    """
    Select processing jobs with optional filtering.
    
    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        status: Filter by job status
        tracked_streamer_id: Filter by tracked streamer ID
    
    Returns:
        List of processing job tuples
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            where_clauses = []
            params = []
            
            if status is not None:
                where_clauses.append("pj.status = %s")
                params.append(status)
            
            if tracked_streamer_id is not None:
                where_clauses.append("pj.tracked_streamer_id = %s")
                params.append(tracked_streamer_id)
            
            where_clause = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_clause}" if where_clause else ""
            
            params.extend([limit, offset])
            
            query = f"""
                SELECT pj.id, pj.tracked_streamer_id, pj.twitch_stream_id, pj.status,
                       pj.started_at, pj.completed_at, pj.error_message, pj.retry_count,
                       pj.created_at, pj.updated_at,
                       ts.twitch_username, ts.display_name,
                       s.title as stream_title, s.start as stream_start
                FROM stream_sniper.processing_jobs pj
                JOIN stream_sniper.tracked_streamers ts ON pj.tracked_streamer_id = ts.id
                LEFT JOIN stream_sniper.stream s ON pj.twitch_stream_id = s.twitch_id
                {where_clause}
                ORDER BY pj.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error selecting processing jobs: {e}")
        return []


@log_database_operation
def select_processing_job_by_id_db(job_id: int) -> Optional[Tuple]:
    """
    Select a processing job by ID.
    
    Args:
        job_id: ID of the processing job
    
    Returns:
        Processing job tuple or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT pj.id, pj.tracked_streamer_id, pj.twitch_stream_id, pj.status,
                       pj.started_at, pj.completed_at, pj.error_message, pj.retry_count,
                       pj.created_at, pj.updated_at,
                       ts.twitch_username, ts.display_name,
                       s.title as stream_title, s.start as stream_start
                FROM stream_sniper.processing_jobs pj
                JOIN stream_sniper.tracked_streamers ts ON pj.tracked_streamer_id = ts.id
                LEFT JOIN stream_sniper.stream s ON pj.twitch_stream_id = s.twitch_id
                WHERE pj.id = %s
                """,
                (job_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting processing job by ID: {e}")
        return None


@log_database_operation
def update_processing_job_db(job_id: int, **kwargs) -> bool:
    """
    Update processing job information.
    
    Args:
        job_id: ID of the processing job
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
        'status', 'started_at', 'completed_at', 'error_message', 'retry_count'
    ]
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = %s")
            params.append(value)
    
    if not set_clauses:
        return False
    
    # Always update the updated_at field
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(job_id)
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            query = f"""
                UPDATE stream_sniper.processing_jobs 
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            cursor.execute(query, params)
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating processing job: {e}")
        return False


@log_database_operation
def delete_processing_job_db(job_id: int) -> bool:
    """
    Delete a processing job from the database.
    
    Args:
        job_id: ID of the processing job
    
    Returns:
        True if successful, False otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM stream_sniper.processing_jobs WHERE id = %s",
                (job_id,)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting processing job: {e}")
        return False


@log_database_operation
def count_processing_jobs_db(
    status: Optional[str] = None,
    tracked_streamer_id: Optional[int] = None
) -> int:
    """
    Count processing jobs with optional filtering.
    
    Args:
        status: Filter by job status
        tracked_streamer_id: Filter by tracked streamer ID
    
    Returns:
        Number of processing jobs
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            where_clauses = []
            params = []
            
            if status is not None:
                where_clauses.append("status = %s")
                params.append(status)
            
            if tracked_streamer_id is not None:
                where_clauses.append("tracked_streamer_id = %s")
                params.append(tracked_streamer_id)
            
            where_clause = " AND ".join(where_clauses)
            where_clause = f"WHERE {where_clause}" if where_clause else ""
            
            query = f"SELECT COUNT(*) FROM stream_sniper.processing_jobs {where_clause}"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error counting processing jobs: {e}")
        return 0


@log_database_operation
def start_processing_job_db(job_id: int) -> bool:
    """
    Mark a processing job as started.
    
    Args:
        job_id: ID of the processing job
    
    Returns:
        True if successful, False otherwise
    """
    return update_processing_job_db(
        job_id,
        status=JOB_STATUS_IN_PROGRESS,
        started_at=datetime.now()
    )


@log_database_operation
def complete_processing_job_db(job_id: int) -> bool:
    """
    Mark a processing job as completed.
    
    Args:
        job_id: ID of the processing job
    
    Returns:
        True if successful, False otherwise
    """
    return update_processing_job_db(
        job_id,
        status=JOB_STATUS_COMPLETED,
        completed_at=datetime.now()
    )


@log_database_operation
def fail_processing_job_db(job_id: int, error_message: str, increment_retry: bool = True) -> bool:
    """
    Mark a processing job as failed.
    
    Args:
        job_id: ID of the processing job
        error_message: Error message to store
        increment_retry: Whether to increment retry count
    
    Returns:
        True if successful, False otherwise
    """
    update_data = {
        'status': JOB_STATUS_FAILED,
        'error_message': error_message,
        'completed_at': datetime.now()
    }
    
    if increment_retry:
        # Get current retry count and increment
        job = select_processing_job_by_id_db(job_id)
        if job:
            current_retry_count = job[7]  # retry_count is at index 7
            update_data['retry_count'] = current_retry_count + 1
    
    return update_processing_job_db(job_id, **update_data)


@log_database_operation
def select_pending_jobs_db(limit: int = 10) -> List[Tuple]:
    """
    Select pending processing jobs for processing.
    
    Args:
        limit: Maximum number of jobs to return
    
    Returns:
        List of pending processing job tuples
    """
    return select_processing_jobs_db(
        limit=limit,
        offset=0,
        status=JOB_STATUS_PENDING
    )


@log_database_operation
def select_failed_jobs_for_retry_db(max_retries: int = 3, limit: int = 10) -> List[Tuple]:
    """
    Select failed processing jobs that can be retried.
    
    Args:
        max_retries: Maximum number of retries allowed
        limit: Maximum number of jobs to return
    
    Returns:
        List of failed processing job tuples that can be retried
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT pj.id, pj.tracked_streamer_id, pj.twitch_stream_id, pj.status,
                       pj.started_at, pj.completed_at, pj.error_message, pj.retry_count,
                       pj.created_at, pj.updated_at,
                       ts.twitch_username, ts.display_name,
                       s.title as stream_title, s.start as stream_start
                FROM stream_sniper.processing_jobs pj
                JOIN stream_sniper.tracked_streamers ts ON pj.tracked_streamer_id = ts.id
                LEFT JOIN stream_sniper.stream s ON pj.twitch_stream_id = s.twitch_id
                WHERE pj.status = %s AND pj.retry_count < %s
                ORDER BY pj.updated_at ASC
                LIMIT %s
                """,
                (JOB_STATUS_FAILED, max_retries, limit)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error selecting failed jobs for retry: {e}")
        return []


@log_database_operation
def get_processing_stats_db() -> dict:
    """
    Get processing job statistics.
    
    Returns:
        Dictionary with processing statistics
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    status,
                    COUNT(*) as count
                FROM stream_sniper.processing_jobs
                GROUP BY status
                """
            )
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM stream_sniper.processing_jobs")
            total_result = cursor.fetchone()
            stats['total'] = total_result[0] if total_result else 0
            
            # Get recent activity (last 24 hours)
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM stream_sniper.processing_jobs 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
            )
            recent_result = cursor.fetchone()
            stats['recent_24h'] = recent_result[0] if recent_result else 0
            
            return stats
    except Exception as e:
        logger.error(f"Error getting processing stats: {e}")
        return {}


@log_database_operation
def job_exists_db(tracked_streamer_id: int, twitch_stream_id: int) -> bool:
    """
    Check if a processing job already exists for a stream.
    
    Args:
        tracked_streamer_id: ID of the tracked streamer
        twitch_stream_id: Twitch stream ID
    
    Returns:
        True if job exists, False otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM stream_sniper.processing_jobs 
                WHERE tracked_streamer_id = %s AND twitch_stream_id = %s
                """,
                (tracked_streamer_id, twitch_stream_id)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking job existence: {e}")
        return False