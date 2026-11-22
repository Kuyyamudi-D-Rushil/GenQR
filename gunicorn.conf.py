"""Gunicorn production configuration for CloudQR on Render."""

import os

# Render passes the listening port via the $PORT environment variable (default 10000)
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Concurrency & worker model tuned for Cloud container performance
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("PYTHON_GET_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Log directly to stdout/stderr for Render live log aggregation
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# Graceful worker restart
graceful_timeout = 30
