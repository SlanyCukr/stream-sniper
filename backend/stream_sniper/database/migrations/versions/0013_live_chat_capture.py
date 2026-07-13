"""Add live chat session identity and message deduplication.

Revision ID: 0013
Revises: 0012
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.stream
            ADD COLUMN IF NOT EXISTS twitch_stream_session_id bigint NULL,
            ADD COLUMN IF NOT EXISTS live_capture_complete boolean NOT NULL DEFAULT false;
        CREATE UNIQUE INDEX IF NOT EXISTS stream_twitch_session_uq
            ON stream_sniper.stream (twitch_stream_session_id)
            WHERE twitch_stream_session_id IS NOT NULL;

        ALTER TABLE stream_sniper.message
            ADD COLUMN IF NOT EXISTS source_message_id text NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS message_source_message_id_uq
            ON stream_sniper.message (source_message_id)
            WHERE source_message_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS stream_sniper.message_source_message_id_uq;
        ALTER TABLE stream_sniper.message DROP COLUMN IF EXISTS source_message_id;
        DROP INDEX IF EXISTS stream_sniper.stream_twitch_session_uq;
        ALTER TABLE stream_sniper.stream
            DROP COLUMN IF EXISTS live_capture_complete,
            DROP COLUMN IF EXISTS twitch_stream_session_id;
        """
    )
