#!/usr/bin/env python3
"""
Re-embeds incident_embeddings rows written by the old embedder
(sentence-transformers on torch) with the current one (fastembed, I-1).
Same model and 384 dims, but a different runtime, so stored vectors and
new query vectors should come from the same embedder.

- Idempotent: a row whose metadata.embedding_model is already the current
  embedder (app.rag.vector_store.EMBEDDER_ID) is skipped, so re-running
  after a partial run only finishes the rest.
- Batched: rows are read and embedded --batch-size at a time.
- --dry-run reports what would change and writes nothing.

Run once, from the worker's environment (it needs SUPABASE_URL and
SUPABASE_SERVICE_KEY, and the model, which the worker image bakes in):

    python scripts/reembed_incidents.py --dry-run
    python scripts/reembed_incidents.py
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.vector_store import EMBEDDER_ID  # noqa: E402

TABLE = "incident_embeddings"


def reembed(db, encode, batch_size: int = 64, dry_run: bool = False) -> dict:
    """`encode(texts) -> vectors`. Returns counts: scanned, reembedded,
    would_reembed (dry run), already_current."""
    report = {"scanned": 0, "reembedded": 0, "would_reembed": 0, "already_current": 0}
    start = 0
    while True:
        rows = (
            db.table(TABLE).select("id, content, metadata").order("id")
            .range(start, start + batch_size - 1).execute().data or []
        )
        if not rows:
            break
        start += len(rows)
        report["scanned"] += len(rows)
        stale = [r for r in rows if (r.get("metadata") or {}).get("embedding_model") != EMBEDDER_ID]
        report["already_current"] += len(rows) - len(stale)
        if not stale:
            continue
        if dry_run:
            report["would_reembed"] += len(stale)
            continue
        for row, vector in zip(stale, encode([r["content"] for r in stale])):
            metadata = {**(row.get("metadata") or {}), "embedding_model": EMBEDDER_ID}
            db.table(TABLE).update({"embedding": vector, "metadata": metadata}).eq("id", row["id"]).execute()
            report["reembedded"] += 1
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from app.database import get_supabase
    from app.rag.vector_store import encode_texts

    print(json.dumps(reembed(get_supabase(), encode_texts, args.batch_size, args.dry_run)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
