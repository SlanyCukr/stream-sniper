"""Application query for creator attendance and regular-chatters read models."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from stream_sniper.database.gateways.creators.records import CreatorRegularRow

from .regulars_models import CreatorRegulars, Regular


class SelectCreatorRegulars(Protocol):
    def __call__(
        self,
        creator_id: int,
        min_streams: int,
        limit: int,
        *,
        sort: str,
        direction: str,
        include_bots: bool,
    ) -> list[CreatorRegularRow]: ...


@dataclass(frozen=True)
class CreatorRegularsSources:
    count_streams: Callable[[int], int]
    select_regulars: SelectCreatorRegulars


def get_creator_regulars(
    creator_id: int,
    min_streams: int,
    limit: int,
    sources: CreatorRegularsSources,
    *,
    sort: str,
    direction: str,
    include_bots: bool,
) -> CreatorRegulars:
    """Calculate creator attendance from explicit persistence sources."""
    total_streams = int(sources.count_streams(creator_id))
    rows = sources.select_regulars(
        creator_id,
        min_streams,
        limit,
        sort=sort,
        direction=direction,
        include_bots=include_bots,
    )
    regulars = [
        Regular(
            chatter_id=row.chatter_id,
            nick=row.nick,
            streams_attended=row.streams_attended,
            attendance_rate=round(row.streams_attended / total_streams, 4) if total_streams else 0.0,
            first_seen=row.first_seen,
            last_seen=row.last_seen,
            last_stream_attended=row.last_stream_attended,
            message_count=row.message_count,
        )
        for row in rows
    ]
    return CreatorRegulars(
        creator_id=creator_id,
        total_streams=total_streams,
        regulars=regulars,
    )
