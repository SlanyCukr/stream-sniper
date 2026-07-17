"""Application queries for stream listings and detailed stream analytics."""

from datetime import date

from stream_sniper.database.gateways.streams.stream_table_gateway import (
    count_streams_db,
    select_chatters_in_stream_db,
    select_creators_that_wrote_in_stream_db,
    select_most_active_chatters_db,
    select_most_tagged_chatters_db,
    select_stream_comprehensive_db,
    select_stream_page_db,
)

from .catalog_models import OtherCreator, RankedChatter, StreamDetails, StreamInfo, StreamListItem, StreamParticipant


def list_streams(
    creator_id: int,
    offset: int,
    limit: int = 20,
    *,
    sort: str,
    direction: str,
    title: str | None,
    date_from: date | None,
    date_to: date | None,
    min_messages: int | None,
) -> list[StreamListItem]:
    """Own stream read-model assembly while the HTTP layer owns transport and caching."""
    rows = select_stream_page_db(
        creator_id,
        offset,
        limit,
        sort=sort,
        direction=direction,
        title=title,
        date_from=date_from,
        date_to=date_to,
        min_messages=min_messages,
    )
    return [
        StreamListItem(
            stream_id=row.stream_id,
            creator_name=row.creator_name,
            start=row.start,
            end=row.end,
            thumbnail_url=row.thumbnail_url,
            message_count=row.message_count,
        )
        for row in rows
    ]


def count_streams(
    creator_id: int,
    *,
    title: str | None,
    date_from: date | None,
    date_to: date | None,
    min_messages: int | None,
) -> int:
    return count_streams_db(
        creator_id,
        title=title,
        date_from=date_from,
        date_to=date_to,
        min_messages=min_messages,
    )


def stream_details(stream_id: int) -> StreamDetails | None:
    info = select_stream_comprehensive_db(stream_id)
    if info is None:
        return None
    return StreamDetails(
        info=StreamInfo(
            title=info.title,
            start=str(info.start),
            end=str(info.end) if info.end is not None else None,
            thumbnail_url=info.thumbnail_url,
            message_count=info.message_count,
            creator_nick=info.creator_nick,
            creator_display_name=info.creator_display_name,
            profile_image_url=info.profile_image_url,
            creator_id=info.creator_id,
        ),
        most_active_chatters=[
            RankedChatter(chatter_id=row.chatter_id, nick=row.nick, count=row.rank_count)
            for row in select_most_active_chatters_db(stream_id)
        ],
        most_tagged_chatters=[
            RankedChatter(chatter_id=row.chatter_id, nick=row.nick, count=row.rank_count)
            for row in select_most_tagged_chatters_db(stream_id)
        ],
        other_creators=[
            OtherCreator(creator_id=row.creator_id, nick=row.nick)
            for row in select_creators_that_wrote_in_stream_db(stream_id, info.creator_id)
        ],
        chatters=[
            StreamParticipant(chatter_id=row.chatter_id, nick=row.nick)
            for row in select_chatters_in_stream_db(stream_id)
        ],
    )
