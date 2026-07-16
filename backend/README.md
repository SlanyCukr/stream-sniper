# Stream Sniper Backend

The backend component of Stream Sniper - a Twitch stream analytics platform that collects, processes, and serves chat data.

## Overview

This backend provides:

- **Data Collection**: Captures Twitch VOD and live chat
- **REST API**: Serves typed analytics and operational endpoints with FastAPI
- **Analytics Jobs**: Builds stream rollups, digests, and bot classifications
- **Database Management**: Uses function-based PostgreSQL table gateways and Alembic migrations

## Installation

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`uv.lock` is the
single source of truth; there is no `requirements.txt`).

```bash
# Create the virtualenv from the lockfile (includes the dev group)
cd backend
uv sync

# Run an entry point inside the managed environment
uv run stream-sniper --help
```

## Usage

### Data Collection

```bash
stream-sniper <twitch_username>
```

### API Server

```bash
stream-sniper-api
```

### Docker
```bash
# Run API server
docker-compose up api

# Run data collector
TWITCH_USERNAME=someuser docker-compose up collector
```

## API Endpoints

- `GET /health` - Health check
- `GET /health/detailed` - Detailed system status
- `GET /metrics/prometheus` - Prometheus metrics
- `GET /streams/` - Get streams with pagination
- `GET /stream/{stream_id}/` - Get stream details
- `GET /chatter/{chatter_id}/messages/` - Get chatter messages
- `GET /creators` - Get all creators

## Architecture

```
backend/
├── stream_sniper/           # Main package
│   ├── api/                # REST API components
│   │   └── features/       # Domain routers and transport models
│   ├── application/        # Cross-gateway query and write-workflow orchestration
│   ├── analytics/          # Rollups, digests, and enrichment jobs
│   ├── collector/          # Archived-stream, VOD, and live-chat collection
│   ├── database/           # Function-based table gateways and migrations
│   └── tracking/           # Stream monitoring and processing queue
├── tests/                  # Test suite
└── pyproject.toml         # Package configuration
```

API routers own HTTP validation, authorization, caching, and error translation.
They may call a single table gateway for narrow CRUD, while workflows spanning
multiple gateways belong under `application/`.

## Database Schema

- **creator** - Twitch streamers
- **stream** - Stream sessions
- **chatter** - Chat participants
- **message_text** - Deduplicated messages
- **message** - Chat messages with relationships

## Dependencies

- **twitchAPI**: Twitch API integration
- **requests**: project-owned Twitch archived-chat GraphQL client
- **psycopg2-binary**: PostgreSQL connectivity
- **fastapi**: REST API framework
- **uvicorn**: ASGI server

## Development

```bash
# Sync the environment (dev tools are in the PEP 735 dev group, installed by default)
uv sync

# Run tests
uv run pytest

# Lint and type-check
uv run ruff check .
uv run mypy stream_sniper/
```
