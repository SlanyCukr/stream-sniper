# Stream Sniper - Project Instructions

A comprehensive Twitch stream analytics platform that collects, processes, and visualizes chat data from Twitch streams with user authentication, admin controls, and automated streamer tracking.

**Important**: This project contains component-specific documentation:
- **Backend**: `backend/CLAUDE.md` - Backend development instructions
- **Frontend**: `frontend/CLAUDE.md` - Frontend development instructions
- **Tracking System**: `TRACKING_SYSTEM.md` - Automated tracking system documentation

## Project Overview

**Stream Sniper** is a multi-component system designed to analyze Twitch stream chat interactions. It downloads chat data from Twitch VODs, processes messages, stores them in a PostgreSQL database, and provides both a web dashboard and REST API for data analysis and visualization.

## Architecture

The system consists of four main components:

### 1. Backend (`backend/`)
- **Data Collection**: Downloads and processes chat data from Twitch VODs
- **REST API**: FastAPI server providing HTTP endpoints for data access
- **Database**: PostgreSQL integration with normalized schema
- **Entry Points**: 
  - `stream-sniper <username>` - CLI command for data collection
  - `stream-sniper-api` - REST API server
  - `stream-sniper-tracking` - Automated tracking service

### 2. Frontend (`frontend/`)
- **React Application**: Modern React-based web interface
- **Analytics Dashboard**: Stream browsing, chat analysis, and visualization
- **API Integration**: Connects to backend REST API
- **Development Server**: `npm start` for local development

### 3. Database (External)
- **PostgreSQL**: Normalized schema in `stream_sniper` namespace
- **External Service**: Not included in Docker Compose (separate instance required)

### 4. Authentication & Admin System
- **User Management**: JWT-based authentication with role-based access control
- **Admin Interface**: Complete admin dashboard for user and system management
- **Automated Tracking**: Background service for automatic streamer monitoring and processing

## Database Schema

PostgreSQL database with normalized schema in `stream_sniper` namespace:

### Core Tables
- **`creator`** - Twitch streamers (id, nick, display_name, profile_image_url)
- **`stream`** - Individual stream sessions (id, twitch_id, title, start/end times, message_count, creator_id)
- **`chatter`** - Unique chat participants (id, nick)
- **`message_text`** - Deduplicated message content (id, text)
- **`message`** - Individual chat messages (id, chatter_id, stream_id, message_text_id, timestamp)

### Authentication & Admin Tables
- **`users`** - System users with authentication (id, username, email, password_hash, role, active)
- **`tracked_streamers`** - Streamers monitored by automation system
- **`processing_jobs`** - Background processing jobs with status tracking

### Key Relationships
- Messages link to chatters, streams, and message text via foreign keys
- Streams belong to creators
- Support for message tagging (tagged_chatter_id in messages)

## Quick Start

### Docker Development (Recommended)
Everything runs in Docker with hot reload - no need to install Node.js or Python locally:

```bash
# Start all services with hot reload
docker-compose up

# Start specific services
docker-compose up api         # API only
docker-compose up frontend    # Frontend only
docker-compose up tracking    # Tracking service only

# Run data collection
TWITCH_USERNAME=someuser docker-compose up collector

# Production deployment
docker-compose -f docker-compose.prod.yml up -d frontend

# Access production application
# Frontend: https://stream-sniper.slanycukr.com
# API: https://stream-sniper-api.slanycukr.com

# Rebuild containers after dependency changes
docker-compose up --build
```

### Local Development (Alternative)
```bash
# Backend
cd backend
pip install -e .
stream-sniper <username>      # Data collection
stream-sniper-api             # API server
stream-sniper-tracking        # Automated tracking service

# Authentication & Admin
# Access admin panel at /admin after login
# Default admin setup available through API

# Frontend
cd frontend
npm install
npm start                     # Development server
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
│   │   ├── api/             # FastAPI REST API
│   │   ├── auth/            # Authentication system
│   │   ├── collector/       # Data collection
│   │   ├── database/        # Database layer
│   │   └── tracking/        # Automated tracking system
│   └── tests/               # Test suite
├── frontend/                 # React frontend
│   ├── README.md            # Frontend documentation
│   ├── CLAUDE.md            # Frontend developer instructions
│   ├── src/                 # React source code
│   │   ├── components/      # Reusable components
│   │   ├── contexts/        # React contexts (Auth)
│   │   ├── views/           # Page components
│   │   │   ├── admin/       # Admin interface
│   │   │   ├── auth/        # Authentication pages
│   │   │   └── ui/          # Main application views
│   │   └── layouts/         # Layout components
│   └── public/              # Static assets
└── TRACKING_SYSTEM.md       # Automated tracking documentation
```

## Development Environment

- **Docker**: Required for development (handles Python 3.12 and Node.js 18+ automatically)
- **Database**: PostgreSQL with `stream_sniper` schema (external, not included in Docker Compose)
- **Configuration**: Environment variables loaded from `.env` files
- **Hot Reload**: Automatic code reloading for both frontend and backend
- **Local Installation**: Optional - Docker handles all dependencies

## Production Deployment

- **Frontend**: Nginx-based production container with optimized build
- **Backend**: Production-ready FastAPI server with authentication
- **Infrastructure**: Deployed on RPI infrastructure (pi5ram8)
- **SSL**: HTTPS termination via VPS reverse proxy
- **Domain**: Production frontend available at stream-sniper.slanycukr.com
- **API**: Backend API at stream-sniper-api.slanycukr.com
- **Database**: PostgreSQL on RPI infrastructure
- **Monitoring**: Full tracking system with admin controls

## Key Features

### Analytics Capabilities
- Stream message volume analysis
- Most active chatters identification
- Message tagging and interaction analysis
- Creator cross-stream participation tracking
- Temporal message patterns

### Authentication & Security
- JWT-based user authentication
- Role-based access control (user/admin)
- Password hashing with bcrypt
- Session management with token expiration
- Protected routes and API endpoints

### Administrative Features
- User management (create, update, delete, role assignment)
- System statistics and monitoring
- Automated streamer tracking management
- Processing job monitoring and control
- Service management (start/stop/restart tracking)

### Automated Tracking System
- Background monitoring of Twitch streamers
- Automatic chat processing when streams end
- Job queuing with retry capabilities
- Real-time status monitoring
- Concurrent processing with configurable limits

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
- User authentication and profile management
- Admin interface for system administration
- Automated tracking management dashboard
- Processing job monitoring and control

## Security Considerations

The codebase is designed for legitimate stream analytics purposes:
- Read-only access to public Twitch chat data
- Standard database practices with parameterized queries
- JWT-based authentication with secure token handling
- Password hashing using bcrypt
- Role-based access control throughout the system
- Rate limiting on authentication endpoints
- Protected routes and API endpoints
- Input validation and sanitization
- No obvious malicious functionality detected

## Performance Optimizations

- **Database Buffering**: Batch database operations
- **Message Deduplication**: Prevents duplicate storage
- **Pagination**: API endpoints support offset-based pagination
- **Frontend Optimization**: Code splitting and memoization
- **Comprehensive Monitoring**: Health checks and metrics endpoints
- **Concurrent Processing**: Configurable concurrent job processing
- **Background Services**: Automated processing with resource management
- **Caching**: Session caching and API response optimization

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

### Docker Development Workflow
```bash
# Start development environment
docker-compose up

# View logs
docker-compose logs -f api        # API logs
docker-compose logs -f frontend   # Frontend logs
docker-compose logs -f            # All logs

# Rebuild after dependency changes
docker-compose up --build

# Stop services
docker-compose down

# Clean up containers and volumes
docker-compose down -v
```

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

# Create admin user (after API is running)
curl -X POST http://localhost:5002/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"admin123"}'

# Update user role to admin
curl -X PUT http://localhost:5002/auth/users/1/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"role":"admin"}'
```

### Testing
```bash
# Run tests in containers
docker-compose run --rm api pytest
docker-compose run --rm frontend npm test

# Local testing (if dependencies installed)
cd backend && pytest
cd frontend && npm test
```

### Health Checks
```bash
# Check API health
curl http://localhost:5002/health

# Check metrics
curl http://localhost:5002/metrics

# Check frontend
curl http://localhost:3000

# Check authentication
curl -X POST http://localhost:5002/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Check tracking service
curl -X GET http://localhost:5002/admin/tracking/service/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Port Conflicts**: Check if ports 5002 (API) and 3000 (frontend) are available
3. **Environment Variables**: Verify `.env` files are properly configured
4. **Docker Issues**: Run `docker-compose down && docker-compose up --build`
5. **Authentication Issues**: 
   - Check JWT token expiration
   - Verify user roles and permissions
   - Ensure proper Authorization headers
6. **Tracking Service Issues**:
   - Check if tracking service is running
   - Verify Twitch API credentials
   - Check processing job status in admin interface
7. **Hot Reload Not Working**: 
   - Frontend: Check volume mounts in docker-compose.yml
   - Backend: Ensure uvicorn --reload is working
   - Try `docker-compose down -v && docker-compose up --build`

### Development Tips
- **Code Changes**: Automatically detected and reloaded (no restart needed)
- **Package Changes**: Rebuild containers with `docker-compose up --build`
- **Database Schema**: Update manually, containers don't manage DB schema
- **Environment Variables**: Restart containers after .env changes

### Logs
```bash
# API logs
docker-compose logs api

# Frontend logs
docker-compose logs frontend

# All logs
docker-compose logs

# Tracking service logs
docker-compose logs tracking

# Authentication logs
docker-compose logs api | grep -i auth
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
- **Authentication**: JWT-based session management
- **Deployment**: Production-ready Docker configurations
- **CI/CD**: GitHub Actions with comprehensive testing and security checks