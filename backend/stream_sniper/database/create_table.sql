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
    constraint creator_nick_uindex
        unique (nick)
);

create table stream_sniper.stream
(
    id            serial        primary key,
    twitch_id     bigint        not null,
    title         varchar(255)  not null,
    start         timestamp      not null,
    end           timestamp      null,
    thumbnail_url varchar(255)  null,
    message_count int default 0 not null,
    creator_id    int           null,
    constraint stream__twitch_id_uindex
        unique (twitch_id),
    constraint stream__creator_id_fk
        foreign key (creator_id) references stream_sniper.creator (id)
);

create table stream_sniper.message
(
    id                serial primary key,
    chatter_id        int                                  null,
    tagged_chatter_id int                                  null,
    stream_id         int                                  null,
    message_text_id   bigint                               not null,
    time              timestamp default current_timestamp null,
    constraint message_chatter_id_fk
        foreign key (chatter_id) references stream_sniper.chatter (id),
    constraint message_stream_id_fk
        foreign key (stream_id) references stream_sniper.stream (id),
    constraint message_text_id_fk
        foreign key (message_text_id) references stream_sniper.message_text (id)
);

create table stream_sniper.message_text
(
    id   serial primary key,
    text varchar(255) not null,
    constraint text_uq
        unique (text)
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

