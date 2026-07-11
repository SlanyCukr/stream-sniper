"""message(chatter_id, time DESC, id DESC) keyset index, built CONCURRENTLY

Backs per-chatter recent-message reads (chatter_id filter, newest-first).
See 0002 for the CONCURRENTLY / offline / INVALID-index rationale.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _guard_online() -> None:
    if op.get_context().as_sql:
        raise RuntimeError(
            "0005 builds an index CONCURRENTLY and cannot be emitted offline (--sql); "
            "run online (stream-sniper-migrate / uv run alembic upgrade)."
        )


def upgrade() -> None:
    _guard_online()
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS message_chatter_time_id_idx "
            "ON stream_sniper.message (chatter_id, time DESC, id DESC)"
        )


def downgrade() -> None:
    _guard_online()
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS stream_sniper.message_chatter_time_id_idx")
