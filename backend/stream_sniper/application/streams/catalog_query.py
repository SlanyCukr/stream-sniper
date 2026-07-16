"""Application queries for stream listings and detailed stream analytics."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from stream_sniper.database.gateways.streams.records import (
    OtherCreatorRow,
    RankedChatterRow,
    StreamComprehensiveRow,
    StreamListRow,
    StreamParticipantRow,
)

from .catalog_models import OtherCreator, RankedChatter, StreamDetails, StreamInfo, StreamListItem, StreamParticipant


class ListStreams(Protocol):
    def __call__(
        self,
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
    ) -> list[StreamListRow]: ...


class CountStreams(Protocol):
    def __call__(
        self,
        creator_id: int,
        *,
        title: str | None,
        date_from: date | None,
        date_to: date | None,
        min_messages: int | None,
    ) -> int: ...


@dataclass(frozen=True)
class StreamCatalogSources:
    list_streams: ListStreams
    count_streams: CountStreams
    stream_details: Callable[[int], StreamComprehensiveRow | None]
    most_active_chatters: Callable[[int], list[RankedChatterRow]]
    most_tagged_chatters: Callable[[int], list[RankedChatterRow]]
    other_creators: Callable[[int, int], list[OtherCreatorRow]]
    stream_chatters: Callable[[int], list[StreamParticipantRow]]


class StreamCatalogQuery:
    """Own stream read-model assembly while the HTTP layer owns transport and caching."""

    def __init__(self, sources: StreamCatalogSources) -> None:
        self._sources = sources

    def list_streams(
        self,
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
        rows = self._sources.list_streams(
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
        self,
        creator_id: int,
        *,
        title: str | None,
        date_from: date | None,
        date_to: date | None,
        min_messages: int | None,
    ) -> int:
        return self._sources.count_streams(
            creator_id,
            title=title,
            date_from=date_from,
            date_to=date_to,
            min_messages=min_messages,
        )

    def stream_details(self, stream_id: int) -> StreamDetails | None:
        info = self._sources.stream_details(stream_id)
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
                for row in self._sources.most_active_chatters(stream_id)
            ],
            most_tagged_chatters=[
                RankedChatter(chatter_id=row.chatter_id, nick=row.nick, count=row.rank_count)
                for row in self._sources.most_tagged_chatters(stream_id)
            ],
            other_creators=[
                OtherCreator(creator_id=row.creator_id, nick=row.nick)
                for row in self._sources.other_creators(stream_id, info.creator_id)
            ],
            chatters=[
                StreamParticipant(chatter_id=row.chatter_id, nick=row.nick)
                for row in self._sources.stream_chatters(stream_id)
            ],
        )
