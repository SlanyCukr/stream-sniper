import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address

from ..database.chatter_table_gateway import select_all_chatters_on_stream_db, select_chatters_by_prefix_db
from ..database.connection_pool import close_pool
from ..database.creator_table_gateway import select_creator_top_chatters_db, select_creators_db
from ..database.message_table_gateway import (
    select_chatter_id_db,
    select_chatter_messages_db,
    select_chatter_stream_activity_db,
)
from ..database.stream_table_gateway import (
    select_all_stream_count_db,
    select_all_streams_db,
    select_chatter_messages_on_stream_db,
    select_chatters_in_stream_db,
    select_creators_that_wrote_in_stream_db,
    select_most_active_chatters_db,
    select_most_tagged_chatters_db,
    select_stream_comprehensive_db,
)
from ..logging_config import get_logger, setup_logging
from .auth_endpoints import router as auth_router
from .cache import CacheTTL, get_cache, warm_cache

# Import our new modules
from .config import get_config
from .health import HealthStatus as HealthStatusEnum
from .health import get_health_checker
from .middleware import setup_middleware
from .monitoring import (
    get_metrics_collector,
    get_monitoring_data,
    record_cache_operation,
    record_request_metrics,
    setup_monitoring,
)
from .rate_limiter import limiter, rate_limits, setup_rate_limiting
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
class Creator(BaseModel):
    """Twitch creator/streamer information"""

    id: int = Field(..., description="Unique creator ID", json_schema_extra={"example": 1})
    display_name: str = Field(..., description="Creator's display name on Twitch", json_schema_extra={"example": "SomeStreamer"})


class Chatter(BaseModel):
    """Chat participant information"""

    id: int = Field(..., description="Unique chatter ID", json_schema_extra={"example": 1})
    nick: str = Field(..., description="Chatter's nickname", json_schema_extra={"example": "viewer123"})


class ChatterID(BaseModel):
    """Chatter ID response"""

    id: int = Field(..., description="Unique chatter ID", json_schema_extra={"example": 1})


class Message(BaseModel):
    """Chat message information"""

    text: str = Field(..., description="Message content", json_schema_extra={"example": "Hello chat!"})
    timestamp: str = Field(..., description="Message timestamp", json_schema_extra={"example": "2024-01-15 20:30:15"})


class StreamBasic(BaseModel):
    """Basic stream information"""

    id: int = Field(..., description="Unique stream ID", json_schema_extra={"example": 1})
    display_name: str = Field(..., description="Stream title/display name", json_schema_extra={"example": "Epic Gaming Session"})
    start: str = Field(..., description="Stream start time", json_schema_extra={"example": "2024-01-15 20:00:00"})
    end: str = Field(..., description="Stream end time", json_schema_extra={"example": "2024-01-15 23:30:00"})
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    message_count: int = Field(..., description="Total number of chat messages", json_schema_extra={"example": 1250})


class ActiveChatter(BaseModel):
    """Most active chatter statistics"""

    chatter_id: int = Field(..., description="Chatter ID", json_schema_extra={"example": 42})
    nick: str = Field(..., description="Chatter nickname", json_schema_extra={"example": "chatty_user"})
    message_count: int = Field(..., description="Number of messages sent", json_schema_extra={"example": 125})


class TaggedChatter(BaseModel):
    """Most tagged chatter statistics"""

    tagged_chatter_id: int = Field(..., description="Tagged chatter ID", json_schema_extra={"example": 15})
    nick: str = Field(..., description="Tagged chatter nickname", json_schema_extra={"example": "popular_user"})
    tag_count: int = Field(..., description="Number of times tagged", json_schema_extra={"example": 45})


class StreamComprehensive(BaseModel):
    """Comprehensive stream information with analytics"""

    title: str = Field(..., description="Stream title", json_schema_extra={"example": "Epic Gaming Session"})
    start: str = Field(..., description="Stream start time", json_schema_extra={"example": "2024-01-15 20:00:00"})
    end: str = Field(..., description="Stream end time", json_schema_extra={"example": "2024-01-15 23:30:00"})
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    message_count: int = Field(..., description="Total chat messages", json_schema_extra={"example": 1250})
    creator_nick: str = Field(..., description="Creator nickname", json_schema_extra={"example": "streamer123"})
    creator_display_name: str = Field(..., description="Creator display name", json_schema_extra={"example": "Amazing Streamer"})
    profile_image_url: Optional[str] = Field(None, description="Creator profile image URL")
    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})


class StreamDetails(BaseModel):
    """Detailed stream analytics response"""

    csi: List[Any] = Field(..., description="Comprehensive stream info tuple")
    mac: List[List[Any]] = Field(..., description="Most active chatters")
    mtc: List[List[Any]] = Field(..., description="Most tagged chatters")
    octw: List[List[Any]] = Field(..., description="Other creators that wrote in stream")
    cis: List[List[Any]] = Field(..., description="Chatters in stream")


class StreamsResponse(BaseModel):
    """Paginated streams response"""

    streams: List[List[Any]] = Field(..., description="List of stream data tuples")
    max_offset: int = Field(..., description="Maximum offset for pagination", json_schema_extra={"example": 1000})


class ErrorResponse(BaseModel):
    """Error response model"""

    detail: str = Field(..., description="Error message", json_schema_extra={"example": "Stream not found"})


class HealthStatus(BaseModel):
    """Basic health status (database is the only critical component checked)"""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    database: Optional[Dict[str, Any]] = Field(None, description="Database connection pool status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: Optional[float] = Field(None, description="Application uptime in seconds")
    error: Optional[str] = Field(None, description="Error detail when the health check itself fails")


class DetailedHealthStatus(BaseModel):
    """Comprehensive health status with system metrics"""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    components: Dict[str, Any] = Field(..., description="Component health status")
    system: Dict[str, Any] = Field(..., description="System metrics and information")


class MetricsResponse(BaseModel):
    """API metrics and monitoring data"""

    system: Dict[str, Any] = Field(..., description="System metrics")
    requests: Dict[str, Any] = Field(..., description="Request statistics")
    cache: Dict[str, Any] = Field(..., description="Cache performance metrics")
    rate_limiting: Dict[str, Any] = Field(..., description="Rate limiting metrics")
    endpoints: Dict[str, Any] = Field(..., description="Per-endpoint statistics")


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
    
    * **Redis Caching**: Intelligent caching of expensive database queries
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

# Include tracking router
app.include_router(tracking_router)


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


@app.get(
    "/chatter/{chatter_id}/messages",
    response_model=List[List[str]],
    tags=["Chatters"],
    summary="Get messages by chatter",
    description=f"""
    Retrieve all messages sent by a specific chatter across all streams.
    Returns a list of [message_text, timestamp] tuples.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of messages with timestamps",
            "content": {
                "application/json": {
                    "example": [
                        ["Hello everyone!", "2024-01-15 20:30:15"],
                        ["Great stream!", "2024-01-15 20:45:22"],
                        ["@streamer keep it up!", "2024-01-15 21:10:03"],
                    ]
                }
            },
        },
        404: {"model": ErrorResponse, "description": "Chatter not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_messages(
    request: Request, response: Response, chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42})
):
    """Get all messages sent by a specific chatter"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("chatter_messages", chatter_id)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_messages")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "chatter_messages")
        result = select_chatter_messages_db(chatter_id)

        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found or has no messages")

        # Cache the result
        cache.set(cache_key, result, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_messages")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatter messages: {e}")
        record_cache_operation("error", "chatter_messages")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/chatter/{nick}/chatter_id",
    response_model=List[int],
    tags=["Chatters"],
    summary="Get chatter ID by nickname",
    description=f"""
    Look up a chatter's unique ID using their nickname.
    Returns the chatter ID that can be used in other endpoints.
    
    **Rate Limit**: {rate_limits.SEARCH}
    """,
    responses={
        200: {"description": "Chatter ID found", "content": {"application/json": {"example": [42]}}},
        404: {"model": ErrorResponse, "description": "Chatter not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.SEARCH)
def get_chatter_id(
    request: Request, response: Response, nick: str = Path(..., description="Chatter nickname", json_schema_extra={"example": "viewer123"})
):
    """Get chatter ID by their nickname"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("chatter_id", nick)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_id")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "chatter_id")
        result = select_chatter_id_db(nick)

        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found")

        # Cache the result
        cache.set(cache_key, result, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_id")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatter ID: {e}")
        record_cache_operation("error", "chatter_id")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/chatters/search",
    response_model=List[List[Any]],
    tags=["Chatters"],
    summary="Search chatters by nickname prefix",
    description=f"""
    Case-insensitive prefix search over chatter nicknames, for autocomplete.
    Returns a list of [chatter_id, nick] pairs ordered by nick.
    Queries shorter than 2 characters return an empty list.

    **Rate Limit**: {rate_limits.SEARCH}
    """,
    responses={
        200: {
            "description": "List of matching [id, nick] pairs",
            "content": {"application/json": {"example": [[42, "ninja"], [77, "ninjastreams"]]}},
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.SEARCH)
def search_chatters(
    request: Request,
    response: Response,
    q: str = Query(..., description="Nickname prefix to search for", json_schema_extra={"example": "nin"}),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of suggestions"),
):
    """Prefix-search chatter nicknames for autocomplete suggestions."""
    prefix = q.strip()
    # Avoid scanning the index on 1-character prefixes (too many matches).
    if len(prefix) < 2:
        return []

    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("chatter_search", prefix.lower(), limit)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_search")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "chatter_search")
        result = select_chatters_by_prefix_db(prefix, limit)

        # Cache the result (empty results are cached too, to absorb repeat typing)
        cache.set(cache_key, result, CacheTTL.CHATTER_SEARCH)
        record_cache_operation("set", "chatter_search")
        response.headers["X-Cache"] = "MISS"

        return result
    except Exception as e:
        logger.error(f"Error searching chatters: {e}")
        record_cache_operation("error", "chatter_search")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/streams",
    response_model=StreamsResponse,
    tags=["Streams"],
    summary="Get streams with pagination",
    description=f"""
    Retrieve streams for a specific creator with pagination support.
    Use creator_id = -1 to get streams from all creators.
    
    Each stream in the response contains:
    - Stream ID
    - Display name/title
    - Start time
    - End time
    - Thumbnail URL
    - Message count
    
    **Rate Limit**: {rate_limits.BULK}
    """,
    responses={
        200: {
            "description": "Paginated list of streams",
            "content": {
                "application/json": {
                    "example": {
                        "streams": [
                            [
                                1,
                                "Epic Gaming Session",
                                "2024-01-15 20:00:00",
                                "2024-01-15 23:30:00",
                                "https://example.com/thumb.jpg",
                                1250,
                            ],
                            [
                                2,
                                "Chill Stream",
                                "2024-01-14 18:00:00",
                                "2024-01-14 22:00:00",
                                "https://example.com/thumb2.jpg",
                                856,
                            ],
                        ],
                        "max_offset": 1000,
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.BULK)
def get_streams(
    request: Request,
    response: Response,
    creator_id: int = Query(..., description="Creator ID (use -1 for all creators)", json_schema_extra={"example": 5}),
    offset: int = Query(0, description="Pagination offset", json_schema_extra={"example": 0}, ge=0),
):
    """Get paginated list of streams for a creator"""
    try:
        cache = get_cache()

        # Cache streams data
        streams_cache_key = cache._generate_key("streams", creator_id, offset)
        cached_streams = cache.get(streams_cache_key)

        # Cache max offset data
        count_cache_key = cache._generate_key("stream_count", creator_id)
        cached_count = cache.get(count_cache_key)

        streams_from_cache = cached_streams is not None
        count_from_cache = cached_count is not None

        # Fetch missing data
        if not streams_from_cache:
            record_cache_operation("miss", "streams")
            streams = select_all_streams_db(creator_id, offset)
            cache.set(streams_cache_key, streams, CacheTTL.STREAM_DETAILS)
            record_cache_operation("set", "streams")
        else:
            record_cache_operation("hit", "streams")
            streams = cached_streams

        if not count_from_cache:
            record_cache_operation("miss", "stream_count")
            max_offset = select_all_stream_count_db(creator_id)
            cache.set(count_cache_key, max_offset, CacheTTL.STREAM_COUNT)
            record_cache_operation("set", "stream_count")
        else:
            record_cache_operation("hit", "stream_count")
            max_offset = cached_count

        # Set cache header
        if streams_from_cache and count_from_cache:
            response.headers["X-Cache"] = "HIT"
        elif streams_from_cache or count_from_cache:
            response.headers["X-Cache"] = "PARTIAL"
        else:
            response.headers["X-Cache"] = "MISS"

        return {"streams": streams, "max_offset": max_offset}
    except Exception as e:
        logger.error(f"Error fetching streams: {e}")
        record_cache_operation("error", "streams")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/stream/{stream_id}/chatters",
    response_model=List[List[Any]],
    tags=["Streams"],
    summary="Get all chatters in a stream",
    description=f"""
    Retrieve all unique chatters who participated in a specific stream.
    Returns chatter information including their IDs and nicknames.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of chatters in the stream",
            "content": {
                "application/json": {"example": [[42, "viewer123"], [15, "chatty_user"], [87, "stream_regular"]]}
            },
        },
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_stream_chatters(
    request: Request, response: Response, stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1})
):
    """Get all chatters who participated in a stream"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("stream_chatters", stream_id)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_chatters")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "stream_chatters")
        result = select_all_chatters_on_stream_db(stream_id)

        if not result:
            raise HTTPException(status_code=404, detail="Stream not found or has no chatters")

        # Cache the result
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "stream_chatters")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stream chatters: {e}")
        record_cache_operation("error", "stream_chatters")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/stream/{stream_id}",
    response_model=StreamDetails,
    tags=["Streams"],
    summary="Get comprehensive stream analytics",
    description=f"""
    Get detailed analytics and information for a specific stream.
    
    Returns comprehensive data including:
    - **csi**: Comprehensive stream info (title, times, creator details)
    - **mac**: Most active chatters (top 3 by message count)
    - **mtc**: Most tagged chatters (top 3 by tag mentions)
    - **octw**: Other creators who wrote in this stream
    - **cis**: Count of unique chatters in stream
    
    This endpoint provides a complete analytics overview of stream chat activity.
    
    **Rate Limit**: {rate_limits.ANALYTICS}
    """,
    responses={
        200: {
            "description": "Comprehensive stream analytics",
            "content": {
                "application/json": {
                    "example": {
                        "csi": [
                            "Epic Gaming Session",
                            "2024-01-15 20:00:00",
                            "2024-01-15 23:30:00",
                            "https://thumb.jpg",
                            1250,
                            "streamer123",
                            "Amazing Streamer",
                            "https://profile.jpg",
                            5,
                        ],
                        "mac": [[42, "chatty_user", 125], [15, "regular_viewer", 89], [7, "stream_fan", 76]],
                        "mtc": [[15, "popular_user", 45], [23, "famous_chatter", 32], [11, "mentioned_user", 28]],
                        "octw": [[99, "other_streamer"], [101, "guest_creator"]],
                        "cis": [[287]],
                    }
                }
            },
        },
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream(
    request: Request, response: Response, stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1})
):
    """Get comprehensive analytics for a specific stream"""
    try:
        cache = get_cache()

        # Check if complete analytics are cached
        analytics_cache_key = cache._generate_key("stream_analytics", stream_id)
        cached_analytics = cache.get(analytics_cache_key)

        if cached_analytics is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_analytics")
            return cached_analytics

        # Cache miss - fetch all data
        record_cache_operation("miss", "stream_analytics")

        comprehensive_stream_info = select_stream_comprehensive_db(stream_id)
        if not comprehensive_stream_info:
            raise HTTPException(status_code=404, detail="Stream not found")

        # Fetch related analytics data
        most_active_chatters = select_most_active_chatters_db(stream_id)
        most_tagged_chatters = select_most_tagged_chatters_db(stream_id)
        other_creators_that_wrote = select_creators_that_wrote_in_stream_db(stream_id, comprehensive_stream_info[8])
        chatters_in_stream = select_chatters_in_stream_db(stream_id)

        analytics_data = {
            "csi": comprehensive_stream_info,
            "mac": most_active_chatters,
            "mtc": most_tagged_chatters,
            "octw": other_creators_that_wrote,
            "cis": chatters_in_stream,
        }

        # Cache the complete analytics
        cache.set(analytics_cache_key, analytics_data, CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "stream_analytics")
        response.headers["X-Cache"] = "MISS"

        return analytics_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stream analytics: {e}")
        record_cache_operation("error", "stream_analytics")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/stream/{stream_id}/chatter/{chatter_id}/messages",
    response_model=List[str],
    tags=["Streams"],
    summary="Get chatter messages in specific stream",
    description=f"""
    Retrieve all messages sent by a specific chatter during a particular stream.
    This is useful for analyzing individual user participation in specific streams.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of messages from the chatter in this stream",
            "content": {
                "application/json": {
                    "example": [
                        "Hello everyone!",
                        "Great play!",
                        "@streamer that was amazing!",
                        "Thanks for the stream!",
                    ]
                }
            },
        },
        404: {"model": ErrorResponse, "description": "Stream or chatter not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_messages_on_stream(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
):
    """Get messages from a specific chatter in a specific stream"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("chatter_stream_messages", stream_id, chatter_id)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_stream_messages")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "chatter_stream_messages")
        result = select_chatter_messages_on_stream_db(stream_id, chatter_id)

        if not result:
            raise HTTPException(status_code=404, detail="No messages found for this chatter in this stream")

        # Extract message text and cache
        messages = [message[0] for message in result]
        cache.set(cache_key, messages, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_stream_messages")
        response.headers["X-Cache"] = "MISS"

        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatter messages on stream: {e}")
        record_cache_operation("error", "chatter_stream_messages")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/creators",
    response_model=List[List[Any]],
    tags=["Creators"],
    summary="Get all creators",
    description=f"""
    Retrieve a list of all Twitch creators/streamers in the database.
    Each creator entry contains their ID and display name.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of all creators",
            "content": {
                "application/json": {
                    "example": [[1, "Amazing Streamer"], [2, "Pro Gamer"], [3, "Chat Master"], [4, "Stream Legend"]]
                }
            },
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_creators(request: Request, response: Response):
    """Get all creators in the database"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("creators")
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creators")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "creators")
        result = select_creators_db()

        # Cache the result
        cache.set(cache_key, result, CacheTTL.CREATORS)
        record_cache_operation("set", "creators")
        response.headers["X-Cache"] = "MISS"

        return result
    except Exception as e:
        logger.error(f"Error fetching creators: {e}")
        record_cache_operation("error", "creators")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/creator/{creator_id}/top-chatters",
    response_model=List[List[Any]],
    tags=["Creators"],
    summary="Get a creator's most active chatters",
    description=f"""
    Retrieve the most active chatters across ALL of a creator's streams.
    Returns a list of [chatter_id, nick, message_count] tuples ordered by
    message count descending.

    An empty list is returned when the creator has no chat activity.

    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of the creator's most active chatters",
            "content": {
                "application/json": {
                    "example": [[42, "chatty_user", 1250], [15, "regular_viewer", 980], [7, "stream_fan", 640]]
                }
            },
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_creator_top_chatters(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 5}),
    limit: int = Query(25, ge=1, le=200, description="Maximum number of chatters to return", json_schema_extra={"example": 25}),
):
    """Get the most active chatters across all of a creator's streams"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("creator_top_chatters", creator_id, limit)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_top_chatters")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "creator_top_chatters")
        result = select_creator_top_chatters_db(creator_id, limit)

        # Cache the result (an empty list is a valid, cacheable state)
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "creator_top_chatters")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching creator top chatters: {e}")
        record_cache_operation("error", "creator_top_chatters")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/chatter/{chatter_id}/stream-activity",
    response_model=List[List[Any]],
    tags=["Chatters"],
    summary="Get a chatter's cross-stream footprint",
    description=f"""
    Retrieve the streams a chatter appeared in (up to their 100 most active),
    along with their message count per stream. Returns a list of
    [stream_id, title, start, creator_id, creator_display_name, message_count]
    tuples ordered by message count descending.

    An empty list is returned when the chatter has no recorded activity.

    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of streams the chatter appeared in with per-stream message counts",
            "content": {
                "application/json": {
                    "example": [
                        [1, "Epic Gaming Session", "2024-01-15 20:00:00", 5, "Amazing Streamer", 125],
                        [2, "Chill Stream", "2024-01-14 18:00:00", 5, "Amazing Streamer", 42],
                    ]
                }
            },
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_stream_activity(
    request: Request, response: Response, chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42})
):
    """Get every stream a chatter appeared in with their per-stream message count"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("chatter_stream_activity", chatter_id)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_stream_activity")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "chatter_stream_activity")
        result = select_chatter_stream_activity_db(chatter_id)

        # Cache the result (an empty list is a valid, cacheable state)
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "chatter_stream_activity")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatter stream activity: {e}")
        record_cache_operation("error", "chatter_stream_activity")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/health",
    response_model=HealthStatus,
    tags=["Health"],
    summary="Basic Health Check",
    description=f"""
    Basic health check endpoint for load balancer health checks.
    Only checks critical components (database connectivity).
    
    Returns 200 if system is operational, 503 if critical issues exist.
    
    **Rate Limit**: {rate_limits.HEALTH}
    """,
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T20:30:15Z",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "database": {"status": "healthy", "healthy": True, "response_time_ms": 5.2},
                    }
                }
            },
        },
        503: {
            "description": "System is unhealthy - critical issues detected",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2024-01-15T20:30:15Z",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "database": {"status": "critical", "healthy": False, "response_time_ms": 5000},
                    }
                }
            },
        },
    },
)
@limiter.limit(rate_limits.HEALTH)
def health_check(request: Request, response: Response):
    """Basic health check endpoint for load balancers"""
    try:
        health_checker = get_health_checker()
        overall_status, health_data = health_checker.get_basic_health()

        # Set HTTP status code based on health
        if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL]:
            response.status_code = 503
        else:
            response.status_code = 200

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(e),
        }


@app.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    tags=["Health"],
    summary="Detailed Health Check",
    description=f"""
    Comprehensive health check with detailed system monitoring.
    
    Includes:
    * All system components (database, cache, rate limiter, external APIs)
    * System resource utilization (CPU, memory, disk)
    * Component response times and detailed status
    * External dependency checks (Twitch API)
    
    **Rate Limit**: {rate_limits.HEALTH}
    """,
    responses={
        200: {
            "description": "Detailed system health information",
        },
        503: {
            "description": "System has critical issues",
        },
    },
)
@limiter.limit(rate_limits.HEALTH)
def detailed_health_check(request: Request, response: Response):
    """Comprehensive health check with system metrics"""
    try:
        health_checker = get_health_checker()
        overall_status, health_data = health_checker.get_detailed_health()

        # Set HTTP status code based on health
        if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL]:
            response.status_code = 503
        elif overall_status == HealthStatusEnum.DEGRADED:
            response.status_code = 200  # Degraded is still operational
        else:
            response.status_code = 200

        return health_data

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(e),
        }


@app.get(
    "/metrics/prometheus",
    tags=["Monitoring"],
    summary="Prometheus Metrics",
    description=f"""
    Prometheus-compatible metrics endpoint for monitoring systems.
    
    Returns metrics in Prometheus exposition format including:
    * Component health status (as numeric values)
    * Component response times
    * System resource utilization
    * Application uptime
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Prometheus metrics in text format",
            "content": {
                "text/plain": {
                    "example": """# HELP stream_sniper_component_health Health status of system components
# TYPE stream_sniper_component_health gauge
stream_sniper_component_health{component="database"} 1.0
stream_sniper_component_health{component="cache"} 1.0
"""
                }
            },
        }
    },
)
@limiter.limit(rate_limits.GENERAL)
def prometheus_metrics(request: Request):
    """Get Prometheus-compatible metrics"""
    try:
        health_checker = get_health_checker()
        metrics_text = health_checker.generate_prometheus_metrics()

        return Response(content=metrics_text, media_type="text/plain; version=0.0.4")

    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        error_time = int(time.time() * 1000)
        error_metrics = f"""# HELP stream_sniper_metrics_error Error generating metrics
# TYPE stream_sniper_metrics_error gauge
stream_sniper_metrics_error 1 {error_time}
"""
        return Response(content=error_metrics, media_type="text/plain; version=0.0.4")


# Monitoring endpoints
@app.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Monitoring"],
    summary="API Performance Metrics",
    description=f"""
    Get comprehensive performance metrics and monitoring data.
    
    Includes:
    * Request statistics and response times
    * Cache hit/miss rates and performance
    * Rate limiting statistics
    * Per-endpoint performance metrics
    * System uptime and health
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Performance metrics data",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_metrics(request: Request):
    """Get comprehensive API performance metrics"""
    try:
        metrics_data = get_monitoring_data()
        return metrics_data
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@app.get(
    "/cache/stats",
    tags=["Monitoring"],
    summary="Cache Statistics",
    description=f"""
    Get detailed cache performance statistics.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Cache statistics",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_cache_stats(request: Request):
    """Get detailed cache performance statistics"""
    try:
        cache = get_cache()
        cache_stats = cache.get_stats()

        # Add metrics from monitoring
        collector = get_metrics_collector()
        summary = collector.get_summary_stats()

        return {
            "redis_stats": cache_stats,
            "performance_metrics": summary.get("cache", {}),
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Error fetching cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cache statistics")


@app.post(
    "/cache/flush",
    tags=["Monitoring"],
    summary="Flush Cache",
    description=f"""
    Flush all cached data. Use with caution as this will impact performance
    until cache is rebuilt.
    
    **Rate Limit**: {rate_limits.HEAVY}
    """,
    responses={
        200: {
            "description": "Cache flushed successfully",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.HEAVY)
def flush_cache(request: Request):
    """Flush all cached data"""
    try:
        cache = get_cache()
        success = cache.flush_all()

        if success:
            return {"message": "Cache flushed successfully", "timestamp": datetime.now().isoformat() + "Z"}
        else:
            raise HTTPException(status_code=500, detail="Failed to flush cache")
    except Exception as e:
        logger.error(f"Error flushing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to flush cache")


# Root endpoint for API information
@app.get(
    "/", tags=["API Info"], summary="API Information", description="Get basic information about the Stream Sniper API"
)
def root():
    """Welcome endpoint with API information"""
    return {
        "name": config.title,
        "version": config.version,
        "description": config.description,
        "docs": "/docs",
        "redoc": "/redoc",
        "features": {
            "caching": config.cache.enabled,
            "rate_limiting": config.rate_limit.enabled,
            "compression": config.compression.enabled,
            "monitoring": config.monitoring.enabled,
        },
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "metrics": "/metrics",
            "prometheus_metrics": "/metrics/prometheus",
            "cache_stats": "/cache/stats",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port, log_level="info" if not config.debug else "debug")
