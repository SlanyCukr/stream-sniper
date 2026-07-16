"""Application-owned orchestration for scene analytics read models."""

from typing import Literal

from ...database.gateways.content.scene_table_gateway import (
    select_scene_leaderboard_db,
    select_scene_peak_viewers_db,
)
from ...database.gateways.content.stream_copypasta_stats_table_gateway import (
    select_copypasta_context_db,
    select_copypasta_propagation_db,
    select_scene_copypastas_db,
)
from ...database.gateways.streams.stream_viewer_sample_table_gateway import (
    select_latest_sample_time_db,
    select_live_now_db,
)
from .models import (
    Copypasta,
    CopypastaContextMessage,
    CopypastaOccurrence,
    CopypastaPropagation,
    LeaderboardEntry,
    LiveStreamer,
    SceneCopypastas,
    SceneLeaderboard,
    SceneLive,
)


class CopypastaNotFoundError(LookupError):
    pass


def get_copypasta_propagation(message_text_id: int, context_seconds: int) -> CopypastaPropagation:
    text, rows = select_copypasta_propagation_db(message_text_id)
    if text is None:
        raise CopypastaNotFoundError
    occurrences = [
        CopypastaOccurrence(
            stream_id=row.stream_id,
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            profile_image_url=row.profile_image_url,
            stream_title=row.stream_title,
            stream_start=row.stream_start,
            first_seen=row.first_seen,
            usage_count=row.usage_count,
            chatter_count=row.chatter_count,
        )
        for row in rows
    ]
    first = next((item for item in occurrences if item.first_seen is not None), None)
    if first is None:
        context_rows = []
    else:
        assert first.first_seen is not None
        context_rows = select_copypasta_context_db(first.stream_id, first.first_seen, context_seconds, 100)
    context = [
        CopypastaContextMessage(
            id=row.id,
            time=row.time,
            chatter_id=row.chatter_id,
            nick=row.nick,
            text=row.text,
        )
        for row in context_rows
    ]
    return CopypastaPropagation(
        message_text_id=message_text_id,
        text=text,
        usage_count=sum(item.usage_count for item in occurrences),
        chatter_appearances=sum(item.chatter_count for item in occurrences),
        stream_count=len(occurrences),
        creator_count=len({item.creator_id for item in occurrences}),
        first_seen=first.first_seen if first else None,
        occurrences=occurrences,
        origin_context=context,
    )


def get_scene_live() -> SceneLive:
    live = [
        LiveStreamer(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            profile_image_url=row.profile_image_url,
            viewer_count=row.viewer_count,
            title=row.title,
            session_started_at=row.session_started_at,
            sampled_at=row.sampled_at,
        )
        for row in select_live_now_db()
    ]
    live.sort(key=lambda streamer: streamer.viewer_count, reverse=True)
    return SceneLive(live=live, live_count=len(live), last_sample_at=select_latest_sample_time_db())


def get_scene_leaderboard(window: int) -> SceneLeaderboard:
    rows = select_scene_leaderboard_db(window)
    peak_map = {row.creator_id: row.peak_viewers for row in select_scene_peak_viewers_db(window)}
    entries = [
        LeaderboardEntry(
            rank=rank,
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            profile_image_url=row.profile_image_url,
            streams=row.streams,
            hours_streamed=row.hours_streamed,
            total_messages=row.total_messages,
            msgs_per_min=row.msgs_per_min,
            chatter_appearances=row.chatter_appearances,
            peak_viewers=peak_map.get(row.creator_id),
        )
        for rank, row in enumerate(rows, start=1)
    ]
    return SceneLeaderboard(window_days=window, entries=entries)


def get_scene_copypastas(
    days: int | None,
    creator_id: int | None,
    sort: Literal["usage", "spread", "recent"],
    limit: int,
    offset: int,
) -> SceneCopypastas:
    rows, total = select_scene_copypastas_db(days, creator_id, sort, limit, offset)
    items = [
        Copypasta(
            message_text_id=row.message_text_id,
            text=row.text,
            usage_count=row.usage_count,
            chatter_appearances=row.chatter_appearances,
            stream_count=row.stream_count,
            creator_count=row.creator_count,
            first_seen=row.first_seen,
            last_stream_start=row.last_stream_start,
        )
        for row in rows
    ]
    return SceneCopypastas(total=total, offset=offset, limit=limit, items=items)
