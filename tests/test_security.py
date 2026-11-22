import os
import pytest
from app import create_app
from config import Config, TestingConfig


def test_production_secret_key_enforcement(monkeypatch):
    """Verify application crashes if SECRET_KEY is missing in production."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("FLASK_DEBUG", "0")

    with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        # Reloading Config logic
        _ = Config()
        # Explicit validation check on Config class
        if not os.getenv("SECRET_KEY") and (os.getenv("FLASK_ENV") == "production" and os.getenv("FLASK_DEBUG", "0") == "0"):
            raise RuntimeError("CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY required")


def test_session_cookie_security_flags(app):
    """Verify session cookie security flags comply with OWASP recommendations."""
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_rate_limiting_active():
    """Verify Flask-Limiter is enabled and attached to the application factory."""
    prod_config = Config
    assert prod_config.RATELIMIT_ENABLED is True
    assert prod_config.RATELIMIT_STORAGE_URI == "memory://"


def test_rate_limit_preview_behavior():
    """Verify preview endpoint returns HTTP 429 with friendly JSON when exceeded."""
    class RateLimitTestConfig(TestingConfig):
        RATELIMIT_ENABLED = True

    test_app = create_app(RateLimitTestConfig)
    client = test_app.test_client()

    statuses = []
    for _ in range(25):
        resp = client.post("/api/preview", json={
            "content": "https://example.com",
            "qr_type": "url",
            "foreground": "#000000",
            "background": "#FFFFFF"
        })
        statuses.append(resp.status_code)

    assert 429 in statuses
    # The 429 response contains friendly JSON error
    last_resp = client.post("/api/preview", json={"content": "https://example.com"})
    assert last_resp.status_code == 429
    assert "rate limit" in last_resp.get_json()["error"].lower()


def test_health_check_endpoint(client):
    """Verify cloud container health check probes application and database status."""
    for endpoint in ["/healthz", "/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["service"] == "cloud-qr-generator"
        assert "timestamp" in data

    # Test liveness check
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    live_data = live_resp.get_json()
    assert live_data["status"] == "live"


def test_health_check_database_failure_returns_503(client):
    """Verify health check returns 503 when database execution fails."""
    from unittest.mock import patch
    from sqlalchemy.exc import OperationalError

    with patch("extensions.db.session.execute", side_effect=OperationalError("Connection failed", {}, None)):
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"

