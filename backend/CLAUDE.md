# Stream Sniper Backend - Developer Instructions

Python 3.14 + FastAPI Twitch analytics backend. See `/CLAUDE.md` (project) and
`/frontend/CLAUDE.md` (frontend).

## Development Workflow

Work on a **feature branch and open a PR** — do not push to `main`. Pushing to
`main` triggers the RPI production deploy (`.github/workflows/deploy.yml`).

Dependencies are managed with **uv** (`uv.lock` is the single source of truth;
there is no `requirements.txt`). Dev tools live in the PEP 735
`[dependency-groups] dev` group.

```bash
cd backend
uv sync                       # create .venv from uv.lock (incl. dev group)
uv sync --locked              # verify the lock is up to date (CI uses this)
uv run stream-sniper --help   # run an entry point inside the venv
uv add <pkg>                  # add a runtime dep (updates pyproject + uv.lock)
uv add --dev <pkg>            # add a dev-only dep
uv lock                       # re-resolve after manual pyproject edits
```

Tooling is **ruff** (replaces black/isort/flake8) + **mypy** (soft):

```bash
uv run ruff check .           # lint
uv run ruff check . --fix     # autofix
uv run ruff format .          # format (not enforced in CI yet)
uv run mypy stream_sniper/    # type check (advisory)
```

## Entry Points (`[project.scripts]`)

- `stream-sniper <username>` → `stream_sniper.cli:main` — data collection CLI
- `stream-sniper-api` → `stream_sniper.api.server:run` — REST API on :5002
- `stream-sniper-tracking` → `stream_sniper.tracking.service:run_tracking_service` — automated tracking
- `stream-sniper-migrate` → `stream_sniper.database.commands.migrate:main` — packaged Alembic wrapper (the prod/container way to run migrations; needs no `alembic.ini` or cwd)
- `stream-sniper-rollup` → `stream_sniper.analytics.operations.backfill:main` — analytics rollup backfill
- `stream-sniper-classify-bots` → `stream_sniper.analytics.operations.bot_detection:main` — chatter classification
- `stream-sniper-digest` → `stream_sniper.analytics.operations.digest:main` — analytics digest generation
- `stream-sniper-live` → `stream_sniper.collector.live.service:run_live_service` — live-chat service
- `stream-sniper-live-auth` → `stream_sniper.collector.live.auth_cli:main` — interactive Twitch authorization

## Architecture

Packages under `stream_sniper/`:

- **`collector/`** — `TwitchCollectorFacade` composes creator lookup, VOD ingestion,
  and the Twitch adapter. `vod_ingestion.py` owns persistence orchestration,
  `twitch_vod_chat_downloader.py` selects VODs while `twitch_archived_chat.py` owns
  the Twitch GraphQL pagination contract, and `live/` contains the
  loop-native live collector and message sink. `database_buffer.py` batches writes.
- **`application/`** — typed read/query orchestration spanning multiple gateways.
  FastAPI handlers own HTTP and caching concerns; application queries assemble the
  domain result without importing FastAPI. Application-owned Pydantic models are
  reusable read contracts for those workflows; `api/features/` models are reserved
  for HTTP-specific request or response shapes.
- **`analytics/`** — offline rollups, scene/moment enrichment, digests, and bot
  classification jobs.
- **`database/`** — **function-based table-gateway pattern**: each `*_table_gateway.py`
  owns parameterized operations for one table or aggregate. `core/connection_pool.py`
  owns scoped `psycopg2` `ThreadedConnectionPool` lifecycles; `core/decorators.py` provides
  `@with_cursor`. Gateways are grouped by capability: `analytics/` for stream-wide
  rollups, `content/` for moments and scenes, `community/` for audience relationships,
  and `creators/` for creator-specific analytics. Schema is versioned with **Alembic** in
  `database/migrations/` — hand-written raw SQL (`op.execute` / `op.create_*`, **not**
  autogenerate; there are no ORM models). `database/create_table.sql` is a
  reference-only baseline snapshot mirrored by revision `0001`.
- **`api/`** — `api.py:create_app` is the reusable FastAPI composition root and
  `asgi.py:app` is the environment-loading production ASGI boundary. Platform
  concerns include auth/policy, runtime startup, caching, error boundaries, health,
  monitoring, rate limiting, and config. **`api/features/`** groups routers by
  product domain (`auth/`, `tracking/`, `streams/`, `content/`, `creators/`,
  `community/`, `chatters/`, and `operations/`) and keeps only HTTP-specific models
  beside them. Multi-gateway assembly belongs in `application/`;
  simple single-gateway CRUD and streaming response adapters may remain in handlers.
- **`tracking/`** — `stream_monitor.py`, `processing_queue.py`,
  `stream_processor.py`, `scheduler.py`. See `/TRACKING_SYSTEM.md`.
- **`utils/`** — cross-cutting helpers with no domain dependencies
  (`discord.py` owns Discord webhook delivery, shared by the scene digest CLI
  and the tracking went-live alerts).

### Database access

```python
from stream_sniper.database.core.decorators import with_cursor

@with_cursor
def select_example_db(*, cursor):
    cursor.execute("SELECT value FROM stream_sniper.example")
    return cursor.fetchone()

from stream_sniper.database.gateways.identity.creator_table_gateway import select_creator_id_db
creator_id = select_creator_id_db("streamer")
```

Use `@with_cursor` for standalone reads. CRUD modules may pair `read_cursor()` with
`write_cursor()` so transaction ownership remains visible beside their mutations;
modules that mix protocols keep decorated operations read-only and explicit blocks
for writes.

Use `DatabaseBuffer` (`collector/archived/database_buffer.py`) for bulk message inserts;
always parameterize queries.

### Database migrations (Alembic)

```bash
cd backend
uv run alembic revision -m "add X" --rev-id NNNN   # then edit upgrade()/downgrade() with raw SQL
uv run alembic upgrade head                        # local dev
uv run alembic current | history | heads           # inspect
```

Rules:
- **Hand-written raw SQL only** — no autogenerate, no models. Schema-qualify every
  object (`stream_sniper.<name>`) so offline (`--sql`) mode works.
- **`CREATE INDEX CONCURRENTLY` / any non-transactional DDL must use
  `with op.get_context().autocommit_block():`** and be the sole DDL in its revision
  (Alembic wraps migrations in a transaction by default). Such revisions must refuse
  offline mode (check `op.get_context().as_sql`). See `0002_chatter_nick_lower_prefix_idx.py`.
- **Schema creation lives in `env.py`** (a separate committed transaction, before the
  version table), because `version_table_schema="stream_sniper"` makes Alembic create
  `alembic_version` before any migration runs. `env.py` reuses `connection_pool.py`'s
  `POSTGRES_*` environment contract — no migration-only aliases are introduced.
- **Prod is manual:** `docker exec stream-sniper-api stream-sniper-migrate upgrade head`
  (see root `CLAUDE.md` runbook). Migrations are intentionally **not** in `deploy.yml`.
  `uv run alembic` is **dev-only** (no `uv`/source in the prod image; use
  `stream-sniper-migrate` there — the migrations dir is packaged into the wheel, so it
  works inside `stream-sniper-api` / `stream-sniper-tracking`).

## Authentication

Stack is **bcrypt** (password hashing, used directly — no passlib) + **PyJWT**
(HS256 tokens — no python-jose). `load_config()` reads `JWT_SECRET_KEY` or
`SECRET_KEY` into `AuthConfig`; `create_app()` validates that explicit snapshot at
the composition boundary. Importing `auth.py` or the application factory does not
read environment state or require a signing secret.

```python
from fastapi import Depends
from stream_sniper.api.security.auth import get_current_user, get_current_admin_user

@router.get("/protected")
async def protected(user = Depends(get_current_user)): ...

@router.post("/admin/action")
async def admin_only(user = Depends(get_current_admin_user)): ...
```

Roles are `user` / `admin`. Bootstrap an admin: `POST /auth/register`, then
`PUT /auth/users/<id>/role {"role":"admin"}` with a JWT.

## Environment Variables (actually read by the code)

```bash
# Database (connection_pool.py and migrations/env.py)
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT
DB_POOL_MIN_CONN, DB_POOL_MAX_CONN, DB_CONNECT_TIMEOUT, DB_COMMAND_TIMEOUT

# Auth (load_config at API composition) — one of these is REQUIRED for the API
JWT_SECRET_KEY   # preferred
SECRET_KEY       # fallback (prod compose/deploy sets this)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES   # default 30

# Twitch (collector/twitch_api.py) — REQUIRED for the collector
TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
```

Caching and rate limiting are **in-process** (no Redis / external store): `cache.py`
is a thread-safe TTL dict; `rate_limiter.py` uses slowapi's `memory://` storage.
Both are per-process and reset on restart — fine for the single-process API.

See `.env.example` for the full surface (cache TTLs, rate limits, CORS,
monitoring).

## Testing

```bash
uv run pytest                 # full suite
uv run pytest tests/unit      # unit tests
uv run pytest tests/integration
uv run pytest --cov=stream_sniper
docker-compose run --rm api pytest   # in-container
```

API tests construct explicit `APIConfig` snapshots; imports do not require auth
environment state. Integration/gateway tests need Postgres (`TEST_DB_*` env in CI).
Layout: `tests/unit/`, `tests/integration/`, `tests/fixtures/`.

## Docker

Multi-stage **uv** builds (`ghcr.io/astral-sh/uv` builder → `python:3.14-slim`
runtime, non-root `app` user, no gcc needed — all deps ship manylinux wheels):

- `Dockerfile.api` — API image. CMD runs `uvicorn ... :5002` **without** `--reload`.
  Dev hot-reload is a `docker-compose.yml` command override + a bind mount of
  `./backend/stream_sniper` onto the installed package path in the venv's
  site-packages (not baked into the image).
- `Dockerfile.collector` — `ENTRYPOINT ["stream-sniper"]`, username as arg.

```bash
docker-compose up api                     # dev, hot reload
docker-compose logs -f api
TWITCH_USERNAME=someuser docker-compose up collector
```

## Code Style

- Never log/expose secrets; async/await for API I/O; graceful degradation over crashes.
