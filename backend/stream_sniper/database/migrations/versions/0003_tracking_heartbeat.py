"""tracking heartbeat table

Cross-process liveness for the tracking service. The tracking process (a separate
container from the API) upserts a single row here roughly every 15s; the API reads
it with an age check to report monitoring health on the admin dashboard. Both
processes already connect to Postgres, so this replaces the earlier Redis-based
heartbeat once Redis was removed from the stack.

Ordinary transactional DDL (no CONCURRENTLY), so it runs online or offline (--sql).

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stream_sniper.tracking_heartbeat
        (
            component  varchar(64)  PRIMARY KEY,
            status     jsonb        NOT NULL,
            updated_at timestamptz  NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stream_sniper.tracking_heartbeat")
