"""Application orchestration for scene-wide chat search."""

from datetime import UTC, date, datetime, timedelta

from ...database.gateways.chat.message_replay_gateway import (
    StreamContextRow,
    select_message_window_db,
    select_stream_context_db,
)
from ...database.gateways.chat.message_search_gateway import (
    SearchHitRow,
    search_messages_db,
    select_first_messages_db,
    select_term_frequency_db,
)
from ..streams.message_models import MessageItem
from .search_models import (
    ContextCreator,
    ContextResponse,
    ContextStream,
    FirstMatchResponse,
    FrequencyPoint,
    FrequencyResponse,
    HitChatter,
    HitCreator,
    HitStream,
    SearchHit,
    SearchMessagesResponse,
)


class SearchContextNotFoundError(LookupError):
    pass


def _map_search_hit(row: SearchHitRow) -> SearchHit:
    return SearchHit(
        message_id=row.message_id,
        time=row.time,
        text=row.text,
        chatter=HitChatter(id=row.chatter_id, nick=row.chatter_nick, is_bot=row.chatter_is_bot),
        stream=HitStream(id=row.stream_id, title=row.stream_title),
        creator=HitCreator(id=row.creator_id, nick=row.creator_nick, display_name=row.creator_display_name),
    )


def _map_context_stream(row: StreamContextRow) -> ContextStream:
    return ContextStream(
        id=row.stream_id,
        title=row.stream_title,
        creator=ContextCreator(id=row.creator_id, nick=row.creator_nick, display_name=row.creator_display_name),
    )


def search_messages(
    term: str,
    creator_id: int | None,
    days: int | None,
    limit: int,
    offset: int,
) -> SearchMessagesResponse:
    rows, has_more = search_messages_db(term, creator_id, days, limit, offset)
    return SearchMessagesResponse(
        query=term,
        items=[_map_search_hit(row) for row in rows],
        has_more=has_more,
    )


def find_first_match(term: str, creator_id: int | None) -> FirstMatchResponse:
    found = select_first_messages_db(term, creator_id)
    return FirstMatchResponse(
        query=term,
        first=_map_search_hit(found.first) if found.first is not None else None,
        by_creator=[_map_search_hit(row) for row in found.by_creator],
        total_matches=found.total_matches,
    )


def search_frequency(
    term: str,
    days: int,
    creator_id: int | None,
    *,
    today: date | None = None,
) -> FrequencyResponse:
    counts = {row.day: row.matches for row in select_term_frequency_db(term, days, creator_id)}
    end = today or datetime.now(UTC).date()
    current = end - timedelta(days=days - 1)
    points: list[FrequencyPoint] = []
    while current <= end:
        iso = current.isoformat()
        points.append(FrequencyPoint(date=iso, count=counts.get(iso, 0)))
        current += timedelta(days=1)
    return FrequencyResponse(query=term, days=days, points=points)


def get_search_context(stream_id: int, message_id: int, radius: int) -> ContextResponse:
    rows = select_message_window_db(stream_id, message_id, radius)
    stream = select_stream_context_db(stream_id)
    if not rows or stream is None:
        raise SearchContextNotFoundError

    messages = [MessageItem.from_row(row) for row in rows]
    hit_index = next((index for index, item in enumerate(messages) if item.id == message_id), None)
    if hit_index is None:
        raise SearchContextNotFoundError
    return ContextResponse(stream=_map_context_stream(stream), messages=messages, hit_index=hit_index)
