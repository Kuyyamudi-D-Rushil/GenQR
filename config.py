import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base application configuration with strict production security."""

    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    TESTING = False

    # Production Secret Key Enforcement:
    # Require SECRET_KEY from environment variables unless explicitly in dev mode
    _secret_key = os.getenv("SECRET_KEY")
    if not _secret_key:
        if ENV == "development" or DEBUG:
            _secret_key = "dev-insecure-fallback-secret-key-for-local-use-only"
        else:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "The SECRET_KEY environment variable must be set in production. "
                "Set a strong random key in your environment or Render settings."
            )
    SECRET_KEY = _secret_key

    # Render uses 'postgres://' which SQLAlchemy 1.4+ deprecated in favor of 'postgresql://'
    # SQLAlchemy 2.0 with psycopg (v3) uses 'postgresql+psycopg://'
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///qr_generator.db")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_db_url.startswith("postgresql://"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pooling and pre-ping to prevent stale connections on cloud PostgreSQL
    if raw_db_url.startswith("postgresql"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # Security & CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevents unexpected form expiry during active user sessions
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB max payload

    # Secure Session Cookie Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        (ENV == "production" and not DEBUG)
        or os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
    )

    # Rate Limiting Settings
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"


class TestingConfig(Config):
    """Configuration for automated test suite."""

    TESTING = True
    DEBUG = True
    ENV = "testing"
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
