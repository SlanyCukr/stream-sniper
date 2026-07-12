"""scene expansion: bot flag, copypasta stats, viewer sample index

Adds the scene-expansion surface (bot detection, copypasta library, live-now):
  * chatter gains is_bot / bot_reason (NULLABLE by design: NULL = "not yet
    classified" so the UI can tell unknown apart from a confirmed human; the
    stream-sniper-classify-bots pass writes TRUE + a reason string)
  * stream_copypasta_stats - per-stream copypasta usage rollup (written by the
    rollup engine, aggregated scene-wide by the /scene/copypastas endpoint)
  * stream_viewer_sample (sampled_at DESC) index - supports the /scene/live
    freshness scan and the leaderboard's windowed peak-viewers aggregate.
    Plain (non-CONCURRENT) index: the table is days old and small, and this
    revision must stay transactional/offline-capable.

Ordinary transactional DDL (all IF NOT EXISTS, schema-qualified), so it runs
online or offline (--sql).

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.chatter
            ADD COLUMN IF NOT EXISTS is_bot     boolean NULL,
            ADD COLUMN IF NOT EXISTS bot_reason text    NULL;

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_copypasta_stats (
            stream_id       int       NOT NULL,
            message_text_id bigint    NOT NULL,
            usage_count     int       NOT NULL,
            chatter_count   int       NOT NULL,
            first_seen      timestamp NULL,
            CONSTRAINT stream_copypasta_stats_pk PRIMARY KEY (stream_id, message_text_id),
            CONSTRAINT stream_copypasta_stats_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id),
            CONSTRAINT stream_copypasta_stats_text_fk FOREIGN KEY (message_text_id)
                REFERENCES stream_sniper.message_text (id)
        );

        CREATE INDEX IF NOT EXISTS stream_viewer_sample_sampled_at_idx
            ON stream_sniper.stream_viewer_sample (sampled_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS stream_sniper.stream_viewer_sample_sampled_at_idx;

        DROP TABLE IF EXISTS stream_sniper.stream_copypasta_stats;

        ALTER TABLE stream_sniper.chatter
            DROP COLUMN IF EXISTS bot_reason,
            DROP COLUMN IF EXISTS is_bot;
        """
    )
