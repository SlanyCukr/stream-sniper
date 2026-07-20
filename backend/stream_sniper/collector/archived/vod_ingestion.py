"""Checked archived-VOD ingestion pipeline."""

from dataclasses import dataclass

from ...analytics.rollups.rollup_engine import RollupOutcome, compute_stream_rollup
from ...database.gateways.chat.chatter_table_gateway import (
    find_or_insert_chatter_id_db,
    insert_new_chatters_db,
    select_chatter_ids_by_nicks_db,
)
from ...database.gateways.chat.emote_dictionary_table_gateway import upsert_twitch_emotes_db
from ...database.gateways.chat.message_table_gateway import insert_message_db
from ...database.gateways.chat.message_text_table_gateway import (
    insert_message_texts_db,
    select_message_text_ids_db,
)
from ...database.gateways.streams.stream_table_gateway import update_stream_message_count_db
from .archived_stream import ensure_archived_stream_db
from .chat_parser import TwitchChatParser
from .database_buffer import DatabaseBuffer
from .message_rows import build_message_rows, collect_mention_nicks
from .twitch_archived_chat import ArchivedChatMessage
from .twitch_vod_chat_downloader import VodChatStream

CHAT_BATCH_SIZE = 20_000


@dataclass(frozen=True)
class BatchIngestionResult:
    message_count: int
    emotes_discovered: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class VodIngestionResult:
    twitch_vod_id: int
    stream_id: int
    message_count: int
    batches: tuple[BatchIngestionResult, ...]
    rollup: RollupOutcome


class VodIngestionPipeline:
    """Persist one downloaded VOD through explicit parse, write, and rollup stages."""

    def __init__(self, creator_id: int, creator_nick: str) -> None:
        self.creator_id = creator_id
        self.parser = TwitchChatParser()
        self.message_buffer = DatabaseBuffer(insert_message_db, 5000)
        self.seen_emote_names: set[str] = set()
        find_or_insert_chatter_id_db(creator_nick)

    def _ingest_batch(self, payloads: list[ArchivedChatMessage], stream_id: int) -> BatchIngestionResult:
        batch = self.parser.parse_batch(payloads)
        insert_new_chatters_db(list(batch.unique_nicks))
        insert_message_texts_db(list(batch.unique_messages))
        # Batch-scoped lookups (plus @mention targets from earlier streams) instead
        # of reloading the ever-growing chatter/message_text tables per batch.
        lookup_nicks = sorted({*batch.unique_nicks, *collect_mention_nicks(batch)})
        persisted = build_message_rows(
            batch,
            stream_id,
            select_chatter_ids_by_nicks_db(lookup_nicks),
            select_message_text_ids_db(list(batch.unique_messages)),
        )
        for row in persisted.rows:
            self.message_buffer.add_item(row)

        new_emotes = tuple(
            (name, provider_id) for name, provider_id in persisted.emotes if name not in self.seen_emote_names
        )
        if new_emotes:
            upsert_twitch_emotes_db(list(new_emotes))
            self.seen_emote_names.update(name for name, _ in new_emotes)
        return BatchIngestionResult(
            message_count=persisted.message_count,
            emotes_discovered=new_emotes,
        )

    def ingest(self, vod: VodChatStream) -> VodIngestionResult:
        stream_id = ensure_archived_stream_db(
            vod.twitch_vod_id,
            vod.started_at,
            self.creator_id,
            vod.title,
            vod.duration,
            vod.thumbnail_url,
        )
        batches: list[BatchIngestionResult] = []
        payload_batch: list[ArchivedChatMessage] = []
        for payload in vod.messages:
            payload_batch.append(payload)
            if len(payload_batch) == CHAT_BATCH_SIZE:
                batches.append(self._ingest_batch(payload_batch, stream_id))
                payload_batch = []
        if payload_batch:
            batches.append(self._ingest_batch(payload_batch, stream_id))

        message_count = sum(batch.message_count for batch in batches)
        self.message_buffer.flush()
        update_stream_message_count_db(stream_id, message_count)
        rollup = compute_stream_rollup(stream_id)
        rollup.require_success()
        return VodIngestionResult(
            twitch_vod_id=vod.twitch_vod_id,
            stream_id=stream_id,
            message_count=message_count,
            batches=tuple(batches),
            rollup=rollup,
        )
