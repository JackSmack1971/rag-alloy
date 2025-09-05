# rag-alloy

FastAPI service with file ingestion capabilities.

## API

- `POST /ingest` – upload a file and receive a job identifier. Files larger than `MAX_UPLOAD_BYTES` (default 50MB) are rejected with HTTP 413.
