"""
FastAPI entrypoint.

Responsibilities (and only these — business logic lives in graph/ and services/):
  - Receive & verify GitHub webhooks
  - Build the initial LangGraph state from the AST payload
  - Stream graph.astream() transitions to the frontend as SSE
"""
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json

from app.config import get_settings
from app.security import verify_github_signature
from app.schemas.github import PullRequestWebhook
from app.services.ast_client import ASTClient
from app.graph.workflow import build_graph
from app.graph.state import ReviewState

app = FastAPI(title="Ignition")

settings = get_settings()
ast_client = ASTClient(base_url=settings.ast_service_url)
graph = build_graph()


@app.post("/webhooks/github")
async def github_webhook(request: Request, _: None = Depends(verify_github_signature)):
    payload = await request.json()

    try:
        event = PullRequestWebhook.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {exc}")

    if event.action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "action": event.action}

    # Kick off analysis; caller gets a stream handle, not a blocking result.
    return StreamingResponse(
        run_review_stream(event),
        media_type="text/event-stream",
    )


async def run_review_stream(event: PullRequestWebhook):
    """
    Bridges the AST analyzer -> initial graph state -> graph.astream()
    into an SSE-formatted generator.
    """
    ast_payload = await ast_client.analyze_git(
        repo_full_name=event.repository.full_name,
        pr_number=event.pull_request.number,
        clone_url=event.repository.clone_url,
        ref=event.pull_request.head_sha,
        base_ref=event.pull_request.base_sha,
    )

    initial_state = ReviewState.from_ast_payload(ast_payload, event)

    async for state_update in graph.astream(initial_state):
        yield f"data: {json.dumps(state_update, default=str)}\n\n"


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}