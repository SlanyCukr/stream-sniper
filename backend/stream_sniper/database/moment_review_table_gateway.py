"""Database gateway for moment_review (human curation state).

Kept separate from stream_moment so a rollup recompute never wipes a curator's
bookmark/reject decisions. Last-writer-wins is accepted at this scale.
"""

from .decorators import with_cursor_connection


@with_cursor_connection
def upsert_moment_review_db(
    stream_id, bucket_minute, status, cursor, connection, *, clip_url=None, note=None
):
    """Set workflow status and optional clip metadata; returns the new updated_at."""
    cursor.execute(
        """
        INSERT INTO moment_review (stream_id, bucket_minute, status, clip_url, note, updated_at)
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (stream_id, bucket_minute) DO UPDATE SET
            status = EXCLUDED.status,
            clip_url = EXCLUDED.clip_url,
            note = EXCLUDED.note,
            updated_at = EXCLUDED.updated_at
        RETURNING TO_CHAR(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS')
        """,
        (stream_id, bucket_minute, status, clip_url, note),
    )
    updated_at = cursor.fetchone()[0]
    connection.commit()
    return updated_at


@with_cursor_connection
def delete_moment_review_db(stream_id, bucket_minute, cursor, connection):
    """Clear a moment's review status. Returns the number of rows removed."""
    cursor.execute(
        "DELETE FROM moment_review WHERE stream_id = %s AND bucket_minute = %s",
        (stream_id, bucket_minute),
    )
    deleted = cursor.rowcount
    connection.commit()
    return deleted
