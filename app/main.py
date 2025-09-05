"""FastAPI application exposing ingestion and collection management APIs."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from qdrant_client import QdrantClient

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))

if location := os.environ.get("QDRANT_LOCATION"):
    qdrant = QdrantClient(location=location)
else:
    qdrant = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", "6333")),
    )

app = FastAPI()


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
