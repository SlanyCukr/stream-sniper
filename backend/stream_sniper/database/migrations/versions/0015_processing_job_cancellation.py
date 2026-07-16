"""Add durable processing-job cancellation requests.

Revision ID: 0015
Revises: 0014
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE stream_sniper.processing_jobs
    ADD COLUMN cancellation_requested_at timestamptz;
""")


def downgrade() -> None:
    op.execute("""
ALTER TABLE stream_sniper.processing_jobs
    DROP COLUMN IF EXISTS cancellation_requested_at;
""")
