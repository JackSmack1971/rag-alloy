# rag-alloy

FastAPI service with file ingestion capabilities.

## API

- `POST /ingest` – upload a file and receive a job identifier. Files larger than `MAX_UPLOAD_BYTES` (default 50MB) are rejected with HTTP 413. Re-uploading an identical file returns the existing job ID without reprocessing.
- `GET /ingest/{job_id}` – retrieve status and artifact metadata for an ingestion job.
- `GET /collections/{collection}/stats` – retrieve vector and point counts for a collection.
- `DELETE /collections/{collection}` – remove a collection and all associated vectors and metadata.
- `POST /query` – retrieve text chunks for a query. The response includes per-retriever scores, fused ranking, and citations with `file_id`, `page`, character `span`, and the cited text segment. When `graph` is true, neighboring nodes from a NetworkX or Neo4j graph are returned based on spaCy entity extraction.
- `GET /healthz` – report service health status.
- `GET /metrics` – Prometheus metrics for the service.

`POST /ingest` and `DELETE /collections/{collection}` require `Authorization: Bearer <APP_TOKEN>` when `APP_AUTH_MODE` is set to `token`.

## Configuration

The service respects the following environment variables:

- `CHUNK_SIZE` – max characters per chunk during ingestion (default 800).
- `CHUNK_OVERLAP` – number of overlapping characters between chunks (default 120).
- `APP_AUTH_MODE` – set to `token` (default) to require `Authorization: Bearer <APP_TOKEN>` for mutating endpoints or `none` to disable authentication.
- `APP_TOKEN` – bearer token used when `APP_AUTH_MODE=token` (default `change_me`).

## Index

The `index` package contains an embedding store built on Qdrant. It computes
sentence-transformer embeddings, stores DocArray metadata, and deduplicates
content using a SHA-256 hash of each text chunk.

## Graph

The `graph` package provides spaCy-powered entity extraction (`graph/entities.py`) and optional graph expansion using NetworkX or Neo4j.

## Evaluation

The `eval/harness.py` module computes recall@10, mean reciprocal rank (MRR),
and p95 retrieval latency. The script reports whether the measured values meet
the PRD targets of recall≥0.85, MRR≥0.65, and latency≤900 ms.
