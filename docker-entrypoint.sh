#!/usr/bin/env bash
set -e

# Persistent Bun AST service (warm ts-morph Project cache per repo)
(cd ast-analyzer && bun run server.ts) &

# FastAPI / LangGraph orchestrator
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

wait -n
exit $?