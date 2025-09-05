RAG-Alloy — Product Requirements Document (PRD)
A unified, offline-capable, multimodal RAG platform that fuses vector, lexical, and graph retrieval with agentic reasoning—delivered as a Python 3.11 service (FastAPI) with optional local LLM execution (Ollama).
1) Executive Summary
RAG-Alloy provides a single application that combines five complementary RAG patterns—document Q&A, multimodal retrieval, offline/on-device operation, knowledge-graph reasoning, and agentic tool use—behind a clean API and lightweight web UI. The system ingests heterogeneous content (PDF, DOCX, PPTX, XLSX, images), builds semantic and lexical indices plus an optional knowledge graph, and answers questions with citations. It is privacy-first by default (local processing, no network required) but supports cloud resources when available.
Primary Users
• Analyst/Researcher: Ask targeted questions across large document sets and get cited answers.
• Knowledge Ops / RevOps: Ingest recurring content (reports, policies) and keep an evolving knowledge graph.
• Developers & Power Users: Embed RAG-Alloy in internal tools or dashboards via the API.
Business Goals
• Reduce time-to-insight for unstructured content by ≥50%.
• Achieve evidence-backed responses with ≥95% citation coverage.
• Operate fully offline on a developer laptop while scaling to server mode.
2) Goals & Non-Goals
2.1 Goals
• Unified Retrieval: Blend semantic (embeddings), lexical (BM25), and graph (entities/relations) evidence.
• Multimodal Ingestion: Parse text, tables, and images from common office formats and scanned PDFs (OCR-ready).
• Agentic Reasoning: Enable tool-calling and multi-step workflows (e.g., math on extracted tables).
• Offline-First: Run end-to-end locally; optionally enable Neo4j and remote stores.
• Deterministic Ops: Ship with pinned dependency versions and a minimal, reproducible setup.
• API-First: Expose ingestion, query, and admin endpoints; include citations in responses.
• Observability & Eval: Provide retrieval and answer-quality metrics and basic health/usage telemetry.
2.2 Non-Goals
• Building a full enterprise RBAC/SSO suite (basic API key/JWT only in MVP).
• Real-time web crawling or continuous sync (batch ingestion only in MVP).
• Fine-tuning foundation models; we rely on local runners and HF models.
• Heavy UI/analytics; MVP ships a minimal chat + citations view and a graph preview.
3) Success Metrics (MVP Targets)
• Answer Evidence Coverage: ≥95% of answers include ≥1 citation; ≥80% include ≥2.
• Retrieval Quality: Recall@k (k=10) ≥85% on a seeded validation set.
• Latency (Local, 8C/16G dev box):
• Query (no LLM generation, top-k retrieval + rerank): p50 ≤ 350 ms, p95 ≤ 900 ms.
• Full answer (LLM generation using local runner): p50 ≤ 3.0 s, p95 ≤ 7.0 s.
• Ingestion Throughput: ≥30 medium PDFs/hour locally (text-only; OCR excluded).
• Stability: 99.5% successful API calls under nominal load.
• Footprint: Base service (no GPU models) < 1.5 GB RAM steady-state.
4) Core User Stories & Acceptance Criteria
• Upload & Index
• As an analyst, I can upload PDFs/DOCX/PPTX/XLSX/images and see ingestion status.
• Acceptance: POST /ingest returns a job id; GET /ingest/{id} transitions pending→processing→done|error, and GET /collections/{cid}/stats shows counts for chunks, tokens, images, tables.
• Ask & Cite
• As a user, I ask a question and receive an answer with top-k evidence spans and file-level citations.
• Acceptance: POST /query returns {answer, citations:[{file, page, span}], traces: {router, retrievers}}. ≥95% responses contain ≥1 citation on seeded set.
• Hybrid Retrieval
• As a user, rare keywords (e.g., IDs) are found even if embeddings are weak.
• Acceptance: When a query contains rare tokens, BM25 hits appear in final top-k after fusion; toggle retrieval_mode=semantic|lexical|hybrid.
• Graph Reasoning (Optional)
• As a user, I can enable graph enrichment to retrieve entities/relations relevant to my question.
• Acceptance: With graph mode on, POST /query includes a graph_context section when entity linking fires; disabling graph mode removes it.
• Offline Local LLM (Optional)
• As a user, I can run the full pipeline offline using a local model via Ollama.
• Acceptance: Setting GEN_PROVIDER=ollama yields answers with no external calls; switching to transformers uses a local HF pipeline.
• Observability
• As an operator, I can view health, index size, and basic performance metrics.
• Acceptance: GET /healthz → ok; /metrics exposes counters/histograms (Prometheus format).
5) Product Scope (MVP)
5.1 Ingestion
• File types: PDF, DOCX, PPTX, XLSX, PNG/JPG (OCR-ready).
• Parsing: unstructured pipeline + pypdf for PDF text; chunking with overlap; basic metadata extraction.
• Optional OCR pass for scanned images (hook present; OCR package not included/pinned in MVP).
5.2 Indexing & Storage
• Vector store: Qdrant (client mode) for persistent embeddings; DocArray for schema & local in-memory workflows.
• Lexical index: rank-bm25 (in-process).
• Graph: networkx local graph; optional Neo4j (remote/local) when enabled.
5.3 Retrieval & Fusion
• Semantic top-k via embeddings (sentence-transformers); lexical top-k via BM25.
• Reciprocal Rank Fusion (RRF) to merge semantic + lexical.
• Optional graph expansion: link top entities from retrieved chunks and pull neighbors.
5.4 Reasoning & Orchestration
• Router + retriever graph via LangGraph.
• Prompt and tool policies via LangChain.
• Tools: calculator, simple CSV/XLSX table read/aggregate, date/time.
• Generation via local HF pipeline or Ollama (disabled by default).
5.5 API & Minimal UI
• FastAPI endpoints (OpenAPI docs enabled).
• Lightweight HTML/JS chat panel (bundled) for local use; graph preview if Neo4j enabled.
6) System Architecture (High-Level)
Services
• API Layer (FastAPI/Uvicorn/Starlette): auth, orchestration endpoints, OpenAPI.
• Ingestion Workers: parse → chunk → embed → store (synchronous for MVP, async queued in v1).
• Retrieval Engine: semantic, lexical, fusion, optional graph hop.
• Reasoner: LangGraph controller; calls LLM runner and tools.
• Stores:
• Qdrant (persistent vectors)
• DocArray schemas & in-memory ops
• Neo4j (optional graph)
• Local LLM Runner: Transformers pipeline or Ollama.
Data Flow (Query)
API → Router (LangGraph) → Retrieval (semantic+lexical+graph) → Context Pack → LLM → Answer+citations
7) Functional Requirements
7.1 Ingestion
• R1: Accept file uploads up to configurable max (default 50 MB/file).
• R2: Parse text, tables, and basic image captions/alt-text if present.
• R3: Chunking: recursive character splitter with overlap (defaults: 800 chars, 120 overlap).
• R4: Compute embeddings for text chunks; store {embedding, text, metadata, sha256, source_uri}.
• R5: Maintain collection namespace; support delete by file/collection.
7.2 Retrieval
• R6: Support mode=semantic|lexical|hybrid with RRF when hybrid.
• R7: Return top-k (default 8) with score breakdown per retriever and fused rank.
• R8: Optional entity extraction (lightweight) to seed graph neighborhood fetch.
7.3 Reasoning & Generation
• R9: Allow generation providers: none (retrieve-only), transformers (local), ollama (local).
• R10: Always include source citations (file id + page + character span estimate if available).
7.4 Administration & Observability
• R11: Healthcheck, metrics, and basic configuration endpoint.
• R12: Configuration via .env and/or YAML (documented keys).
8) Non-Functional Requirements
• Runtime: Python 3.11.x only (MVP verified); reject startup on other majors.
• Performance: Latency & throughput per §3 targets.
• Portability: Linux/macOS primary; Windows best-effort if dependencies resolve.
• Security: Local file processing by default; no external calls unless explicitly enabled. API key/JWT for write endpoints.
• Privacy: No telemetry egress by default; opt-in for anonymous metrics.
• Resilience: Idempotent ingestion (SHA-256 dedupe); graceful shutdown.
9) Public API (MVP)
• POST /ingest
Body: {collection, files[], ocr?:bool} → 202 {job_id}
• GET /ingest/{job_id}
→ {status, error?, artifacts:[{file_id, pages, chunks}]}
• GET /collections/{collection}/stats
→ {docs, chunks, vectors, last_update}
• DELETE /collections/{collection}
→ 204
• POST /query
Body: {collection, query, top_k?:int, retrieval_mode?:'semantic'|'lexical'|'hybrid', graph?:bool, provider?:'none'|'transformers'|'ollama'}
→ {answer, citations:[{file_id, page?, span?}], contexts:[…], scores:{semantic:[…], lexical:[…], fused:[…]}, graph_context?}
• GET /healthz → ok
• GET /metrics → Prometheus text format
10) Configuration Keys (MVP)
# Core PYTHON_VERSION=3.11 APP_PORT=8080 APP_LOG_LEVEL=INFO APP_AUTH_MODE=token # token|none # Stores QDRANT_HOST=localhost QDRANT_PORT=6333 QDRANT_COLLECTION=rag_alloy_default # Retrieval RETRIEVAL_DEFAULT_MODE=hybrid RETRIEVAL_TOP_K=8 FUSION_METHOD=rrf # Graph (optional) GRAPH_ENABLED=false NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=change_me # Generation GEN_PROVIDER=none # none|transformers|ollama TRANSFORMERS_MODEL=sentence-transformers/all-MiniLM-L6-v2 # example; local path allowed OLLAMA_MODEL=llama3:instruct 
11) Bill of Materials (Pinned Versions)
Python runtime: 3.11.x (documented requirement; project targets 3.11)
# --- API layer --- fastapi==0.116.1 uvicorn[standard]==0.32.0 starlette==0.47.3 pydantic==2.11.7 python-multipart==0.0.17 httpx==0.27.2 # --- RAG orchestration --- langchain==0.3.7 langgraph==0.2.58 # --- Embeddings / LLM plumbing --- sentence-transformers==3.1.0 transformers==4.56.1 torch==2.8.0 # install CUDA-specific wheels separately if needed # --- Vector store & schemas --- qdrant-client==1.15.1 docarray==0.41.0 # --- Ingestion / parsing / OCR-ready --- unstructured[pdf,docx,pptx,xlsx,image]==0.18.14 pypdf==6.0.0 # --- Hybrid retrieval (lexical + neural) --- rank-bm25==0.2.2 # --- Graph enrichment (local + optional Neo4j) --- networkx==3.4.2 neo4j==5.26.0 # --- Optional local LLM runner (disabled by default) --- ollama==0.4.4 
Compatibility notes
• fastapi 0.116.1 with starlette 0.47.3 and pydantic v2 series is aligned.
• torch 2.8.0: for GPU, document separate install of CUDA-matched wheels.
• unstructured 0.18.14: extra groups pin parsing backends for office formats and images.
• Neo4j is optional; when disabled, networkx provides local graph ops only.
12) Data Model (Conceptual)
• Document {id, collection, uri, media_type, metadata{author,date,tags}, sha256}
• Chunk {id, document_id, text|caption, type:text|table|image, page?, span?, meta, embedding(vector)}
• Lexical Index Entry {chunk_id, tokens}
• Graph Node {id, type:entity|concept|doc, labels[], props{}}
• Graph Edge {id, src, dst, type, props{}}
• Query Trace {id, ts, router_decision, retriever_scores, graph_ops[], provider}
13) User Experience (MVP UI)
• Chat Panel: query input, answer view, expandable citations list (file/page), copy-to-clipboard.
• Upload Page: drag-and-drop; progress and per-file status.
• Admin: simple metrics (docs/chunks), toggle graph mode, set generation provider.
• Graph Preview (if Neo4j): minimal force-directed view (top-N nodes from last query).
14) Evaluation & QA
Test Sets
• Seeded gold-standard Q/A pairs across the ingested corpus with labeled supporting passages.
Automatic Checks (CI/Local)
• Retrieval validation: Recall@k, MRR.
• Citation guardrail: answers without citations are flagged (fail threshold configurable).
• Latency budget checks on synthetic workloads.
• Basic memory footprint smoke test.
Manual QA
• Parse fidelity on sample PDFs (native vs scanned).
• Hybrid retrieval win cases (rare token queries).
• Graph-enabled queries (entity hop correctness).
15) Security & Privacy
• Local-first processing; no automatic egress.
• API key/JWT for mutation endpoints (ingest/delete).
• Temporary files cleaned post-ingest; stored artifacts namespaced per collection.
• Optional encryption at rest deferred to v1 (document design stubbed).
• Logs avoid sensitive payloads; redact file names and content in traces where configured.
16) Telemetry & Ops
• Metrics: request counters, latency histograms per endpoint; retrieval stage timings; ingestion throughput.
• Logs: structured JSON with correlation ids per request.
• Feature Flags: graph mode, provider selection, OCR passthrough.
17) Rollout Plan
• M0 — Skeleton (Week 1)
FastAPI scaffold, health, minimal ingest + semantic retrieval only, pinned env.
• M1 — Hybrid Retrieval (Week 2)
BM25 + fusion; citations; metrics; minimal UI.
• M2 — Graph Optional (Week 3-4)
Entity linking, networkx context hops; Neo4j toggle; graph preview.
• M3 — Agentic Tools (Week 4-5)
LangGraph controller; calculator/table tools; provider switches (transformers/ollama).
• M4 — Hardening (Week 6)
Evaluation suite, performance tuning, docs, packaging.
18) Risks & Mitigations
• PDF/Office parsing edge cases → keep parsers modular; allow raw text upload fallback.
• GPU/BLAS variations (torch wheels) → document install matrix; CPU-only baseline must pass all tests.
• Index drift after failed ingest → transactional writes; mark-and-sweep cleanup on error.
• Citation gaps on long tables/images → use page-level fallback spans; prefer nearest text anchors.
19) Open Questions (Track to Decision)
• OCR engine choice & license (Tesseract vs PaddleOCR) for the default extras.
• Default embedding model selection (size/quality trade-off) for CPU-only baseline.
• Minimal viable entity linker (rule-based vs lightweight NER) for graph seeding.
20) Definition of Done (MVP)
• All Goals in §2.1 demonstrably met; Metrics in §3 hit on seeded corpus.
• API contract in §9 stable and documented (OpenAPI + examples).
• BoM in §11 pinned and reproducible; Python 3.11 enforced at startup.
• CI passes: retrieval/evidence checks, latency bounds, smoke suite.
• Quickstart guide enables end-to-end local run (no GPU, offline).
Appendix A — Quickstart (Developer)
# 1) Python 3.11.x & venv pyenv install 3.11.9 && pyenv local 3.11.9 python -m venv .venv && source .venv/bin/activate # 2) Install pinned deps pip install -U pip pip install -r requirements.txt # 3) Start Qdrant (if not already running) docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant # 4) Launch API uvicorn app.main:app --host 0.0.0.0 --port 8080 # 5) OpenAPI # http://localhost:8080/docs 
requirements.txt should contain exactly the BoM in §11.
Appendix B — MVP Directory Layout
app/ api/ # FastAPI routes core/ # settings, logging, auth ingest/ # parsers, chunkers, OCR hooks index/ # qdrant/docarray adapters, bm25 graph/ # networkx + neo4j client (optional) retriever/ # fusion, rerank, entity link reasoner/ # langgraph flows, tools, providers models/ # pydantic schemas ui/ # minimal chat + graph preview tests/ eval/ # recall@k, citation checks, latency harness 

---

RAG-Alloy — Technical Architecture Document (TAD) (Lean, MVP scope)
Runtime contract: Python 3.11.x only. All library versions pinned exactly as in the PRD §11 (requirements.txt is authoritative).
1) System Overview
RAG-Alloy is a local-first retrieval system that fuses semantic (embeddings), lexical (BM25), and optional graph context to answer questions with citations. It exposes a FastAPI service and ships a minimal web UI. Optional modules: Neo4j (graph DB), Ollama (local LLM).
2) Architecture Views
2.1 Container / Component View
graph TD A[Client / Minimal UI] -->|HTTP| B[FastAPI API] D[.env / YAML Config] --> B B -->|submit| C[Ingestion Pipeline] C -->|embeddings| E[Qdrant Vector Store] C -->|metadata/chunks| F[DocArray] C -->|lexical tokens| G[BM25 In-Process Index] C -->|optional KG writes| H[(Neo4j) Optional] B -->|/query| I[Retrieval & Fusion Engine] I -->|semantic| E I -->|lexical| G I -->|optional graph hop| H I -->|context| J[Reasoner (LangGraph)] J -->|LLM calls| K[[Local LLM Runner]] K -->|transformers| L[(HF Pipeline)] K -->|ollama| M[(Ollama)] B --> N[Observability / Metrics] 
2.2 Deployment View (MVP)
• Process 1: uvicorn (FastAPI app)
• Process 2: (optional) neo4j (local Docker or remote)
• Process 3: (optional) ollama daemon (local)
External services: Qdrant (Docker) bound on localhost:6333.
2.3 Data Flow (Happy Paths)
Ingestion (single file)
• POST /ingest → persist temp file → parse with unstructured/pypdf.
• Chunk text/tables/images → compute embeddings → upsert to Qdrant.
• Tokenize terms → update in-process BM25.
• Optionally extract entities/relations → write to networkx in-mem and Neo4j if enabled.
Query
• POST /query → LangGraph router runs retrieval plan.
• Parallel: semantic top-k (Qdrant) + lexical top-k (BM25).
• Fuse via RRF → optional graph hop to expand evidence window.
• Reasoner composes answer (provider=none|transformers|ollama).
• Return {answer, citations, traces, scores}.
3) Key Components & Responsibilities
ComponentTechResponsibilitiesAPI LayerFastAPI + Uvicorn/StarletteAuth, routing, validation (Pydantic v2), OpenAPI docs, error mappingIngestionunstructured, pypdf, sentence-transformersParse → chunk → embed → persist vectors/metadata; idempotency via SHA-256StoresQdrant, DocArrayVector persistence; lightweight schemas (DocArray) for chunk metadataLexical Indexrank-bm25In-process token index; rebuilt incrementally per collectionGraph (opt.)networkx + neo4jLocal graph ops; optional external graph DBOrchestrationLangGraph + LangChainRouter, tools (calculator, table ops), prompt policiesLLM RunnerTransformers (HF) or OllamaLocal text generation; disabled by defaultObservabilityPrometheus text endpoint, JSON logsRequest counters, latency histograms, stage timings 
4) Data Model (Logical)
Document
• id: str, collection: str, uri: str, media_type: str, sha256: str
• metadata: {author?: str, created_at?: str, tags?: [str], extra?: dict}
Chunk
• id: str, document_id: str, type: "text"|"table"|"image"
• page?: int, span?: [start, end]?, text?: str, table_csv_path?: str, image_ref?: str
• embedding: List[float], score?: float, meta: dict
Lexical Index Entry
• chunk_id: str, tokens: List[str]
Graph (opt.)
• Node: {id, type, labels[], props{}}
• Edge: {id, src, dst, type, props{}}
QueryTrace
• {id, ts, router, retriever_scores{semantic[], lexical[], fused[]}, graph_ops[], provider}
5) Interfaces (Schemas)
5.1 API (selected)
POST /ingest
{ "collection": "string", "ocr": false } 
Response:
{ "job_id": "uuid" } 
POST /query
{ "collection": "string", "query": "string", "top_k": 8, "retrieval_mode": "hybrid", "graph": false, "provider": "none" } 
Response:
{ "answer": "string", "citations": [{"file_id":"doc-1","page":5,"span":[120,220]}], "contexts": [{"chunk_id":"...","text":"...","score":0.83}], "scores": {"semantic":[...],"lexical":[...],"fused":[...]}, "graph_context": {"nodes":[...],"edges":[...]}, "traces": {"router":"pathA->B","timings_ms":{"semantic":120,"lexical":30,"fusion":5}} } 
Error envelope (all endpoints)
{ "error": { "code":"BAD_REQUEST|NOT_FOUND|CONFLICT|INTERNAL", "message":"...", "details":{} } } 
6) Config Keys (runtime)
PYTHON_VERSION=3.11 APP_PORT=8080 APP_LOG_LEVEL=INFO APP_AUTH_MODE=token # token|none APP_TOKEN=change_me QDRANT_HOST=localhost QDRANT_PORT=6333 QDRANT_COLLECTION=rag_alloy_default RETRIEVAL_DEFAULT_MODE=hybrid # semantic|lexical|hybrid RETRIEVAL_TOP_K=8 FUSION_METHOD=rrf GRAPH_ENABLED=false NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=change_me GEN_PROVIDER=none # none|transformers|ollama TRANSFORMERS_MODEL=hf:Qwen2.5-0.5B-Instruct # example local OLLAMA_MODEL=llama3:instruct 
7) Performance & Sizing (MVP)
• Latency budgets (local CPU): retrieve-only p50 ≤ 350 ms, p95 ≤ 900 ms; with gen p50 ≤ 3 s, p95 ≤ 7 s.
• Throughput: ≥30 medium PDFs/hour (text-only).
• Memory: base service <1.5 GB (no GPU models).
8) Security Model (MVP)
• Auth: Token header for mutating endpoints; read endpoints can be open or token-gated via config.
• Privacy: No network egress unless explicitly enabled (Neo4j remote, model pulls).
• Files: Stored under collection namespace; SHA-256 dedupe; temp cleanup after ingest.
• Logging: Structured JSON; redact content; include correlation ids.
9) Observability
• /metrics Prometheus text (requests, latency histograms per stage).
• /healthz liveness.
• Request-scoped traces (durations for semantic, lexical, fusion, graph hop, generation).
10) Sequence Diagrams
Query (Hybrid + Optional Graph)
sequenceDiagram participant UI participant API participant Retriever participant Qdrant participant BM25 participant Graph participant Reasoner UI->>API: POST /query API->>Retriever: plan(query, mode=hybrid, graph=false/true) par Semantic Retriever->>Qdrant: topK(embeddings) Qdrant-->>Retriever: vectors + meta and Lexical Retriever->>BM25: topK(tokens) BM25-->>Retriever: chunk ids + scores end alt graph==true Retriever->>Graph: expand(entities) Graph-->>Retriever: neighborhood nodes/edges end Retriever->>Reasoner: context pack Reasoner-->>API: answer + citations + scores API-->>UI: 200 OK 
11) Build & Packaging
• requirements.txt = PRD BoM (exact pins).
• Makefile targets:
• make venv && make install (pip install -r requirements.txt)
• make run (uvicorn app.main:app --port 8080)
• make qdrant-up (docker compose up qdrant)
• make test (unit + eval)
• make fmt (ruff/black optional; not pinned here)
• make eval (Recall@k, citation coverage, latency smoke)
12) Risks & Mitigations (MVP)
• Parser brittleness → fallback to pypdf text; raw text upload path.
• Torch wheel / CUDA variance → CPU-only baseline supported; document GPU wheels separately.
• Index inconsistency on failures → transactional upsert; mark-and-sweep on pipeline errors.
RAG-Alloy — Functional Requirements Document (FRD) (Lean, MVP scope)
1) Scope & Assumptions
• Scope: Local-first RAG service with ingestion, hybrid retrieval (semantic+lexical), optional graph enrichment, optional local LLM generation, and minimal UI.
• Assumptions: Python 3.11.x; Qdrant reachable at localhost:6333; no external network required; Neo4j and Ollama disabled by default.
2) Functional Requirements
2.1 Ingestion
FR-ING-01 Upload & Queue
• API: POST /ingest (multipart form).
• Rules: collection required; max file size default 50 MB (configurable).
• Result: {job_id} with observable status via GET /ingest/{job_id}.
FR-ING-02 Parsing & Chunking
• Use unstructured (pdf, docx, pptx, xlsx, image) and pypdf for robust PDF text.
• Default chunker: recursive char splitter size=800, overlap=120.
• Persist Doc + Chunk records with sha256 and original source_uri.
FR-ING-03 Embedding & Storage
• Model: sentence-transformers==3.1.0 (configurable path) → vector dim set by model.
• Upsert vectors to Qdrant collection; store text+meta in DocArray.
• Maintain BM25 tokens for each chunk in collection-scoped index.
FR-ING-04 Idempotency & Cleanup
• Duplicate file content (same SHA-256 within collection) is skipped unless force=true.
• Temp files removed after successful ingest; partial failures roll back staged writes.
2.2 Retrieval
FR-RET-01 Modes
• retrieval_mode: semantic|lexical|hybrid (default hybrid).
• Top-k default 8; scores normalized to [0,1].
FR-RET-02 Fusion
• RRF with configurable weightings (defaults equal).
• Return per-retriever scores and fused ranking.
FR-RET-03 Graph Enrichment (Optional)
• When graph=true and GRAPH_ENABLED=true, extract light entities from fused top-k and fetch N-hop neighbors from networkx/Neo4j to augment contexts.
FR-RET-04 Citations
• Each answer must include ≥1 citation if any evidence returned; otherwise return "answer": "", error:"NO_EVIDENCE" unless provider=none and contexts returned.
2.3 Reasoning & Generation
FR-GEN-01 Providers
• provider=none|transformers|ollama (default none).
• When none, return only contexts, citations, and suggested snippets (no free-form answer).
FR-GEN-02 Tooling
• Provide calculator and CSV/XLSX aggregation utilities; use LangGraph tool calling.
FR-GEN-03 Determinism Controls
• Expose max_tokens, temperature, and seed (best-effort) for local generation.
2.4 Administration & Observability
FR-OPS-01 Health: GET /healthz returns {"status":"ok"} if API and Qdrant reachable.
FR-OPS-02 Metrics: GET /metrics exposes Prometheus counters/histograms:
• http_requests_total{path,method,status}
• stage_latency_ms_bucket{stage ∈ [semantic,lexical,fusion,graph,gen]}
• ingest_duration_ms_bucket
FR-OPS-03 Collections
• GET /collections/{collection}/stats → {docs, chunks, vectors, last_update}
• DELETE /collections/{collection} → cascade delete vectors + metadata.
3) Detailed API Contract (MVP)
3.1 POST /ingest (multipart)
Form fields:
• collection: str (required)
• ocr: bool (optional; default false)
• files[]: file (≥1)
Responses:
• 202 Accepted: { "job_id": "uuid" }
• 413: file too large
• 400: missing collection / no files
3.2 GET /ingest/{job_id}
Response:
{ "status": "pending|processing|done|error", "error": null, "artifacts": [ {"file_id":"doc-uuid","pages":12,"chunks":48} ] } 
3.3 POST /query
Body:
{ "collection":"string", "query":"string", "top_k":8, "retrieval_mode":"hybrid", "graph":false, "provider":"none", "gen_params":{"max_tokens":256,"temperature":0.2,"seed":123} } 
Errors:
• 404 if collection not found
• 400 invalid params
• 503 if provider unavailable (ollama/transformers not initialized)
3.4 GET /collections/{collection}/stats
200:
{"docs":10,"chunks":1800,"vectors":1800,"last_update":"2025-09-05T12:00:00Z"} 
3.5 DELETE /collections/{collection}
204 No Content (idempotent)
4) Acceptance Criteria & Test Matrix
4.1 Functional Acceptance
• AC-ING-01: Upload 3 PDFs → /ingest returns job id and status done with correct chunk counts.
• AC-ING-02: Re-upload same content → system dedupes (no net new chunks).
• AC-RET-01: Rare keyword query (present in corpus) is returned in top-k under lexical and present in final hybrid.
• AC-RET-02: Generic concept query yields top-k from semantic retriever with sensible scores.
• AC-RET-03: graph=true adds graph_context when GRAPH_ENABLED.
• AC-GEN-01: provider=none returns empty answer but non-empty contexts and citations.
• AC-GEN-02: provider=transformers returns an answer string and citations.
• AC-OPS-01: /healthz returns ok; /metrics exposes counters/histograms.
4.2 Quality Gates (CI)
• Retrieval: Recall@10 ≥ 0.85 on seeded set; MRR ≥ 0.65.
• Evidence: ≥95% of generated answers include ≥1 citation; ≥80% include ≥2.
• Latency (CPU baseline): retrieve-only p95 ≤ 900 ms; with generation p95 ≤ 7 s.
• Parsing: 0 fatal errors on sample doc bundle; parser fallbacks cover scanned vs native.
• Contract: OpenAPI schema validation for request/response examples.
5) Non-Functional Requirements (verifiable)
• Runtime: Service fails fast if not under Python 3.11.x.
• Security: Write endpoints require token unless APP_AUTH_MODE=none.
• Privacy: No external requests unless Neo4j/ollama/transformers model download explicitly enabled.
• Resilience: Partial ingestion failures do not leave orphaned vectors (checked by sweep).
• Portability: Linux/macOS primary; Windows best-effort.
• Observability: Every /query emits stage timings in traces and increments metrics.
6) Test Cases (Representative)
• TC-ING-PDF-NATIVE: 20-page text PDF → expect ~N chunks (±10%), no OCR path.
• TC-ING-PDF-SCANNED: image-only PDF with ocr=false → minimal/no chunks; with ocr=true (when OCR added later) → chunks exist.
• TC-RET-RARE-TOKEN: Query “INV-00459273” → BM25 ranks chunk #1; hybrid fused top-3 contains the chunk.
• TC-RET-SEMANTIC-ABSTRACT: Query “quarterly revenue recognition policy” → semantic hits dominate; lexical contributes little.
• TC-GEN-NONE: provider=none → answer="" and non-empty contexts.
• TC-GEN-TRANSFORMERS: Provide small local model; answer returned with ≥1 citation.
• TC-OPS-METRICS: /metrics contains stage_latency_ms_bucket{stage="semantic"} after at least one query.
7) Error Handling & Codes
CodeWhenClient Action400 BAD_REQUESTInvalid params, missing fieldsFix payload404 NOT_FOUNDUnknown collection or jobCreate/ingest first409 CONFLICTDuplicate ingest with force=falseRetry with force=true if desired413 PAYLOAD_TOO_LARGEFile exceeds limitSplit or increase limit503 SERVICE_UNAVAILABLEProvider not initialized / Qdrant downRetry after init / restore service 
8) Rollout & Ops Runbook (MVP)
• Start Qdrant: docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
• Create venv & Install: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
• Run API: uvicorn app.main:app --host 0.0.0.0 --port 8080
• Smoke: GET /healthz → ok; ingest small PDF; run sample queries.
• (Optional) Start Neo4j and/or Ollama, flip flags, verify /query?graph=true and generation.
9) Open Items (tracked)
• OCR package selection and pins (Tesseract/PaddleOCR) for the future OCR path.
• Default CPU-friendly embedding model choice & evaluation baselines.
• Minimal entity linker implementation (rule-based vs NER) for graph seeding.
Appendix A — Pydantic Schemas (concise)
# app/models/api.py (illustrative, Pydantic v2) class IngestJob(BaseModel): job_id: str class IngestStatus(BaseModel): status: Literal["pending","processing","done","error"] error: str | None = None artifacts: list[dict] = [] class QueryRequest(BaseModel): collection: str query: str top_k: int = 8 retrieval_mode: Literal["semantic","lexical","hybrid"] = "hybrid" graph: bool = False provider: Literal["none","transformers","ollama"] = "none" gen_params: dict | None = None class Citation(BaseModel): file_id: str page: int | None = None span: tuple[int,int] | None = None class QueryResponse(BaseModel): answer: str citations: list[Citation] contexts: list[dict] scores: dict graph_context: dict | None = None traces: dict 

