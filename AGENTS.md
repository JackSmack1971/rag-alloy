<!-- This AGENTS.md file is meant for AI coding agents working on the RAG‑Alloy repository. It complements README.md by providing agent‑specific guidance about environment setup, architecture, testing, coding conventions and pull‑request expectations. Facts in this document are cited back to the authoritative product/technical requirements document (rag‑alloy‑prd‑frd‑tad.md). -->
RAG‑Alloy — Agent Guidance
RAG‑Alloy is a unified, offline‑capable, multimodal retrieval‑augmented generation platform. It fuses semantic, lexical and graph retrieval with agentic reasoning and exposes a FastAPI service. The MVP runs entirely locally on Python 3.11 with optional local LLM execution via Ollama and uses Qdrant, DocArray and networkx for storage and retrieval[1][2].
Project Overview
Purpose: Provide a single service that ingests heterogeneous files (PDF, DOCX, PPTX, XLSX, images), builds semantic/lexical indices and an optional knowledge graph, and answers questions with citations[3].
Modes: Retrieval can operate in semantic, lexical or hybrid mode and can optionally enrich context via lightweight graph hops[4].
Reasoning: A LangGraph‑based reasoner coordinates retrieval and invokes tools (calculator, CSV/XLSX aggregation, date/time) before delegating generation to a local HF or Ollama model when enabled[5].
API & UI: Exposes REST endpoints for ingestion, job status retrieval, querying and admin; ships a minimal HTML/JS chat panel with optional graph preview[6].
Query responses expose per-retriever scores and fused rankings via ``models/query.py``. Citation objects include the cited text segment along with ``file_id``, ``page``, and character ``span``.
Privacy & Security: Local processing by default; no network egress unless explicitly enabled. Mutating endpoints require token authentication[7][8].
Setup Commands
Follow these steps to bootstrap a development environment on Linux/macOS. The runtime requires Python 3.11.x; the service fails fast on other major versions[1][9].
Clone the repository and install Python 3.11 (e.g. via pyenv).
Create a virtual environment and activate it:
python3.11 -m venv .venv
source .venv/bin/activate
Install pinned dependencies. The requirements file exactly mirrors the bill of materials in the PRD[10]:
pip install -U pip
pip install -r requirements.txt
Start the vector store (Qdrant). The system expects Qdrant on localhost:6333[11]. You can run it via Docker:
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
Run the API with Uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8080
Optional services: For graph enrichment or local LLM generation, also start Neo4j and/or Ollama and adjust the environment flags (see Configuration Keys). Without those services the system will run in retrieval‑only mode[12].
Verify startup. Navigate to http://localhost:8080/healthz for a health check and http://localhost:8080/docs to view auto‑generated API docs[13].
Environment Variables
Configuration can be provided via .env or environment variables. Key defaults include[14][15]:
Key
Default / Description
PYTHON_VERSION
3.11 – enforced on startup[9]
APP_PORT
8080 – port for Uvicorn
APP_AUTH_MODE
token – set to none to disable auth[16]
APP_TOKEN
change_me – bearer token for write endpoints
MAX_UPLOAD_BYTES
52_428_800 – max upload size in bytes for /ingest
CHUNK_SIZE
800 – max characters per chunk during ingestion
CHUNK_OVERLAP
120 – number of overlapping characters between chunks
QDRANT_HOST/PORT
localhost/6333 – vector store location
RETRIEVAL_DEFAULT_MODE
hybrid – semantic, lexical or hybrid[17]
RETRIEVAL_TOP_K
8 – number of chunks returned by each retriever[17]
FUSION_METHOD
rrf – reciprocal rank fusion
GRAPH_ENABLED
false – enable graph enrichment when true
GEN_PROVIDER
none – none, transformers or ollama[18]
TRANSFORMERS_MODEL
example: sentence-transformers/all-MiniLM-L6-v2[19]
OLLAMA_MODEL
example: llama3:instruct[19]

Repository Layout
The repository follows a modular layout. Key directories include[20]:
Path
Purpose
app/
FastAPI routes, dependency injection and application
settings[21].


ingest/
Parsers, chunkers and OCR hooks for file ingestion[21].
index/
Qdrant/DocArray adapters and BM25 index code[21]. Includes an embedding store
that hashes text with SHA-256 to deduplicate and persists DocArray metadata.
graph/
networkx + Neo4j adapters for optional graph enrichment[21].
retriever/
Reciprocal rank fusion and retriever orchestration[4].
reasoner/
LangGraph flows, tool implementations and provider logic[5].
models/
Pydantic schemas for API requests and responses[22].
ui/
Minimal HTML/JS chat front‑end and optional graph view[6].
tests/ & eval/
Unit tests, retrieval/evaluation harness and latency checks[23].

Build & Test Commands
The project uses Makefile targets to streamline development. Common commands:
Command
Description
make install
Create a virtual environment and install pinned dependencies using requirements.txt[24].
make run
Start the API locally (uvicorn app.main:app --port 8080)[21][25].
make qdrant-up
Start a local Qdrant instance via Docker[26].
make test
Run unit tests and evaluation suite (retrieval recall, citation coverage, latency smoke)[27][28].
make eval
Execute evaluation harness (Recall@k, MRR, latency budgets)[29].
make fmt
Optional formatting via ruff/black (not pinned)[30].

The CI quality gates require:
Retrieval: Recall@10 ≥ 0.85 and MRR ≥ 0.65 on the seeded validation set[31].
Evidence coverage: At least 95 % of generated answers must include ≥1 citation and 80 % must include ≥2[32].
Latency: p95 latency ≤ 900 ms for retrieval and ≤ 7 s when generation is enabled[33].
Run make test locally before submitting a pull request to ensure these gates pass.
Testing & Acceptance Criteria
Acceptance criteria for the MVP include ingestion, retrieval, generation and observability behaviours. Representative acceptance tests include:
AC‑ING‑01: Upload 3 PDFs; /ingest returns a job ID and status transitions to done with correct chunk counts[34].
AC‑ING‑02: Re‑uploading the same content deduplicates by SHA‑256[35].
AC‑RET‑01: A rare keyword query appears in the BM25 result set and the fused top‑k[36].
AC‑RET‑02: Abstract queries are dominated by semantic retrieval[36].
AC‑GEN‑01: With provider=none the answer is empty but contexts and citations are returned[37].
AC‑GEN‑02: With provider=transformers a string answer and citations are returned[38].
AC‑OPS‑01: /healthz returns OK and /metrics exposes counters/histograms[39].
Use these scenarios when writing new tests or debugging regressions. Automated test cases live under tests/ and can be executed via the Make targets above.
Code Style & Conventions
Python 3.11 only: Do not attempt to support other major versions[9].
Type hints & Pydantic v2: Use type annotations throughout. API models should derive from BaseModel with field validations[22].
Formatting: Use Black and Ruff (optionally via make fmt). Ensure there are no linting errors before committing.
Idempotent ingestion: Use SHA‑256 to deduplicate files and implement transactional writes; partial failures must not leave orphaned vectors[40].
Documentation: Docstrings for functions/classes; update this AGENTS.md and README.md when adding new features or changing interfaces.
Pull Request Guidelines
Branching: Use descriptive branch names (e.g. feature/graph-enrichment).
Title format: [rag‑alloy] <short summary> to make PRs easy to scan.
Pre‑submit checks: Always run make lint (if configured) and make test. PRs should pass all unit tests, retrieval/evaluation metrics and type checks[41].
Tests: Add or update tests for the code you change, even if not requested[42].
Documentation: Update API docs (OpenAPI via FastAPI) and any relevant markdown docs to reflect changes.
Security: Do not hardcode credentials. Use environment variables or secrets management. Mutating endpoints require token auth; ensure tests cover authentication paths[43].
High‑Level Architecture
The system consists of four major subsystems[2]:
API Layer: FastAPI app running under Uvicorn. Handles routing, authentication, validation and OpenAPI docs[44].
Ingestion Pipeline: Parses uploaded documents using Unstructured and PyPDF, splits them into chunks, computes embeddings and stores vectors in Qdrant and metadata in DocArray[45][46].
Retrieval & Fusion Engine: Retrieves top‑k chunks from semantic and lexical indices, merges them via Reciprocal Rank Fusion and optionally performs lightweight graph hops[4][17].
Reasoner & Tools: LangGraph orchestrates retrieval and tool invocation; it calls the LLM runner (transformers or Ollama) when generation is enabled[5].
Context flows: API → Router (LangGraph) → Retrieval (semantic/lexical/graph) → Context Pack → LLM → Answer with citations[47].
Open Items & Future Work
Several design decisions are still under discussion. Track these items in issues and note that future PRs may address them[48][49]:
OCR package selection: Decide between Tesseract or PaddleOCR for scanned PDF support[50].
Default embedding model: Evaluate CPU‑friendly embedding models and update TRANSFORMERS_MODEL accordingly[51].
Entity linker: Choose between rule‑based or lightweight NER for graph seeding[52].
Contact & Support
If you need clarification or encounter issues, create a GitHub Issue in this repository. Include reproduction steps, error messages and any relevant logs (/healthz, /metrics or trace outputs). For urgent matters or security concerns, contact the repository maintainers via the channels listed in README.md.

[1] [2] [3] [4] [5] [6] [7] [8] [9] [10] [11] [12] [13] [14] [15] [16] [17] [18] [19] [20] [21] [22] [23] [24] [25] [26] [27] [28] [29] [30] [31] [32] [33] [34] [35] [36] [37] [38] [39] [40] [41] [42] [43] [44] [45] [46] [47] [48] [49] [50] [51] [52] rag-alloy-prd-frd-tad.md
https://github.com/JackSmack1971/rag-alloy/blob/main/rag-alloy-prd-frd-tad.md
