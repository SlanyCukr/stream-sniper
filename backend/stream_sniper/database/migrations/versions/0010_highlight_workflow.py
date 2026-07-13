"""Add clip workflow metadata and states to moment reviews.

Revision ID: 0010
Revises: 0009
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.moment_review
            DROP CONSTRAINT IF EXISTS moment_review_status_check;
        ALTER TABLE stream_sniper.moment_review
            ADD COLUMN IF NOT EXISTS clip_url text NULL,
            ADD COLUMN IF NOT EXISTS note text NULL,
            ADD CONSTRAINT moment_review_status_check
                CHECK (status IN ('bookmarked', 'rejected', 'clipped', 'published'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE stream_sniper.moment_review
        SET status = 'bookmarked'
        WHERE status IN ('clipped', 'published');
        ALTER TABLE stream_sniper.moment_review
            DROP CONSTRAINT IF EXISTS moment_review_status_check;
        ALTER TABLE stream_sniper.moment_review
            ADD CONSTRAINT moment_review_status_check
                CHECK (status IN ('bookmarked', 'rejected'));
        ALTER TABLE stream_sniper.moment_review
            DROP COLUMN IF EXISTS note,
            DROP COLUMN IF EXISTS clip_url;
        """
    )
