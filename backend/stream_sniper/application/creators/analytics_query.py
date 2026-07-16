"""Application-owned creator analytics queries."""

from ...database.gateways.analytics.stream_metrics_table_gateway import select_creator_metrics_series_db
from ...database.gateways.identity.creator_table_gateway import select_creator_summary_db
from .analytics_models import CreatorSummary, CreatorTrends, LatestCreatorStream, TrendPoint


class CreatorNotFoundError(LookupError):
    pass


def get_creator_summary(creator_id: int) -> CreatorSummary:
    row = select_creator_summary_db(creator_id)
    if row is None:
        raise CreatorNotFoundError
    latest_stream = (
        LatestCreatorStream(
            stream_id=row.latest_stream_id,
            title=row.latest_stream_title or "",
            start=row.latest_stream_start,
        )
        if row.latest_stream_id is not None
        else None
    )
    return CreatorSummary(
        creator_id=row.creator_id,
        nick=row.nick,
        display_name=row.display_name,
        profile_image_url=row.profile_image_url,
        twitch_user_id=str(row.twitch_user_id) if row.twitch_user_id is not None else None,
        total_streams=row.total_streams,
        first_stream_at=row.first_stream_at,
        last_stream_at=row.last_stream_at,
        total_messages=row.total_messages,
        duration_seconds=row.duration_seconds,
        messages_per_minute=row.messages_per_minute,
        audience_size=row.audience_size,
        regulars=row.regulars,
        latest_stream=latest_stream,
    )


def get_creator_trends(creator_id: int, limit: int) -> CreatorTrends:
    points = [
        TrendPoint(
            stream_id=record.stream_id,
            title=record.title,
            start=record.start,
            duration_seconds=record.duration_seconds,
            message_count=record.message_count,
            messages_per_minute=record.messages_per_minute,
            unique_chatters=record.unique_chatters,
            new_chatters=record.new_chatters,
            returning_chatters=record.returning_chatters,
        )
        for record in select_creator_metrics_series_db(creator_id, limit)
    ]
    return CreatorTrends(creator_id=creator_id, points=points)
