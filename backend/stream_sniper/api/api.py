import time
from contextlib import asynccontextmanager

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.util import get_remote_address

from ..database.connection_pool import close_pool
from ..logging_config import get_logger, setup_logging
from .auth_endpoints import router as auth_router
from .cache import warm_cache
from .chatter_endpoints import router as chatter_router
from .config import get_config
from .creator_endpoints import router as creator_router
from .middleware import setup_middleware
from .monitoring import record_request_metrics, setup_monitoring
from .operations_endpoints import router as operations_router
from .rate_limiter import setup_rate_limiting
from .stream_endpoints import router as stream_router
from .tracking_endpoints import router as tracking_router

load_dotenv()

# Setup structured logging
setup_logging(environment="production")
logger = get_logger(__name__)

# Get configuration
config = get_config()
if not config.validate():
    raise RuntimeError("Invalid configuration. Please check your environment variables.")


# Pydantic Models for API Documentation




# Tags for endpoint organization
tags_metadata = [
    {"name": "Authentication", "description": "User authentication, registration, and account management"},
    {"name": "Tracking", "description": "Automated streamer tracking and processing management"},
    {"name": "Chatters", "description": "Operations related to chat participants and their messages"},
    {"name": "Streams", "description": "Stream information, analytics, and chat data"},
    {"name": "Creators", "description": "Twitch creator/streamer information"},
    {"name": "Health", "description": "API health monitoring and connection pool status"},
    {"name": "Monitoring", "description": "Performance metrics and monitoring endpoints"},
    {"name": "API Info", "description": "General API information and documentation"},
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: warm caches on startup, close resources on shutdown."""
    logger.info("Starting Stream Sniper API...")

    if config.cache.enabled and config.cache.warm_on_startup:
        try:
            warm_cache()
            logger.info("Cache warming completed")
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")

    logger.info(f"API started successfully on {config.host}:{config.port}")

    yield

    logger.info("Shutting down Stream Sniper API...")
    try:
        close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.warning(f"Error closing connection pool: {e}")


# FastAPI App Configuration
app = FastAPI(
    lifespan=lifespan,
    title=config.title,
    description="""
    A comprehensive Twitch stream analytics API that provides access to chat data, 
    stream statistics, and user interaction analytics from Twitch VODs.
    
    ## Features
    
    * **Authentication**: Secure user registration, login, and JWT-based authentication
    * **Stream Analytics**: Get detailed information about Twitch streams including message counts, duration, and metadata
    * **Chat Analysis**: Access chat messages, most active chatters, and interaction patterns
    * **Creator Insights**: Track creator participation across different streams
    * **User Analytics**: Analyze individual chatter behavior and message history
    * **Tagging Analytics**: Discover most mentioned/tagged users in chat
    * **Performance**: Built-in caching and rate limiting for optimal performance
    * **Monitoring**: Comprehensive metrics and health monitoring
    
    ## Authentication
    
    * **JWT Tokens**: Secure authentication using JSON Web Tokens
    * **Role-based Access**: Support for user and admin roles
    * **Password Security**: Bcrypt password hashing
    * **User Management**: Registration, login, profile updates, and admin controls
    
    ## Performance Features
    
    * **Caching**: Intelligent in-process caching of expensive database queries
    * **Rate Limiting**: Configurable rate limits to prevent abuse
    * **Response Compression**: Automatic compression for large responses
    * **Health Monitoring**: Real-time health checks and performance metrics
    
    ## Data Source
    
    All data is collected from publicly available Twitch VOD chat logs and processed 
    to provide meaningful analytics and insights.
    """,
    version=config.version,
    contact={
        "name": "Stream Sniper",
        "url": "https://github.com/your-repo/stream-sniper",
    },
    license_info={
        "name": "MIT",
    },
    servers=[{"url": f"http://localhost:{config.port}", "description": "Development server"}],
    openapi_tags=tags_metadata,
)

# Setup structured logging middleware
setup_middleware(app, config)

# Setup middleware
if config.cors_enabled:
    origins = config.cors_origins.split(",") if config.cors_origins != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=config.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add compression middleware
if config.compression.enabled:
    app.add_middleware(
        GZipMiddleware, minimum_size=config.compression.min_size, compresslevel=config.compression.compression_level
    )

# Setup rate limiting
if config.rate_limit.enabled:
    setup_rate_limiting(app)

# Setup monitoring
if config.monitoring.enabled:
    setup_monitoring()

# Include authentication router
app.include_router(auth_router)

# Include chatter router
app.include_router(chatter_router)

# Include stream router
app.include_router(stream_router)

# Include creator router
app.include_router(creator_router)

# Include tracking router
app.include_router(tracking_router)

# Include operations router
app.include_router(operations_router)


# Middleware for request metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate metrics
    response_time_ms = (time.time() - start_time) * 1000
    client_ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent")

    # Check if response came from cache
    cache_hit = response.headers.get("X-Cache") == "HIT"

    # Check if request was rate limited
    rate_limited = response.status_code == 429

    # Record metrics
    if config.monitoring.collect_request_metrics:
        record_request_metrics(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            cache_hit=cache_hit,
            rate_limited=rate_limited,
        )

    # Add health check specific headers
    if request.url.path.startswith("/health"):
        response.headers["X-Health-Check"] = "true"
        response.headers["X-Health-Response-Time"] = str(round(response_time_ms, 2))

    return response









if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port, log_level="info" if not config.debug else "debug")
