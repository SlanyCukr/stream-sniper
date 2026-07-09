# Stream Sniper - Project Instructions

Twitch stream analytics platform: downloads chat from Twitch VODs, stores it in PostgreSQL, and serves a Next.js dashboard + FastAPI REST API with JWT auth, admin controls, and automated streamer tracking.

Component-specific docs:
- **Backend**: `backend/CLAUDE.md`
- **Frontend**: `frontend/CLAUDE.md`
- **Tracking system**: `TRACKING_SYSTEM.md`

## Architecture

- **Backend** (`backend/`, Python 3.14 + FastAPI, uv-managed with committed `uv.lock`): packages `api/`, `auth/`, `collector/`, `database/`, `tracking/`. Entry points: `stream-sniper <username>` (collection), `stream-sniper-api` (REST), `stream-sniper-tracking` (automation).
- **Frontend** (`frontend/`, Next.js 16 App Router + React 19, Bootstrap/SASS): `app|components|views|contexts|lib|hooks|styles`, admin UI under `app/(app)/admin/`. See `frontend/CLAUDE.md`.
- **Database**: PostgreSQL, normalized schema in the `stream_sniper` namespace — **external**, not in Docker Compose. Schema is versioned with **Alembic** (`backend/stream_sniper/database/migrations/`, hand-written raw-SQL migrations — no ORM/autogenerate). `create_table.sql` is a **reference-only** snapshot of the baseline table set, mirrored by revision `0001` (which additionally creates the `stream_sniper` schema). Tables: `creator`, `stream`, `chatter`, `message_text` (deduplicated content), `message`, plus `users`, `tracked_streamers`, `processing_jobs`.

## Quick Start

Docker is the primary path (hot reload for both components; no local Node/Python needed):

```bash
docker-compose up                                  # everything
docker-compose up api|frontend|tracking            # single service
TWITCH_USERNAME=someuser docker-compose up collector
docker-compose up --build                          # after dependency changes
docker-compose logs -f api|frontend|tracking
```

Local alternative: `cd backend && uv sync` then `uv run stream-sniper-api` (or the other entry points above); `cd frontend && npm install && npm run dev`.

Ports: API 5002, frontend 3000. Health: `curl http://localhost:5002/health` (also `/metrics`). Admin panel at `/admin` after login.

Required env: the API/tracking fail fast without a JWT signing secret — set `JWT_SECRET_KEY` (or `SECRET_KEY`). The collector requires `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET`. DB connection uses `USER/PASSWORD/HOST/DATABASE/PORT` (see `.env.example`).

## Database setup

```bash
psql -U postgres -c "CREATE DATABASE stream_sniper;"
cd backend && uv run alembic upgrade head    # creates schema + tables + indexes (fresh DB)
# Bootstrap admin: POST /auth/register, then PUT /auth/users/<id>/role {"role":"admin"} with a JWT
```

`alembic upgrade head` creates the `stream_sniper` schema itself (no manual `CREATE SCHEMA`). For an **existing** DB predating Alembic (e.g. prod), stamp the baseline first — see the one-time prod runbook below.

Schema is versioned via Alembic and is **not** auto-run on deploy (a revision may build an index `CONCURRENTLY` on a large table). After deploying, run migrations explicitly: `docker exec stream-sniper-api stream-sniper-migrate upgrade head`.

## Testing

```bash
docker-compose run --rm api pytest        # in-container
cd backend && uv run pytest tests/unit     # local unit tests
```

## Production

Deployed on RPI infrastructure (pi5ram8), HTTPS via VPS reverse proxy:
- Frontend: https://stream-sniper.slanycukr.com — a Next.js `output: standalone` **Node** container (not nginx), prod compose maps host `3001 -> 3000`.
- API: not on its own subdomain — the frontend proxies `/api/*` to the backend container (Next.js `rewrites()` → `API_PROXY_TARGET`); reachable at https://stream-sniper.slanycukr.com/api.

```bash
docker-compose -f docker-compose.prod.yml up -d stream-sniper-frontend
```

### Database migrations (manual — not auto-run on deploy)

Migrations run via the packaged `stream-sniper-migrate` entry point (works inside the
source-less prod image; `uv run alembic` is dev-only). **One-time bootstrap** on the
existing prod DB (it already has every table but no `alembic_version`) — stamp the
baseline `0001` (**never `head`**, or `0002` never builds the index), then upgrade:

```bash
docker exec stream-sniper-api stream-sniper-migrate current   # expect empty
docker exec stream-sniper-api stream-sniper-migrate stamp 0001
docker exec stream-sniper-api stream-sniper-migrate upgrade head   # builds the index CONCURRENTLY
docker exec stream-sniper-api stream-sniper-migrate current   # -> 0002 (head)
```

After each future deploy that adds a revision, run `docker exec stream-sniper-api stream-sniper-migrate upgrade head`.
If a `CONCURRENTLY` build is interrupted it leaves an INVALID index — `DROP INDEX CONCURRENTLY stream_sniper.<name>;` then re-run.

## Gotchas

- Port conflicts: 5002 (API) / 3000 (frontend).
- Restart containers after `.env` changes; rebuild after package changes.
- Hot reload broken → check volume mounts in docker-compose.yml; last resort `docker-compose down -v && docker-compose up --build`.
