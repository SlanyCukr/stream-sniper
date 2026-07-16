"""Make processing-job enqueue idempotent for each streamer VOD.

Revision ID: 0016
Revises: 0015
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The old check-then-insert path could race. Preserve the most useful row
    # for any identity that already raced before enforcing the invariant.
    op.execute("""
WITH ranked AS (
    SELECT id,
           row_number() OVER (
               PARTITION BY tracked_streamer_id, twitch_vod_id
               ORDER BY CASE status
                            WHEN 'completed' THEN 1
                            WHEN 'in_progress' THEN 2
                            WHEN 'pending' THEN 3
                            ELSE 4
                        END,
                        updated_at DESC,
                        id DESC
           ) AS duplicate_rank
    FROM stream_sniper.processing_jobs
)
DELETE FROM stream_sniper.processing_jobs AS jobs
USING ranked
WHERE jobs.id = ranked.id
  AND ranked.duplicate_rank > 1;
""")
    op.create_unique_constraint(
        "processing_jobs_streamer_vod_uq",
        "processing_jobs",
        ["tracked_streamer_id", "twitch_vod_id"],
        schema="stream_sniper",
    )


def downgrade() -> None:
    op.drop_constraint(
        "processing_jobs_streamer_vod_uq",
        "processing_jobs",
        schema="stream_sniper",
        type_="unique",
    )
