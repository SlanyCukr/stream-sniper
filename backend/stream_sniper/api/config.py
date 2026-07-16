"""
Configuration management for API settings including rate limits and cache settings.
Centralizes all configurable parameters with environment variable support.
"""

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CacheConfig:
    """Cache configuration settings (in-process cache — no external store)."""

    enabled: bool = True
    default_ttl: int = 3600  # 1 hour

    ttl_creators: int = 7200  # 2 hours
    ttl_stream_count: int = 1800  # 30 minutes
    ttl_stream_analytics: int = 3600  # 1 hour
    ttl_most_active_chatters: int = 3600  # 1 hour
    ttl_most_tagged_chatters: int = 3600  # 1 hour
    ttl_stream_details: int = 1800  # 30 minutes
    ttl_chatter_messages: int = 1800  # 30 minutes
    ttl_health_check: int = 300  # 5 minutes

    warm_on_startup: bool = True
    warm_creators: bool = True
    warm_stream_counts: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration settings."""

    enabled: bool = True
    strategy: str = "moving-window"
    headers_enabled: bool = True

    default_limit: str = "1000 per hour"
    general: str = "100 per minute"
    analytics: str = "30 per minute"
    heavy: str = "10 per minute"
    health: str = "300 per minute"
    bulk: str = "20 per minute"
    search: str = "50 per minute"


@dataclass
class CompressionConfig:
    """Response compression configuration settings."""

    enabled: bool = True
    min_size: int = 1024  # 1KB minimum
    compression_level: int = 6  # Default gzip level

    mime_types: str = "application/json,text/plain,text/html,application/javascript,text/css"


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration settings."""

    enabled: bool = True

    collect_request_metrics: bool = True
    collect_cache_metrics: bool = True
    collect_rate_limit_metrics: bool = True

    metrics_retention_hours: int = 24


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    user: str = ""
    password: str = ""
    host: str = "localhost"
    database: str = ""
    port: int = 5432
    options: str = "-c search_path=stream_sniper"

    pool_min_conn: int = 2
    pool_max_conn: int = 20
    connect_timeout: int = 10
    command_timeout: int = 60

    health_check_interval: int = 30


@dataclass
class AuthConfig:
    """JWT configuration resolved at an executable boundary."""

    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@dataclass
class APIConfig:
    """Main API configuration combining all settings."""

    title: str = "Stream Sniper API"
    description: str = "Twitch stream analytics API"
    version: str = "1.0.0"

    host: str = "0.0.0.0"
    port: int = 5002
    debug: bool = False

    cors_enabled: bool = True
    cors_origins: str = "*"
    cors_credentials: bool = True

    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for serialization."""

        return asdict(self)

    def validate(self) -> bool:
        """Return whether the configuration satisfies runtime invariants."""
        try:
            if not (1 <= self.port <= 65535):
                raise ValueError(f"Invalid API port: {self.port}")

            if self.database.connect_timeout <= 0:
                raise ValueError(f"Invalid database connect timeout: {self.database.connect_timeout}")

            if self.database.pool_min_conn < 1:
                raise ValueError(f"Invalid database min connections: {self.database.pool_min_conn}")

            if self.database.pool_max_conn < self.database.pool_min_conn:
                raise ValueError("Database max connections must be >= min connections")

            if self.cache.default_ttl < 1:
                raise ValueError(f"Invalid default TTL: {self.cache.default_ttl}")

            if not self.auth.secret_key:
                raise ValueError("JWT signing secret is not configured")

            return True

        except ValueError as e:
            from ..logging_config import get_logger

            logger = get_logger(__name__)
            logger.error(f"Configuration validation error: {e}")
            return False


def _bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    return env.get(name, str(default)).lower() == "true"


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    return int(env.get(name, default))


def load_config(environ: Mapping[str, str] | None = None) -> APIConfig:
    """Build a fresh configuration snapshot from the supplied environment."""
    env = os.environ if environ is None else environ
    return APIConfig(
        title=env.get("API_TITLE", "Stream Sniper API"),
        description=env.get("API_DESCRIPTION", "Twitch stream analytics API"),
        version=env.get("API_VERSION", "1.0.0"),
        host=env.get("API_HOST", "0.0.0.0"),
        port=_int(env, "API_PORT", 5002),
        debug=_bool(env, "API_DEBUG", False),
        cors_enabled=_bool(env, "CORS_ENABLED", True),
        cors_origins=env.get("CORS_ORIGINS", "*"),
        cors_credentials=_bool(env, "CORS_CREDENTIALS", True),
        cache=CacheConfig(
            enabled=_bool(env, "CACHE_ENABLED", True),
            default_ttl=_int(env, "CACHE_DEFAULT_TTL", 3600),
            ttl_creators=_int(env, "CACHE_TTL_CREATORS", 7200),
            ttl_stream_count=_int(env, "CACHE_TTL_STREAM_COUNT", 1800),
            ttl_stream_analytics=_int(env, "CACHE_TTL_STREAM_ANALYTICS", 3600),
            ttl_most_active_chatters=_int(env, "CACHE_TTL_MOST_ACTIVE_CHATTERS", 3600),
            ttl_most_tagged_chatters=_int(env, "CACHE_TTL_MOST_TAGGED_CHATTERS", 3600),
            ttl_stream_details=_int(env, "CACHE_TTL_STREAM_DETAILS", 1800),
            ttl_chatter_messages=_int(env, "CACHE_TTL_CHATTER_MESSAGES", 1800),
            ttl_health_check=_int(env, "CACHE_TTL_HEALTH_CHECK", 300),
            warm_on_startup=_bool(env, "CACHE_WARM_ON_STARTUP", True),
            warm_creators=_bool(env, "CACHE_WARM_CREATORS", True),
            warm_stream_counts=_bool(env, "CACHE_WARM_STREAM_COUNTS", True),
        ),
        rate_limit=RateLimitConfig(
            enabled=_bool(env, "RATE_LIMIT_ENABLED", True),
            strategy=env.get("RATE_LIMIT_STRATEGY", "moving-window"),
            headers_enabled=_bool(env, "RATE_LIMIT_HEADERS_ENABLED", True),
            default_limit=env.get("RATE_LIMIT_DEFAULT", "1000 per hour"),
            general=env.get("RATE_LIMIT_GENERAL", "100 per minute"),
            analytics=env.get("RATE_LIMIT_ANALYTICS", "30 per minute"),
            heavy=env.get("RATE_LIMIT_HEAVY", "10 per minute"),
            health=env.get("RATE_LIMIT_HEALTH", "300 per minute"),
            bulk=env.get("RATE_LIMIT_BULK", "20 per minute"),
            search=env.get("RATE_LIMIT_SEARCH", "50 per minute"),
        ),
        compression=CompressionConfig(
            enabled=_bool(env, "COMPRESSION_ENABLED", True),
            min_size=_int(env, "COMPRESSION_MIN_SIZE", 1024),
            compression_level=_int(env, "COMPRESSION_LEVEL", 6),
            mime_types=env.get(
                "COMPRESSION_MIME_TYPES",
                "application/json,text/plain,text/html,application/javascript,text/css",
            ),
        ),
        monitoring=MonitoringConfig(
            enabled=_bool(env, "MONITORING_ENABLED", True),
            collect_request_metrics=_bool(env, "MONITORING_REQUEST_METRICS", True),
            collect_cache_metrics=_bool(env, "MONITORING_CACHE_METRICS", True),
            collect_rate_limit_metrics=_bool(env, "MONITORING_RATE_LIMIT_METRICS", True),
            metrics_retention_hours=_int(env, "MONITORING_RETENTION_HOURS", 24),
        ),
        database=DatabaseConfig(
            user=env.get("POSTGRES_USER", ""),
            password=env.get("POSTGRES_PASSWORD", ""),
            host=env.get("POSTGRES_HOST", "localhost"),
            database=env.get("POSTGRES_DB", ""),
            port=_int(env, "POSTGRES_PORT", 5432),
            pool_min_conn=_int(env, "DB_POOL_MIN_CONN", 2),
            pool_max_conn=_int(env, "DB_POOL_MAX_CONN", 20),
            connect_timeout=_int(env, "DB_CONNECT_TIMEOUT", 10),
            command_timeout=_int(env, "DB_COMMAND_TIMEOUT", 60),
            health_check_interval=_int(env, "DB_HEALTH_CHECK_INTERVAL", 30),
        ),
        auth=AuthConfig(
            secret_key=env.get("JWT_SECRET_KEY") or env.get("SECRET_KEY", ""),
            algorithm=env.get("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=_int(env, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30),
        ),
    )


def validate_config(config: APIConfig) -> bool:
    """Validate an explicit configuration snapshot."""
    return config.validate()


def log_config_summary(config: APIConfig) -> None:
    """Log a summary of an explicit configuration snapshot."""
    from ..logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("=== Stream Sniper API Configuration ===")
    logger.info(f"API: {config.title} v{config.version}")
    logger.info(f"Server: {config.host}:{config.port} (debug={config.debug})")
    logger.info(f"Cache: {'enabled' if config.cache.enabled else 'disabled'} (in-process)")
    logger.info(f"Rate Limiting: {'enabled' if config.rate_limit.enabled else 'disabled'}")
    logger.info(f"Compression: {'enabled' if config.compression.enabled else 'disabled'}")
    logger.info(f"Monitoring: {'enabled' if config.monitoring.enabled else 'disabled'}")
    logger.info(f"Database Pool: {config.database.pool_min_conn}-{config.database.pool_max_conn} connections")
    logger.info("=" * 40)


def create_env_template() -> str:
    """Return a complete example environment file."""
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
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=localhost
POSTGRES_DB=your_database_name
POSTGRES_PORT=5432

# Database Pool Settings
DB_POOL_MIN_CONN=2
DB_POOL_MAX_CONN=20
DB_CONNECT_TIMEOUT=10
DB_COMMAND_TIMEOUT=60
DB_HEALTH_CHECK_INTERVAL=30

# Cache Behavior (in-process cache — no external store)
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
