"""
Structured JSON logging with a correlation ID threaded through every log
line in a review's lifecycle, via a contextvars.ContextVar rather than
passing correlation_id as an explicit argument through every function in
the call chain (webhook -> repo/review creation -> Arq job -> each graph
node -> each LLM call -> GitHub comment post). This is deliberately not
structlog or any new logging framework — stdlib `logging` plus one
Formatter and one ContextVar, per the explicit scope for this task.

Why a ContextVar works here without extra plumbing: asyncio Tasks capture
a snapshot of the current context when created (including anything spawned
via asyncio.create_task/gather, which is how LangGraph runs the parallel
agent_2a/2b/2c fan-out) — so setting the correlation ID once at the top of
a request/job and never touching it again is sufficient for it to show up
on every log line emitted anywhere in that call tree, including inside
concurrently-running graph nodes.

Entry points that call set_correlation_id (one per place a "new" unit of
work starts, so the same ID doesn't leak across unrelated requests):
  - app/main.py::github_webhook (generates/reads it)
  - app/services/review_pipeline.py::run_review_job (receives it as an arg)
  - app/main.py::approve_hitl / reject_hitl (reads it back off the review row)
  - app/main.py::stream_review_events (reads it back off the review row)
"""
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Attributes every logging.LogRecord carries by default — anything NOT in
# this set on a record was passed via logger.info(..., extra={...}) and
# should be surfaced as a structured field in the JSON output.
_STANDARD_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {"taskName"}


def set_correlation_id(correlation_id: str | None) -> None:
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        # Any extra= fields a call site attached (e.g. agent name, model,
        # duration_ms, token counts) ride along as their own JSON fields,
        # not interpolated into the free-text message.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Call once per process (FastAPI app startup, Arq worker startup) —
    NOT logging.basicConfig(), which the two entry points used
    independently before this and which doesn't know about correlation IDs
    or JSON structure."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
