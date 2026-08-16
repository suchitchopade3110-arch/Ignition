#!/usr/bin/env bash
set -e

# Single-container mode (e.g. a Railway/Render deploy without separate
# services) — all three processes as siblings, same as before this
# migration, plus the new Arq worker. Requires REDIS_URL pointing at a
# real Redis instance (see docs/SECRET_ROTATION.md-adjacent note below);
# this script does not provision one.
#
# AST_ANALYZER_HOST is left unset here on purpose, so server.ts defaults
# to binding 127.0.0.1 — correct in this topology since the worker and
# FastAPI are sibling processes in this same container/network namespace
# (see the comment in ast-analyzer/server.ts).

# Persistent Bun AST service (warm ts-morph Project cache per repo)
(cd ast-analyzer && bun run server.ts) &

# Arq worker — executes review jobs enqueued by FastAPI below. This is new
# as of the Arq/Redis migration: FastAPI itself no longer runs the
# LangGraph pipeline directly.
arq app.worker.WorkerSettings &

# FastAPI — HTTP API + SSE. Enqueues jobs, no longer executes them.
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

wait -n
exit $?