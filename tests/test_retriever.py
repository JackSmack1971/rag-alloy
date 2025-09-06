from pathlib import Path
import sys
import hashlib

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from retriever.base import BaseRetriever
from index.embedding_store import TextDoc
import networkx as nx


class FakeStore:
    def __init__(self, docs: list[TextDoc]):
        self.docs = docs

    def add_texts(self, texts, metadatas=None):
        pass

    def query(self, query: str, top_k: int = 5):
        # naive semantic search: return docs containing the query word reversed order
        matches = [d for d in self.docs if query in d.text]
        matches.reverse()
        return matches[:top_k]


class DummyStore:
    def __init__(self) -> None:
        self.texts: dict[str, TextDoc] = {}

    def _sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def add_texts(self, texts, metadatas=None):
        metas = list(metadatas) if metadatas else [{} for _ in texts]
        ids = []
        for text, meta in zip(texts, metas):
            full_hash = self._sha256(text)
            uid = full_hash[:32]
            if uid in self.texts:
                continue
            self.texts[uid] = TextDoc(text=text, tags=meta)
            ids.append(uid)
        return ids

    def query(self, query: str, top_k: int = 5):
        return []


def test_hybrid_rrf_fuses_results():
    corpus = [
        TextDoc(text="alpha beta", tags={"file_id": "f1", "page": 1, "span": [0, 10]}),
        TextDoc(text="beta gamma", tags={"file_id": "f2", "page": 2, "span": [0, 10]}),
        TextDoc(text="gamma delta", tags={"file_id": "f3", "page": 3, "span": [0, 10]}),
    ]
    store = FakeStore(corpus)
    retriever = BaseRetriever(store, corpus)

    docs, graph_ctx = retriever.retrieve("beta", top_k=2, mode="hybrid")
    texts = [d.text for d in docs]
    assert texts[0] in {"alpha beta", "beta gamma"}
    assert len(docs) == 2
    assert graph_ctx is None
    assert docs[0].tags.get("file_id")
    assert "page" in docs[0].tags and "span" in docs[0].tags


def test_graph_expansion_returns_neighbors():
    corpus = [TextDoc(text="Alice met Bob in Paris", tags={"file_id": "f1"})]
    store = FakeStore(corpus)
    g = nx.Graph()
    g.add_edge("Alice", "Bob")
    g.add_edge("Bob", "Eve")
    retriever = BaseRetriever(store, corpus, graph=g)

    docs, graph_ctx = retriever.retrieve(
        "Alice",
        top_k=1,
        mode="semantic",
        graph=True,
        graph_params={"neighbors": 5, "depth": 2},
    )
    assert docs[0].text == "Alice met Bob in Paris"
    assert graph_ctx is not None
    assert "Eve" in graph_ctx["nodes"]
    assert ("Bob", "Eve") in graph_ctx["edges"] or ("Eve", "Bob") in graph_ctx["edges"]


def test_add_texts_skips_existing_ids():
    store = DummyStore()
    retriever = BaseRetriever(store)
    doc = TextDoc(text="repeat", tags={"file_id": "f1"})
    retriever.add_texts([doc])
    retriever.add_texts([doc])
    assert len(retriever.corpus) == 1
