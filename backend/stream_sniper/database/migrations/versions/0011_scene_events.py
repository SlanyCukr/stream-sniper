"""Add deterministic scene-event feed storage.

Revision ID: 0011
Revises: 0010
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stream_sniper.scene_event (
            id              bigserial   PRIMARY KEY,
            event_type      text        NOT NULL,
            occurred_at     timestamp   NOT NULL,
            creator_id      int         NULL REFERENCES stream_sniper.creator (id),
            stream_id       int         NULL REFERENCES stream_sniper.stream (id),
            message_text_id bigint      NULL REFERENCES stream_sniper.message_text (id),
            title           text        NOT NULL,
            summary         text        NOT NULL,
            metadata        jsonb       NOT NULL DEFAULT '{}'::jsonb,
            dedupe_key      text        NOT NULL UNIQUE,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS scene_event_occurred_idx
            ON stream_sniper.scene_event (occurred_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS scene_event_creator_idx
            ON stream_sniper.scene_event (creator_id, occurred_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stream_sniper.scene_event")
