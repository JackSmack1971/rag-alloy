from pathlib import Path
import sys

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from retriever.base import BaseRetriever
from index.embedding_store import TextDoc


class FakeStore:
    def __init__(self, docs: list[str]):
        self.docs = docs

    def add_texts(self, texts, metadatas=None):
        pass

    def query(self, query: str, top_k: int = 5):
        # naive semantic search: return docs containing the query word reversed order
        matches = [d for d in self.docs if query in d]
        matches.reverse()
        return [TextDoc(text=m, tags={}) for m in matches[:top_k]]


def test_hybrid_rrf_fuses_results():
    corpus = ["alpha beta", "beta gamma", "gamma delta"]
    store = FakeStore(corpus)
    retriever = BaseRetriever(store, corpus)

    res = retriever.retrieve("beta", top_k=2, mode="hybrid")
    texts = [d.text for d in res]
    assert texts[0] in {"alpha beta", "beta gamma"}
    assert len(res) == 2
