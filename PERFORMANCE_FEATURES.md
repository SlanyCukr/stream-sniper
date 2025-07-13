# Stream Sniper API Performance Features

This document describes the performance enhancements added to the Stream Sniper API, including caching, rate limiting, compression, and monitoring capabilities.

## Overview

The Stream Sniper API has been enhanced with comprehensive performance features designed to:

- **Improve Response Times**: Redis-based caching for expensive database operations
- **Prevent Abuse**: Configurable rate limiting with Redis backend
- **Reduce Bandwidth**: Response compression for large payloads
- **Monitor Performance**: Real-time metrics and health monitoring
- **Ensure Reliability**: Graceful degradation when dependencies are unavailable

## Features

### 1. Redis Caching

**Purpose**: Cache expensive database queries and analytics results to dramatically improve response times for frequently accessed data.

**Key Benefits**:
- Reduces database load by caching query results
- Configurable TTL (Time To Live) for different data types
- Intelligent cache key management
- Automatic cache warming on startup
- Graceful degradation when Redis is unavailable

**Cached Endpoints**:
- `/creators` - Creator list (TTL: 2 hours)
- `/streams/` - Stream listings (TTL: 30 minutes)
- `/stream/{id}/` - Stream analytics (TTL: 1 hour)
- `/chatter/{id}/messages/` - Chatter messages (TTL: 30 minutes)
- All other endpoints with appropriate TTL settings

**Cache Headers**:
- `X-Cache: HIT` - Response served from cache
- `X-Cache: MISS` - Response fetched from database
- `X-Cache: PARTIAL` - Some data from cache, some from database

### 2. Rate Limiting

**Purpose**: Prevent API abuse and ensure fair usage across all clients.

**Implementation**: Uses slowapi (FastAPI-compatible Flask-Limiter) with Redis backend for distributed rate limiting.

**Rate Limits by Endpoint Type**:
- **General endpoints**: 100 requests/minute
- **Analytics endpoints**: 30 requests/minute (more expensive)
- **Heavy operations**: 10 requests/minute (cache flush, etc.)
- **Health checks**: 300 requests/minute (for monitoring)
- **Bulk data**: 20 requests/minute
- **Search operations**: 50 requests/minute

**Features**:
- IP-based identification by default
- Support for API key authentication (future)
- Bypass capabilities for localhost (development)
- Configurable whitelist IPs
- Detailed rate limit headers in responses
- Custom error responses with retry information

### 3. Response Compression

**Purpose**: Reduce bandwidth usage and improve response times for large payloads.

**Implementation**: GZip compression middleware with configurable settings.

**Settings**:
- Minimum size: 1KB (configurable)
- Compression level: 6 (configurable)
- Supported MIME types: JSON, HTML, JavaScript, CSS, plain text

### 4. Monitoring and Metrics

**Purpose**: Provide comprehensive insights into API performance and usage patterns.

**Available Metrics**:
- Request statistics (count, response times, status codes)
- Cache performance (hit/miss rates, operations)
- Rate limiting statistics
- Per-endpoint performance metrics
- System uptime and health

**Monitoring Endpoints**:
- `/health` - Comprehensive health check
- `/metrics` - Performance metrics and statistics
- `/cache/stats` - Detailed cache performance
- `/cache/flush` - Manual cache flushing (rate limited)

## Configuration

All features are configurable via environment variables. Copy `.env.example` to `.env` and modify as needed.

### Essential Configuration

```bash
# Database (Required)
USER=your_db_user
PASSWORD=your_db_password
HOST=localhost
DATABASE=your_database_name

# Redis (Required for caching and rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional_password

# API Settings
API_PORT=5002
API_HOST=0.0.0.0
```

### Performance Tuning

```bash
# Cache TTL Settings (seconds)
CACHE_TTL_CREATORS=7200           # 2 hours
CACHE_TTL_STREAM_ANALYTICS=3600   # 1 hour
CACHE_TTL_STREAM_DETAILS=1800     # 30 minutes

# Rate Limiting
RATE_LIMIT_GENERAL=100 per minute
RATE_LIMIT_ANALYTICS=30 per minute
RATE_LIMIT_HEAVY=10 per minute

# Database Pool
DB_POOL_MIN_CONN=2
DB_POOL_MAX_CONN=20
```

### Feature Toggles

```bash
# Enable/Disable Features
CACHE_ENABLED=true
RATE_LIMIT_ENABLED=true
COMPRESSION_ENABLED=true
MONITORING_ENABLED=true
CACHE_WARM_ON_STARTUP=true
```

## Deployment

### Docker Deployment (Recommended)

The included `docker-compose.yml` provides a complete deployment with Redis:

```bash
# Start all services (API + Redis)
docker-compose up -d

# Start only the API (requires external Redis)
docker-compose up api

# View logs
docker-compose logs -f api
```

### Manual Deployment

1. Install Redis:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Start the API:
   ```bash
   stream-sniper-api
   # or
   python -m stream_sniper.api.server
   ```

## Performance Impact

### Expected Improvements

**Cache Hit Scenarios**:
- 90%+ reduction in response time for cached endpoints
- Significant reduction in database load
- Improved concurrent user capacity

**Rate Limiting Benefits**:
- Protection against abuse and DoS attacks
- Fair resource allocation among users
- Predictable performance under load

**Compression Benefits**:
- 60-80% reduction in response size for JSON data
- Faster response times over slower connections
- Reduced bandwidth costs

### Monitoring and Alerts

Monitor these key metrics for optimal performance:

1. **Cache Hit Rate**: Should be > 80% for frequently accessed endpoints
2. **Response Times**: Should remain under 200ms for cached responses
3. **Rate Limit Violations**: Monitor for abuse patterns
4. **Database Connection Pool**: Watch for connection exhaustion
5. **Redis Health**: Ensure Redis availability for optimal performance

## Troubleshooting

### Common Issues

**1. Cache Not Working**
- Check Redis connectivity: `redis-cli ping`
- Verify `REDIS_HOST` and `REDIS_PORT` settings
- Check Redis authentication if password is set

**2. Rate Limiting Issues**
- Verify Redis connection (rate limiting requires Redis)
- Check if IP is whitelisted in development
- Use bypass token for testing: `X-Rate-Limit-Bypass: your_token`

**3. Performance Issues**
- Monitor cache hit rates via `/cache/stats`
- Check database connection pool status via `/health`
- Review metrics via `/metrics` endpoint

**4. High Memory Usage**
- Adjust cache TTL settings to reduce memory usage
- Monitor Redis memory usage
- Consider Redis memory policies (allkeys-lru recommended)

### Health Monitoring

The `/health` endpoint provides comprehensive system status:

```json
{
  "status": "healthy",
  "database": {
    "status": "active",
    "healthy": true,
    "minconn": 2,
    "maxconn": 20
  },
  "cache": {
    "enabled": true,
    "status": "healthy",
    "redis_version": "7.0.0"
  },
  "rate_limiting": {
    "enabled": true,
    "storage": "redis"
  }
}
```

### Performance Monitoring

Use the `/metrics` endpoint to monitor API performance:

```json
{
  "requests": {
    "total": 10000,
    "per_minute": 50.5,
    "avg_response_time_ms": 45.2
  },
  "cache": {
    "hit_rate": 85.5,
    "miss_rate": 14.5
  },
  "rate_limiting": {
    "rate_limit_percentage": 2.1
  }
}
```

## Best Practices

### Development

1. **Use localhost bypass**: Set `RATE_LIMIT_BYPASS_LOCALHOST=true` for development
2. **Disable cache warming**: Set `CACHE_WARM_ON_STARTUP=false` for faster startup
3. **Use debug logging**: Set `API_DEBUG=true` for detailed logs

### Production

1. **Enable all features**: Caching, rate limiting, compression, and monitoring
2. **Set appropriate TTLs**: Balance between performance and data freshness
3. **Configure Redis persistence**: Use RDB or AOF for data durability
4. **Monitor metrics regularly**: Set up alerts for performance degradation
5. **Use Redis password**: Secure your Redis instance in production

### Scaling

1. **Redis Clustering**: For high availability and horizontal scaling
2. **Multiple API instances**: Load balance behind nginx/haproxy
3. **Database read replicas**: Separate read and write operations
4. **CDN integration**: Cache static responses at edge locations

## Security Considerations

### Rate Limiting Security

- Rate limits are applied per IP address
- Bypass tokens should be kept secret and rotated regularly
- Whitelist only trusted IPs in production
- Monitor for rate limit violations as potential abuse indicators

### Cache Security

- Redis should be password-protected in production
- Cache keys include hashed parameters to prevent collisions
- No sensitive data is cached (only IDs and public information)
- Cache TTLs ensure data doesn't become stale

### Monitoring Security

- Metrics endpoints should be rate limited
- Consider restricting metrics access to internal networks
- Cache flush endpoint is heavily rate limited to prevent abuse

## Migration Guide

For existing deployments, follow these steps to enable performance features:

1. **Update dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install and configure Redis**:
   ```bash
   # Install Redis
   sudo apt-get install redis-server
   
   # Start Redis
   sudo systemctl start redis-server
   ```

3. **Update configuration**:
   ```bash
   cp .env.example .env
   # Add Redis configuration to your existing .env
   ```

4. **Test the deployment**:
   ```bash
   # Check health
   curl http://localhost:5002/health
   
   # Check metrics
   curl http://localhost:5002/metrics
   ```

5. **Monitor performance**:
   - Watch cache hit rates in `/cache/stats`
   - Monitor response times in `/metrics`
   - Verify rate limiting is working as expected

The API maintains backward compatibility, so existing clients will continue to work without changes while benefiting from improved performance.