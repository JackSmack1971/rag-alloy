"""FastAPI application exposing ingestion and collection management APIs."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from qdrant_client import QdrantClient

from models.query import (
    QueryRequest,
    QueryResponse,
    RankedDocument,
    RetrieverScores,
)
from reasoner.runner import Runner
from retriever.base import BaseRetriever

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))

if location := os.environ.get("QDRANT_LOCATION"):
    qdrant = QdrantClient(location=location)
else:
    qdrant = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", "6333")),
    )

app = FastAPI()


retriever: BaseRetriever | None = None


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept a file upload and return a job identifier placeholder.

    The request is rejected with HTTP 413 when the file exceeds
    ``MAX_UPLOAD_BYTES``.
    """
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    return {"job_id": "todo"}


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
    for rank, doc in enumerate(fused_docs, start=1):
        text = doc.text
        sem_score = next((d.score for d in sem if d.doc.text == text), None)
        lex_score = next((d.score for d in lex if d.doc.text == text), None)
        scores = RetrieverScores(semantic=sem_score, lexical=lex_score)
        results.append(RankedDocument(text=text, rank=rank, scores=scores))

    context = "\n\n".join(doc.text for doc in fused_docs)
    prompt = f"Context:\n{context}\n\nQuestion: {req.query}\nAnswer:"
    runner = Runner(req.provider)
    answer = runner.generate(prompt)

    return QueryResponse(query=req.query, answer=answer, results=results)
