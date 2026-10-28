"""
I-1 / I-2: sentence-transformers and torch (plus 15 nvidia-* CUDA wheels)
are replaced by fastembed, which runs the same
sentence-transformers/all-MiniLM-L6-v2 on ONNX Runtime. Still 384 dims
(the vector(384) column), still off the event loop, the model baked into
the image, and a script to re-embed rows written by the old embedder.
"""
import importlib.util
import math
import os
import re
from pathlib import Path

import pytest

import app.rag.vector_store as vs
from tests.fake_supabase import FakeSupabase

REPO = Path(__file__).resolve().parents[1]


class FakeModel:
    """Returns un-normalized vectors so normalization is observable."""

    def __init__(self, dim=384):
        self.dim = dim
        self.calls: list[list[str]] = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return iter([[3.0, 4.0] + [0.0] * (self.dim - 2) for _ in texts])


@pytest.fixture
def model(monkeypatch):
    m = FakeModel()
    monkeypatch.setattr(vs, "_get_model", lambda: m)
    return m


def test_vectors_are_384_dims_and_unit_length(model):
    [v] = vs.encode_texts(["hello"])
    assert len(v) == 384 and math.isclose(math.sqrt(sum(x * x for x in v)), 1.0)
    assert v[:2] == [0.6, 0.8]


def test_a_wrong_dimension_is_refused_before_it_reaches_the_vector_column(monkeypatch):
    monkeypatch.setattr(vs, "_get_model", lambda: FakeModel(dim=768))
    with pytest.raises(ValueError, match="384"):
        vs.encode_texts(["hello"])


@pytest.mark.asyncio
async def test_new_rows_record_which_embedder_wrote_them(model):
    inserted = {}
    store = vs.VectorStore.__new__(vs.VectorStore)
    store._embeddings = type("E", (), {"insert": lambda self, *a: inserted.setdefault("args", a)})()
    await store.record_incident("acme/widgets", "content", {"severity": "high"})
    assert inserted["args"][3] == {"severity": "high", "embedding_model": vs.EMBEDDER_ID}
    assert vs.EMBEDDER_ID == "fastembed:sentence-transformers/all-MiniLM-L6-v2"


# --- lockfile, CI guard, image ----------------------------------------------------

def test_no_torch_or_cuda_wheels_in_the_lockfile():
    lock = (REPO / "requirements.txt").read_text()
    assert not re.search(r"^(nvidia-|triton|cuda-|torch==|sentence-transformers==)", lock, re.M)
    assert re.search(r"^fastembed==", lock, re.M) and re.search(r"^onnxruntime==", lock, re.M)
    source = (REPO / "requirements.in").read_text()
    assert re.search(r"^fastembed==", source, re.M)
    assert not re.search(r"^(torch|sentence-transformers)\b", source, re.M) and "download.pytorch.org" not in source


def test_ci_guards_against_cuda_wheels():
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    assert "! grep -E '^(nvidia-|triton|cuda-)' requirements.txt" in ci


def test_the_image_bakes_the_model_and_runs_offline():
    dockerfile = (REPO / "Dockerfile").read_text()
    build, runtime = dockerfile.split("AS runtime", 1)
    assert "TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2'" in build
    assert "COPY --from=build /opt/models /opt/models" in runtime
    assert re.search(r"FASTEMBED_CACHE_PATH=/opt/models", runtime) and re.search(r"HF_HUB_OFFLINE=1", runtime)


# --- scripts/reembed_incidents.py ----------------------------------------------------

def _script():
    spec = importlib.util.spec_from_file_location("reembed_incidents", REPO / "scripts" / "reembed_incidents.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(n, done=()):
    return [{"id": f"r{i:03d}", "repo_full_name": "acme/widgets", "content": f"incident {i}",
             "embedding": [0.0] * 384,
             "metadata": {"embedding_model": vs.EMBEDDER_ID} if i in done else {"severity": "low"}}
            for i in range(n)]


def _encode(texts):
    return [[1.0] + [0.0] * 383 for _ in texts]


def test_reembed_dry_run_writes_nothing():
    db = FakeSupabase({"incident_embeddings": _rows(5)})
    report = _script().reembed(db, _encode, batch_size=2, dry_run=True)
    assert report == {"scanned": 5, "reembedded": 0, "would_reembed": 5, "already_current": 0}
    assert not [q for q in db.queries if q[1] == "update"]


def test_reembed_updates_old_rows_in_batches_and_is_idempotent():
    db = FakeSupabase({"incident_embeddings": _rows(5, done={1})})
    batches = []

    def encode(texts):
        batches.append(len(texts))
        return _encode(texts)

    script = _script()
    first = script.reembed(db, encode, batch_size=2)
    assert first == {"scanned": 5, "reembedded": 4, "would_reembed": 0, "already_current": 1}
    assert max(batches) <= 2
    row = next(r for r in db.tables["incident_embeddings"] if r["id"] == "r000")
    assert row["embedding"][0] == 1.0 and row["metadata"] == {"severity": "low", "embedding_model": vs.EMBEDDER_ID}
    second = script.reembed(db, encode, batch_size=2)
    assert second == {"scanned": 5, "reembedded": 0, "would_reembed": 0, "already_current": 5}


# --- the real model (needs the model download: Hugging Face) --------------------------

@pytest.mark.skipif(os.getenv("IGNITION_LIVE_MODEL_TESTS") != "1",
                    reason="downloads the real model; CI runs it with IGNITION_LIVE_MODEL_TESTS=1")
def test_the_real_model_embeds_three_sentences_sensibly():
    vs._get_model.cache_clear()
    a, b, c = vs.encode_texts([
        "The repository layer must not import route handlers.",
        "Data access code should never depend on the HTTP routes.",
        "My cat likes to sleep in the sun all afternoon.",
    ])
    assert len(a) == len(b) == len(c) == 384

    def cos(x, y):
        return sum(p * q for p, q in zip(x, y))  # unit vectors
    assert cos(a, b) > cos(a, c) + 0.2 and cos(a, b) > cos(b, c) + 0.2
