"""
Gunicorn production configuration.
"""
import multiprocessing
import os

# ─── Server Socket ────────────────────────────────────────
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# ─── Worker Processes ─────────────────────────────────────
workers = int(os.getenv("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "sync"
worker_connections = 1000

# ─── Timeouts ────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 30
graceful_timeout = 30

# ─── Request Limits ──────────────────────────────────────
max_requests = 1000
max_requests_jitter = 50
limit_request_line = 8190
limit_request_fields = 100

# ─── Logging ─────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ─── Security ────────────────────────────────────────────
forwarded_allow_ips = "*"

# ─── Preload ─────────────────────────────────────────────
preload_app = True


def on_starting(server):
    """Called just before the master process is initialized."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")
