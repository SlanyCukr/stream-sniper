"""message chat-metadata columns (is_subscriber, badges, emote_count)

Adds per-message metadata captured by the collector from the VOD chat feed.
All three columns are nullable with no DEFAULT, so this is a metadata-only
ADD COLUMN (no table rewrite) and old rows are simply left NULL.

Ordinary transactional DDL, so it runs online or offline (--sql).

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.message
            ADD COLUMN IF NOT EXISTS is_subscriber boolean  NULL,
            ADD COLUMN IF NOT EXISTS badges        text     NULL,
            ADD COLUMN IF NOT EXISTS emote_count   smallint NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.message
            DROP COLUMN IF EXISTS emote_count,
            DROP COLUMN IF EXISTS badges,
            DROP COLUMN IF EXISTS is_subscriber
        """
    )
