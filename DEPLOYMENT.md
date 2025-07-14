# Stream Sniper Docker Deployment Guide

This guide explains how to deploy Stream Sniper using Docker with an external PostgreSQL database.

## Architecture Overview

The deployment consists of three main services:
- **Frontend**: React application served by Nginx on port 3000
- **API**: FastAPI backend on port 5002
- **Redis**: Caching and rate limiting on port 6379

External dependencies:
- **PostgreSQL**: External database on Raspberry Pi (89.221.212.146:5432)

## Prerequisites

1. **Docker and Docker Compose**: Ensure Docker and Docker Compose v2 are installed
2. **External PostgreSQL**: Database server running on 89.221.212.146:5432
3. **Network Access**: Ensure the Docker host can reach the PostgreSQL server
4. **Environment Configuration**: Proper `.env` file configuration

## Quick Start

### 1. Clone and Navigate
```bash
cd /home/slanycukr/Documents/stream-sniper
```

### 2. Environment Configuration
Ensure your `.env` file contains:
```bash
# Database Configuration (External PostgreSQL on Raspberry Pi)
DATABASE=postgres
HOST=89.221.212.146
PORT=5432
PASSWORD=606361611Aa.
USER=slanycukr

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# API Configuration
API_HOST=0.0.0.0
API_PORT=5002
API_DEBUG=false

# CORS Configuration
CORS_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_CREDENTIALS=true

# Cache Configuration
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BYPASS_LOCALHOST=true

# Environment
PYTHONUNBUFFERED=1

# Frontend Configuration
REACT_APP_API_URL=http://localhost:3000/api
```

### 3. Deploy All Services
```bash
# Build and start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Verify Deployment
```bash
# Test frontend
curl http://localhost:3000/health

# Test API directly
curl http://localhost:5002/health

# Test API through frontend proxy
curl http://localhost:3000/api/health

# Test Redis
docker exec stream-sniper-redis-1 redis-cli ping
```

## Service Details

### Frontend Service
- **Port**: 3000
- **Technology**: React + Nginx
- **Health Check**: `/health`
- **Features**:
  - Multi-stage Docker build
  - Production-optimized Nginx configuration
  - API proxy to backend service
  - Static asset caching
  - GZIP compression
  - Security headers

### API Service
- **Port**: 5002
- **Technology**: FastAPI + Python 3.12
- **Health Check**: `/health`
- **Features**:
  - External PostgreSQL database connection
  - Redis caching
  - Rate limiting
  - Comprehensive health checks
  - Prometheus metrics
  - Structured logging

### Redis Service
- **Port**: 6379
- **Technology**: Redis 7 Alpine
- **Features**:
  - Memory-optimized configuration (256MB limit)
  - LRU eviction policy
  - Health monitoring
  - Data persistence

## Development vs Production

### Development (default)
Uses `docker-compose.override.yml`:
- Debug logging enabled
- Rate limiting disabled
- CORS allows localhost
- Services restart on failure disabled
- Lower memory limits

### Production
Use `docker-compose.prod.yml`:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production features:
- Optimized resource limits
- Security hardening
- Rate limiting enabled
- Higher cache TTL values
- Service restart policies
- Internal port exposure only

## Health Monitoring

All services include comprehensive health checks:

### Service Health Status
```bash
# Check all services
docker compose ps

# Individual service health
curl http://localhost:3000/health      # Frontend
curl http://localhost:5002/health      # API
docker exec stream-sniper-redis-1 redis-cli ping  # Redis
```

### API Health Response
The API health endpoint returns detailed status:
```json
{
  "status": "healthy",
  "database": {
    "status": "healthy",
    "healthy": true,
    "response_time_ms": 94.81
  },
  "cache": {
    "status": "healthy", 
    "healthy": true,
    "response_time_ms": 1.92
  },
  "rate_limiting": {
    "status": "degraded",
    "healthy": false,
    "enabled": false
  },
  "timestamp": "2025-07-13T19:35:11.892870Z",
  "version": "1.0.0"
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check network connectivity
   docker exec stream-sniper-api-1 ping 89.221.212.146
   
   # Check PostgreSQL is running on Raspberry Pi
   ssh -p 2222 pi@89.221.212.146 "sudo systemctl status postgresql"
   ```

2. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :3000
   lsof -i :5002
   
   # Kill process if needed
   kill <PID>
   ```

3. **Service Won't Start**
   ```bash
   # Check logs
   docker compose logs <service_name>
   
   # Restart specific service
   docker compose restart <service_name>
   ```

4. **Frontend Can't Reach API**
   ```bash
   # Check nginx proxy configuration
   docker exec stream-sniper-frontend-1 curl http://api:5002/health
   
   # Check internal network
   docker network ls
   docker network inspect stream-sniper_stream-sniper
   ```

### Log Monitoring
```bash
# Follow all logs
docker compose logs -f

# Service-specific logs
docker compose logs -f frontend
docker compose logs -f api
docker compose logs -f redis

# Recent logs only
docker compose logs --tail 50 api
```

## Maintenance Commands

### Service Management
```bash
# Stop all services
docker compose down

# Stop specific service
docker compose stop frontend

# Restart services
docker compose restart

# Rebuild and restart
docker compose up -d --build

# Remove everything (data loss!)
docker compose down -v --remove-orphans
```

### Updates and Scaling
```bash
# Pull latest images
docker compose pull

# Scale services (if needed)
docker compose up -d --scale api=2

# Update specific service
docker compose up -d --build api
```

### Data Management
```bash
# Backup Redis data
docker exec stream-sniper-redis-1 redis-cli BGSAVE

# View Redis data
docker exec -it stream-sniper-redis-1 redis-cli
```

## Security Considerations

1. **Network Security**: Only necessary ports are exposed
2. **Database Access**: Uses external PostgreSQL with authentication
3. **Environment Variables**: Sensitive data in `.env` files (not committed)
4. **Container Security**: Services run with minimal privileges where possible
5. **HTTPS**: Consider adding SSL/TLS termination for production
6. **Firewall**: Limit access to exposed ports (3000, 5002, 6379)

## Performance Optimization

1. **Resource Limits**: Configured for optimal memory usage
2. **Caching**: Redis provides aggressive caching with appropriate TTLs
3. **Compression**: Nginx GZIP compression enabled
4. **Database**: Connection pooling configured (2-20 connections)
5. **Static Assets**: Efficient caching strategies

## Backup Strategy

1. **Redis Data**: Automatic persistence enabled
2. **Database**: External PostgreSQL on Raspberry Pi (managed separately)
3. **Application Data**: Stateless services, no persistent volumes needed
4. **Configuration**: `.env` and `docker-compose.yml` files in version control

## Support

For issues or questions:
1. Check service logs: `docker compose logs`
2. Verify health endpoints
3. Review this documentation
4. Check external dependencies (PostgreSQL, network connectivity)

## File Structure

```
stream-sniper/
├── docker-compose.yml              # Main service definitions
├── docker-compose.override.yml     # Development overrides  
├── docker-compose.prod.yml         # Production configuration
├── .env                           # Environment variables
├── Dockerfile.api                 # API service build
├── Dockerfile.collector           # Collector service build
├── frontend/
│   ├── Dockerfile                # Frontend build (React + Nginx)
│   ├── nginx.conf                # Nginx site configuration
│   ├── nginx.main.conf           # Main Nginx configuration
│   └── .env                      # Frontend environment variables
└── DEPLOYMENT.md                 # This file
```

## Next Steps

After successful deployment:
1. Set up monitoring and alerting
2. Configure automated backups
3. Implement CI/CD pipeline
4. Add SSL/TLS certificates for production
5. Set up log aggregation
6. Configure external load balancer if needed