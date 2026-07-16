"""Add atomic processing-job lease ownership.

Revision ID: 0014
Revises: 0013
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE stream_sniper.processing_jobs
    RENAME COLUMN twitch_stream_id TO twitch_vod_id;
ALTER TABLE stream_sniper.tracked_streamers
    RENAME COLUMN last_processed_stream_id TO last_processed_vod_id;
ALTER TABLE stream_sniper.processing_jobs
    ADD COLUMN worker_token varchar(64),
    ADD COLUMN lease_expires_at timestamptz;
CREATE INDEX processing_jobs_dispatch_idx
    ON stream_sniper.processing_jobs (status, updated_at, id);
""")


def downgrade() -> None:
    op.execute("""
DROP INDEX IF EXISTS stream_sniper.processing_jobs_dispatch_idx;
ALTER TABLE stream_sniper.processing_jobs
    DROP COLUMN IF EXISTS lease_expires_at,
    DROP COLUMN IF EXISTS worker_token;
ALTER TABLE stream_sniper.processing_jobs
    RENAME COLUMN twitch_vod_id TO twitch_stream_id;
ALTER TABLE stream_sniper.tracked_streamers
    RENAME COLUMN last_processed_vod_id TO last_processed_stream_id;
""")
