"""Capture title/category/tag context during live tracking.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stream_sniper.stream_context_sample (
            id                       bigserial   PRIMARY KEY,
            tracked_streamer_id      int         NOT NULL
                REFERENCES stream_sniper.tracked_streamers (id),
            twitch_stream_session_id bigint      NOT NULL,
            sampled_at               timestamptz NOT NULL,
            session_started_at       timestamptz NULL,
            title                    text        NULL,
            category_id              text        NULL,
            category_name            text        NULL,
            language                 text        NULL,
            tags                     jsonb       NULL,
            is_mature                boolean     NULL,
            CONSTRAINT stream_context_sample_uq
                UNIQUE (tracked_streamer_id, twitch_stream_session_id, sampled_at)
        );
        CREATE INDEX IF NOT EXISTS stream_context_sample_session_idx
            ON stream_sniper.stream_context_sample
               (tracked_streamer_id, twitch_stream_session_id, sampled_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stream_sniper.stream_context_sample")
