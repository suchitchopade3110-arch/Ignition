"""
Prometheus metrics — GET /metrics (app/main.py), unauthenticated like
/healthz (a scraper needs to reach it without a session).

Deliberately not prometheus-fastapi-instrumentator or any other
auto-instrumentation package: this app's most useful metrics are business
events (webhook outcomes, review lifecycle, rate-limit rejections) that no
generic HTTP auto-instrumentor knows about, and the generic HTTP
request/latency metrics it WOULD add for free are covered here too via one
small middleware. One dependency (prometheus_client) covers both instead
of two.

Single process-wide REGISTRY (prometheus_client's default) — correct for
this deployment: the FastAPI process and the Arq worker process are
already separate (app/main.py vs app/worker.py), so there's no
multi-process-within-one-metrics-endpoint problem to solve with the
multiprocess collector prometheus_client also offers. If this backend is
ever run with multiple worker processes behind one /metrics endpoint
(e.g. gunicorn -w N), that collector would need to replace this — flagging
the boundary rather than silently assuming it away.
"""
from prometheus_client import Counter, Histogram, Gauge

# --- HTTP-level (recorded by the middleware in app/main.py) ---
http_requests_total = Counter(
    "ignition_http_requests_total",
    "Total HTTP requests handled, labeled by method, route template, and status code.",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "ignition_http_request_duration_seconds",
    "HTTP request latency in seconds, labeled by method and route template.",
    ["method", "path"],
)

rate_limit_exceeded_total = Counter(
    "ignition_rate_limit_exceeded_total",
    "Requests rejected by slowapi rate limiting, labeled by route path.",
    ["path"],
)

# --- Webhook (app/main.py::github_webhook) ---
webhook_events_total = Counter(
    "ignition_webhook_events_total",
    "GitHub webhook deliveries received, labeled by event type and outcome.",
    ["event_type", "outcome"],  # outcome: queued | duplicate | ignored | processed | rejected
)

# --- Review lifecycle (app/services/review_pipeline.py) ---
reviews_completed_total = Counter(
    "ignition_reviews_completed_total",
    "Reviews that reached a terminal state, labeled by final status.",
    ["status"],  # completed | failed | waiting_hitl (timeout) | cancelled
)

review_duration_seconds = Histogram(
    "ignition_review_duration_seconds",
    "Wall-clock time from review start to terminal state, in seconds.",
    buckets=(1, 5, 10, 20, 30, 45, 60, 90, 120, 180, 300),
)

# --- HITL (app/main.py::approve_hitl / reject_hitl) ---
hitl_resolutions_total = Counter(
    "ignition_hitl_resolutions_total",
    "Human-in-the-loop reviews resolved, labeled by outcome.",
    ["outcome"],  # approved | rejected
)

hitl_pending_gauge = Gauge(
    "ignition_hitl_pending",
    "Reviews currently waiting on human approval — set from /api/hitl/pending's own query "
    "each time that endpoint is polled, not tracked incrementally, so it reflects the same "
    "source of truth the dashboard reads rather than drifting from it over time.",
)
