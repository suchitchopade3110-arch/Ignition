"""
Audit I-1 and P1-7 (embedder):
  - importing the web app must not import sentence_transformers/torch —
    only the worker ever embeds anything;
  - encode() is CPU-bound and the Supabase client is synchronous, so both
    run off the event loop (asyncio.to_thread), never on it.
"""
import os
import subprocess
import sys
import threading
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import app.rag.vector_store as vector_store_module
from app.rag.vector_store import VectorStore

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_importing_the_web_app_does_not_import_the_embedder():
    code = (
        "import sys, app.main; "
        "loaded = [m for m in ('sentence_transformers', 'torch') if m in sys.modules]; "
        "print('LOADED', loaded); sys.exit(1 if loaded else 0)"
    )
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    env.update({
        "GITHUB_APP_ID": "1", "GITHUB_WEBHOOK_SECRET": "x", "LLM_API_KEY": "x",
        "SUPABASE_URL": "https://dummy-project.supabase.co", "SUPABASE_SERVICE_KEY": "x",
    })
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-500:] + proc.stderr[-1500:]


class _FakeVector(list):
    def tolist(self):
        return list(self)


def _store(record: dict) -> VectorStore:
    """A VectorStore whose model, DB and repository record which thread ran them."""
    main = threading.get_ident()

    def encode(text, normalize_embeddings=True):
        record["encode_off_loop"] = threading.get_ident() != main
        return _FakeVector([0.0] * 384)

    def rpc_execute():
        record["rpc_off_loop"] = threading.get_ident() != main
        return MagicMock(data=[])

    def insert(*args):
        record["insert_off_loop"] = threading.get_ident() != main

    store = VectorStore.__new__(VectorStore)
    store._db = MagicMock()
    store._db.rpc.return_value.execute.side_effect = rpc_execute
    store._embeddings = MagicMock(insert=MagicMock(side_effect=insert))
    record["model"] = MagicMock(encode=MagicMock(side_effect=encode))
    return store


@pytest.mark.asyncio
async def test_encode_and_supabase_calls_run_off_the_event_loop(monkeypatch):
    record: dict = {}
    store = _store(record)
    monkeypatch.setattr(vector_store_module, "_get_model", lambda: record["model"])
    await store.similar_incidents("acme/widgets", "query")
    await store.record_incident("acme/widgets", "content", {})
    assert record == {**record, "encode_off_loop": True, "rpc_off_loop": True, "insert_off_loop": True}


def test_model_is_loaded_lazily_by_its_full_id_on_cpu(monkeypatch):
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = MagicMock(name="SentenceTransformer")
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    vector_store_module._get_model.cache_clear()
    try:
        vector_store_module._get_model()
    finally:
        vector_store_module._get_model.cache_clear()
    fake_module.SentenceTransformer.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
