"""message(stream_id, time, id) keyset index, built CONCURRENTLY

Backs the chronological message-replay endpoint (GET /stream/{id}/messages):
`WHERE stream_id = %s ... ORDER BY time ASC, id ASC` with a keyset cursor.
See 0002 for the CONCURRENTLY / offline / INVALID-index rationale.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _guard_online() -> None:
    if op.get_context().as_sql:
        raise RuntimeError(
            "0004 builds an index CONCURRENTLY and cannot be emitted offline (--sql); "
            "run online (stream-sniper-migrate / uv run alembic upgrade)."
        )


def upgrade() -> None:
    _guard_online()
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS message_stream_time_id_idx "
            "ON stream_sniper.message (stream_id, time, id)"
        )


def downgrade() -> None:
    _guard_online()
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS stream_sniper.message_stream_time_id_idx")
