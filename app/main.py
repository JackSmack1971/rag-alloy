"""FastAPI application exposing ingestion and collection management APIs."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator
from qdrant_client import QdrantClient

from ingest.parsers import parse_document
from ingest.chunking import chunk_text
from index.embedding_store import EmbeddingStore

if sys.version_info[:2] != (3, 11):  # pragma: no cover - defensive startup check
    raise SystemExit("Python 3.11 is required")

from models.query import (
    QueryRequest,
    QueryResponse,
    RankedDocument,
    Citation,
    RetrieverScores,
)
from reasoner.runner import Runner
from retriever.base import BaseRetriever

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HASH_MAP_PATH = UPLOAD_DIR / "hashes.json"
if HASH_MAP_PATH.exists():
    HASH_TO_JOB: dict[str, str] = json.loads(HASH_MAP_PATH.read_text())
else:
    HASH_TO_JOB = {}

if location := os.environ.get("QDRANT_LOCATION"):
    qdrant = QdrantClient(location=location)
    store = EmbeddingStore(location=location)
else:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    qdrant = QdrantClient(host=host, port=port)
    store = EmbeddingStore(host=host, port=port)

app = FastAPI()

Instrumentator().instrument(app).expose(
    app, include_in_schema=False, endpoint="/metrics"
)


retriever: BaseRetriever | None = None


@app.post("/ingest", status_code=202)
async def ingest(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept a file upload, embed its contents and return a job ID.

    The request is rejected with HTTP 413 when the file exceeds
    ``MAX_UPLOAD_BYTES``.
    """
    data = await file.read()
    size = len(data)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    digest = hashlib.sha256(data).hexdigest()
    if digest in HASH_TO_JOB:
        return {"job_id": HASH_TO_JOB[digest]}

    job_id = str(uuid4())
    suffix = Path(file.filename).suffix
    dest = UPLOAD_DIR / f"{job_id}{suffix}"
    dest.write_bytes(data)

    try:
        elements = parse_document(dest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    full_text = "\n\n".join(
        getattr(el, "text", "") for el in elements if getattr(el, "text", "").strip()
    )
    chunks = chunk_text(full_text)
    metadatas = [{"file_id": job_id} for _ in chunks]
    store.add_texts(chunks, metadatas)
    HASH_TO_JOB[digest] = job_id
    HASH_MAP_PATH.write_text(json.dumps(HASH_TO_JOB))

    return {"job_id": job_id}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok"}


@app.get("/collections/{collection}/stats")
def collection_stats(collection: str) -> dict[str, Any]:
    """Return basic statistics for a Qdrant ``collection``."""

    existing = {c.name for c in qdrant.get_collections().collections}
    if collection not in existing:
        raise HTTPException(status_code=404, detail="Collection not found")
    info = qdrant.get_collection(collection_name=collection)
    return {"points_count": info.points_count, "vectors_count": info.vectors_count}


@app.delete("/collections/{collection}")
def delete_collection(collection: str) -> dict[str, Any]:
    """Delete ``collection`` from Qdrant along with all stored data."""

    existing = {c.name for c in qdrant.get_collections().collections}
    if collection not in existing:
        raise HTTPException(status_code=404, detail="Collection not found")
    qdrant.delete_collection(collection_name=collection)
    return {"status": "deleted"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """Retrieve documents for ``req.query`` using the configured retriever.

    The response includes per-retriever scores for each returned text chunk
    alongside its fused rank.
    """

    if retriever is None:
        raise HTTPException(status_code=500, detail="Retriever not configured")

    sem = []
    lex = []
    if req.mode in {"semantic", "hybrid"}:
        sem = retriever._semantic_search(req.query, req.top_k)
    if req.mode in {"lexical", "hybrid"}:
        lex = retriever._lexical_search(req.query, req.top_k)

    if req.mode == "semantic":
        fused_docs = [rd.doc for rd in sem]
    elif req.mode == "lexical":
        fused_docs = [rd.doc for rd in lex]
    else:
        fused_docs = retriever._fuse([sem, lex], req.top_k)

    results: list[RankedDocument] = []
    citations: list[Citation] = []
    for rank, doc in enumerate(fused_docs, start=1):
        text = doc.text
        sem_score = next((d.score for d in sem if d.doc.text == text), None)
        lex_score = next((d.score for d in lex if d.doc.text == text), None)
        scores = RetrieverScores(semantic=sem_score, lexical=lex_score)
        meta = doc.tags
        file_id = meta.get("file_id", "")
        page = meta.get("page")
        span = tuple(meta["span"]) if "span" in meta else None
        results.append(
            RankedDocument(
                text=text,
                rank=rank,
                file_id=file_id,
                page=page,
                span=span,
                scores=scores,
            )
        )
        citations.append(Citation(file_id=file_id, page=page, span=span, text=text))

    context = "\n\n".join(doc.text for doc in fused_docs)
    prompt = f"Context:\n{context}\n\nQuestion: {req.query}\nAnswer:"
    runner = Runner(req.provider)
    answer = runner.generate(prompt)

    return QueryResponse(
        query=req.query, answer=answer, citations=citations, results=results
    )
