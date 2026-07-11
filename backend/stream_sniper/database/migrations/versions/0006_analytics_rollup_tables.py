"""analytics rollup tables + viewer-sample table

Creates the derived-analytics tables written by the rollup engine
(stream_sniper/analytics/) and read by the analytics API:
  * stream_viewer_sample  - live viewer-count snapshots (tracking service)
  * stream_time_bucket    - per-minute message/unique-chatter buckets
  * stream_chatter_stats  - per-stream per-chatter aggregates
  * stream_metrics        - one summary row per stream
  * creator_chatter_stats - per-creator per-chatter "regulars" aggregates
plus a supporting stream(creator_id, start DESC) index for the trends series.

Ordinary transactional DDL (all CREATE ... IF NOT EXISTS, schema-qualified), so
it runs online or offline (--sql).

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stream_sniper.stream_viewer_sample (
            id                       bigserial   PRIMARY KEY,
            tracked_streamer_id      int         NOT NULL,
            twitch_stream_session_id bigint      NOT NULL,
            sampled_at               timestamptz NOT NULL,
            viewer_count             int         NOT NULL,
            title                    text        NULL,
            session_started_at       timestamptz NULL,
            CONSTRAINT stream_viewer_sample_streamer_fk FOREIGN KEY (tracked_streamer_id)
                REFERENCES stream_sniper.tracked_streamers (id),
            CONSTRAINT stream_viewer_sample_uq
                UNIQUE (tracked_streamer_id, twitch_stream_session_id, sampled_at)
        );
        CREATE INDEX IF NOT EXISTS stream_viewer_sample_session_idx
            ON stream_sniper.stream_viewer_sample (tracked_streamer_id, twitch_stream_session_id, sampled_at);

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_time_bucket (
            stream_id       int       NOT NULL,
            bucket_minute   timestamp NOT NULL,
            message_count   int       NOT NULL,
            unique_chatters int       NOT NULL,
            CONSTRAINT stream_time_bucket_pk PRIMARY KEY (stream_id, bucket_minute),
            CONSTRAINT stream_time_bucket_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id)
        );

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_chatter_stats (
            stream_id          int       NOT NULL,
            chatter_id         int       NOT NULL,
            message_count      int       NOT NULL,
            first_message_time timestamp NULL,
            last_message_time  timestamp NULL,
            CONSTRAINT stream_chatter_stats_pk PRIMARY KEY (stream_id, chatter_id),
            CONSTRAINT stream_chatter_stats_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id),
            CONSTRAINT stream_chatter_stats_chatter_fk FOREIGN KEY (chatter_id)
                REFERENCES stream_sniper.chatter (id)
        );
        CREATE INDEX IF NOT EXISTS stream_chatter_stats_chatter_idx
            ON stream_sniper.stream_chatter_stats (chatter_id);

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_metrics (
            stream_id            int           PRIMARY KEY,
            total_messages       int           NOT NULL,
            unique_chatters      int           NOT NULL,
            duration_seconds     int           NULL,
            messages_per_minute  numeric(10,2) NULL,
            peak_messages        int           NOT NULL DEFAULT 0,
            peak_bucket_minute   timestamp     NULL,
            new_chatters         int           NOT NULL DEFAULT 0,
            returning_chatters   int           NOT NULL DEFAULT 0,
            computed_at          timestamptz   NOT NULL DEFAULT now(),
            CONSTRAINT stream_metrics_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id)
        );

        CREATE TABLE IF NOT EXISTS stream_sniper.creator_chatter_stats (
            creator_id           int         NOT NULL,
            chatter_id           int         NOT NULL,
            streams_attended     int         NOT NULL,
            total_messages       bigint      NOT NULL,
            first_seen_stream_id int         NULL,
            first_seen_at        timestamp   NULL,
            last_seen_stream_id  int         NULL,
            last_seen_at         timestamp   NULL,
            updated_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT creator_chatter_stats_pk PRIMARY KEY (creator_id, chatter_id),
            CONSTRAINT creator_chatter_stats_creator_fk FOREIGN KEY (creator_id)
                REFERENCES stream_sniper.creator (id),
            CONSTRAINT creator_chatter_stats_chatter_fk FOREIGN KEY (chatter_id)
                REFERENCES stream_sniper.chatter (id)
        );
        CREATE INDEX IF NOT EXISTS creator_chatter_stats_attendance_idx
            ON stream_sniper.creator_chatter_stats (creator_id, streams_attended DESC);
        CREATE INDEX IF NOT EXISTS creator_chatter_stats_recency_idx
            ON stream_sniper.creator_chatter_stats (creator_id, last_seen_at DESC);

        CREATE INDEX IF NOT EXISTS stream_creator_start_idx
            ON stream_sniper.stream (creator_id, start DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS stream_sniper.stream_creator_start_idx;
        DROP TABLE IF EXISTS stream_sniper.creator_chatter_stats;
        DROP TABLE IF EXISTS stream_sniper.stream_metrics;
        DROP TABLE IF EXISTS stream_sniper.stream_chatter_stats;
        DROP TABLE IF EXISTS stream_sniper.stream_time_bucket;
        DROP TABLE IF EXISTS stream_sniper.stream_viewer_sample;
        """
    )
