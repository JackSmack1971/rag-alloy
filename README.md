# rag-alloy

FastAPI service with file ingestion capabilities.

## API

- `POST /ingest` – upload a file and receive a job identifier. Files larger than `MAX_UPLOAD_BYTES` (default 50MB) are rejected with HTTP 413.
- `GET /collections/{collection}/stats` – retrieve vector and point counts for a collection.
- `DELETE /collections/{collection}` – remove a collection and all associated vectors and metadata.
- `POST /query` – retrieve text chunks for a query. The response includes per-retriever scores, fused ranking, and citations with `file_id`, `page`, character `span`, and the cited text segment. When `graph=true`, neighboring nodes from a NetworkX or Neo4j graph are returned based on spaCy entity extraction.
- `GET /healthz` – report service health status.
- `GET /metrics` – Prometheus metrics for the service.

## Configuration

The ingestion pipeline respects the following environment variables:

- `CHUNK_SIZE` – max characters per chunk during ingestion (default 800).
- `CHUNK_OVERLAP` – number of overlapping characters between chunks (default 120).

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
