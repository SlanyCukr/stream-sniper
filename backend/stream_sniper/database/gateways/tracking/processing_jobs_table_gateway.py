"""
Database gateway for processing_jobs table operations.
"""

from dataclasses import dataclass

from stream_sniper.application.tracking.models import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_IN_PROGRESS,
    JOB_STATUS_PENDING,
    JobStatus,
    ProcessingJob,
)

from ...core.decorators import read_cursor, write_cursor


@dataclass(frozen=True)
class ClaimedProcessingJob:
    job: ProcessingJob
    worker_token: str


def _build_processing_job_filter(
    status: JobStatus | None,
    tracked_streamer_id: int | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if status is not None:
        clauses.append("pj.status = %s")
        params.append(status)
    if tracked_streamer_id is not None:
        clauses.append("pj.tracked_streamer_id = %s")
        params.append(tracked_streamer_id)
    return (f"WHERE {' AND '.join(clauses)}" if clauses else "", params)


def enqueue_processing_job_db(
    tracked_streamer_id: int, twitch_vod_id: int, status: JobStatus = JOB_STATUS_PENDING
) -> int | None:
    """Atomically enqueue a streamer/VOD identity, returning ``None`` if it already exists."""

    with write_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO stream_sniper.processing_jobs
            (tracked_streamer_id, twitch_vod_id, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (tracked_streamer_id, twitch_vod_id) DO NOTHING
            RETURNING id
            """,
            (tracked_streamer_id, twitch_vod_id, status),
        )
        result = cursor.fetchone()
        return result[0] if result else None


def select_processing_jobs_db(
    limit: int = 100,
    offset: int = 0,
    status: JobStatus | None = None,
    tracked_streamer_id: int | None = None,
) -> list[ProcessingJob]:
    """Select a filtered processing-job page, newest first."""

    with read_cursor() as cursor:
        where_clause, params = _build_processing_job_filter(status, tracked_streamer_id)
        params.extend([limit, offset])

        query = f"""
            SELECT pj.id, pj.tracked_streamer_id, pj.twitch_vod_id, pj.status,
                   pj.started_at, pj.completed_at, pj.error_message, pj.retry_count,
                   pj.created_at, pj.updated_at,
                   ts.twitch_username, ts.display_name,
                   s.title as stream_title, s.start as stream_start
            FROM stream_sniper.processing_jobs pj
            JOIN stream_sniper.tracked_streamers ts ON pj.tracked_streamer_id = ts.id
            LEFT JOIN stream_sniper.stream s ON pj.twitch_vod_id = s.twitch_id
            {where_clause}
            ORDER BY pj.created_at DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, params)
        return [ProcessingJob(*row) for row in cursor.fetchall()]


def select_processing_job_by_id_db(job_id: int) -> ProcessingJob | None:
    """Select one processing job with streamer and archived-stream context."""

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT pj.id, pj.tracked_streamer_id, pj.twitch_vod_id, pj.status,
                   pj.started_at, pj.completed_at, pj.error_message, pj.retry_count,
                   pj.created_at, pj.updated_at,
                   ts.twitch_username, ts.display_name,
                   s.title as stream_title, s.start as stream_start
            FROM stream_sniper.processing_jobs pj
            JOIN stream_sniper.tracked_streamers ts ON pj.tracked_streamer_id = ts.id
            LEFT JOIN stream_sniper.stream s ON pj.twitch_vod_id = s.twitch_id
            WHERE pj.id = %s
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        return ProcessingJob(*row) if row else None


def count_processing_jobs_db(status: JobStatus | None = None, tracked_streamer_id: int | None = None) -> int:
    """Count processing jobs using the same filters as the page query."""

    with read_cursor() as cursor:
        where_clause, params = _build_processing_job_filter(status, tracked_streamer_id)
        query = f"SELECT COUNT(*) FROM stream_sniper.processing_jobs pj {where_clause}"

        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else 0


def complete_processing_job_and_advance_streamer_db(job_id: int, worker_token: str) -> bool:
    """Complete a leased job and advance its streamer in one SQL transition."""
    with write_cursor() as cursor:
        cursor.execute(
            """WITH completed AS (
                   UPDATE stream_sniper.processing_jobs
                   SET status = %s, completed_at = CURRENT_TIMESTAMP,
                       worker_token = NULL, lease_expires_at = NULL,
                       cancellation_requested_at = NULL,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s AND status = %s AND worker_token = %s
                     AND cancellation_requested_at IS NULL
                   RETURNING tracked_streamer_id, twitch_vod_id
               )
               UPDATE stream_sniper.tracked_streamers AS streamer
               SET last_processed_vod_id = completed.twitch_vod_id,
                   updated_at = CURRENT_TIMESTAMP
               FROM completed
               WHERE streamer.id = completed.tracked_streamer_id""",
            (JOB_STATUS_COMPLETED, job_id, JOB_STATUS_IN_PROGRESS, worker_token),
        )
        return bool(cursor.rowcount == 1)


def fail_processing_job_db(
    job_id: int,
    error_message: str,
    *,
    worker_token: str,
    increment_retry: bool = True,
) -> bool:
    """Fail the job only while ``worker_token`` still owns its active lease."""
    retry_increment = 1 if increment_retry else 0
    with write_cursor() as cursor:
        cursor.execute(
            """UPDATE stream_sniper.processing_jobs
               SET status = %s, error_message = %s,
                   completed_at = CURRENT_TIMESTAMP,
                   retry_count = retry_count + %s,
                   worker_token = NULL, lease_expires_at = NULL,
                   cancellation_requested_at = NULL,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND status = %s AND worker_token = %s""",
            (
                JOB_STATUS_FAILED,
                error_message,
                retry_increment,
                job_id,
                JOB_STATUS_IN_PROGRESS,
                worker_token,
            ),
        )
        return bool(cursor.rowcount == 1)


def cancel_processing_job_db(job_id: int, *, worker_token: str, terminal_retry_count: int) -> bool:
    """Record cancellation after the synchronous worker has stopped and prevent auto-retry."""
    with write_cursor() as cursor:
        cursor.execute(
            """UPDATE stream_sniper.processing_jobs
               SET status = %s, error_message = 'Job was cancelled',
                   completed_at = CURRENT_TIMESTAMP,
                   retry_count = GREATEST(retry_count, %s),
                   worker_token = NULL, lease_expires_at = NULL,
                   cancellation_requested_at = NULL,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND status = %s AND worker_token = %s""",
            (JOB_STATUS_FAILED, terminal_retry_count, job_id, JOB_STATUS_IN_PROGRESS, worker_token),
        )
        return bool(cursor.rowcount == 1)


def retry_failed_processing_job_db(job_id: int) -> bool:
    """Atomically return one failed job to pending state."""
    with write_cursor() as cursor:
        cursor.execute(
            """UPDATE stream_sniper.processing_jobs
               SET status = %s, started_at = NULL, completed_at = NULL,
                   error_message = NULL, worker_token = NULL,
                   lease_expires_at = NULL, cancellation_requested_at = NULL,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND status = %s""",
            (JOB_STATUS_PENDING, job_id, JOB_STATUS_FAILED),
        )
        return bool(cursor.rowcount == 1)


def request_processing_job_cancellation_db(job_id: int) -> bool:
    """Persist cancellation for a pending or leased in-progress job."""
    with write_cursor() as cursor:
        cursor.execute(
            """UPDATE stream_sniper.processing_jobs
               SET cancellation_requested_at = CURRENT_TIMESTAMP,
                   status = CASE WHEN status = %s THEN %s ELSE status END,
                   completed_at = CASE WHEN status = %s THEN CURRENT_TIMESTAMP ELSE completed_at END,
                   error_message = CASE WHEN status = %s THEN 'Cancelled before processing' ELSE error_message END,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND status IN (%s, %s)""",
            (
                JOB_STATUS_PENDING,
                JOB_STATUS_FAILED,
                JOB_STATUS_PENDING,
                JOB_STATUS_PENDING,
                job_id,
                JOB_STATUS_PENDING,
                JOB_STATUS_IN_PROGRESS,
            ),
        )
        return bool(cursor.rowcount == 1)


def processing_job_cancellation_requested_db(job_id: int, worker_token: str) -> bool:
    """Return whether the matching active lease has a durable cancellation request."""
    with read_cursor() as cursor:
        cursor.execute(
            """SELECT 1 FROM stream_sniper.processing_jobs
               WHERE id = %s AND status = %s AND worker_token = %s
                 AND cancellation_requested_at IS NOT NULL""",
            (job_id, JOB_STATUS_IN_PROGRESS, worker_token),
        )
        return cursor.fetchone() is not None


def claim_processing_jobs_db(
    *, limit: int, max_retries: int, worker_token: str, lease_seconds: int = 1800
) -> list[ClaimedProcessingJob]:
    """Recover expired leases and atomically claim the fairest runnable jobs."""
    with write_cursor() as cursor:
        cursor.execute(
            """
            WITH recovered AS (
                UPDATE stream_sniper.processing_jobs
                SET status = %(failed)s,
                    error_message = 'Processing lease expired',
                    retry_count = retry_count + 1,
                    worker_token = NULL,
                    lease_expires_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = %(in_progress)s
                  AND lease_expires_at < CURRENT_TIMESTAMP
            ), candidates AS (
                SELECT id
                FROM stream_sniper.processing_jobs
                WHERE status = %(pending)s
                  AND cancellation_requested_at IS NULL
                   OR (status = %(failed)s AND retry_count < %(max_retries)s
                       AND cancellation_requested_at IS NULL)
                ORDER BY updated_at ASC, id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT %(limit)s
            ), claimed AS (
                UPDATE stream_sniper.processing_jobs pj
                SET status = %(in_progress)s,
                    started_at = CURRENT_TIMESTAMP,
                    completed_at = NULL,
                    error_message = NULL,
                    worker_token = %(worker_token)s,
                    lease_expires_at = CURRENT_TIMESTAMP
                        + make_interval(secs => %(lease_seconds)s),
                    cancellation_requested_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                FROM candidates
                WHERE pj.id = candidates.id
                RETURNING pj.*
            )
            SELECT c.id, c.tracked_streamer_id, c.twitch_vod_id, c.status,
                   c.started_at, c.completed_at, c.error_message, c.retry_count,
                   c.created_at, c.updated_at,
                   ts.twitch_username, ts.display_name,
                   s.title, s.start, c.worker_token
            FROM claimed c
            JOIN stream_sniper.tracked_streamers ts ON c.tracked_streamer_id = ts.id
            LEFT JOIN stream_sniper.stream s ON c.twitch_vod_id = s.twitch_id
            ORDER BY c.updated_at ASC, c.id ASC
            """,
            {
                "pending": JOB_STATUS_PENDING,
                "failed": JOB_STATUS_FAILED,
                "in_progress": JOB_STATUS_IN_PROGRESS,
                "max_retries": max_retries,
                "limit": limit,
                "worker_token": worker_token,
                "lease_seconds": lease_seconds,
            },
        )
        return [ClaimedProcessingJob(job=ProcessingJob(*row[:14]), worker_token=row[14]) for row in cursor.fetchall()]


def select_processing_stats_db() -> dict[str, int]:
    """Return job counts by status, total, and rows created in the last 24 hours."""

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                status,
                COUNT(*) as count
            FROM stream_sniper.processing_jobs
            GROUP BY status
            """
        )

        stats: dict[str, int] = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]

        cursor.execute("SELECT COUNT(*) FROM stream_sniper.processing_jobs")
        total_result = cursor.fetchone()
        stats["total"] = total_result[0] if total_result else 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stream_sniper.processing_jobs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
        )
        recent_result = cursor.fetchone()
        stats["recent_24h"] = recent_result[0] if recent_result else 0

        return stats
