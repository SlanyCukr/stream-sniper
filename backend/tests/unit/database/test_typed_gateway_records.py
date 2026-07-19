"""Contract tests for named gateway rows and explicit patch fields."""

from datetime import datetime

import pytest

from stream_sniper.application.tracking.models import (
    ProcessingJob,
    TrackedStreamer,
)
from stream_sniper.database.gateways.analytics.records import (
    StreamBucketRow,
    StreamHeaderRow,
    StreamMetricsRow,
    TopEmoteRow,
    TopPhraseRow,
)
from stream_sniper.database.gateways.analytics.stream_emote_stats_table_gateway import select_stream_emotes_db
from stream_sniper.database.gateways.analytics.stream_metrics_table_gateway import (
    select_stream_header_db,
    select_stream_metrics_db,
)
from stream_sniper.database.gateways.analytics.stream_phrase_stats_table_gateway import select_stream_phrases_db
from stream_sniper.database.gateways.analytics.stream_time_bucket_table_gateway import select_stream_buckets_db
from stream_sniper.database.gateways.chat.message_replay_gateway import select_stream_messages_db
from stream_sniper.database.gateways.chat.records import MessageReplayRow
from stream_sniper.database.gateways.community.audience_movement_table_gateway import (
    select_creator_audience_movement_db,
)
from stream_sniper.database.gateways.community.creator_overlap_table_gateway import select_overlap_db
from stream_sniper.database.gateways.community.records import (
    AudienceMovementRows,
    CommunityCreatorRow,
    CommunityPairRow,
)
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.content.stream_moment_table_gateway import select_stream_moments_db
from stream_sniper.database.gateways.identity.creator_table_gateway import select_creator_summary_db
from stream_sniper.database.gateways.identity.records import CreatorSummaryRow, UserRow
from stream_sniper.database.gateways.identity.user_table_gateway import select_user_by_id_db, update_user_db
from stream_sniper.database.gateways.streams.records import (
    StreamComprehensiveRow,
    StreamContextChangeRow,
    ViewerSampleRow,
)
from stream_sniper.database.gateways.streams.stream_context_table_gateway import select_stream_context_changes_db
from stream_sniper.database.gateways.streams.stream_table_gateway import select_stream_comprehensive_db
from stream_sniper.database.gateways.streams.stream_viewer_sample_table_gateway import (
    select_stream_viewer_samples_db,
)
from stream_sniper.database.gateways.tracking.processing_jobs_table_gateway import (
    select_processing_jobs_db,
)
from stream_sniper.database.gateways.tracking.tracked_streamers_table_gateway import (
    select_tracked_streamers_db,
    update_tracked_streamer_db,
)

NOW = datetime(2026, 7, 15, 12, 0)


def test_identity_and_tracking_queries_return_named_rows(mock_connection_pool):
    _, _, cursor = mock_connection_pool

    cursor.fetchone.return_value = (1, "alice", "a@example.com", "hash", "admin", True, NOW)
    user = select_user_by_id_db(1)
    assert isinstance(user, UserRow)
    assert user.username == "alice"

    cursor.fetchall.return_value = [
        (2, 3, "streamer", "Streamer", True, None, 99, True, NOW, NOW, 1, None, "Streamer", None, "alice")
    ]
    streamers = select_tracked_streamers_db()
    assert isinstance(streamers[0], TrackedStreamer)
    assert streamers[0].last_processed_twitch_vod_id == 99

    cursor.fetchall.return_value = [
        (4, 2, 99, "pending", None, None, None, 0, NOW, NOW, "streamer", "Streamer", "Title", NOW)
    ]
    jobs = select_processing_jobs_db()
    assert isinstance(jobs[0], ProcessingJob)
    assert jobs[0].twitch_vod_id == 99


def test_composite_analytics_queries_return_named_rows(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.fetchone.return_value = (
        5,
        "alice",
        "Alice",
        None,
        123,
        12,
        "2026-01-01T00:00:00",
        "2026-07-01T00:00:00",
        500,
        3600,
        8.3,
        100,
        20,
        9,
        "Latest",
        "2026-07-01T00:00:00",
    )
    summary = select_creator_summary_db(5)
    assert isinstance(summary, CreatorSummaryRow)
    assert summary.latest_stream_id == 9

    cursor.fetchone.return_value = (100, 80, 60, 40, 20)
    cursor.fetchall.side_effect = [
        [(2, "source", "Source", 12)],
        [(3, "destination", "Destination", 8)],
    ]
    movement = select_creator_audience_movement_db(5, 30, 8)
    assert isinstance(movement, AudienceMovementRows)
    assert movement.summary.retained == 60
    assert movement.prior_channels_for_gained[0].chatter_count == 12


def test_patch_gateways_reject_unknown_fields_before_sql(mock_connection_pool):
    _, _, cursor = mock_connection_pool

    with pytest.raises(TypeError):
        update_user_db(1, typo=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        update_tracked_streamer_db(1, typo=True)  # type: ignore[call-arg]

    cursor.execute.assert_not_called()


def test_nullable_patch_fields_can_be_cleared(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.rowcount = 1

    assert update_tracked_streamer_db(1, notes=None)
    assert cursor.execute.call_args.args[1] == [None, 1]


def test_message_and_community_projections_preserve_named_field_order(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.fetchall.return_value = [(101, "2026-07-15T12:34:56.123456", 202, "nick-203", "text-204", True, "badge-205")]

    messages = select_stream_messages_db(7, 10)

    assert messages == [
        MessageReplayRow(101, "2026-07-15T12:34:56.123456", 202, "nick-203", "text-204", True, "badge-205")
    ]
    assert messages[0].chatter_id == 202
    assert messages[0].text == "text-204"

    cursor.reset_mock()
    cursor.fetchall.side_effect = [
        [(301, "nick-302", "display-303", 304, 305, "computed-306")],
        [(301, 401, 402, 403)],
    ]

    creators, pairs = select_overlap_db(1)

    assert creators == [CommunityCreatorRow(301, "nick-302", "display-303", 304, 305, "computed-306")]
    assert pairs == [CommunityPairRow(301, 401, 402, 403)]
    assert creators[0].chatters == 304
    assert creators[0].regulars == 305
    assert pairs[0].shared_chatters == 402
    assert pairs[0].shared_regulars == 403


def test_stream_report_and_timeline_projections_preserve_named_field_order(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.fetchone.return_value = (
        "title-1",
        "start-2",
        "end-3",
        "thumb-4",
        5,
        "nick-6",
        "display-7",
        "profile-8",
        9,
    )
    comprehensive = select_stream_comprehensive_db(10)
    assert comprehensive == StreamComprehensiveRow(
        "title-1", "start-2", "end-3", "thumb-4", 5, "nick-6", "display-7", "profile-8", 9
    )
    assert comprehensive.creator_nick == "nick-6"
    assert comprehensive.creator_id == 9

    cursor.fetchone.return_value = (11, 12, 13, 14.5, 15, "peak-16", 17, 18, 19, 20)
    metrics = select_stream_metrics_db(10)
    assert metrics == StreamMetricsRow(11, 12, 13, 14.5, 15, "peak-16", 17, 18, 19, 20)
    assert metrics.messages_per_minute == 14.5
    assert metrics.returning_chatters == 18

    cursor.fetchone.return_value = ("start-21", "twitch-22")
    header = select_stream_header_db(10)
    assert header == StreamHeaderRow("start-21", "twitch-22")

    cursor.fetchall.return_value = [("bucket-31", 32, 33, 34, 35)]
    assert select_stream_buckets_db(10) == [StreamBucketRow("bucket-31", 32, 33, 34, 35)]

    cursor.fetchall.return_value = [("sample-41", 42)]
    assert select_stream_viewer_samples_db(10) == [ViewerSampleRow("sample-41", 42)]

    cursor.fetchall.return_value = [
        ("moment-51", 52, 53, 54.5, 55.5, 56, 0.57, 0.58, [{"p": 59}], [{"m": 60}], "status-61", None, None)
    ]
    moments = select_stream_moments_db(10)
    assert moments == [
        StreamMomentRow(
            "moment-51", 52, 53, 54.5, 55.5, 56, 0.57, 0.58, [{"p": 59}], [{"m": 60}], "status-61", None, None
        )
    ]
    assert moments[0].baseline == 54.5
    assert moments[0].unique_chatters == 56


def test_context_and_ranked_report_rows_preserve_named_field_order(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.fetchall.return_value = [("sample-71", "title-72", "cat-73", "category-74", "lang-75", ["tag-76"], True)]
    context = select_stream_context_changes_db(10)
    assert context == [
        StreamContextChangeRow("sample-71", "title-72", "cat-73", "category-74", "lang-75", ["tag-76"], True)
    ]
    assert context[0].category_id == "cat-73"
    assert context[0].category_name == "category-74"

    cursor.fetchall.return_value = [("emote-81", "source-82", "provider-83", 84, 85)]
    assert select_stream_emotes_db(10, 1) == [TopEmoteRow("emote-81", "source-82", "provider-83", 84, 85)]

    cursor.fetchall.return_value = [("phrase-91", 92, 93)]
    assert select_stream_phrases_db(10, 1) == [TopPhraseRow("phrase-91", 92, 93)]
