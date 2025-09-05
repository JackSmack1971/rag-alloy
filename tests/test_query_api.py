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
    def __init__(self, docs: list[str]):
        self.docs = docs

    def add_texts(self, texts, metadatas=None):
        pass

    def query(self, query: str, top_k: int = 5):
        matches = [d for d in self.docs if query in d]
        matches.reverse()
        return [TextDoc(text=m, tags={}) for m in matches[:top_k]]


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
    import app.main as main
    return importlib.reload(main)


def test_query_returns_ranked_scores():
    main = _reload_app()
    corpus = ["alpha beta", "beta gamma", "gamma delta"]
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
    first = body["results"][0]
    assert first["rank"] == 1
    assert set(first["scores"].keys()) == {"semantic", "lexical"}
