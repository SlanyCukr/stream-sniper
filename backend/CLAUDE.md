# Stream Sniper Backend - Developer Instructions

**Cross-Reference**: See main project instructions in `/CLAUDE.md` and frontend instructions in `/frontend/CLAUDE.md`

## Development Workflow

**CRITICAL**: After every completed task or code change, MUST commit and push to repository:

```bash
git add .
git commit -m "Descriptive commit message"
git push origin main
```

## Backend-Specific Developer Instructions

The backend is a Python package for Twitch stream analytics with three main entry points:
- `stream-sniper <username>` - Data collection CLI
- `stream-sniper-api` - REST API server
- `stream-sniper-tracking` - Automated tracking service

## Recent Major Updates

This backend now includes:
- **Authentication System**: JWT-based authentication with role-based access control
- **Admin Interface**: Complete admin API endpoints for system management
- **Automated Tracking**: Background service for streamer monitoring and processing
- **Enhanced Security**: Password hashing, rate limiting, and protected routes

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
- **Authentication Endpoints** - Login, register, user management
- **Admin Endpoints** - User management, system stats, tracking control
- **Rate Limiting** - Built-in request throttling
- **Protected Routes** - JWT authentication middleware

### Database Schema

PostgreSQL with `stream_sniper` namespace:
- **creator** - Twitch streamers
- **stream** - Individual stream sessions  
- **chatter** - Chat participants
- **message_text** - Deduplicated message content
- **message** - Chat messages with relationships
- **users** - System users with authentication
- **tracked_streamers** - Streamers monitored by automation
- **processing_jobs** - Background processing jobs

### New Components (Recent)

#### Authentication System (`stream_sniper/api/auth.py`)
- **JWT Token Management** - Secure token generation and validation
- **Password Hashing** - bcrypt for secure password storage
- **Role-based Access** - User and admin role management
- **Session Management** - Token expiration and refresh

#### Admin Endpoints (`stream_sniper/api/auth_endpoints.py`)
- **User Management** - CRUD operations for users
- **System Statistics** - Real-time system monitoring
- **Role Management** - Admin-only user role controls
- **Account Controls** - User activation/deactivation

#### Tracking System (`stream_sniper/tracking/`)
- **Stream Monitor** - Polls Twitch API for stream status
- **Processing Queue** - Manages background processing jobs
- **Stream Processor** - Handles chat data collection
- **Scheduler** - Coordinates all tracking services

#### Tracking Endpoints (`stream_sniper/api/tracking_endpoints.py`)
- **Streamer Management** - Add/remove tracked streamers
- **Job Monitoring** - View and control processing jobs
- **Service Control** - Start/stop/restart tracking service
- **Statistics** - Tracking system metrics

## Key Files

### Entry Points
- `cli.py` - Command-line interface for collection and API
- `api/api.py` - FastAPI application setup with authentication
- `tracking_service.py` - Automated tracking service entry point

### Configuration
- `pyproject.toml` - Package configuration and dependencies
- `requirements.txt` - Python dependencies
- `logging_config.py` - Logging setup

### Authentication & Database
- `database/user_table_gateway.py` - User database operations
- `database/tracked_streamers_table_gateway.py` - Tracking database operations
- `database/processing_jobs_table_gateway.py` - Job management database operations
- `api/protected_routes.py` - Route protection middleware

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

# Tracking service
stream-sniper-tracking                      # Start automated tracking service

# Authentication examples
curl -X POST http://localhost:5002/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"admin123"}'

curl -X POST http://localhost:5002/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

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

### Authentication & Security
- **python-jose[cryptography]** - JWT token handling
- **passlib[bcrypt]** - Password hashing
- **python-multipart** - Form data handling
- **python-dotenv** - Environment variable management

### Background Processing
- **asyncio** - Asynchronous processing
- **aiofiles** - Async file operations
- **schedule** - Job scheduling (for tracking service)

### Monitoring
- **psutil** - System metrics
- **prometheus-client** - Metrics export

## Security Features

This codebase is designed for legitimate stream analytics with comprehensive security:
- Read-only access to public Twitch chat data
- Standard database practices with parameterized queries
- JWT-based authentication with secure token handling
- Password hashing using bcrypt with salt
- Role-based access control (user/admin)
- Rate limiting on authentication endpoints
- Input validation and sanitization
- Protected routes with authentication middleware
- No malicious functionality detected

## Authentication System

### JWT Implementation
```python
# Token generation example
from stream_sniper.api.auth import create_access_token

access_token = create_access_token(
    data={"sub": username, "role": "user"}
)
```

### Password Security
```python
# Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash("plain_password")
verified = pwd_context.verify("plain_password", hashed_password)
```

### Role-based Access
```python
# Protected endpoint example
from fastapi import Depends
from stream_sniper.api.auth import get_current_admin_user

@router.get("/admin/endpoint")
async def admin_only_endpoint(
    current_user: User = Depends(get_current_admin_user)
):
    # Admin-only functionality
    pass
```

## API Development

### FastAPI Patterns
```python
# Endpoint example
from fastapi import APIRouter, HTTPException, Depends
from stream_sniper.api.rate_limiter import rate_limit
from stream_sniper.api.auth import get_current_user

router = APIRouter()

@router.get("/endpoint")
@rate_limit(requests_per_minute=60)
async def get_endpoint(current_user = Depends(get_current_user)):
    try:
        # Implementation with user context
        return {"data": "response", "user": current_user.username}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin-only endpoint
@router.post("/admin/endpoint")
async def admin_endpoint(
    current_user = Depends(get_current_admin_user)
):
    # Admin functionality
    return {"message": "Admin operation completed"}
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
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=stream_sniper
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Twitch API
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret

# Authentication
SECRET_KEY=your_secret_key_for_jwt_signing
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# API Settings
API_HOST=0.0.0.0
API_PORT=5002
CORS_ORIGINS=["http://localhost:3000"]

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Tracking Service
MONITOR_INTERVAL=300  # 5 minutes
MAX_CONCURRENT_JOBS=3
MAX_RETRIES=3
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
3. Implement authentication/authorization if needed
4. Implement rate limiting if needed
5. Add health check if accessing external services
6. Write unit and integration tests
7. Update API documentation

### Adding Authentication to Endpoint
```python
from fastapi import Depends
from stream_sniper.api.auth import get_current_user, get_current_admin_user

# User authentication required
@router.get("/protected")
async def protected_endpoint(
    current_user = Depends(get_current_user)
):
    return {"message": f"Hello {current_user.username}"}

# Admin authentication required
@router.post("/admin/action")
async def admin_action(
    current_user = Depends(get_current_admin_user)
):
    return {"message": "Admin action completed"}
```

### Managing Tracked Streamers
```python
from stream_sniper.database.tracked_streamers_table_gateway import TrackedStreamersTableGateway

gateway = TrackedStreamersTableGateway()

# Add streamer to tracking
streamer_id = gateway.add_tracked_streamer(
    creator_id=123,
    twitch_username="streamer_name",
    display_name="Streamer Display Name",
    created_by=user_id
)

# Update streamer settings
gateway.update_tracked_streamer(
    streamer_id=streamer_id,
    is_active=True,
    processing_enabled=True
)
```

### Managing Processing Jobs
```python
from stream_sniper.database.processing_jobs_table_gateway import ProcessingJobsTableGateway

gateway = ProcessingJobsTableGateway()

# Create new job
job_id = gateway.create_job(
    tracked_streamer_id=streamer_id,
    twitch_stream_id=stream_id
)

# Update job status
gateway.update_job_status(
    job_id=job_id,
    status="completed"
)
```

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
6. Update tracking system if needed

### Tracking Service Management
```python
# Start tracking service programmatically
from stream_sniper.tracking.scheduler import TrackingScheduler

scheduler = TrackingScheduler()
scheduler.start()

# Check service status
status = scheduler.get_status()
print(f"Service running: {status['running']}")

# Stop service
scheduler.stop()
```

### Database Migrations
When adding new tables or columns:
1. Update `create_table.sql` with new schema
2. Create migration script if needed
3. Update table gateway classes
4. Add corresponding API endpoints
5. Update frontend components if needed
6. Write tests for new functionality