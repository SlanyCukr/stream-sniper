"""Ops-hardening regression tests: proxy-aware rate-limit keys and the CORS credentials gate.

Both defects came from the 2026-07-18 security audit:
- The limiter keyed on ``request.client.host``, but production traffic all arrives through
  the Next.js server-side proxy — every user shared ONE bucket.
- Wildcard CORS origins with ``allow_credentials=True`` makes Starlette reflect any request
  Origin with credentials allowed.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from stream_sniper.api.api import create_app
from stream_sniper.api.config import APIConfig, AuthConfig
from stream_sniper.api.security.rate_limiter import _client_key


def _request(headers: dict[str, str] | None = None, client_host: str = "172.18.0.5"):
    """A minimal Request stand-in: _client_key only touches .headers and .client.host."""
    lowered = {key.lower(): value for key, value in (headers or {}).items()}
    return SimpleNamespace(headers=lowered, client=SimpleNamespace(host=client_host))


class TestClientKey:
    def test_no_proxy_headers_falls_back_to_client_host(self):
        assert _client_key(_request()) == "172.18.0.5"

    def test_cf_connecting_ip_wins_over_everything(self):
        request = _request(
            {
                "CF-Connecting-IP": "203.0.113.7",
                "X-Real-IP": "198.51.100.1",
                "X-Forwarded-For": "192.0.2.9",
            }
        )
        assert _client_key(request) == "203.0.113.7"

    def test_x_real_ip_wins_over_forwarded_for(self):
        request = _request({"X-Real-IP": "198.51.100.1", "X-Forwarded-For": "192.0.2.9"})
        assert _client_key(request) == "198.51.100.1"

    def test_forwarded_for_rightmost_public_entry(self):
        # Client-supplied (spoofable) entries sit LEFT of the entry our proxy appended;
        # the rightmost public entry is the trustworthy one.
        request = _request({"X-Forwarded-For": "6.6.6.6, 93.184.216.34"})
        assert _client_key(request) == "93.184.216.34"

    def test_forwarded_for_skips_private_proxy_hops(self):
        # Internal proxy addresses (our own infra) must not become the key.
        request = _request({"X-Forwarded-For": "93.184.216.34, 10.0.0.2, 172.18.0.9"})
        assert _client_key(request) == "93.184.216.34"

    def test_invalid_header_values_fall_through(self):
        # Garbage in a spoofable header must not mint a fresh bucket.
        request = _request(
            {"CF-Connecting-IP": "not-an-ip", "X-Real-IP": "also junk", "X-Forwarded-For": "nope"},
            client_host="172.18.0.5",
        )
        assert _client_key(request) == "172.18.0.5"

    def test_ipv6_client_supported(self):
        request = _request({"X-Real-IP": "2001:db8::1"})
        assert _client_key(request) == "2001:db8::1"


def _app(cors_origins: str, cors_credentials: bool = True):
    config = APIConfig(
        auth=AuthConfig(secret_key="test-secret"),
        cors_origins=cors_origins,
        cors_credentials=cors_credentials,
    )
    return create_app(config)


class TestCORSCredentialsGate:
    def test_wildcard_origins_never_allow_credentials(self):
        app = _app("*", cors_credentials=True)
        # No lifespan: middleware works without startup, and unit tests have no DB.
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Without the gate, Starlette would REFLECT the origin and allow credentials.
        assert response.headers.get("access-control-allow-origin") == "*"
        assert "access-control-allow-credentials" not in response.headers

    def test_explicit_allowlist_keeps_credentials(self):
        app = _app("https://stream-sniper.slanycukr.com", cors_credentials=True)
        client = TestClient(app)
        allowed = client.options(
            "/health",
            headers={
                "Origin": "https://stream-sniper.slanycukr.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed.headers.get("access-control-allow-origin") == "https://stream-sniper.slanycukr.com"
        assert allowed.headers.get("access-control-allow-credentials") == "true"
        assert denied.headers.get("access-control-allow-origin") is None
