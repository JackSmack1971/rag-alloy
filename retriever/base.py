"""Retrieval utilities combining semantic and lexical search.

This module exposes :class:`BaseRetriever` which wraps a semantic embedding
store and a BM25 lexical index. Queries can be executed in three modes:

``semantic``
    Only embedding based search via :class:`~index.embedding_store.EmbeddingStore`.
``lexical``
    Only BM25 based keyword search using :mod:`rank_bm25`.
``hybrid``
    Results from both retrievers are combined using Reciprocal Rank Fusion
    (RRF). The RRF implementation follows the formulation from
    [Cormack et al., 2009].

The retriever is intentionally lightweight; it keeps an in-memory corpus for
BM25 and delegates persistence of embeddings to ``EmbeddingStore``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple, Dict, Any

from rank_bm25 import BM25Okapi

from index.embedding_store import EmbeddingStore, TextDoc
from graph.entities import extract_entities

try:
    import networkx as nx
except Exception:  # pragma: no cover - networkx is optional at runtime
    nx = None  # type: ignore


@dataclass
class RetrievedDoc:
    """Container representing a retrieved document."""

    doc: TextDoc
    score: float


class BaseRetriever:
    """Combine semantic and lexical retrieval with optional graph expansion."""

    def __init__(
        self,
        store: EmbeddingStore,
        corpus: Sequence[str] | None = None,
        graph: Any | None = None,
    ) -> None:
        self.store = store
        self.corpus: List[str] = list(corpus or [])
        self.bm25 = BM25Okapi([c.split() for c in self.corpus]) if self.corpus else None
        self.graph = graph
        if corpus:
            # Ensure texts are available in the embedding store.
            self.store.add_texts(corpus)

    # ------------------------------------------------------------------
    def add_texts(self, texts: Iterable[str]) -> None:
        """Add ``texts`` to both semantic and lexical indices."""

        new_texts = list(texts)
        if not new_texts:
            return
        self.corpus.extend(new_texts)
        self.store.add_texts(new_texts)
        tokenized = [c.split() for c in self.corpus]
        self.bm25 = BM25Okapi(tokenized)

    # ------------------------------------------------------------------
    def _lexical_search(self, query: str, top_k: int) -> List[RetrievedDoc]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.split())
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [RetrievedDoc(TextDoc(text=self.corpus[i], tags={}), score=s) for i, s in ranked]

    # ------------------------------------------------------------------
    def _semantic_search(self, query: str, top_k: int) -> List[RetrievedDoc]:
        docs = self.store.query(query, top_k=top_k)
        # ``EmbeddingStore.query`` returns results in ranked order but without scores.
        return [RetrievedDoc(doc=d, score=1.0) for d in docs]

    # ------------------------------------------------------------------
    def _fuse(self, results: Sequence[Sequence[RetrievedDoc]], top_k: int, k: int = 60) -> List[TextDoc]:
        scores: defaultdict[str, float] = defaultdict(float)
        docs: dict[str, TextDoc] = {}
        for result_set in results:
            for rank, item in enumerate(result_set, start=1):
                key = item.doc.text  # use text as a simple identifier
                docs[key] = item.doc
                scores[key] += 1.0 / (k + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [docs[key] for key, _ in ranked]

    # ------------------------------------------------------------------
    def _expand_graph(self, docs: Sequence[TextDoc]) -> Dict[str, Any] | None:
        """Extract entities from ``docs`` and fetch their neighbours.

        Supports both ``networkx`` graphs and Neo4j drivers. The return value is
        a dictionary with ``nodes`` and ``edges`` lists suitable for JSON
        serialisation or ``None`` when no graph context is available.
        """

        if not self.graph:
            return None
        entities: List[str] = []
        for d in docs:
            entities.extend(extract_entities(d.text))
        if not entities:
            return None

        graph_ctx: Dict[str, Any] = {"nodes": [], "edges": []}
        if nx and isinstance(self.graph, nx.Graph):
            seen: set[str] = set()
            for ent in entities:
                if self.graph.has_node(ent):
                    seen.add(ent)
                    for nbr in self.graph.neighbors(ent):
                        graph_ctx["edges"].append((ent, nbr))
                        seen.add(nbr)
            graph_ctx["nodes"] = list(seen)
            return graph_ctx if graph_ctx["nodes"] else None

        # Neo4j driver support
        if hasattr(self.graph, "session"):
            with self.graph.session() as session:  # type: ignore[call-arg]
                nodes: set[str] = set()
                edges: List[Tuple[str, str]] = []
                for ent in entities:
                    result = session.run(
                        "MATCH (e {name: $name})--(n) RETURN e.name AS src, n.name AS dst",
                        {"name": ent},
                    )
                    for record in result:
                        src = record["src"]
                        dst = record["dst"]
                        nodes.update({src, dst})
                        edges.append((src, dst))
            if nodes:
                graph_ctx["nodes"] = list(nodes)
                graph_ctx["edges"] = edges
                return graph_ctx
        return None

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
        graph: bool = False,
    ) -> Tuple[List[TextDoc], Dict[str, Any] | None]:
        """Retrieve documents matching ``query`` using ``mode``.

        When ``graph`` is ``True`` and a graph was provided at initialisation,
        neighbouring nodes of entities found in the retrieved documents are
        returned as ``graph_context``.
        """

        mode = mode.lower()
        docs: List[TextDoc]
        if mode == "semantic":
            docs = [rd.doc for rd in self._semantic_search(query, top_k)]
        elif mode == "lexical":
            docs = [rd.doc for rd in self._lexical_search(query, top_k)]
        elif mode == "hybrid":
            sem = self._semantic_search(query, top_k)
            lex = self._lexical_search(query, top_k)
            docs = self._fuse([sem, lex], top_k)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")

        graph_ctx = self._expand_graph(docs) if graph else None
        return docs, graph_ctx
