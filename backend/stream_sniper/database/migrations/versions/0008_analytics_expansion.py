"""analytics expansion tables (emotes, phrases, moments, community overlap)

Adds the derived-analytics surface for the expansion features, all written by the
rollup engine (stream_sniper/analytics/) and read by the analytics API:
  * stream_time_bucket / stream_metrics gain sub_messages + emote_messages columns
    (NULLABLE by design: NULL = "not yet recomputed under 0008" so the UI can tell an
    unknown apart from a legitimate 0; the rollup always writes real values, possibly 0)
  * emote_dictionary   - BTTV seed + Twitch emotes learned at collection time
  * stream_emote_stats - per-stream emote usage (rollup: message text x dictionary)
  * stream_phrase_stats- per-stream recurring phrases (rollup: Python n-grams)
  * stream_moment      - persisted enriched moments (rollup: DELETE+INSERT per stream)
  * moment_review      - human curation state, SEPARATE so a recompute never wipes it
  * creator_audience / creator_overlap - community overlap (global recompute)

Ordinary transactional DDL (all CREATE ... IF NOT EXISTS / ADD COLUMN IF NOT EXISTS,
schema-qualified), so it runs online or offline (--sql). No new index on message.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stream_sniper.stream_time_bucket
            ADD COLUMN IF NOT EXISTS sub_messages   int NULL,
            ADD COLUMN IF NOT EXISTS emote_messages int NULL;

        ALTER TABLE stream_sniper.stream_metrics
            ADD COLUMN IF NOT EXISTS sub_messages   int NULL,
            ADD COLUMN IF NOT EXISTS emote_messages int NULL;

        CREATE TABLE IF NOT EXISTS stream_sniper.emote_dictionary (
            id          serial      PRIMARY KEY,
            name        text        NOT NULL,
            source      text        NOT NULL CHECK (source IN ('bttv', 'twitch')),
            provider_id text        NULL,
            first_seen  timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT emote_dictionary_uq UNIQUE (name, source)
        );
        CREATE INDEX IF NOT EXISTS emote_dictionary_name_idx
            ON stream_sniper.emote_dictionary (name);

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_emote_stats (
            stream_id     int NOT NULL,
            emote_id      int NOT NULL,
            usage_count   int NOT NULL,
            chatter_count int NOT NULL,
            CONSTRAINT stream_emote_stats_pk PRIMARY KEY (stream_id, emote_id),
            CONSTRAINT stream_emote_stats_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id),
            CONSTRAINT stream_emote_stats_emote_fk FOREIGN KEY (emote_id)
                REFERENCES stream_sniper.emote_dictionary (id)
        );
        CREATE INDEX IF NOT EXISTS stream_emote_stats_emote_idx
            ON stream_sniper.stream_emote_stats (emote_id);

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_phrase_stats (
            stream_id     int  NOT NULL,
            phrase        text NOT NULL,
            usage_count   int  NOT NULL,
            chatter_count int  NOT NULL,
            CONSTRAINT stream_phrase_stats_pk PRIMARY KEY (stream_id, phrase),
            CONSTRAINT stream_phrase_stats_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id)
        );

        CREATE TABLE IF NOT EXISTS stream_sniper.stream_moment (
            stream_id       int           NOT NULL,
            bucket_minute   timestamp     NOT NULL,
            offset_seconds  int           NOT NULL,
            message_count   int           NOT NULL,
            baseline        numeric(10,2) NOT NULL,
            ratio           numeric(10,2) NULL,
            unique_chatters int           NOT NULL,
            sub_share       numeric(5,4)  NULL
                CHECK (sub_share IS NULL OR (sub_share >= 0 AND sub_share <= 1)),
            emote_share     numeric(5,4)  NULL
                CHECK (emote_share IS NULL OR (emote_share >= 0 AND emote_share <= 1)),
            top_phrases     jsonb         NULL,
            sample_messages jsonb         NULL,
            computed_at     timestamptz   NOT NULL DEFAULT now(),
            CONSTRAINT stream_moment_pk PRIMARY KEY (stream_id, bucket_minute),
            CONSTRAINT stream_moment_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id)
        );

        CREATE TABLE IF NOT EXISTS stream_sniper.moment_review (
            stream_id     int         NOT NULL,
            bucket_minute timestamp   NOT NULL,
            status        text        NOT NULL CHECK (status IN ('bookmarked', 'rejected')),
            updated_at    timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT moment_review_pk PRIMARY KEY (stream_id, bucket_minute),
            CONSTRAINT moment_review_stream_fk FOREIGN KEY (stream_id)
                REFERENCES stream_sniper.stream (id)
        );
        CREATE INDEX IF NOT EXISTS moment_review_status_idx
            ON stream_sniper.moment_review (status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS stream_sniper.creator_audience (
            creator_id  int         PRIMARY KEY,
            chatters    int         NOT NULL,
            regulars    int         NOT NULL,
            computed_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT creator_audience_creator_fk FOREIGN KEY (creator_id)
                REFERENCES stream_sniper.creator (id)
        );

        CREATE TABLE IF NOT EXISTS stream_sniper.creator_overlap (
            creator_a       int         NOT NULL,
            creator_b       int         NOT NULL,
            shared_chatters int         NOT NULL,
            shared_regulars int         NOT NULL,
            computed_at     timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT creator_overlap_pk PRIMARY KEY (creator_a, creator_b),
            CONSTRAINT creator_overlap_order_ck CHECK (creator_a < creator_b),
            CONSTRAINT creator_overlap_a_fk FOREIGN KEY (creator_a)
                REFERENCES stream_sniper.creator (id),
            CONSTRAINT creator_overlap_b_fk FOREIGN KEY (creator_b)
                REFERENCES stream_sniper.creator (id)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS stream_sniper.creator_overlap;
        DROP TABLE IF EXISTS stream_sniper.creator_audience;
        DROP INDEX IF EXISTS stream_sniper.moment_review_status_idx;
        DROP TABLE IF EXISTS stream_sniper.moment_review;
        DROP TABLE IF EXISTS stream_sniper.stream_moment;
        DROP TABLE IF EXISTS stream_sniper.stream_phrase_stats;
        DROP INDEX IF EXISTS stream_sniper.stream_emote_stats_emote_idx;
        DROP TABLE IF EXISTS stream_sniper.stream_emote_stats;
        DROP INDEX IF EXISTS stream_sniper.emote_dictionary_name_idx;
        DROP TABLE IF EXISTS stream_sniper.emote_dictionary;

        ALTER TABLE stream_sniper.stream_metrics
            DROP COLUMN IF EXISTS emote_messages,
            DROP COLUMN IF EXISTS sub_messages;

        ALTER TABLE stream_sniper.stream_time_bucket
            DROP COLUMN IF EXISTS emote_messages,
            DROP COLUMN IF EXISTS sub_messages;
        """
    )
