import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))

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
