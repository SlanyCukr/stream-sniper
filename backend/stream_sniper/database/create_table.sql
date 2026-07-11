-- REFERENCE ONLY — do not apply by hand.
-- Human-readable snapshot of the table/column/constraint set. The baseline tables are
-- mirrored by Alembic revision 0001 (stream_sniper/database/migrations/versions/0001_...);
-- this file additionally mirrors the transactional analytics additions from revisions
-- 0006 (rollup + viewer-sample tables) and 0007 (message metadata columns) so the full
-- table shape is readable in one place. NOTE: revision 0001 additionally issues
-- CREATE SCHEMA IF NOT EXISTS stream_sniper (online schema creation lives in env.py); this
-- file assumes the schema already exists, as it always did.
-- Schema is now versioned with Alembic; build/upgrade a DB with:
--   cd backend && uv run alembic upgrade head        (fresh DB)
-- CONCURRENTLY indexes (chatter_nick_lower_prefix_idx / 0002, message_stream_time_id_idx /
-- 0004, message_chatter_time_id_idx / 0005) and the tracking_heartbeat table (0003) live
-- ONLY in their migrations, NOT here. See backend/CLAUDE.md "Database migrations".

create table stream_sniper.chatter
(
    id   serial       primary key,
    nick varchar(255) not null,
    constraint chatter_name_uindex
        unique (nick)
);

create table stream_sniper.creator
(
    id                serial        primary key,
    nick              varchar(255) not null,
    display_name      varchar(255) not null,
    profile_image_url varchar(255) not null,
    twitch_id         bigint,
    constraint creator_nick_uindex
        unique (nick)
);

create table stream_sniper.stream
(
    id            serial        primary key,
    twitch_id     bigint        not null,
    title         varchar(255)  not null,
    start         timestamp      not null,
    "end"         timestamp      null,
    thumbnail_url varchar(255)  null,
    message_count int default 0 not null,
    creator_id    int           null,
    constraint stream__twitch_id_uindex
        unique (twitch_id),
    constraint stream__creator_id_fk
        foreign key (creator_id) references stream_sniper.creator (id)
);

create table stream_sniper.message_text
(
    id   serial primary key,
    text text not null,
    constraint text_uq
        unique (text)
);

create table stream_sniper.message
(
    id                serial primary key,
    chatter_id        int                                  null,
    tagged_chatter_id int                                  null,
    stream_id         int                                  null,
    message_text_id   bigint                               not null,
    time              timestamp default current_timestamp null,
    is_subscriber     boolean                              null,  -- rev 0007
    badges            text                                 null,  -- rev 0007
    emote_count       smallint                             null,  -- rev 0007
    constraint message_chatter_id_fk
        foreign key (chatter_id) references stream_sniper.chatter (id),
    constraint message_stream_id_fk
        foreign key (stream_id) references stream_sniper.stream (id),
    constraint message_text_id_fk
        foreign key (message_text_id) references stream_sniper.message_text (id)
);

create table stream_sniper.users
(
    id           serial       primary key,
    username     varchar(255) not null,
    email        varchar(255) not null,
    password_hash varchar(255) not null,
    role         varchar(50)  not null default 'user',
    is_active    boolean      not null default true,
    created_at   timestamp    not null default current_timestamp,
    updated_at   timestamp    not null default current_timestamp,
    constraint users_username_uindex
        unique (username),
    constraint users_email_uindex
        unique (email)
);

create table stream_sniper.tracked_streamers
(
    id                        serial       primary key,
    creator_id                int          not null,
    twitch_username           varchar(255) not null,
    display_name              varchar(255) not null,
    is_active                 boolean      not null default true,
    last_stream_check         timestamp    null,
    last_processed_stream_id  bigint       null,
    processing_enabled        boolean      not null default true,
    created_at                timestamp    not null default current_timestamp,
    updated_at                timestamp    not null default current_timestamp,
    created_by                int          null,
    notes                     text         null,
    constraint tracked_streamers_creator_id_fk
        foreign key (creator_id) references stream_sniper.creator (id),
    constraint tracked_streamers_created_by_fk
        foreign key (created_by) references stream_sniper.users (id),
    constraint tracked_streamers_creator_id_uindex
        unique (creator_id),
    constraint tracked_streamers_twitch_username_uindex
        unique (twitch_username)
);

create table stream_sniper.processing_jobs
(
    id                    serial       primary key,
    tracked_streamer_id   int          not null,
    twitch_stream_id      bigint       not null,
    status                varchar(50)  not null default 'pending',
    started_at            timestamp    null,
    completed_at          timestamp    null,
    error_message         text         null,
    retry_count           int          not null default 0,
    created_at            timestamp    not null default current_timestamp,
    updated_at            timestamp    not null default current_timestamp,
    constraint processing_jobs_tracked_streamer_id_fk
        foreign key (tracked_streamer_id) references stream_sniper.tracked_streamers (id),
    constraint processing_jobs_status_check
        check (status IN ('pending', 'in_progress', 'completed', 'failed'))
);

-- ---------------------------------------------------------------------------
-- Analytics rollup + viewer-sample tables (Alembic revision 0006).
-- ---------------------------------------------------------------------------

create table stream_sniper.stream_viewer_sample
(
    id                       bigserial   primary key,
    tracked_streamer_id      int         not null,
    twitch_stream_session_id bigint      not null,
    sampled_at               timestamptz not null,
    viewer_count             int         not null,
    title                    text        null,
    session_started_at       timestamptz null,
    constraint stream_viewer_sample_streamer_fk
        foreign key (tracked_streamer_id) references stream_sniper.tracked_streamers (id),
    constraint stream_viewer_sample_uq
        unique (tracked_streamer_id, twitch_stream_session_id, sampled_at)
);

create table stream_sniper.stream_time_bucket
(
    stream_id       int       not null,
    bucket_minute   timestamp not null,
    message_count   int       not null,
    unique_chatters int       not null,
    constraint stream_time_bucket_pk primary key (stream_id, bucket_minute),
    constraint stream_time_bucket_stream_fk
        foreign key (stream_id) references stream_sniper.stream (id)
);

create table stream_sniper.stream_chatter_stats
(
    stream_id          int       not null,
    chatter_id         int       not null,
    message_count      int       not null,
    first_message_time timestamp null,
    last_message_time  timestamp null,
    constraint stream_chatter_stats_pk primary key (stream_id, chatter_id),
    constraint stream_chatter_stats_stream_fk
        foreign key (stream_id) references stream_sniper.stream (id),
    constraint stream_chatter_stats_chatter_fk
        foreign key (chatter_id) references stream_sniper.chatter (id)
);
create index stream_chatter_stats_chatter_idx
    on stream_sniper.stream_chatter_stats (chatter_id);

create table stream_sniper.stream_metrics
(
    stream_id            int           primary key,
    total_messages       int           not null,
    unique_chatters      int           not null,
    duration_seconds     int           null,
    messages_per_minute  numeric(10,2) null,
    peak_messages        int           not null default 0,
    peak_bucket_minute   timestamp     null,
    new_chatters         int           not null default 0,
    returning_chatters   int           not null default 0,
    computed_at          timestamptz   not null default now(),
    constraint stream_metrics_stream_fk
        foreign key (stream_id) references stream_sniper.stream (id)
);

create table stream_sniper.creator_chatter_stats
(
    creator_id           int         not null,
    chatter_id           int         not null,
    streams_attended     int         not null,
    total_messages       bigint      not null,
    first_seen_stream_id int         null,
    first_seen_at        timestamp   null,
    last_seen_stream_id  int         null,
    last_seen_at         timestamp   null,
    updated_at           timestamptz not null default now(),
    constraint creator_chatter_stats_pk primary key (creator_id, chatter_id),
    constraint creator_chatter_stats_creator_fk
        foreign key (creator_id) references stream_sniper.creator (id),
    constraint creator_chatter_stats_chatter_fk
        foreign key (chatter_id) references stream_sniper.chatter (id)
);
create index creator_chatter_stats_attendance_idx
    on stream_sniper.creator_chatter_stats (creator_id, streams_attended desc);
create index creator_chatter_stats_recency_idx
    on stream_sniper.creator_chatter_stats (creator_id, last_seen_at desc);

create index stream_creator_start_idx
    on stream_sniper.stream (creator_id, start desc);

