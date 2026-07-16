"""Async adapter for running one exact synchronous VOD ingestion job."""

import asyncio
from typing import cast

from ..collector.archived.twitch_collector_facade import TwitchCollectorFacade
from ..collector.archived.vod_ingestion import VodIngestionResult


async def run_vod_job(twitch_username: str, twitch_vod_id: int) -> VodIngestionResult:
    """Ingest exactly ``twitch_vod_id`` in a worker thread and verify its identity."""

    def ingest_vod_sync() -> VodIngestionResult:
        collector = TwitchCollectorFacade(
            twitch_username,
            twitch_vod_id=twitch_vod_id,
        )
        result = collector.ingest_archived_vods(max_vods=1)
        if result.processed_count != 1:
            raise RuntimeError(f"Twitch VOD {twitch_vod_id} was not processed")
        ingested = cast(VodIngestionResult, result.processed_vods[0])
        if ingested.twitch_vod_id != twitch_vod_id:
            raise RuntimeError(f"Requested Twitch VOD {twitch_vod_id}, ingested {ingested.twitch_vod_id}")
        return ingested

    worker = asyncio.create_task(asyncio.to_thread(ingest_vod_sync))
    try:
        return cast(VodIngestionResult, await asyncio.shield(worker))
    except asyncio.CancelledError:
        # Thread workers cannot be interrupted safely. Keep the async job leased
        # until persistence has stopped, then let the queue record cancellation.
        # Continue draining if another caller repeats the cancellation request.
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Consume any late worker exception without letting it override the
        # already-accepted durable cancellation outcome.
        if not worker.cancelled():
            worker.exception()
        raise
