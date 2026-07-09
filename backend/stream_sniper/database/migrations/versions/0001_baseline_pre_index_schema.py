"""baseline pre-index schema

Reproduces the pre-Alembic production schema (8 tables + inline PK/UNIQUE/FK/CHECK
constraints + their implicit constraint-backed indexes and serial sequences).
Reproduces the same TABLE/CONSTRAINT set as create_table.sql, plus a
`CREATE SCHEMA IF NOT EXISTS stream_sniper` prologue that create_table.sql never
contained (schema creation was always a manual prerequisite there; it now lives in
env.py for the online path and here for offline/self-contained runs). Deliberately
EXCLUDES chatter_nick_lower_prefix_idx — that is revision 0002. Type/FK quirks are
preserved on purpose (message.tagged_chatter_id has no FK; message.message_text_id
is bigint referencing message_text.id serial).

On a fresh DB: this runs (schema already ensured by env.py; CREATE TABLEs execute).
On prod: this is `stamp`-ed, never run (tables already exist).

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE SCHEMA IF NOT EXISTS stream_sniper;

CREATE TABLE stream_sniper.chatter
(
    id   serial       PRIMARY KEY,
    nick varchar(255) NOT NULL,
    CONSTRAINT chatter_name_uindex UNIQUE (nick)
);

CREATE TABLE stream_sniper.creator
(
    id                serial       PRIMARY KEY,
    nick              varchar(255) NOT NULL,
    display_name      varchar(255) NOT NULL,
    profile_image_url varchar(255) NOT NULL,
    twitch_id         bigint,
    CONSTRAINT creator_nick_uindex UNIQUE (nick)
);

CREATE TABLE stream_sniper.stream
(
    id            serial        PRIMARY KEY,
    twitch_id     bigint        NOT NULL,
    title         varchar(255)  NOT NULL,
    start         timestamp     NOT NULL,
    "end"         timestamp     NULL,
    thumbnail_url varchar(255)  NULL,
    message_count int DEFAULT 0 NOT NULL,
    creator_id    int           NULL,
    CONSTRAINT stream__twitch_id_uindex UNIQUE (twitch_id),
    CONSTRAINT stream__creator_id_fk
        FOREIGN KEY (creator_id) REFERENCES stream_sniper.creator (id)
);

CREATE TABLE stream_sniper.message_text
(
    id   serial PRIMARY KEY,
    text text   NOT NULL,
    CONSTRAINT text_uq UNIQUE (text)
);

CREATE TABLE stream_sniper.message
(
    id                serial PRIMARY KEY,
    chatter_id        int                                 NULL,
    tagged_chatter_id int                                 NULL,
    stream_id         int                                 NULL,
    message_text_id   bigint                              NOT NULL,
    time              timestamp DEFAULT current_timestamp NULL,
    CONSTRAINT message_chatter_id_fk
        FOREIGN KEY (chatter_id) REFERENCES stream_sniper.chatter (id),
    CONSTRAINT message_stream_id_fk
        FOREIGN KEY (stream_id) REFERENCES stream_sniper.stream (id),
    CONSTRAINT message_text_id_fk
        FOREIGN KEY (message_text_id) REFERENCES stream_sniper.message_text (id)
);

CREATE TABLE stream_sniper.users
(
    id            serial       PRIMARY KEY,
    username      varchar(255) NOT NULL,
    email         varchar(255) NOT NULL,
    password_hash varchar(255) NOT NULL,
    role          varchar(50)  NOT NULL DEFAULT 'user',
    is_active     boolean      NOT NULL DEFAULT true,
    created_at    timestamp    NOT NULL DEFAULT current_timestamp,
    updated_at    timestamp    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT users_username_uindex UNIQUE (username),
    CONSTRAINT users_email_uindex UNIQUE (email)
);

CREATE TABLE stream_sniper.tracked_streamers
(
    id                       serial       PRIMARY KEY,
    creator_id               int          NOT NULL,
    twitch_username          varchar(255) NOT NULL,
    display_name             varchar(255) NOT NULL,
    is_active                boolean      NOT NULL DEFAULT true,
    last_stream_check        timestamp    NULL,
    last_processed_stream_id bigint       NULL,
    processing_enabled       boolean      NOT NULL DEFAULT true,
    created_at               timestamp    NOT NULL DEFAULT current_timestamp,
    updated_at               timestamp    NOT NULL DEFAULT current_timestamp,
    created_by               int          NULL,
    notes                    text         NULL,
    CONSTRAINT tracked_streamers_creator_id_fk
        FOREIGN KEY (creator_id) REFERENCES stream_sniper.creator (id),
    CONSTRAINT tracked_streamers_created_by_fk
        FOREIGN KEY (created_by) REFERENCES stream_sniper.users (id),
    CONSTRAINT tracked_streamers_creator_id_uindex UNIQUE (creator_id),
    CONSTRAINT tracked_streamers_twitch_username_uindex UNIQUE (twitch_username)
);

CREATE TABLE stream_sniper.processing_jobs
(
    id                  serial       PRIMARY KEY,
    tracked_streamer_id int          NOT NULL,
    twitch_stream_id    bigint       NOT NULL,
    status              varchar(50)  NOT NULL DEFAULT 'pending',
    started_at          timestamp    NULL,
    completed_at        timestamp    NULL,
    error_message       text         NULL,
    retry_count         int          NOT NULL DEFAULT 0,
    created_at          timestamp    NOT NULL DEFAULT current_timestamp,
    updated_at          timestamp    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT processing_jobs_tracked_streamer_id_fk
        FOREIGN KEY (tracked_streamer_id) REFERENCES stream_sniper.tracked_streamers (id),
    CONSTRAINT processing_jobs_status_check
        CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
);
""")


def downgrade() -> None:
    # Drop in reverse FK order (children before parents). The schema itself is
    # intentionally NOT dropped, so alembic_version (which lives in stream_sniper)
    # survives a full downgrade. serial sequences drop automatically with their tables.
    op.execute("""
DROP TABLE IF EXISTS stream_sniper.processing_jobs;
DROP TABLE IF EXISTS stream_sniper.tracked_streamers;
DROP TABLE IF EXISTS stream_sniper.message;
DROP TABLE IF EXISTS stream_sniper.users;
DROP TABLE IF EXISTS stream_sniper.message_text;
DROP TABLE IF EXISTS stream_sniper.stream;
DROP TABLE IF EXISTS stream_sniper.creator;
DROP TABLE IF EXISTS stream_sniper.chatter;
""")
