"""Default application-service composition for HTTP adapters."""

from collections.abc import Callable

from ..application.creators.regulars_query import CreatorRegularsSources
from ..application.streams.catalog_query import StreamCatalogQuery, StreamCatalogSources
from ..application.streams.compare_query import StreamComparisonSources
from ..application.streams.report_query import StreamReportSources
from ..application.streams.timeline_query import StreamTimelineSources
from ..database.gateways.analytics.stream_compare_table_gateway import (
    select_stream_compare_buckets_db,
    select_stream_compare_headers_db,
    select_stream_pair_retention_db,
)
from ..database.gateways.analytics.stream_emote_stats_table_gateway import select_stream_emotes_db
from ..database.gateways.analytics.stream_metrics_table_gateway import (
    select_creator_report_series_db,
    select_stream_header_db,
    select_stream_metrics_db,
)
from ..database.gateways.analytics.stream_phrase_stats_table_gateway import select_stream_phrases_db
from ..database.gateways.analytics.stream_time_bucket_table_gateway import select_stream_buckets_db
from ..database.gateways.community.creator_overlap_table_gateway import (
    select_creator_neighbors_db,
    select_overlap_db,
)
from ..database.gateways.content.stream_moment_table_gateway import select_stream_moments_db
from ..database.gateways.creators.creator_chatter_stats_table_gateway import select_creator_regulars_db
from ..database.gateways.streams.stream_context_table_gateway import select_stream_context_changes_db
from ..database.gateways.streams.stream_table_gateway import (
    count_streams_db,
    select_chatters_in_stream_db,
    select_creators_that_wrote_in_stream_db,
    select_most_active_chatters_db,
    select_most_tagged_chatters_db,
    select_stream_comprehensive_db,
    select_stream_page_db,
)
from ..database.gateways.streams.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db


def _late_bound[**P, R](resolve: Callable[[], Callable[P, R]]) -> Callable[P, R]:
    """Keep source bundles patchable without rebuilding query objects per request."""

    def call(*args: P.args, **kwargs: P.kwargs) -> R:
        return resolve()(*args, **kwargs)

    return call


STREAM_CATALOG_QUERY = StreamCatalogQuery(
    StreamCatalogSources(
        list_streams=_late_bound(lambda: select_stream_page_db),
        count_streams=_late_bound(lambda: count_streams_db),
        stream_details=_late_bound(lambda: select_stream_comprehensive_db),
        most_active_chatters=_late_bound(lambda: select_most_active_chatters_db),
        most_tagged_chatters=_late_bound(lambda: select_most_tagged_chatters_db),
        other_creators=_late_bound(lambda: select_creators_that_wrote_in_stream_db),
        stream_chatters=_late_bound(lambda: select_chatters_in_stream_db),
    )
)


STREAM_TIMELINE_SOURCES = StreamTimelineSources(
    select_buckets=_late_bound(lambda: select_stream_buckets_db),
    select_metrics=_late_bound(lambda: select_stream_metrics_db),
    select_header=_late_bound(lambda: select_stream_header_db),
    select_moments=_late_bound(lambda: select_stream_moments_db),
    select_viewer_samples=_late_bound(lambda: select_stream_viewer_samples_db),
    select_context_changes=_late_bound(lambda: select_stream_context_changes_db),
)


STREAM_COMPARISON_SOURCES = StreamComparisonSources(
    headers=_late_bound(lambda: select_stream_compare_headers_db),
    buckets=_late_bound(lambda: select_stream_compare_buckets_db),
    viewer_samples=_late_bound(lambda: select_stream_viewer_samples_db),
    retention=_late_bound(lambda: select_stream_pair_retention_db),
)


STREAM_REPORT_SOURCES = StreamReportSources(
    select_comprehensive=_late_bound(lambda: select_stream_comprehensive_db),
    select_metrics=_late_bound(lambda: select_stream_metrics_db),
    select_viewer_samples=_late_bound(lambda: select_stream_viewer_samples_db),
    select_emotes=_late_bound(lambda: select_stream_emotes_db),
    select_phrases=_late_bound(lambda: select_stream_phrases_db),
    select_moments=_late_bound(lambda: select_stream_moments_db),
    select_creator_series=_late_bound(lambda: select_creator_report_series_db),
)


CREATOR_REGULARS_SOURCES = CreatorRegularsSources(
    count_streams=_late_bound(lambda: count_streams_db),
    select_regulars=_late_bound(lambda: select_creator_regulars_db),
)


# Single-gateway queries accept the callable directly. These aliases keep HTTP
# adapters independent from persistence module paths without pass-through factories.
SELECT_COMMUNITY_OVERLAP = _late_bound(lambda: select_overlap_db)
SELECT_CREATOR_NEIGHBORS = _late_bound(lambda: select_creator_neighbors_db)
