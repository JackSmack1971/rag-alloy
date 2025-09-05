"""Evaluation harness computing recall, MRR and latency.

The harness compares measured metrics against product requirement document
(PRD) targets defined in :data:`PRD_TARGETS`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence, Tuple
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

PRD_TARGETS = {
    "recall_at_10": 0.85,
    "mrr": 0.65,
    "p95_latency_ms": 900.0,
}


@dataclass
class EvalResult:
    """Container for evaluation metrics."""

    recall_at_10: float
    mrr: float
    p95_latency_ms: float


def evaluate(
    retriever: any,
    dataset: Sequence[Tuple[str, str]],
    *,
    top_k: int = 10,
) -> EvalResult:
    """Evaluate ``retriever`` over ``dataset``.

    Parameters
    ----------
    retriever:
        Object exposing ``retrieve(query, top_k, mode)``.
    dataset:
        Sequence of ``(query, relevant_id)`` pairs.
    top_k:
        Number of documents to retrieve per query.
    """

    hits = 0
    rr_total = 0.0
    latencies: list[float] = []
    for query, rel_id in dataset:
        start = time.perf_counter()
        docs, _ = retriever.retrieve(query, top_k=top_k, mode="hybrid")
        latencies.append((time.perf_counter() - start) * 1000)
        ids = [d.tags.get("file_id") for d in docs]
        if rel_id in ids:
            hits += 1
            rank = ids.index(rel_id) + 1
            rr_total += 1 / rank
    recall = hits / len(dataset) if dataset else 0.0
    mrr = rr_total / len(dataset) if dataset else 0.0
    if latencies:
        latencies.sort()
        idx = max(int(0.95 * len(latencies)) - 1, 0)
        p95 = latencies[idx]
    else:
        p95 = 0.0
    return EvalResult(recall, mrr, p95)


def meets_prd_targets(result: EvalResult) -> bool:
    """Return ``True`` when ``result`` satisfies :data:`PRD_TARGETS`."""

    return (
        result.recall_at_10 >= PRD_TARGETS["recall_at_10"]
        and result.mrr >= PRD_TARGETS["mrr"]
        and result.p95_latency_ms <= PRD_TARGETS["p95_latency_ms"]
    )


if __name__ == "__main__":
    # Minimal demonstration using an in-memory retriever.
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

    class DummyRetriever:
        def __init__(self, store: FakeStore):
            self.store = store

        def retrieve(self, query: str, top_k: int = 5, mode: str = "hybrid"):
            docs = self.store.query(query, top_k)
            return docs, None

    corpus = [
        TextDoc(text="alpha beta", tags={"file_id": "f1"}),
        TextDoc(text="beta gamma", tags={"file_id": "f2"}),
        TextDoc(text="gamma delta", tags={"file_id": "f3"}),
    ]
    store = FakeStore(corpus)
    retriever = DummyRetriever(store)
    dataset = [("beta", "f1"), ("gamma", "f3")]
    result = evaluate(retriever, dataset, top_k=2)
    print(result)
    print("Meets targets:", meets_prd_targets(result))
