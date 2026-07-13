# Design: Live Twitch Chat Capture Collector

Status: implemented in migrations 0013 and the `stream-sniper-live` service.
Scope: `backend/stream_sniper/`.

## 1. Goal & scope

Add a collector that captures Twitch chat **in real time from an in-progress
broadcast**, complementing the existing VOD-only collector
(`collector/irc_chat_downloader.py` → `chat-downloader` on `VideoType.ARCHIVE`
at `https://www.twitch.tv/videos/{id}`, orchestrated by
`collector/twitch_collector_facade.py:TwitchCollectorFacade`).

What "live" adds over the VOD collector:

- **Coverage of streamers who disable/limit VODs.** Many channels turn VODs off
  or Twitch expires them after 7–60 days; the VOD path then collects nothing.
  Live capture is the only way to get that chat.
- **No wait for VOD publication.** VOD chat is only downloadable after the VOD is
  processed and available; live gives data during and immediately after the
  broadcast.
- **Accurate per-message timestamps and ordering** from the IRC `tmi-sent-ts`
  tag rather than VOD-relative offsets.

**Non-goals:** (1) replacing the VOD collector — it stays as the authoritative
backfill/safety net (see §7); (2) sending messages / moderation (read-only);
(3) new analytics dimensions (emotes, bits, badges) beyond the current schema;
(4) pushing live data to the frontend (dashboard stays poll-based).

## 2. Chosen approach: `twitchAPI.chat.Chat`

Use the **Chat module of the already-vendored `twitchAPI~=4.5.0`** (see
`pyproject.toml` deps) — IRC-over-websocket with auto-reconnect, room join/part,
and typed `ChatEvent.MESSAGE` payloads (`ChatMessage.text`, `.user.name`,
`.sent_timestamp`, `.room`). No new dependency.

Justification vs alternatives:

- **`chat-downloader` live mode** — the lib is unmaintained (last release 2023),
  screen-scrapes/undocumented, and is already our VOD dependency we'd rather not
  lean on further for a long-lived socket.
- **TwitchIO 3.x / EventSub chat** — capable, but a *new* heavyweight dependency
  and an EventSub webhook/websocket surface we don't otherwise need.
- **Raw IRC socket** — we'd reimplement reconnect, PING/PONG, RECONNECT, tag
  parsing, and JOIN rate limiting that `twitchAPI.chat.Chat` already provides.

**OAuth requirement (important).** `Chat` needs a **user access token** with
`AuthScope.CHAT_READ`, set via `twitch.set_user_authentication(...)`. Our current
`collector/twitch_api.py:TwitchAPI.twitch_api_init()` only does app-only
client-credentials (`await Twitch(client_id, client_secret)`), which is **not**
sufficient for chat. `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET` already exist and
are reused; we additionally need a one-time user OAuth for a dedicated read-only
bot account, then persist and auto-refresh its refresh token (twitchAPI refreshes
access tokens itself). Anonymous `justinfan` read is a fallback but is not a
first-class path in the Chat module — treat it as an open question (§8).

## 3. Architecture

New package `collector/live/` (keeps the sync VOD code untouched):

- **`collector/live/live_chat_collector.py` → `LiveChatCollector`** — async
  facade analogous to `TwitchCollectorFacade`. Owns one `Twitch` client + one
  `Chat` instance, registers the `ChatEvent.MESSAGE`/`READY`/`JOIN` handlers,
  and manages the join/part set of channels.
- **`collector/live/live_message_sink.py` → `LiveMessageSink`** — per-channel
  ingestion: resolves creator/stream/chatter/message_text IDs and appends message
  rows to a `DatabaseBuffer`.
- **`collector/live/live_auth.py`** — user-token acquisition/refresh/persistence.

**Reuse of existing pieces:**

- `collector/database_buffer.py:DatabaseBuffer(insert_message_db, ...)` for bulk
  `message` inserts — unchanged. It already uses the `psycopg2`
  `ThreadedConnectionPool`, so it is safe to call from the executor (§5).
- Message-row shape is identical to VOD:
  `(chatter_id, tagged_chatter_id, stream_id, message_text_id, time)` via
  `database/message_table_gateway.py:insert_message_db`.
- Creator bootstrap reuses the logic in
  `TwitchCollectorFacade.insert_creator_get_id` (`select_creator_id_db` /
  `insert_new_creator_db`) — extract it into a small shared helper so both
  facades call it.
- **Chatter / message_text mapping differs by cardinality.** The VOD path
  pre-computes whole-batch dicts (`insert_new_chatters_db` +
  `select_all_chatters_db`, `insert_message_texts_db` +
  `select_all_message_texts_db`) and hands them to `MessageHandler` via
  `set_known_chatters` / `set_known_messages`. Live is one message at a time, so
  `LiveMessageSink` instead uses the single-row upserts already in the gateways —
  `chatter_table_gateway.insert_new_chatter_db(nick)` and
  `message_text_table_gateway.find_or_insert_message_text_id_db(text)` — backed by
  an in-process cache dict per channel (safe: single event loop, §5). Tag
  resolution can reuse `MessageHandler.find_tagged_user_id`. Truncate `text` to
  `varchar(255)` (see schema) before insert.

**The `stream` row for an in-progress broadcast.** The live Twitch `Stream`
object carries a **stream-session id** (`Stream.id`), which is a *different*
number from the VOD **video id** the VOD collector currently stores in
`stream.twitch_id` (unique). Naively inserting the live row under `Stream.id` and
later letting the VOD collector insert the same broadcast under the video id
yields **two `stream` rows for one broadcast → doubled messages**. On first
message for a channel, `LiveMessageSink` inserts the stream via
`stream_table_gateway.insert_stream_db(...)` with
`start = Stream.started_at`, `title = Stream.title`,
`thumbnail_url = Stream.thumbnail_url`, and `end = NULL` (the column is nullable;
pass `None` for `stopped_at`). On stream end it sets `"end"` and calls
`update_stream_message_count_db`.

**Implemented reconciliation key.** Migration 0013 adds a separate unique
`stream.twitch_stream_session_id`, preserving the existing meaning of
`stream.twitch_id` as the VOD video id (which the frontend needs for deep links).
An in-progress row temporarily uses the negative session id as its non-null
`twitch_id`; when Twitch publishes the archive, the VOD collector attaches the
real video id and skips duplicate message ingestion. `message.source_message_id`
also makes websocket reconnect/replay idempotent.

## 4. Entry point & tracking integration

Add to `[project.scripts]`:

```
stream-sniper-live = "stream_sniper.live_service:run_live_service"
```

mirroring `stream-sniper-tracking` → `tracking_service:run_tracking_service`.
`live_service.py` loads `.env`, sets up logging, and runs the `LiveChatCollector`
event loop with SIGINT/SIGTERM handlers (copy the pattern in
`tracking_service.py`).

Two operating modes:

- **Standalone:** join a static channel list from `LIVE_CHANNELS` (comma list).
- **Tracking-driven (target):** `tracking/stream_monitor.py:StreamMonitor`
  already detects the offline→online transition ("Stream started for …") and the
  online→offline transition (which queues the VOD job). Extend those hooks to
  `join_room` when a tracked streamer goes live and `part`/finalize the stream row
  when it ends. The monitor already resolves live status via
  `TwitchAPI.get_stream_info()`, so it can pass `Stream.id`/title/started_at to
  the live collector — no extra Twitch calls.

## 5. Concurrency, backpressure, reconnect

- **Single async loop, many rooms.** One `Chat` instance joins *all* target
  channels; `ChatEvent.MESSAGE` callbacks are dispatched on one event loop, so the
  per-channel caches are plain dicts with no locking. This is the fundamental
  mismatch with the synchronous VOD facade (`asyncio.run(...)` then a blocking
  `while True`) — the live collector is loop-native and never blocks it.
- **Sync DB from async.** `DatabaseBuffer.add_item` is in-memory and cheap; the
  blocking `psycopg2` flush (`call_db_function`) is dispatched with
  `loop.run_in_executor(...)` so a slow commit never stalls message intake.
- **Batching / backpressure.** Keep `DatabaseBuffer`'s size trigger but add a
  periodic `asyncio` flush task (e.g. every `LIVE_FLUSH_INTERVAL`, default 5 s) so
  low-traffic channels still persist promptly and unflushed loss on crash is
  bounded. A very hot channel is naturally batched by buffer size.
- **Reconnect / rate limits.** `Chat` auto-reconnects; on `READY`/reconnect,
  re-`join_room` the full target set. Stagger joins to respect Twitch's JOIN rate
  (~20 joins / 10 s for a normal account) when fanning out to many channels.

## 6. Config, Docker, prod

New env (alongside existing `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET`):

```
TWITCH_BOT_REFRESH_TOKEN   # user-token refresh for CHAT_READ (persisted)
LIVE_CHANNELS              # standalone mode: comma-separated logins
LIVE_FLUSH_INTERVAL=5      # seconds
LIVE_BUFFER_SIZE=1000      # rows per flush (lower than VOD's 5000)
```

Add to `docs/../.env.example`. **Docker:** a new `live` service in
`docker-compose.yml` reusing `Dockerfile.collector`/api image with the
hot-reload bind mount, `command: ["stream-sniper-live"]`, `restart: unless-stopped`
(unlike the one-shot `collector`). **Prod** (`docker-compose.prod.yml`): a
`stream-sniper-live` service reusing `image: stream-sniper-api:latest` with
`command: ["python","-m","stream_sniper.live_service"]`, `restart: unless-stopped`,
same `POSTGRES_*`/`TWITCH_*` env block as `stream-sniper-tracking`, on the
`stream-sniper-prod` network. On the RPI it is one lightweight always-on
container; the persisted refresh token needs a small mounted volume or secret.

## 7. Failure modes, dedup, rollout

- **Crash / websocket drop:** unflushed in-memory buffer is lost → keep flush
  interval short; the **VOD collector remains the backfill** that fills any gap,
  which is the core reason it is retained.
- **Token expiry:** twitchAPI refreshes access tokens from the stored refresh
  token; alert if refresh itself fails.
- **DB pool pressure:** executor-dispatched flushes are bounded by
  `DB_POOL_MAX_CONN`; buffer absorbs spikes.
- **Live vs later-VOD dedup:** `message` rows have no natural unique key, so if
  both paths write to the *same* `stream` row they double-count. Rule: **a
  live-captured broadcast is not VOD-reprocessed.** Record the captured
  stream-session id (analogous to `tracked_streamers.last_processed_stream_id`)
  and have `StreamMonitor._queue_stream_for_processing` skip a VOD job for a
  session already captured live. With the §3 convergent-`twitch_id` change,
  stream-level dedup is automatic and only message-level reprocessing must be
  gated.

**Phased rollout:** (1) standalone CLI, one channel, verify live rows match the
later VOD for the same stream; (2) multi-channel + flush/reconnect tuning;
(3) tracking-driven auto join/part + stream finalization; (4) converge
`stream.twitch_id` on stream-session id and disable redundant VOD reprocessing.

## 8. Open questions / risks

- **Headless user OAuth on the RPI:** the initial `UserAuthenticator` flow needs a
  browser once; how do we bootstrap and store the refresh token securely? Is
  anonymous `justinfan` read viable to avoid a user token entirely?
- **`stream.twitch_id` migration:** existing rows are keyed by VOD video id;
  converging on stream-session id needs a backfill/migration plan (schema is
  applied by hand per project convention).
- **`varchar(255)` truncation:** live messages can exceed 255 chars; confirm the
  truncation policy matches whatever the VOD path currently does.
- **Message-before-stream-row ordering:** first messages may arrive before
  `get_stream_info()` returns; lazily create the `stream` row on first message and
  buffer until its id is known.
- **Timestamp source:** use `ChatMessage.sent_timestamp` (`tmi-sent-ts`) vs local
  receive time.
- **Ad-hoc channels:** creator may not exist in `creator`; reuse the
  insert-creator path, but this pulls in a Twitch `get_users` call per new channel.
