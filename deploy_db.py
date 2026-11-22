"""Database migration runner for CloudQR deployment.

Applies Alembic database migrations directly using Flask-Migrate's Python API,
avoiding Flask CLI command discovery issues in cloud container environments.
"""

import os
import sys

# Ensure FLASK_APP and a fallback SECRET_KEY are present for standalone migrations
os.environ.setdefault("FLASK_APP", "app:app")
os.environ.setdefault("SECRET_KEY", "db-migration-bootstrap-key")

from app import create_app
from extensions import db
from flask_migrate import upgrade


def run_migrations():
    """Execute all pending Alembic migrations safely on the target database."""
    print("[MIGRATE] Initializing CloudQR application context for migrations...")
    app = create_app()

    with app.app_context():
        raw_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        # Mask credentials in logs for security
        safe_target = raw_uri.split("@")[-1] if "@" in raw_uri else raw_uri.split("///")[-1]
        print(f"[MIGRATE] Target database host/file: {safe_target}")
        print("[MIGRATE] Executing Alembic upgrade to head...")

        upgrade()

        print("[MIGRATE] Database migrations applied successfully! Schema is up-to-date.")


if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as e:
        print(f"[MIGRATE] Migration failure: {e}", file=sys.stderr)
        sys.exit(1)
