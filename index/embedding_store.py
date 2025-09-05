"""Qdrant-backed embedding store with SHA-256 deduplication.

This module uses sentence-transformers to compute embeddings and persists them
in a Qdrant collection. Text chunks are deduplicated via SHA-256 of their
content before upsert. Metadata is stored using DocArray's ``BaseDoc`` models.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, Iterable, List

from docarray import BaseDoc
from pydantic import Field
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

DEFAULT_COLLECTION = "documents"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class TextDoc(BaseDoc):
    """Simple document schema stored as Qdrant payload."""

    text: str
    tags: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingStore:
    """Store and query embeddings in Qdrant with DocArray metadata."""

    def __init__(
        self,
        model_name: str | None = None,
        collection_name: str = DEFAULT_COLLECTION,
        *,
        host: str | None = None,
        port: int | None = None,
        location: str | None = None,
    ) -> None:
        """Initialize the embedding store.

        Parameters
        ----------
        model_name:
            Sentence-transformers model name. Defaults to
            ``TRANSFORMERS_MODEL`` env var or a sensible CPU model.
        collection_name:
            Name of the Qdrant collection to use.
        host, port:
            Qdrant host and port. Ignored when ``location`` is provided.
        location:
            Optional location string for QdrantClient, e.g. ``":memory:"`` for
            an ephemeral in-memory instance useful in tests.
        """

        self.model_name = model_name or os.environ.get(
            "TRANSFORMERS_MODEL", DEFAULT_MODEL
        )
        if location is not None:
            self.client = QdrantClient(location=location)
        else:
            host = host or os.environ.get("QDRANT_HOST", "localhost")
            port = port or int(os.environ.get("QDRANT_PORT", "6333"))
            self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.model = SentenceTransformer(self.model_name)
        self._ensure_collection()

    # ------------------------------------------------------------------
    def _ensure_collection(self) -> None:
        """Create the collection if it does not exist."""

        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            dim = self.model.get_sentence_embedding_dimension()
            self.client.create_collection(
                self.collection_name,
                rest.VectorParams(size=dim, distance=rest.Distance.COSINE),
            )

    # ------------------------------------------------------------------
    @staticmethod
    def _sha256(text: str) -> str:
        """Return the SHA-256 hex digest for ``text``."""

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    def add_texts(
        self, texts: Iterable[str], metadatas: Iterable[Dict[str, Any]] | None = None
    ) -> List[str]:
        """Add ``texts`` and their ``metadatas`` to the store.

        Duplicate texts are skipped based on the SHA-256 hash of the text.

        Returns a list of IDs that were newly inserted.
        """

        texts = list(texts)
        if metadatas is None:
            metadatas = [{} for _ in texts]  # type: ignore[misc]
        ids: List[str] = []
        points: List[rest.PointStruct] = []
        for text, metadata in zip(texts, metadatas):
            full_hash = self._sha256(text)
            uid = full_hash[:32]
            if self.client.retrieve(collection_name=self.collection_name, ids=[uid]):
                continue
            doc = TextDoc(text=text, tags=metadata)
            embedding = self.model.encode(text).tolist()
            payload = doc.model_dump(exclude={"id"})
            payload["hash"] = full_hash
            points.append(
                rest.PointStruct(id=uid, vector=embedding, payload=payload)
            )
            ids.append(uid)
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
        return ids

    # ------------------------------------------------------------------
    def query(self, query: str, top_k: int = 5) -> List[TextDoc]:
        """Search the store with ``query`` and return matching ``TextDoc``s."""

        vector = self.model.encode(query).tolist()
        results = self.client.search(
            collection_name=self.collection_name, query_vector=vector, limit=top_k
        )
        docs: List[TextDoc] = []
        for res in results:
            payload = res.payload or {}
            docs.append(TextDoc(**payload))
        return docs
