# rag-alloy

FastAPI service with file ingestion capabilities.

## API

- `POST /ingest` – upload a file and receive a job identifier. Files larger than `MAX_UPLOAD_BYTES` (default 50MB) are rejected with HTTP 413.
- `GET /collections/{collection}/stats` – retrieve vector and point counts for a collection.
- `DELETE /collections/{collection}` – remove a collection and all associated vectors and metadata.

## Configuration

The ingestion pipeline respects the following environment variables:

- `CHUNK_SIZE` – max characters per chunk during ingestion (default 800).
- `CHUNK_OVERLAP` – number of overlapping characters between chunks (default 120).

## Index

The `index` package contains an embedding store built on Qdrant. It computes
sentence-transformer embeddings, stores DocArray metadata, and deduplicates
content using a SHA-256 hash of each text chunk.
