# Stream Sniper Backend

The backend component of Stream Sniper - a Twitch stream analytics platform that collects, processes, and serves chat data.

## Overview

This backend provides:
- **Data Collection**: Downloads chat data from Twitch VODs
- **REST API**: Serves processed data via FastAPI endpoints
- **Database Management**: PostgreSQL integration with normalized schema

## Installation

```bash
# Install in development mode
cd backend
pip install -e .
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
│   ├── collector/          # Data collection modules
│   ├── database/           # Database layer
│   └── utils/             # Utilities
├── tests/                  # Test suite
└── pyproject.toml         # Package configuration
```

## Database Schema

- **creator** - Twitch streamers
- **stream** - Stream sessions
- **chatter** - Chat participants
- **message_text** - Deduplicated messages
- **message** - Chat messages with relationships

## Dependencies

- **twitch-python**: Twitch API integration
- **chat-downloader**: VOD chat extraction
- **psycopg2-binary**: PostgreSQL connectivity
- **fastapi**: REST API framework
- **uvicorn**: ASGI server

## Development

```bash
# Run tests
pytest

# Install dev dependencies
pip install -e ".[dev]"
```