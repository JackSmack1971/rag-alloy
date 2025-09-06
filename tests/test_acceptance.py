from __future__ import annotations

from io import BytesIO
from pathlib import Path
import importlib
import os
import sys
import types
import collections

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from index.embedding_store import EmbeddingStore, TextDoc
from retriever.base import BaseRetriever
from reasoner.runner import Runner


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
    os.environ["APP_AUTH_MODE"] = "none"
    Version = collections.namedtuple("Version", "major minor micro releaselevel serial")
    sys.version_info = Version(3, 11, 0, "final", 0)  # type: ignore[attr-defined]
    import app.main as main
    from app.settings import get_settings
    get_settings.cache_clear()
    return importlib.reload(main)


def _setup_app_with_corpus():
    main = _reload_app()
    corpus = [
        TextDoc(text="alpha beta", tags={"file_id": "f1", "page": 1, "span": [0, 10]}),
        TextDoc(text="rareword appears", tags={"file_id": "f2", "page": 1, "span": [0, 10]}),
        TextDoc(text="gamma delta", tags={"file_id": "f3", "page": 1, "span": [0, 10]}),
    ]
    class Store:
        def __init__(self, docs):
            self.docs = docs
        def add_texts(self, texts, metadatas=None):
            pass
        def query(self, query: str, top_k: int = 5):
            matches = [d for d in self.docs if query in d.text]
            matches.reverse()
            return matches[:top_k]
    store = Store(corpus)
    retriever = BaseRetriever(store, corpus)
    main.retriever = retriever
    client = TestClient(main.app)
    return client, corpus, store, retriever


def test_ac_ing_01_ingest_returns_job_id():
    """AC-ING-01: uploading files returns a job identifier."""

    main = _reload_app()
    client = TestClient(main.app)
    for _ in range(3):
        data = BytesIO(b"dummy")
        resp = client.post("/ingest", files={"file": ("f.pdf", data, "application/pdf")})
        assert resp.status_code == 200
        assert "job_id" in resp.json()


def test_ac_ing_02_deduplicates_reuploads():
    """AC-ING-02: re-uploading the same content deduplicates by hash."""

    store = EmbeddingStore(model_name="sentence-transformers/all-MiniLM-L6-v2", location=":memory:")
    text = "hello world"
    ids1 = store.add_texts([text], [{}])
    assert ids1
    ids2 = store.add_texts([text], [{}])
    assert ids2 == []


def test_ac_ret_01_keyword_in_lexical_and_fused():
    """AC-RET-01: rare keyword appears in lexical and fused results."""

    client, _, _, retriever = _setup_app_with_corpus()
    lex = retriever._lexical_search("rareword", top_k=1)
    assert any("rareword" in rd.doc.text for rd in lex)
    docs, _ = retriever.retrieve("rareword", top_k=1, mode="hybrid")
    assert any("rareword" in d.text for d in docs)


def test_ac_ret_02_semantic_dominates_for_abstract_query():
    """AC-RET-02: abstract queries are handled by semantic retrieval."""

    client, corpus, store, retriever = _setup_app_with_corpus()
    def query(self, query: str, top_k: int = 5):
        return [corpus[0]] if query == "abstract" else []
    store.query = query.__get__(store, type(store))
    docs, _ = retriever.retrieve("abstract", top_k=1, mode="hybrid")
    assert docs[0].text == "alpha beta"
    lex = retriever._lexical_search("abstract", top_k=1)
    assert "abstract" not in lex[0].doc.text


def test_ac_gen_01_provider_none_returns_empty_answer():
    """AC-GEN-01: provider none yields empty answer with citations."""

    client, _, _, _ = _setup_app_with_corpus()
    payload = {"query": "alpha", "top_k": 1, "mode": "hybrid", "provider": "none"}
    resp = client.post("/query", json=payload)
    data = resp.json()
    assert resp.status_code == 200
    assert data["answer"] == ""
    assert data["citations"]


def test_ac_gen_02_provider_transformers_returns_text(monkeypatch):
    """AC-GEN-02: provider transformers returns an answer and citations."""

    def fake_post_init(self):
        pass
    def fake_generate(self, prompt: str, *, max_new_tokens: int = 128) -> str:
        return "dummy"
    monkeypatch.setattr(Runner, "__post_init__", fake_post_init)
    monkeypatch.setattr(Runner, "generate", fake_generate)
    client, _, _, _ = _setup_app_with_corpus()
    payload = {"query": "alpha", "top_k": 1, "mode": "hybrid", "provider": "transformers"}
    resp = client.post("/query", json=payload)
    data = resp.json()
    assert resp.status_code == 200
    assert data["answer"]
    assert data["citations"]
