# Health Monitoring and Observability

The Stream Sniper API includes comprehensive health monitoring capabilities designed for production environments, load balancer integration, and monitoring systems.

## Health Check Endpoints

### Basic Health Check - `/health`

**Purpose**: Load balancer health checks and basic system status  
**Method**: GET  
**Rate Limit**: 300 requests per minute

Returns basic health status focusing on critical components only (database connectivity).

**Response Codes**:
- `200` - System is healthy and operational
- `503` - Critical issues detected (database unavailable)

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-13T18:06:52.123Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "database": {
    "status": "healthy",
    "healthy": true,
    "response_time_ms": 5.2
  }
}
```

### Detailed Health Check - `/health/detailed`

**Purpose**: Comprehensive system monitoring with all components  
**Method**: GET  
**Rate Limit**: 300 requests per minute

Returns detailed health status including all system components, dependencies, and system metrics.

**Response Codes**:
- `200` - System is healthy or degraded but operational
- `503` - Critical or unhealthy status detected

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-13T18:06:52.123Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection pool is healthy",
      "response_time_ms": 5.2,
      "details": {
        "status": "active",
        "minconn": 2,
        "maxconn": 20,
        "healthy": true
      }
    },
    "cache": {
      "status": "degraded",
      "message": "Cache is disabled",
      "response_time_ms": 0.8,
      "details": {
        "enabled": false,
        "status": "disabled"
      }
    },
    "rate_limiter": {
      "status": "healthy",
      "message": "Rate limiter is operational",
      "response_time_ms": 0.2,
      "details": {
        "enabled": true,
        "storage": {
          "type": "redis",
          "status": "healthy"
        }
      }
    },
    "external_apis": {
      "twitch": {
        "status": "healthy",
        "message": "Twitch API is reachable",
        "response_time_ms": 171.7,
        "details": {
          "status_code": 401,
          "url": "https://api.twitch.tv/helix/users"
        }
      }
    }
  },
  "system": {
    "platform": "Linux-6.14.0-23-generic-x86_64",
    "python_version": "3.13.1",
    "cpu_count": 16,
    "resources": {
      "cpu_percent": 2.4,
      "memory": {
        "percent": 21.7,
        "available_mb": 22962.2,
        "used_mb": 5390.3,
        "total_mb": 27352.5
      },
      "disk": {
        "percent": 68.0,
        "free_gb": 78.76,
        "total_gb": 293.08
      },
      "load_average": [0.85, 0.92, 1.1],
      "uptime_seconds": 1234567
    }
  }
}
```

### Prometheus Metrics - `/metrics/prometheus`

**Purpose**: Monitoring system integration (Prometheus, Grafana, etc.)  
**Method**: GET  
**Rate Limit**: 100 requests per minute  
**Content-Type**: `text/plain; version=0.0.4`

Returns metrics in Prometheus exposition format for monitoring and alerting.

**Example Response**:
```
# HELP stream_sniper_component_health Health status of system components (1=healthy, 0.75=degraded, 0.5=unhealthy, 0=critical)
# TYPE stream_sniper_component_health gauge
stream_sniper_component_health{component="database"} 1 1752422816728
stream_sniper_component_health{component="cache"} 0.75 1752422816728
stream_sniper_component_health{component="rate_limiter"} 1 1752422816728
stream_sniper_component_health{component="twitch_api"} 1 1752422816728

# HELP stream_sniper_component_response_time_ms Response time of component health checks in milliseconds
# TYPE stream_sniper_component_response_time_ms gauge
stream_sniper_component_response_time_ms{component="database"} 5.2 1752422816728
stream_sniper_component_response_time_ms{component="cache"} 0.8 1752422816728

# HELP stream_sniper_system_cpu_percent Current CPU usage percentage
# TYPE stream_sniper_system_cpu_percent gauge
stream_sniper_system_cpu_percent 2.4 1752422816728

# HELP stream_sniper_system_memory_percent Current memory usage percentage
# TYPE stream_sniper_system_memory_percent gauge
stream_sniper_system_memory_percent 21.7 1752422816728
```

## Health Status Levels

The system uses a standardized health status hierarchy:

- **healthy** - All components operational
- **degraded** - Some non-critical components have issues (e.g., cache disabled)
- **unhealthy** - Critical components have issues but system partially functional
- **critical** - System has severe issues affecting core functionality
- **unknown** - Unable to determine component status

## Monitored Components

### Database
- **Check**: Connection pool health and query performance
- **Critical**: Yes (system unavailable if unhealthy)
- **Metrics**: Response time, connection pool status

### Redis Cache
- **Check**: Connection and basic operations
- **Critical**: No (degrades performance but system remains functional)
- **Metrics**: Hit/miss rates, memory usage, connection status

### Rate Limiter
- **Check**: Functionality and storage backend
- **Critical**: No (system functional without rate limiting)
- **Metrics**: Request counts, storage backend health

### External APIs
- **Check**: Twitch API connectivity
- **Critical**: No (affects data collection but API remains functional)
- **Metrics**: Response times, status codes

## System Metrics

### Resource Monitoring
- **CPU Usage**: Current percentage utilization
- **Memory**: Usage percentage, available/used/total in MB
- **Disk Space**: Usage percentage, free/total in GB
- **Load Average**: 1, 5, and 15-minute averages (Unix systems)

### Application Metrics
- **Uptime**: Seconds since application start
- **Response Times**: Per-component health check duration
- **Error Rates**: Component failure frequencies

## Load Balancer Integration

Use the basic health endpoint (`/health`) for load balancer health checks:

**HAProxy Example**:
```
backend stream_sniper_api
    option httpchk GET /health
    http-check expect status 200
    server api1 10.0.1.10:5002 check
    server api2 10.0.1.11:5002 check
```

**NGINX Example**:
```nginx
upstream stream_sniper {
    server 10.0.1.10:5002;
    server 10.0.1.11:5002 backup;
}

location /health {
    access_log off;
    proxy_pass http://stream_sniper;
    proxy_set_header Host $host;
}
```

## Monitoring System Integration

### Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'stream-sniper'
    static_configs:
      - targets: ['api.example.com:5002']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

### Grafana Dashboard
Use the Prometheus metrics to create dashboards monitoring:
- Component health status (`stream_sniper_component_health`)
- Response times (`stream_sniper_component_response_time_ms`)
- System resources (`stream_sniper_system_*`)
- Application uptime (`stream_sniper_uptime_seconds`)

### Alerting Rules
```yaml
groups:
  - name: stream_sniper
    rules:
      - alert: StreamSniperDown
        expr: stream_sniper_component_health{component="database"} < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Stream Sniper API is down"
          
      - alert: StreamSniperDegraded
        expr: stream_sniper_component_health{component="cache"} < 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Stream Sniper cache is degraded"
```

## Headers

Health check endpoints include special headers:
- `X-Health-Check: true` - Identifies health check requests
- `X-Health-Response-Time: 5.2` - Health check response time in milliseconds

## Performance

- **Basic Health Check**: < 100ms typical response time
- **Detailed Health Check**: < 500ms typical response time
- **Prometheus Metrics**: < 200ms typical response time
- **Concurrent Requests**: Fully thread-safe, supports high concurrency
- **Resource Usage**: Minimal CPU/memory impact during health checks