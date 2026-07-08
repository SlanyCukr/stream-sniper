# Stream Sniper - Project Instructions

Twitch stream analytics platform: downloads chat from Twitch VODs, stores it in PostgreSQL, and serves a Next.js dashboard + FastAPI REST API with JWT auth, admin controls, and automated streamer tracking.

Component-specific docs:
- **Backend**: `backend/CLAUDE.md`
- **Frontend**: `frontend/CLAUDE.md`
- **Tracking system**: `TRACKING_SYSTEM.md`

## Architecture

- **Backend** (`backend/`, Python 3.14 + FastAPI, uv-managed with committed `uv.lock`): packages `api/`, `auth/`, `collector/`, `database/`, `tracking/`. Entry points: `stream-sniper <username>` (collection), `stream-sniper-api` (REST), `stream-sniper-tracking` (automation).
- **Frontend** (`frontend/`, Next.js 16 App Router + React 19, Bootstrap/SASS): `app|components|views|contexts|lib|hooks|styles`, admin UI under `app/(app)/admin/`. See `frontend/CLAUDE.md`.
- **Database**: PostgreSQL, normalized schema in the `stream_sniper` namespace — **external**, not in Docker Compose. Schema source of truth: `backend/stream_sniper/database/create_table.sql`. Tables: `creator`, `stream`, `chatter`, `message_text` (deduplicated content), `message`, plus `users`, `tracked_streamers`, `processing_jobs`.

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
psql -U postgres -d stream_sniper -f backend/stream_sniper/database/create_table.sql
# Bootstrap admin: POST /auth/register, then PUT /auth/users/<id>/role {"role":"admin"} with a JWT
```

Containers do **not** manage DB schema — apply changes manually.

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

## Gotchas

- Port conflicts: 5002 (API) / 3000 (frontend).
- Restart containers after `.env` changes; rebuild after package changes.
- Hot reload broken → check volume mounts in docker-compose.yml; last resort `docker-compose down -v && docker-compose up --build`.
