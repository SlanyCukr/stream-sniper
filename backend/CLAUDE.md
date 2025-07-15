# Stream Sniper Backend - Developer Instructions

## Development Workflow

**CRITICAL**: After every completed task or code change, MUST commit and push to repository:

```bash
git add .
git commit -m "Descriptive commit message"
git push origin main
```

## Backend-Specific Developer Instructions

The backend is a Python package for Twitch stream analytics with two main entry points:
- `stream-sniper <username>` - Data collection CLI
- `stream-sniper-api` - REST API server

## Installation & Setup

```bash
# Navigate to backend directory
cd backend

# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
stream-sniper --help
stream-sniper-api --help
```

## Architecture

### Core Components

#### Data Collection (`stream_sniper/collector/`)
- **TwitchCollectorFacade** (`twitch_collector_facade.py:17`) - Main orchestrator
- **IrcChatDownloader** (`irc_chat_downloader.py:10`) - Chat data download
- **ChatProcessor & MessageHandler** - Message processing and deduplication
- **TwitchAPI** - Twitch API integration with OAuth

#### Database Layer (`stream_sniper/database/`)
- **Table Gateway Pattern** - Separate gateway classes for each table
- **Connection Pool** - PostgreSQL connection management
- **Decorators** - Database connection and error handling

#### REST API (`stream_sniper/api/`)
- **FastAPI** framework with CORS enabled
- **Health Monitoring** - `/health`, `/health/detailed`, `/metrics/prometheus`
- **Core Endpoints** - Streams, chatters, messages, creators
- **Rate Limiting** - Built-in request throttling

### Database Schema

PostgreSQL with `stream_sniper` namespace:
- **creator** - Twitch streamers
- **stream** - Individual stream sessions  
- **chatter** - Chat participants
- **message_text** - Deduplicated message content
- **message** - Chat messages with relationships

## Key Files

### Entry Points
- `cli.py` - Command-line interface for both tools
- `api/api.py` - FastAPI application setup

### Configuration
- `pyproject.toml` - Package configuration and dependencies
- `requirements.txt` - Python dependencies
- `logging_config.py` - Logging setup

### Docker
- `Dockerfile.api` - API server container
- `Dockerfile.collector` - Data collector container

## Development Commands

```bash
# Data collection
stream-sniper <username>                    # Collect data for specific user
stream-sniper --help                        # Show CLI help

# API server
stream-sniper-api                           # Start API server on port 5002
stream-sniper-api --host 0.0.0.0 --port 8000  # Custom host/port

# Testing
pytest                                      # Run all tests
pytest tests/unit/                          # Unit tests only
pytest tests/integration/                   # Integration tests only
pytest -v                                  # Verbose output
pytest --cov=stream_sniper                 # Coverage report

# Docker development
docker-compose up api                       # API server container
docker-compose up collector                # Data collector container
docker-compose run --rm api pytest         # Run tests in container

# Package management
pip install -e ".[dev]"                    # Install with dev dependencies
pip freeze > requirements.txt              # Update requirements
```

## Code Style Requirements

- **Follow existing patterns** - Check neighboring files for conventions
- **Use existing libraries** - Never assume libraries are available, check imports
- **Security first** - Never expose secrets, use parameterized queries
- **No comments** - Unless explicitly requested
- **Database buffering** - Use `DatabaseBuffer` for batch operations
- **Error handling** - Comprehensive logging and graceful degradation
- **Type hints** - Use Python type hints for better code documentation
- **Async patterns** - Use async/await for I/O operations in API code
- **Environment variables** - Use `.env` files for configuration

## Database Development

### Connection Management
```python
# Use connection pool decorator
from stream_sniper.database.decorators import with_connection

@with_connection
def my_database_operation(connection):
    # Database operations here
    pass
```

### Table Gateway Pattern
```python
# Use existing gateways
from stream_sniper.database.creator_table_gateway import CreatorTableGateway

creator_gateway = CreatorTableGateway()
creator_id = creator_gateway.get_creator_id_by_nick("streamer_name")
```

### Batch Operations
```python
# Use DatabaseBuffer for bulk operations
from stream_sniper.collector.database_buffer import DatabaseBuffer

buffer = DatabaseBuffer()
buffer.add_message(chatter_id, stream_id, message_text_id, timestamp)
buffer.flush()  # Batch insert to database
```

## Testing

Test structure in `tests/`:
- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for workflows
- `fixtures/` - Test data and utilities

### Writing Tests
```python
# Unit test example
import pytest
from stream_sniper.utils.utils import some_function

def test_some_function():
    result = some_function("input")
    assert result == "expected_output"

# Integration test example
def test_database_integration():
    # Test database operations
    pass

# Fixtures
@pytest.fixture
def sample_stream_data():
    return {
        "title": "Test Stream",
        "creator_id": 1,
        "start_time": "2025-01-01T00:00:00Z"
    }
```

### Test Commands
```bash
pytest                                      # Run all tests
pytest tests/unit/                          # Unit tests only
pytest tests/integration/                   # Integration tests only
pytest -v                                  # Verbose output
pytest --cov=stream_sniper                 # Coverage report
pytest --cov-report=html                   # HTML coverage report
pytest -k "test_specific_function"         # Run specific test
```

## Dependencies

### Core
- **twitch-python** - Twitch API integration
- **chat-downloader** - VOD chat extraction  
- **psycopg2-binary** - PostgreSQL connectivity
- **fastapi** - REST API framework
- **uvicorn** - ASGI server

### Monitoring
- **psutil** - System metrics
- **prometheus-client** - Metrics export

## Security Notes

This codebase is designed for legitimate stream analytics:
- Read-only access to public Twitch chat data
- Standard database practices with parameterized queries
- Proper API authentication handling
- No malicious functionality detected

## API Development

### FastAPI Patterns
```python
# Endpoint example
from fastapi import APIRouter, HTTPException
from stream_sniper.api.rate_limiter import rate_limit

router = APIRouter()

@router.get("/endpoint")
@rate_limit(requests_per_minute=60)
async def get_endpoint():
    try:
        # Implementation
        return {"data": "response"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Health Check Implementation
```python
# Health check pattern
from stream_sniper.api.health import HealthChecker

health_checker = HealthChecker()
status = health_checker.check_component("database")
```

### Monitoring Integration
```python
# Metrics collection
from stream_sniper.api.monitoring import monitor_request

@monitor_request
async def monitored_endpoint():
    # Endpoint implementation
    pass
```

## Performance Features

- **Database Buffering** - Batch operations via `DatabaseBuffer`
- **Message Deduplication** - Prevents duplicate storage
- **Pagination** - API endpoints support offset-based pagination
- **Rate Limiting** - Request throttling and caching
- **Health Monitoring** - Comprehensive system status endpoints
- **Connection Pooling** - Database connection management
- **Async Processing** - Non-blocking I/O operations

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/stream_sniper

# Twitch API
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret

# API Settings
API_HOST=0.0.0.0
API_PORT=5002
CORS_ORIGINS=["http://localhost:3000"]

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

### Configuration Management
```python
# Configuration pattern
from stream_sniper.api.config import get_settings

settings = get_settings()
database_url = settings.database_url
```

## Common Backend Tasks

### Adding New API Endpoint
1. Create endpoint in appropriate router (`stream_sniper/api/`)
2. Add validation using Pydantic models
3. Implement rate limiting if needed
4. Add health check if accessing external services
5. Write unit and integration tests
6. Update API documentation

### Adding New Database Table
1. Add table creation SQL to `create_table.sql`
2. Create Table Gateway class in `database/`
3. Add foreign key relationships
4. Create test fixtures
5. Update database buffer if needed

### Adding New Data Collection Feature
1. Implement in `collector/` module
2. Add to `TwitchCollectorFacade` workflow
3. Create database gateway if needed
4. Add configuration options
5. Write comprehensive tests