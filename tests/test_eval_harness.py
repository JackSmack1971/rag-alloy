import importlib.util
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from index.embedding_store import TextDoc
from retriever.base import BaseRetriever


spec = importlib.util.spec_from_file_location(
    "eval.harness", Path(__file__).resolve().parents[1] / "eval" / "harness.py"
)
harness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = harness
spec.loader.exec_module(harness)
EvalResult = harness.EvalResult
evaluate = harness.evaluate
meets_prd_targets = harness.meets_prd_targets


class FakeStore:
    def __init__(self, docs: list[TextDoc]):
        self.docs = docs

    def add_texts(self, texts, metadatas=None):
        pass

    def query(self, query: str, top_k: int = 5):
        matches = [d for d in self.docs if query in d.text]
        matches.reverse()
        return matches[:top_k]


def test_evaluate_returns_metrics():
    corpus = [
        TextDoc(text="alpha beta", tags={"file_id": "f1"}),
        TextDoc(text="beta gamma", tags={"file_id": "f2"}),
        TextDoc(text="gamma delta", tags={"file_id": "f3"}),
    ]
    store = FakeStore(corpus)
    retriever = BaseRetriever(store, corpus)
    dataset = [("beta", "f1"), ("gamma", "f3")]
    result = evaluate(retriever, dataset, top_k=2)
    assert result.recall_at_10 == 1.0
    assert 0 < result.mrr <= 1
    assert result.p95_latency_ms >= 0
    assert not meets_prd_targets(result)
