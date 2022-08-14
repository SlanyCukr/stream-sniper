create table stream_sniper.chatter
(
    id   int auto_increment
        primary key,
    nick varchar(255) not null,
    constraint chatter_name_uindex
        unique (nick)
);

create table stream_sniper.creator
(
    id                int auto_increment
        primary key,
    nick              varchar(255) not null,
    display_name      varchar(255) not null,
    profile_image_url varchar(255) not null,
    constraint creator_nick_uindex
        unique (nick)
);

create table stream_sniper.stream
(
    id            int auto_increment
        primary key,
    twitch_id     bigint        not null,
    title         varchar(255)  not null,
    start         datetime      not null,
    end           datetime      null,
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
    id                int auto_increment
        primary key,
    chatter_id        int                                  null,
    tagged_chatter_id int                                  null,
    stream_id         int                                  null,
    message_text_id   bigint                               not null,
    time              datetime default current_timestamp() null,
    constraint message_chatter_id_fk
        foreign key (chatter_id) references stream_sniper.chatter (id),
    constraint message_stream_id_fk
        foreign key (stream_id) references stream_sniper.stream (id),
    constraint message_text_id_fk
        foreign key (message_text_id) references stream_sniper.message_text (id)
);

create table stream_sniper.message_text
(
    id   bigint auto_increment
        primary key,
    text varchar(255) not null
);

