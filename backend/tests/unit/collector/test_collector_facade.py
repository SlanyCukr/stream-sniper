"""Thin VOD collector coordinator tests."""

from datetime import datetime
from unittest.mock import Mock

from stream_sniper.analytics.rollups.rollup_engine import RollupOutcome
from stream_sniper.collector.archived.twitch_collector_facade import TwitchCollectorFacade
from stream_sniper.collector.archived.twitch_vod_chat_downloader import VodChatStream
from stream_sniper.collector.archived.vod_ingestion import VodIngestionResult


def test_facade_composes_injected_boundaries_and_returns_run_result():
    twitch_client = Mock()
    resolver = Mock()
    resolver.resolve.return_value = 7
    vod = VodChatStream(
        messages=iter([]),
        twitch_vod_id=123,
        started_at=datetime(2024, 1, 15, 20),
        title="title",
        duration="1h",
        thumbnail_url="thumb",
    )
    source = Mock()
    source.open_chat_stream.side_effect = [vod, None]
    pipeline = Mock()
    ingestion = VodIngestionResult(
        twitch_vod_id=123,
        stream_id=9,
        message_count=0,
        batches=(),
        rollup=RollupOutcome(stream_id=9),
    )
    pipeline.ingest.return_value = ingestion

    facade = TwitchCollectorFacade(
        "creator",
        twitch_client=twitch_client,
        creator_resolver=resolver,
        vod_source_factory=lambda *_args: source,
        pipeline_factory=lambda *_args: pipeline,
    )
    result = facade.ingest_archived_vods(max_vods=1)

    assert result.processed_vods == (ingestion,)
    assert result.processed_count == 1
    resolver.resolve.assert_called_once_with("creator", twitch_client)
    pipeline.ingest.assert_called_once_with(vod)
    twitch_client.initialize.assert_called_once_with()
    twitch_client.close.assert_called_once_with()
