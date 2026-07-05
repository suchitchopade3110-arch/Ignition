# Ignition Backend

Autonomous multi-agent PR reviewer. LangGraph orchestrates four agents over a
deterministic-first, verify-before-trust pipeline. See `Ignition_PRD.pdf` for
the full design rationale.

## Structure changes vs. the original skeleton

| Added | Why |
|---|---|
| `app/repositories/` | `database.py` was becoming a dumping ground for ledger writes, baseline reads, and vector queries. Split by data concern (repository pattern) so each is independently testable/mockable. |
| `app/rag/vector_store.py` | The PRD calls for pgvector-backed semantic RAG for Agent 2B's historical-incident lookup. This was previously homeless and would've leaked into the agent file directly. |
| `app/graph/verification/symbol_lookup.py` | The Critic's exact AST/symbol verification is architecturally load-bearing (it's explicitly *not* vector search). Pulled out of `agent_3_critic.py` so it reads as a first-class tool, not an implementation detail. |
| `app/graph/scoring.py` | ACS computation + regression comparison, isolated so the divide-by-zero edge case (flagged in the PRD) is unit-testable without spinning up the graph. |
| `app/graph/routing.py` | Conditional-edge predicates (hard-rule gate, hallucination retry loop, HITL severity gate) live here instead of inline in `workflow.py`, so `workflow.py` stays pure wiring. |
| `app/graph/nodes/agent_4_autofix.py` | Named in the architectural flow diagram but had no file. Isolated because patch-conflict resolution across 4 agents writing to one node is an explicitly unsolved risk — easier to reason about in its own module. |
| `app/prompts/` | Four of five agents are LLM-backed. Prompts live outside orchestration code so they can be versioned/iterated without touching graph logic. |
| `app/security.py` | GitHub webhook HMAC signature verification — was missing entirely. |
| `tests/` | Unit tests for the deterministic pieces (ACS math, retry cap, hard-rule gate) that don't require the LLM layer. |

## Running

\`\`\`bash
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`

The Bun AST service must be running separately (see `ast-analyzer/README` inline
comments in `server.ts`) — `ast_client.py` expects a persistent HTTP service,
not a per-PR subprocess (per the PRD's resolved "Open Decision").