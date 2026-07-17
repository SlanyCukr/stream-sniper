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
    return [StreamListItem.from_row(row) for row in rows]


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
        info=StreamInfo.from_row(info),
        most_active_chatters=[RankedChatter.from_row(row) for row in select_most_active_chatters_db(stream_id)],
        most_tagged_chatters=[RankedChatter.from_row(row) for row in select_most_tagged_chatters_db(stream_id)],
        other_creators=[
            OtherCreator.from_row(row) for row in select_creators_that_wrote_in_stream_db(stream_id, info.creator_id)
        ],
        chatters=[StreamParticipant.from_row(row) for row in select_chatters_in_stream_db(stream_id)],
    )
