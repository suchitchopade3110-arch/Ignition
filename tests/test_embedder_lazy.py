"""
Audit I-1 and P1-7 (embedder):
  - importing the web app must not import the embedder (fastembed and
    onnxruntime since I-1 replaced sentence-transformers/torch) — only the
    worker ever embeds anything;
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
        "loaded = [m for m in ('fastembed', 'onnxruntime', 'sentence_transformers', 'torch') if m in sys.modules]; "
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

    def embed(texts):  # fastembed's TextEmbedding.embed: one vector per text
        record["encode_off_loop"] = threading.get_ident() != main
        return iter([_FakeVector([1.0] + [0.0] * 383) for _ in texts])

    def rpc_execute():
        record["rpc_off_loop"] = threading.get_ident() != main
        return MagicMock(data=[])

    def insert(*args):
        record["insert_off_loop"] = threading.get_ident() != main

    store = VectorStore.__new__(VectorStore)
    store._db = MagicMock()
    store._db.rpc.return_value.execute.side_effect = rpc_execute
    store._embeddings = MagicMock(insert=MagicMock(side_effect=insert))
    record["model"] = MagicMock(embed=MagicMock(side_effect=embed))
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
    # fastembed runs the same model on ONNX Runtime's CPU provider (I-1).
    fake_module = types.ModuleType("fastembed")
    fake_module.TextEmbedding = MagicMock(name="TextEmbedding")
    monkeypatch.setitem(sys.modules, "fastembed", fake_module)
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", "/opt/models")
    vector_store_module._get_model.cache_clear()
    try:
        vector_store_module._get_model()
    finally:
        vector_store_module._get_model.cache_clear()
    fake_module.TextEmbedding.assert_called_once_with(
        model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir="/opt/models")
