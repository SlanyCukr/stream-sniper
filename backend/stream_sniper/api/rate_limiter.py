"""
Rate limiting implementation using slowapi (FastAPI-compatible version of Flask-Limiter).
Provides configurable rate limits backed by in-process memory storage.
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
load_dotenv()


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting. Uses IP address by default,
    but can be extended to use authentication tokens, API keys, etc.

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier for the client
    """
    # Get client IP
    client_ip = get_remote_address(request)

    # Check for API key in headers (for future authentication)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"

    # Check for authenticated user (for future authentication)
    auth_header = request.headers.get("Authorization")
    if auth_header:
        return f"auth:{auth_header[:20]}"  # Use first 20 chars to avoid long keys

    # Default to IP address
    return f"ip:{client_ip}"


def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter instance.

    Uses in-process memory storage: the API runs as a single process, so a shared
    store isn't needed. Counters reset on restart and are per-process (they would
    not be shared across replicas if the app were ever scaled out).

    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(
        key_func=get_identifier,
        storage_uri="memory://",
        default_limits=["1000 per hour"],  # Default global limit
        strategy="moving-window",
        headers_enabled=True,
    )

    logger.info("Rate limiter initialized with in-memory storage")
    return limiter


# Create global limiter instance
limiter = create_limiter()


class RateLimitConfig:
    """
    Rate limiting configuration for different endpoint types.
    Configurable via environment variables.
    """

    def __init__(self):
        """Initialize rate limit configuration from environment variables."""

        # General API limits
        self.GENERAL = os.getenv("RATE_LIMIT_GENERAL", "100 per minute")

        # Analytics endpoints (more expensive)
        self.ANALYTICS = os.getenv("RATE_LIMIT_ANALYTICS", "30 per minute")

        # Heavy computation endpoints
        self.HEAVY = os.getenv("RATE_LIMIT_HEAVY", "10 per minute")

        # Health check (should be generous)
        self.HEALTH = os.getenv("RATE_LIMIT_HEALTH", "300 per minute")

        # Bulk data endpoints
        self.BULK = os.getenv("RATE_LIMIT_BULK", "20 per minute")

        # Search endpoints
        self.SEARCH = os.getenv("RATE_LIMIT_SEARCH", "50 per minute")


# Global rate limit configuration
rate_limits = RateLimitConfig()


def get_rate_limit_stats() -> Dict[str, Any]:
    """
    Get rate limiting statistics and health information.

    Returns:
        Dictionary with rate limiting statistics
    """
    try:
        # In-process memory storage.
        storage_info = {"type": "memory", "status": "healthy"}

        return {
            "enabled": True,
            "storage": storage_info,
            "default_limits": limiter._default_limits,
            "strategy": limiter._strategy,
            "headers_enabled": limiter._headers_enabled,
            "rate_limits": {
                "general": rate_limits.GENERAL,
                "analytics": rate_limits.ANALYTICS,
                "heavy": rate_limits.HEAVY,
                "health": rate_limits.HEALTH,
                "bulk": rate_limits.BULK,
                "search": rate_limits.SEARCH,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get rate limit stats: {e}")
        return {"enabled": False, "error": str(e)}


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom rate limit exceeded handler with detailed error information.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        Custom error response
    """
    return {
        "error": "Rate limit exceeded",
        "detail": f"Rate limit exceeded: {exc.detail}",
        "retry_after": exc.retry_after,
        "limit": str(exc.limit),
        "identifier": get_identifier(request),
        "endpoint": str(request.url.path),
        "timestamp": exc.retry_after,
    }


def setup_rate_limiting(app):
    """
    Setup rate limiting middleware and error handlers for FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Add rate limiting middleware
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # Add custom rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

    logger.info("Rate limiting middleware configured successfully")


def bypass_rate_limit(request: Request) -> bool:
    """
    Check if a request should bypass rate limiting.
    Can be used for whitelisted IPs, admin users, etc.

    Args:
        request: FastAPI request object

    Returns:
        True if rate limiting should be bypassed
    """
    # Check for bypass header (for testing/admin)
    bypass_token = request.headers.get("X-Rate-Limit-Bypass")
    expected_token = os.getenv("RATE_LIMIT_BYPASS_TOKEN")

    if bypass_token and expected_token and bypass_token == expected_token:
        return True

    # Check for whitelisted IPs
    client_ip = get_remote_address(request)
    whitelisted_ips = os.getenv("RATE_LIMIT_WHITELIST_IPS", "").split(",")
    whitelisted_ips = [ip.strip() for ip in whitelisted_ips if ip.strip()]

    if client_ip in whitelisted_ips:
        return True

    # Check for localhost (development)
    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        localhost_bypass = os.getenv("RATE_LIMIT_BYPASS_LOCALHOST", "true").lower() == "true"
        if localhost_bypass:
            return True

    return False


# Decorator for conditional rate limiting
def conditional_rate_limit(limit: str):
    """
    Decorator that applies rate limiting conditionally based on bypass rules.

    Args:
        limit: Rate limit string (e.g., "100 per minute")
    """

    def decorator(func):
        # Apply the rate limit
        limited_func = limiter.limit(limit)(func)

        # Add bypass logic
        def wrapper(*args, **kwargs):
            # Check if we should bypass rate limiting
            # Note: This is a simplified implementation
            # In practice, you'd need access to the request object
            return limited_func(*args, **kwargs)

        return wrapper

    return decorator
