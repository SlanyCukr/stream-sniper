# Stream Sniper Backend - Developer Instructions

Python 3.12 + FastAPI Twitch analytics backend. See `/CLAUDE.md` (project) and
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
- `stream-sniper-tracking` → `stream_sniper.tracking_service:run_tracking_service` — automated tracking

## Architecture

Packages under `stream_sniper/`:

- **`collector/`** — `TwitchCollectorFacade` orchestrates chat download +
  processing; `twitch_api.py` (twitchAPI OAuth, requires Twitch creds),
  `chat_processor.py`, `database_buffer.py` (batch inserts). VOD chat via
  `chat-downloader`.
- **`database/`** — **table-gateway pattern**: one gateway class per table
  (`creator_table_gateway.py`, `stream_table_gateway.py`, `user_table_gateway.py`,
  `tracked_streamers_table_gateway.py`, `processing_jobs_table_gateway.py`, …).
  `connection_pool.py` holds a `psycopg2` `ThreadedConnectionPool`; `decorators.py`
  provides `@with_connection`. Schema source of truth:
  `database/create_table.sql` (containers do **not** manage schema — apply by hand).
- **`api/`** — FastAPI app (`api/api.py:app`), auth (`auth.py`,
  `auth_endpoints.py`), tracking endpoints (`tracking_endpoints.py`), rate limiting
  (`rate_limiter.py`, slowapi), caching (`cache.py`, Redis), health/metrics
  (`health.py`, `monitoring.py`), config (`config.py`).
- **`tracking/`** — `stream_monitor.py`, `processing_queue.py`,
  `stream_processor.py`, `scheduler.py`. See `/TRACKING_SYSTEM.md`.

### Database access

```python
from stream_sniper.database.decorators import with_connection

@with_connection
def op(connection):
    ...

from stream_sniper.database.creator_table_gateway import CreatorTableGateway
creator_id = CreatorTableGateway().get_creator_id_by_nick("streamer")
```

Use `DatabaseBuffer` (`collector/database_buffer.py`) for bulk message inserts;
always parameterize queries.

## Authentication

Stack is **bcrypt** (password hashing, used directly — no passlib) + **PyJWT**
(HS256 tokens — no python-jose). The signing secret is **fail-fast**: `auth.py`
reads `JWT_SECRET_KEY` or `SECRET_KEY` at import and raises `RuntimeError` if
neither is set (so tests/imports need one in the env).

```python
from fastapi import Depends
from stream_sniper.api.auth import get_current_user, get_current_admin_user

@router.get("/protected")
async def protected(user = Depends(get_current_user)): ...

@router.post("/admin/action")
async def admin_only(user = Depends(get_current_admin_user)): ...
```

Roles are `user` / `admin`. Bootstrap an admin: `POST /auth/register`, then
`PUT /auth/users/<id>/role {"role":"admin"}` with a JWT.

## Environment Variables (actually read by the code)

```bash
# Database (connection_pool.py) — POSTGRES_* preferred, legacy un-prefixed fallback
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT
USER, PASSWORD, HOST, DATABASE, PORT   # legacy .env names, still honored
DB_POOL_MIN_CONN, DB_POOL_MAX_CONN, DB_CONNECT_TIMEOUT, DB_COMMAND_TIMEOUT

# Auth (auth.py) — one of these is REQUIRED (fail-fast)
JWT_SECRET_KEY   # preferred
SECRET_KEY       # fallback (prod compose/deploy sets this)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES   # default 30

# Twitch (collector/twitch_api.py) — REQUIRED for the collector
TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

# Redis (cache.py / rate_limiter.py / config.py)
REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
```

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

`tests/conftest.py` sets a dummy `JWT_SECRET_KEY` so API modules import under the
fail-fast. Integration/gateway tests need Postgres (`TEST_DB_*` env in CI).
Layout: `tests/unit/`, `tests/integration/`, `tests/fixtures/`.

## Docker

Multi-stage **uv** builds (`ghcr.io/astral-sh/uv` builder → `python:3.12-slim`
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

- Match neighboring files; check imports before assuming a library is available.
- Parameterized SQL only; never log/expose secrets.
- Type hints; async/await for API I/O; `DatabaseBuffer` for batch writes.
- Comprehensive logging + graceful degradation.
