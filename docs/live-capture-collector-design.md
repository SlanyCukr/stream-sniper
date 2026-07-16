# Live Twitch chat collector

Status: implemented by migration 0013 and the `stream-sniper-live` service.

## Runtime architecture

The live collector complements archived-VOD ingestion; it does not replace it.
`collector/live/live_chat_collector.py:LiveChatCollector` owns one authenticated
`twitchAPI.chat.Chat` connection, synchronizes its room set, supervises periodic
flush and status tasks, and finalizes ended streams. Channels come from
`LIVE_CHANNELS` and, by default, active tracked streamers
(`LIVE_TRACKED_CHANNELS=true`).

`collector/live/live_message_sink.py:LiveMessageSink` is the persistence
boundary. It serializes ingestion and finalization per channel, resolves stream,
chatter, and message-text identifiers off the event loop, buffers canonical
`LiveMessageRow` values, and persists batches off the event loop. Failed flushes
restore the complete pending batch and raise `LiveMessageFlushError`.

`collector/live/contracts.py` contains the structural Twitch message and stream
contracts. `collector/live/auth_cli.py` performs the one-time bot authorization,
and `collector/live/secure_files.py` writes token material with private file
permissions. There is no separate `live_auth.py` module.

## Identity and deduplication

Migration 0013 keeps Twitch broadcast identity separate from archived video
identity with `stream.twitch_stream_session_id`. A live stream initially uses a
negative session ID as its non-null `twitch_id`; archived ingestion later
reconciles the real VOD ID with that row. `message.source_message_id` has a
partial unique index, making websocket reconnects and archived retry overlap
idempotent.

The sink records IRC `sent_timestamp`, subscriber state, badges, emote count,
and the Twitch source message ID. On stream end it flushes accepted rows before
finalizing the stream. The collector then runs the normal stream rollup and
records any rollup failure for operational visibility.

## Authentication and configuration

The service requires the existing `TWITCH_CLIENT_ID` and
`TWITCH_CLIENT_SECRET`, plus either `TWITCH_BOT_REFRESH_TOKEN` or a populated
`TWITCH_BOT_TOKEN_FILE`. It requests only `AuthScope.CHAT_READ`; refreshed tokens
are persisted when a token file is configured.

Runtime settings:

- `LIVE_CHANNELS`: optional comma-separated static channel list.
- `LIVE_TRACKED_CHANNELS`: include active tracked streamers; defaults to `true`.
- `LIVE_FLUSH_INTERVAL`: periodic flush interval; defaults to 5 seconds.
- `LIVE_BUFFER_SIZE`: row threshold for immediate flush; defaults to 1000.

The console entry points are `stream-sniper-live-auth` for initial bot
authorization and `stream-sniper-live` for the long-running collector. Local and
production Compose files define the service, and `.env.example` documents every
setting.

## Failure and lifecycle policy

The collector supervises its background tasks with first-exception semantics:
an unexpected flush or reconciliation failure stops the service instead of
leaving a partially alive process. Shutdown cancels background tasks, retries a
retained flush once, closes Chat and Twitch resources exactly once, and surfaces
any final persistence failure. The archived collector remains the backfill path
for messages unavailable during a live-process outage.
