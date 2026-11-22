import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-replace-in-production-32b0f")

    # Render uses 'postgres://' which SQLAlchemy 1.4+ deprecated in favor of 'postgresql://'
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///qr_generator.db")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevents unexpected form expiry during user sessions
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB max payload


class TestingConfig(Config):
    """Configuration for automated test suite."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
