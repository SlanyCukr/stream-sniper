# Stream Sniper

A comprehensive Twitch stream analytics platform that collects, processes, and visualizes chat data from Twitch streams.

## Project Overview

**Stream Sniper** is a multi-component system designed to analyze Twitch stream chat interactions. It downloads chat data from Twitch VODs, processes messages, stores them in a PostgreSQL database, and provides both a web dashboard and REST API for data analysis and visualization.

## Architecture

The system consists of two main components:

### 1. Data Collection Backend
- **Entry Points**: 
  - `stream-sniper <username>` - CLI command for data collection
  - `main.py <username>` - Legacy entry point (deprecated)
- **Purpose**: Downloads and processes chat data from Twitch VODs
- **Key Features**:
  - Retrieves chat messages from Twitch video archives
  - Processes user nicknames and message content
  - Stores data in normalized PostgreSQL database
  - Handles duplicate detection and data deduplication

### 2. REST API
- **Entry Points**:
  - `stream-sniper-api` - CLI command for API server
  - `python rest_api/api.py` - Legacy entry point
- **Framework**: FastAPI with CORS enabled
- **Port**: 5002
- **Purpose**: Provides HTTP endpoints for accessing processed chat data
- **Key Endpoints**:
  - `/streams/` - Get streams by creator with pagination
  - `/stream/{stream_id}/` - Get comprehensive stream information
  - `/chatter/{chatter_id}/messages/` - Get messages by specific chatter
  - `/creators` - Get all creators in database

## Database Schema

PostgreSQL database with normalized schema in `stream_sniper` namespace:

### Core Tables
- **`creator`** - Twitch streamers (id, nick, display_name, profile_image_url)
- **`stream`** - Individual stream sessions (id, twitch_id, title, start/end times, message_count, creator_id)
- **`chatter`** - Unique chat participants (id, nick)
- **`message_text`** - Deduplicated message content (id, text)
- **`message`** - Individual chat messages (id, chatter_id, stream_id, message_text_id, timestamp)

### Key Relationships
- Messages link to chatters, streams, and message text via foreign keys
- Streams belong to creators
- Support for message tagging (tagged_chatter_id in messages)

## Core Components

### Data Collection Classes (`classes/`)

#### TwitchCollectorFacade
- **File**: `classes/twitch_collector_facade.py:17`
- **Purpose**: Main orchestrator for the data collection process
- **Key Methods**:
  - `start_processing()` - Main processing loop
  - `insert_creator_get_id()` - Creator management

#### IrcChatDownloader
- **File**: `classes/irc_chat_downloader.py:10`
- **Purpose**: Downloads chat data using chat-downloader library
- **Features**: Processes Twitch video URLs, extracts chat messages

#### ChatProcessor & MessageHandler
- **Purpose**: Process chat messages, extract nicknames, handle message deduplication
- **Features**: Message parsing, user identification, database preparation

#### TwitchAPI
- **Purpose**: Integrates with Twitch API for metadata (creator info, video details)
- **Features**: OAuth authentication, video list retrieval, creator information

### Database Layer (`database/`)
- **Pattern**: Table Gateway pattern for database operations
- **Files**: Separate gateway classes for each table
- **Features**: Prepared statements, connection management, query optimization
- **Decorators**: Database connection and error handling decorators

### Utilities (`utils/`)
- **Message Processing**: Chat message parsing and transformation utilities
- **Stream Management**: Stream metadata handling and database updates

## Dependencies

### Core Libraries
- **twitch-python**: Twitch API integration
- **chat-downloader**: VOD chat extraction
- **psycopg2-binary**: PostgreSQL database connectivity
- **twitchAPI**: Additional Twitch API functionality

### Web Framework
- **fastapi**: REST API framework
- **uvicorn**: ASGI server

### Additional Tools
- **tqdm**: Progress bars
- **pytimeparse**: Time parsing utilities

## Usage

### Data Collection
```bash
# Modern CLI (recommended)
stream-sniper <twitch_username>

# Legacy method (deprecated)
python main.py <twitch_username>
```

### REST API Server
```bash
# Modern CLI (recommended)
stream-sniper-api

# Legacy method
python rest_api/api.py
# Server runs on http://0.0.0.0:5002
```

### Docker Usage
```bash
# Run API server
docker-compose up api

# Run data collector
TWITCH_USERNAME=someuser docker-compose up collector

# Run both services
docker-compose up
```

## Development Environment

- **Python Version**: 3.12
- **Virtual Environment**: `venv/` (included in repository)
- **Database**: PostgreSQL with `stream_sniper` schema
- **Configuration**: Environment variables loaded from `.env` files

## Key Features

### Analytics Capabilities
- Stream message volume analysis
- Most active chatters identification
- Message tagging and interaction analysis
- Creator cross-stream participation tracking
- Temporal message patterns

### Data Processing
- Automatic duplicate message detection
- Normalized database storage
- Batch processing with configurable buffer sizes
- Comprehensive logging and error handling

### API Interface
- RESTful endpoints for data access
- JSON response format
- Pagination support for large datasets
- CORS enabled for web client integration

## Security Considerations

The codebase appears to be designed for legitimate stream analytics purposes:
- Read-only access to public Twitch chat data
- Standard database practices with parameterized queries
- No obvious malicious functionality detected
- Proper API authentication handling

## Performance Optimizations

- **Database Buffering**: `DatabaseBuffer` class batches database operations
- **Message Deduplication**: Prevents duplicate storage of identical messages
- **Pagination**: API endpoints support offset-based pagination
- **Logging**: Comprehensive logging for debugging and monitoring

## Development Workflow

**CRITICAL**: After every completed task or code change, MUST commit and push to repository:

```bash
git add .
git commit -m "Descriptive commit message"
git push origin main
```

This ensures:
- All changes are tracked and versioned
- Each task completion is preserved
- Collaboration is seamless
- Code history is preserved
- Rollback capability is maintained

**Note**: Every modification, bug fix, feature addition, or improvement must be immediately committed and pushed upon completion.

## Modernization Status (2025-07-13)

### Security Updates Applied
- **CRITICAL**: Updated Starlette to 0.40.0+ to fix CVE-2024-47874 (score 8.7)
- Updated all dependencies to latest stable versions

### Major Changes
- **Frontend Removed**: Entire Reflex frontend has been removed
- **Dependencies Updated**: 
  - psycopg2-binary: 2.9.9 → 2.9.10
  - twitchAPI: 4.2.1 → 4.5.0 (EventSub V2 support)
  - uvicorn: 0.30.5 → 0.32.1
  - Added python-dotenv for environment variable management

### Docker Support Added
- **Dockerfile.api**: Container for REST API service
- **Dockerfile.collector**: Container for data collection service
- **docker-compose.yml**: Orchestration for both services
- **.dockerignore**: Optimized build context

### Package Structure Completed
- **pyproject.toml**: Complete package configuration for distribution
- **Entry Points**: 
  - `stream-sniper` - CLI for data collection
  - `stream-sniper-api` - REST API server
- **Package Structure**: Full migration to proper Python package layout completed
- **Namespace**: All code organized under `stream_sniper` package

### Modernization Complete ✅
- **Status**: Production Ready
- **Testing**: End-to-end validation completed with real Twitch data
- **Docker**: Fully containerized with multi-service support
- **Package**: Installable Python package with CLI entry points
- **Database**: Schema created and validated with normalized structure

### Future Improvements
See `FUTURE_IMPROVEMENTS.md` for planned enhancements including:
- API documentation with OpenAPI/Swagger
- Database connection pooling
- Comprehensive testing suite
- CI/CD pipeline with GitHub Actions
- Performance and security enhancements

### Quick Start
```bash
# Install package in development mode
pip install -e .

# Run data collection
stream-sniper <username>

# Start API server
stream-sniper-api

# Or use Docker
docker-compose up
```