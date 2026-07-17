"""Application-owned creator analytics queries."""

from ...database.gateways.analytics.stream_metrics_table_gateway import select_creator_metrics_series_db
from ...database.gateways.identity.creator_table_gateway import select_creator_summary_db
from .analytics_models import CreatorSummary, CreatorTrends, TrendPoint


class CreatorNotFoundError(LookupError):
    pass


def get_creator_summary(creator_id: int) -> CreatorSummary:
    row = select_creator_summary_db(creator_id)
    if row is None:
        raise CreatorNotFoundError
    return CreatorSummary.from_row(row)


def get_creator_trends(creator_id: int, limit: int) -> CreatorTrends:
    points = [TrendPoint.from_row(record) for record in select_creator_metrics_series_db(creator_id, limit)]
    return CreatorTrends(creator_id=creator_id, points=points)
