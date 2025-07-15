# Stream Sniper - Project Instructions

A comprehensive Twitch stream analytics platform that collects, processes, and visualizes chat data from Twitch streams.

## Project Overview

**Stream Sniper** is a multi-component system designed to analyze Twitch stream chat interactions. It downloads chat data from Twitch VODs, processes messages, stores them in a PostgreSQL database, and provides both a web dashboard and REST API for data analysis and visualization.

## Architecture

The system consists of three main components:

### 1. Backend (`backend/`)
- **Data Collection**: Downloads and processes chat data from Twitch VODs
- **REST API**: FastAPI server providing HTTP endpoints for data access
- **Database**: PostgreSQL integration with normalized schema
- **Entry Points**: 
  - `stream-sniper <username>` - CLI command for data collection
  - `stream-sniper-api` - REST API server

### 2. Frontend (`frontend/`)
- **React Application**: Modern React-based web interface
- **Analytics Dashboard**: Stream browsing, chat analysis, and visualization
- **API Integration**: Connects to backend REST API
- **Development Server**: `npm start` for local development

### 3. Database (External)
- **PostgreSQL**: Normalized schema in `stream_sniper` namespace
- **External Service**: Not included in Docker Compose (separate instance required)

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

## Quick Start

### Backend Development
```bash
cd backend
pip install -e .
stream-sniper <username>      # Data collection
stream-sniper-api             # API server
```

### Frontend Development
```bash
cd frontend
npm install
npm start                     # Development server
```

### Docker (Recommended)
```bash
docker-compose up             # All services
docker-compose up api         # API only
docker-compose up frontend    # Frontend only
```

## Project Structure

```
stream-sniper/
├── README.md                 # Project overview
├── CLAUDE.md                 # Project-wide instructions
├── docker-compose.yml        # Docker orchestration
├── backend/                  # Python backend
│   ├── README.md            # Backend documentation
│   ├── CLAUDE.md            # Backend developer instructions
│   ├── stream_sniper/       # Main Python package
│   └── tests/               # Test suite
└── frontend/                 # React frontend
    ├── README.md            # Frontend documentation
    ├── CLAUDE.md            # Frontend developer instructions
    ├── src/                 # React source code
    └── public/              # Static assets
```

## Development Environment

- **Python Version**: 3.12
- **Node.js Version**: 18+
- **Database**: PostgreSQL with `stream_sniper` schema (external, not included in Docker Compose)
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

### Web Interface
- React-based dashboard for stream analytics
- Twitch-style chat visualization
- Interactive filtering and pagination
- Real-time data updates

## Security Considerations

The codebase is designed for legitimate stream analytics purposes:
- Read-only access to public Twitch chat data
- Standard database practices with parameterized queries
- No obvious malicious functionality detected
- Proper API authentication handling

## Performance Optimizations

- **Database Buffering**: Batch database operations
- **Message Deduplication**: Prevents duplicate storage
- **Pagination**: API endpoints support offset-based pagination
- **Frontend Optimization**: Code splitting and memoization
- **Comprehensive Monitoring**: Health checks and metrics endpoints

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

## Common Development Tasks

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "Description of changes"

# Push to remote
git push origin main

# Create feature branch
git checkout -b feature/new-feature

# Merge back to main
git checkout main
git merge feature/new-feature
```

### Database Setup
```bash
# Create database and schema
psql -U postgres -c "CREATE DATABASE stream_sniper;"
psql -U postgres -d stream_sniper -f backend/stream_sniper/database/create_table.sql
```

### Testing
```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Docker tests
docker-compose run --rm api pytest
docker-compose run --rm frontend npm test
```

### Deployment
```bash
# Production build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build

# Health check
curl http://localhost:5002/health

# Metrics
curl http://localhost:5002/metrics/prometheus
```

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Port Conflicts**: Check if ports 5002 (API) and 3000 (frontend) are available
3. **Environment Variables**: Verify `.env` files are properly configured
4. **Docker Issues**: Run `docker-compose down && docker-compose up --build`

### Logs
```bash
# API logs
docker-compose logs api

# Frontend logs
docker-compose logs frontend

# All logs
docker-compose logs
```

## Architecture Decision Records

### Backend
- **Language**: Python 3.12 for robust data processing
- **Framework**: FastAPI for modern async API development
- **Database**: PostgreSQL for relational data integrity
- **Package Management**: Poetry/pip for dependency management

### Frontend
- **Framework**: React 18+ for modern UI development
- **State Management**: Local state + custom hooks
- **Styling**: Bootstrap + SASS for responsive design
- **Build Tool**: Create React App for rapid development

### Infrastructure
- **Containerization**: Docker for consistent deployment
- **Orchestration**: Docker Compose for multi-service setup
- **Monitoring**: Built-in health checks and Prometheus metrics
- **Development**: Hot reload for both backend and frontend