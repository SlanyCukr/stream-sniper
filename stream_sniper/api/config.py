"""
Configuration management for API settings including rate limits and cache settings.
Centralizes all configurable parameters with environment variable support.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    
    # Redis connection settings
    host: str = os.getenv('REDIS_HOST', 'localhost')
    port: int = int(os.getenv('REDIS_PORT', 6379))
    db: int = int(os.getenv('REDIS_DB', 0))
    password: Optional[str] = os.getenv('REDIS_PASSWORD')
    
    # Connection timeouts
    connect_timeout: int = int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
    socket_timeout: int = int(os.getenv('REDIS_SOCKET_TIMEOUT', 5))
    health_check_interval: int = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 30))
    
    # Cache behavior
    enabled: bool = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    default_ttl: int = int(os.getenv('CACHE_DEFAULT_TTL', 3600))  # 1 hour
    
    # Cache TTL for different data types (in seconds)
    ttl_creators: int = int(os.getenv('CACHE_TTL_CREATORS', 7200))  # 2 hours
    ttl_stream_count: int = int(os.getenv('CACHE_TTL_STREAM_COUNT', 1800))  # 30 minutes
    ttl_stream_analytics: int = int(os.getenv('CACHE_TTL_STREAM_ANALYTICS', 3600))  # 1 hour
    ttl_most_active_chatters: int = int(os.getenv('CACHE_TTL_MOST_ACTIVE_CHATTERS', 3600))  # 1 hour
    ttl_most_tagged_chatters: int = int(os.getenv('CACHE_TTL_MOST_TAGGED_CHATTERS', 3600))  # 1 hour
    ttl_stream_details: int = int(os.getenv('CACHE_TTL_STREAM_DETAILS', 1800))  # 30 minutes
    ttl_chatter_messages: int = int(os.getenv('CACHE_TTL_CHATTER_MESSAGES', 1800))  # 30 minutes
    ttl_health_check: int = int(os.getenv('CACHE_TTL_HEALTH_CHECK', 300))  # 5 minutes
    
    # Cache warming settings
    warm_on_startup: bool = os.getenv('CACHE_WARM_ON_STARTUP', 'true').lower() == 'true'
    warm_creators: bool = os.getenv('CACHE_WARM_CREATORS', 'true').lower() == 'true'
    warm_stream_counts: bool = os.getenv('CACHE_WARM_STREAM_COUNTS', 'true').lower() == 'true'


@dataclass
class RateLimitConfig:
    """Rate limiting configuration settings."""
    
    # Rate limiting enabled/disabled
    enabled: bool = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    
    # Redis connection for rate limiting
    redis_url: Optional[str] = os.getenv('REDIS_URL')
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', 6379))
    redis_db: int = int(os.getenv('REDIS_DB', 0))
    redis_password: Optional[str] = os.getenv('REDIS_PASSWORD')
    
    # Rate limiting strategy
    strategy: str = os.getenv('RATE_LIMIT_STRATEGY', 'moving-window')
    headers_enabled: bool = os.getenv('RATE_LIMIT_HEADERS_ENABLED', 'true').lower() == 'true'
    
    # Default limits
    default_limit: str = os.getenv('RATE_LIMIT_DEFAULT', '1000 per hour')
    
    # Endpoint-specific limits
    general: str = os.getenv('RATE_LIMIT_GENERAL', '100 per minute')
    analytics: str = os.getenv('RATE_LIMIT_ANALYTICS', '30 per minute')
    heavy: str = os.getenv('RATE_LIMIT_HEAVY', '10 per minute')
    health: str = os.getenv('RATE_LIMIT_HEALTH', '300 per minute')
    bulk: str = os.getenv('RATE_LIMIT_BULK', '20 per minute')
    search: str = os.getenv('RATE_LIMIT_SEARCH', '50 per minute')
    
    # Bypass settings
    bypass_token: Optional[str] = os.getenv('RATE_LIMIT_BYPASS_TOKEN')
    bypass_localhost: bool = os.getenv('RATE_LIMIT_BYPASS_LOCALHOST', 'true').lower() == 'true'
    whitelist_ips: str = os.getenv('RATE_LIMIT_WHITELIST_IPS', '')


@dataclass
class CompressionConfig:
    """Response compression configuration settings."""
    
    enabled: bool = os.getenv('COMPRESSION_ENABLED', 'true').lower() == 'true'
    min_size: int = int(os.getenv('COMPRESSION_MIN_SIZE', 1024))  # 1KB minimum
    compression_level: int = int(os.getenv('COMPRESSION_LEVEL', 6))  # Default gzip level
    
    # Mime types to compress
    mime_types: str = os.getenv('COMPRESSION_MIME_TYPES', 
                               'application/json,text/plain,text/html,application/javascript,text/css')


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration settings."""
    
    enabled: bool = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
    
    # Metrics collection
    collect_request_metrics: bool = os.getenv('MONITORING_REQUEST_METRICS', 'true').lower() == 'true'
    collect_cache_metrics: bool = os.getenv('MONITORING_CACHE_METRICS', 'true').lower() == 'true'
    collect_rate_limit_metrics: bool = os.getenv('MONITORING_RATE_LIMIT_METRICS', 'true').lower() == 'true'
    
    # Metrics retention
    metrics_retention_hours: int = int(os.getenv('MONITORING_RETENTION_HOURS', 24))


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    
    # Connection pool settings
    pool_min_conn: int = int(os.getenv('DB_POOL_MIN_CONN', 2))
    pool_max_conn: int = int(os.getenv('DB_POOL_MAX_CONN', 20))
    connect_timeout: int = int(os.getenv('DB_CONNECT_TIMEOUT', 10))
    command_timeout: int = int(os.getenv('DB_COMMAND_TIMEOUT', 60))
    
    # Health check settings
    health_check_interval: int = int(os.getenv('DB_HEALTH_CHECK_INTERVAL', 30))


@dataclass
class APIConfig:
    """Main API configuration combining all settings."""
    
    # API metadata
    title: str = os.getenv('API_TITLE', 'Stream Sniper API')
    description: str = os.getenv('API_DESCRIPTION', 'Twitch stream analytics API')
    version: str = os.getenv('API_VERSION', '1.0.0')
    
    # Server settings
    host: str = os.getenv('API_HOST', '0.0.0.0')
    port: int = int(os.getenv('API_PORT', 5002))
    debug: bool = os.getenv('API_DEBUG', 'false').lower() == 'true'
    
    # CORS settings
    cors_enabled: bool = os.getenv('CORS_ENABLED', 'true').lower() == 'true'
    cors_origins: str = os.getenv('CORS_ORIGINS', '*')
    cors_credentials: bool = os.getenv('CORS_CREDENTIALS', 'true').lower() == 'true'
    
    # Component configurations
    cache: CacheConfig = CacheConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    compression: CompressionConfig = CompressionConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    database: DatabaseConfig = DatabaseConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        def _convert(obj):
            if hasattr(obj, '__dict__'):
                return {k: _convert(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            return obj
        
        return _convert(self)
    
    def get_redis_url(self) -> str:
        """Get Redis URL for connections."""
        if self.rate_limit.redis_url:
            return self.rate_limit.redis_url
        
        # Build Redis URL from components
        if self.cache.password:
            return f"redis://:{self.cache.password}@{self.cache.host}:{self.cache.port}/{self.cache.db}"
        else:
            return f"redis://{self.cache.host}:{self.cache.port}/{self.cache.db}"
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate port ranges
            if not (1 <= self.port <= 65535):
                raise ValueError(f"Invalid API port: {self.port}")
            
            if not (1 <= self.cache.port <= 65535):
                raise ValueError(f"Invalid Redis port: {self.cache.port}")
            
            # Validate timeout values
            if self.cache.connect_timeout <= 0:
                raise ValueError(f"Invalid cache connect timeout: {self.cache.connect_timeout}")
            
            if self.database.connect_timeout <= 0:
                raise ValueError(f"Invalid database connect timeout: {self.database.connect_timeout}")
            
            # Validate pool settings
            if self.database.pool_min_conn < 1:
                raise ValueError(f"Invalid database min connections: {self.database.pool_min_conn}")
            
            if self.database.pool_max_conn < self.database.pool_min_conn:
                raise ValueError(f"Database max connections must be >= min connections")
            
            # Validate TTL values
            if self.cache.default_ttl < 1:
                raise ValueError(f"Invalid default TTL: {self.cache.default_ttl}")
            
            return True
            
        except ValueError as e:
            print(f"Configuration validation error: {e}")
            return False


# Global configuration instance
config = APIConfig()


def get_config() -> APIConfig:
    """
    Get the global API configuration.
    
    Returns:
        APIConfig instance
    """
    return config


def validate_config() -> bool:
    """
    Validate the current configuration.
    
    Returns:
        True if valid, False otherwise
    """
    return config.validate()


def print_config_summary():
    """Print a summary of the current configuration (excluding sensitive data)."""
    print("=== Stream Sniper API Configuration ===")
    print(f"API: {config.title} v{config.version}")
    print(f"Server: {config.host}:{config.port} (debug={config.debug})")
    print(f"Cache: {'enabled' if config.cache.enabled else 'disabled'} "
          f"(Redis: {config.cache.host}:{config.cache.port})")
    print(f"Rate Limiting: {'enabled' if config.rate_limit.enabled else 'disabled'}")
    print(f"Compression: {'enabled' if config.compression.enabled else 'disabled'}")
    print(f"Monitoring: {'enabled' if config.monitoring.enabled else 'disabled'}")
    print(f"Database Pool: {config.database.pool_min_conn}-{config.database.pool_max_conn} connections")
    print("=" * 40)


def create_env_template() -> str:
    """
    Create a template .env file with all available configuration options.
    
    Returns:
        String containing .env template
    """
    return """
# Stream Sniper API Configuration Template
# Copy this to .env and modify as needed

# API Server Settings
API_TITLE=Stream Sniper API
API_DESCRIPTION=Twitch stream analytics API
API_VERSION=1.0.0
API_HOST=0.0.0.0
API_PORT=5002
API_DEBUG=false

# Database Connection (Required)
USER=your_db_user
PASSWORD=your_db_password
HOST=localhost
DATABASE=your_database_name
PORT=5432

# Database Pool Settings
DB_POOL_MIN_CONN=2
DB_POOL_MAX_CONN=20
DB_CONNECT_TIMEOUT=10
DB_COMMAND_TIMEOUT=60
DB_HEALTH_CHECK_INTERVAL=30

# Redis Cache Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_HEALTH_CHECK_INTERVAL=30

# Cache Behavior
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600
CACHE_WARM_ON_STARTUP=true

# Cache TTL Settings (seconds)
CACHE_TTL_CREATORS=7200
CACHE_TTL_STREAM_COUNT=1800
CACHE_TTL_STREAM_ANALYTICS=3600
CACHE_TTL_MOST_ACTIVE_CHATTERS=3600
CACHE_TTL_MOST_TAGGED_CHATTERS=3600
CACHE_TTL_STREAM_DETAILS=1800
CACHE_TTL_CHATTER_MESSAGES=1800
CACHE_TTL_HEALTH_CHECK=300

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STRATEGY=moving-window
RATE_LIMIT_HEADERS_ENABLED=true
RATE_LIMIT_DEFAULT=1000 per hour

# Rate Limits by Endpoint Type
RATE_LIMIT_GENERAL=100 per minute
RATE_LIMIT_ANALYTICS=30 per minute
RATE_LIMIT_HEAVY=10 per minute
RATE_LIMIT_HEALTH=300 per minute
RATE_LIMIT_BULK=20 per minute
RATE_LIMIT_SEARCH=50 per minute

# Rate Limiting Bypass
RATE_LIMIT_BYPASS_TOKEN=your_secret_bypass_token
RATE_LIMIT_BYPASS_LOCALHOST=true
RATE_LIMIT_WHITELIST_IPS=

# Response Compression
COMPRESSION_ENABLED=true
COMPRESSION_MIN_SIZE=1024
COMPRESSION_LEVEL=6
COMPRESSION_MIME_TYPES=application/json,text/plain,text/html

# CORS Settings
CORS_ENABLED=true
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# Monitoring
MONITORING_ENABLED=true
MONITORING_REQUEST_METRICS=true
MONITORING_CACHE_METRICS=true
MONITORING_RATE_LIMIT_METRICS=true
MONITORING_RETENTION_HOURS=24
""".strip()