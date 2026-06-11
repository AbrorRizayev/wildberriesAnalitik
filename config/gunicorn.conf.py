"""Gunicorn configuration for AIRA (production WSGI server)."""

import multiprocessing
import os

# Bind inside the container; nginx (or any proxy) forwards to this port.
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# Sensible default: (2 * CPU) + 1, capped at 8 so a many-core host doesn't spawn
# dozens of memory-hungry workers for a modest user base. Override via env.
_default_workers = min((multiprocessing.cpu_count() * 2) + 1, 8)
workers = int(os.environ.get('GUNICORN_WORKERS', _default_workers))
threads = int(os.environ.get('GUNICORN_THREADS', '2'))

# Excel parsing happens in-request and can be slow on big files — give it room.
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
graceful_timeout = 30
keepalive = 5

# Recycle workers periodically to bound memory growth from large uploads.
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = 100

# Log to stdout/stderr so the container runtime collects them.
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')