# Stream Sniper Modernization Plan

## Current State Analysis

### Python Version
- **Current**: Python 3.12 (based on .pyc files)
- **Minimum Required**: Python 3.10 (due to union type syntax with `|` operator in frontend code)
- **Recommendation**: Target Python 3.10+ for compatibility

### Security Vulnerabilities Found
- **CRITICAL**: FastAPI's Starlette dependency has CVE-2024-47874 (score 8.7)
  - Affects all Starlette versions prior to 0.39.2
  - Fixed in Starlette 0.40.0+
  - **Action Required**: Update immediately

### Outdated Dependencies
1. **psycopg2-binary**: 2.9.9 → 2.9.10 (minor update available)
2. **twitchAPI**: 4.2.1 → 4.5.0 (major features, EventSub V2 support)
3. **uvicorn**: 0.30.5 → 0.32.1 (several updates available)
4. **reflex**: 0.6.3 (to be removed with frontend)

### Missing Dependencies
- **python-dotenv**: Not in requirements.txt but needed for environment variable loading

## Tasks Completed

1. ✅ Updated requirements.txt with security fixes
2. ✅ Removed frontend directory
3. ✅ Removed reflex dependency
4. ✅ Added python-dotenv to requirements
5. ✅ Updated main.py and api.py to load .env files
6. ✅ Created Docker configuration files:
   - Dockerfile.api
   - Dockerfile.collector
   - docker-compose.yml
   - .dockerignore
7. ✅ Created pyproject.toml for UVX packaging
8. ✅ Started package structure setup

## Remaining Tasks

### 1. Complete Package Restructuring
The current flat structure needs to be reorganized for proper packaging:

```
stream-sniper/
├── src/stream_sniper/
│   ├── __init__.py
│   ├── cli.py              # Entry point for collector
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py       # FastAPI app
│   │   └── endpoints.py    # API routes
│   ├── collector/
│   │   ├── __init__.py
│   │   ├── facade.py       # TwitchCollectorFacade
│   │   ├── downloader.py   # IrcChatDownloader
│   │   ├── processor.py    # ChatProcessor
│   │   └── handler.py      # MessageHandler
│   ├── database/
│   │   ├── __init__.py
│   │   ├── gateways/       # Table gateway classes
│   │   ├── decorators.py
│   │   └── buffer.py
│   └── utils/
│       ├── __init__.py
│       └── message_utils.py
├── tests/
├── docs/
├── docker/
├── pyproject.toml
└── README.md
```

### 2. API Documentation Enhancement
Add OpenAPI/Swagger documentation:
- Add response models with Pydantic
- Add endpoint descriptions
- Add example requests/responses
- Enable automatic API docs at `/docs`

### 3. Database Performance Improvements
Implement connection pooling:
- Replace per-query connections with connection pool
- Use `psycopg2.pool.ThreadedConnectionPool`
- Configure min/max connections
- Add connection retry logic

### 4. Code Quality Improvements
- Add type hints throughout the codebase
- Add docstrings to all functions/classes
- Implement logging configuration
- Add error handling and validation
- Remove hardcoded values

### 5. Testing Infrastructure
- Create unit tests for core functionality
- Add integration tests for API endpoints
- Set up pytest configuration
- Add test coverage reporting

### 6. CI/CD Setup
- GitHub Actions for testing
- Automated dependency updates
- Security scanning
- Docker image building

### 7. Documentation
- Update README with new structure
- Add API documentation
- Create deployment guide
- Document environment variables

### 8. Advanced Features
- Add Redis caching layer
- Implement websocket support for real-time updates
- Add rate limiting to API
- Add authentication/authorization
- Implement async database operations

## Environment Variables Required
```
# PostgreSQL
POSTGRES_HOST=89.221.212.146
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=slanycukr
POSTGRES_PASSWORD=<password>

# Twitch API
TWITCH_CLIENT_ID=<client_id>
TWITCH_CLIENT_SECRET=<client_secret>

# Docker (optional)
TWITCH_USERNAME=<username_for_collector>
```

## Docker Usage
```bash
# Build and run API
docker-compose up api

# Run collector for specific user
TWITCH_USERNAME=someuser docker-compose up collector

# Or run both
docker-compose up
```

## UVX Installation (after packaging)
```bash
# Install globally
uvx install stream-sniper

# Run collector
stream-sniper <username>

# Run API
stream-sniper-api
```

## Security Considerations
- The project appears to be for legitimate analytics purposes
- No malicious code detected
- Proper parameterized queries used
- Consider adding API authentication for production use

## Performance Optimizations Needed
1. Database indexing on frequently queried columns
2. Batch processing optimization in DatabaseBuffer
3. Query optimization for complex joins
4. Caching layer for repeated queries
5. Async operations for better concurrency

## Next Steps Priority
1. **URGENT**: Deploy security fixes (Starlette update)
2. **HIGH**: Complete package restructuring
3. **HIGH**: Add proper error handling and logging
4. **MEDIUM**: Implement connection pooling
5. **MEDIUM**: Add comprehensive tests
6. **LOW**: Add advanced features (caching, websockets)