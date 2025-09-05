from pathlib import Path
import sys
import os
import importlib

# Ensure repo root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from retriever.base import BaseRetriever
from index.embedding_store import TextDoc


class FakeStore:
    def __init__(self, docs: list[TextDoc]):
        self.docs = docs

    def add_texts(self, texts, metadatas=None):
        pass

    def query(self, query: str, top_k: int = 5):
        matches = [d for d in self.docs if query in d.text]
        matches.reverse()
        return matches[:top_k]


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
    import app.main as main
    return importlib.reload(main)


def test_query_returns_ranked_scores():
    main = _reload_app()
    corpus = [
        TextDoc(text="alpha beta", tags={"file_id": "f1", "page": 1, "span": [0, 10]}),
        TextDoc(text="beta gamma", tags={"file_id": "f2", "page": 2, "span": [0, 10]}),
        TextDoc(text="gamma delta", tags={"file_id": "f3", "page": 3, "span": [0, 10]}),
    ]
    store = FakeStore(corpus)
    main.retriever = BaseRetriever(store, corpus)
    client = TestClient(main.app)

    res = client.post(
        "/query", json={"query": "beta", "top_k": 2, "mode": "hybrid", "provider": "none"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == ""
    assert len(body["results"]) == 2
    assert len(body["citations"]) == 2
    first = body["results"][0]
    assert first["rank"] == 1
    assert set(first["scores"].keys()) == {"semantic", "lexical"}
    assert first["file_id"] in {"f1", "f2"}
    assert first["page"] in {1, 2}
    assert first["span"] == [0, 10]
    citation = body["citations"][0]
    assert citation["file_id"] == first["file_id"]
    assert citation["page"] == first["page"]
    assert citation["span"] == first["span"]
    assert citation["text"] == first["text"]
