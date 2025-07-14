# Stream Sniper Docker Deployment Guide

This document provides comprehensive Docker deployment instructions for the Stream Sniper full-stack application.

## 🐳 Overview

Stream Sniper is deployed using Docker Compose with the following services:
- **Frontend**: React 19 application served by Nginx
- **API**: FastAPI backend server
- **Collector**: Data collection service for Twitch chat
- **Redis**: Caching and rate limiting storage
- **PostgreSQL**: Database (optional, can use external)

## 🚀 Quick Start

### Development Environment

```bash
# Clone repository
git clone <repository-url>
cd stream-sniper

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Start all services
docker-compose up

# Access the application
# Frontend: http://localhost:3000
# API: http://localhost:5002
# API Docs: http://localhost:5002/docs
```

### Production Environment

```bash
# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop services
docker-compose down
```

## 📁 Project Structure

```
stream-sniper/
├── docker-compose.yml          # Main orchestration file
├── Dockerfile.api              # Backend API container
├── Dockerfile.collector        # Data collector container
├── frontend/
│   ├── Dockerfile             # Frontend container
│   ├── nginx.conf             # Nginx configuration
│   └── ...                    # React application files
├── k8s/                       # Kubernetes manifests
└── ...
```

## 🔧 Service Configuration

### Frontend Service

**Container**: React application with Nginx
**Port**: 3000
**Health Check**: `/health` endpoint

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  depends_on:
    - api
  restart: unless-stopped
```

**Features**:
- Multi-stage build (Node.js build + Nginx runtime)
- Client-side routing support
- Static asset caching
- Security headers
- Health check endpoint

### API Service

**Container**: FastAPI application
**Port**: 5002
**Health Check**: `/health` endpoint

```yaml
api:
  build:
    context: .
    dockerfile: Dockerfile.api
  ports:
    - "5002:5002"
  env_file:
    - .env
  depends_on:
    - redis
  restart: unless-stopped
```

**Features**:
- OpenAPI/Swagger documentation at `/docs`
- Redis integration for caching
- Health monitoring endpoints
- Environment-based configuration

### Collector Service

**Container**: Python data collection script
**Purpose**: Download and process Twitch chat data

```yaml
collector:
  build:
    context: .
    dockerfile: Dockerfile.collector
  env_file:
    - .env
  command: ["${TWITCH_USERNAME:-defaultuser}"]
  restart: "no"
```

**Usage**:
```bash
# Collect data for specific user
TWITCH_USERNAME=someuser docker-compose up collector

# One-time collection
docker-compose run --rm collector someuser
```

### Redis Service

**Container**: Redis 7 Alpine
**Port**: 6379
**Purpose**: Caching and rate limiting

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  environment:
    - REDIS_PASSWORD=${REDIS_PASSWORD:-}
  restart: unless-stopped
```

**Features**:
- Optional password authentication
- Health checks
- Persistent data volume
- Auto-restart on failure

### PostgreSQL Service (Optional)

**Container**: PostgreSQL 16 Alpine
**Port**: 5432
**Purpose**: Database storage

```yaml
# Uncomment in docker-compose.yml to enable
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./database/create_table.sql:/docker-entrypoint-initdb.d/01-schema.sql
  ports:
    - "5432:5432"
```

## 🔒 Environment Configuration

### Required Environment Variables

```bash
# Database Configuration
USER=your_db_user
PASSWORD=your_db_password
HOST=localhost  # or postgres for Docker
DATABASE=stream_sniper

# Redis Configuration (Optional)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=optional_password

# API Configuration
API_PORT=5002
API_HOST=0.0.0.0

# Twitch Configuration
TWITCH_USERNAME=target_username
```

### Optional Environment Variables

```bash
# Cache Settings
CACHE_ENABLED=true
CACHE_TTL_CREATORS=7200

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_GENERAL=100 per minute

# Monitoring
MONITORING_ENABLED=true
API_DEBUG=false
```

## 📊 Service Commands

### Development Commands

```bash
# Start specific services
docker-compose up frontend api        # Frontend + Backend only
docker-compose up api redis          # Backend + Cache only

# View service logs
docker-compose logs -f api            # API logs
docker-compose logs -f frontend       # Frontend logs
docker-compose logs --tail=100 redis  # Last 100 Redis logs

# Execute commands in containers
docker-compose exec api bash          # Access API container
docker-compose exec redis redis-cli   # Redis CLI access

# Scale services (if needed)
docker-compose up --scale api=2       # Run 2 API instances
```

### Production Commands

```bash
# Start in production mode
docker-compose -f docker-compose.yml up -d

# Update and restart services
docker-compose pull                   # Pull latest images
docker-compose up -d --force-recreate # Recreate containers

# Backup data
docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Monitor resource usage
docker stats                          # Real-time stats
docker-compose top                    # Process information
```

### Data Collection Commands

```bash
# Collect data for specific streamer
TWITCH_USERNAME=ninja docker-compose up collector

# Collect multiple streamers
for user in ninja shroud pokimane; do
  TWITCH_USERNAME=$user docker-compose run --rm collector $user
done

# Schedule regular collection (with cron)
0 */6 * * * cd /path/to/stream-sniper && TWITCH_USERNAME=ninja docker-compose run --rm collector ninja
```

## 🔍 Monitoring and Health Checks

### Health Check Endpoints

```bash
# Frontend health
curl http://localhost:3000/health

# API health
curl http://localhost:5002/health

# Detailed API health
curl http://localhost:5002/health/detailed

# Prometheus metrics
curl http://localhost:5002/metrics/prometheus
```

### Service Status Monitoring

```bash
# Check all services
docker-compose ps

# Monitor logs in real-time
docker-compose logs -f

# Check specific service health
docker-compose exec api curl localhost:5002/health
docker-compose exec redis redis-cli ping
```

## 🛠️ Troubleshooting

### Common Issues

**1. Port Conflicts**
```bash
# Change ports in docker-compose.yml
services:
  frontend:
    ports:
      - "3001:3000"  # Change external port
  api:
    ports:
      - "5003:5002"  # Change external port
```

**2. Database Connection Issues**
```bash
# Check database connectivity
docker-compose exec api python -c "import psycopg2; print('DB OK')"

# Verify environment variables
docker-compose exec api env | grep -E "(USER|PASSWORD|HOST|DATABASE)"
```

**3. Redis Connection Issues**
```bash
# Test Redis connectivity
docker-compose exec api python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# Check Redis logs
docker-compose logs redis
```

**4. Frontend Build Issues**
```bash
# Rebuild frontend container
docker-compose build --no-cache frontend

# Check build logs
docker-compose up frontend --build
```

### Performance Optimization

**1. Resource Limits**
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

**2. Volume Optimization**
```yaml
volumes:
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /fast/ssd/path  # Use SSD for better performance
```

## 🚢 Production Deployment

### Recommended Production Setup

```bash
# 1. Use external managed services
# - PostgreSQL (AWS RDS, Google Cloud SQL)
# - Redis (AWS ElastiCache, Redis Cloud)

# 2. Configure environment for production
cp .env.example .env.production
# Edit with production values

# 3. Use production docker-compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Set up reverse proxy (nginx, traefik)
# 5. Configure SSL certificates
# 6. Set up monitoring and logging
```

### Security Considerations

```bash
# 1. Use non-root users in containers
# 2. Set resource limits
# 3. Use secrets management
# 4. Enable Redis authentication
# 5. Configure firewall rules
# 6. Regular security updates

# Example: Use Docker secrets
echo "your_redis_password" | docker secret create redis_password -
```

### Scaling Strategies

```bash
# 1. Horizontal scaling with load balancer
docker-compose up --scale api=3       # Multiple API instances

# 2. Use Docker Swarm for orchestration
docker swarm init
docker stack deploy -c docker-compose.yml stream-sniper

# 3. Migrate to Kubernetes for advanced orchestration
kubectl apply -k k8s/overlays/production
```

## 📚 Additional Resources

- **Kubernetes Deployment**: See `k8s/` directory for Kubernetes manifests
- **Development Guide**: See `CLAUDE.md` for complete documentation
- **Performance Features**: See `PERFORMANCE_FEATURES.md` for caching details
- **Health Monitoring**: See `HEALTH_MONITORING.md` for monitoring setup

## 🔄 Maintenance

### Regular Tasks

```bash
# Weekly tasks
docker system prune -f                # Clean unused resources
docker-compose pull && docker-compose up -d --force-recreate

# Monthly tasks
docker volume prune -f               # Clean unused volumes
# Update base images and rebuild

# Backup tasks
docker-compose exec postgres pg_dump -U $USER $DATABASE > backup-$(date +%Y%m%d).sql
```

### Updates and Upgrades

```bash
# Update application code
git pull origin main
docker-compose build --no-cache
docker-compose up -d --force-recreate

# Update dependencies
# For backend: Update requirements.txt and rebuild
# For frontend: Update package.json and rebuild
```

This Docker deployment guide provides everything needed to run Stream Sniper in development or production environments with proper monitoring, scaling, and maintenance procedures.