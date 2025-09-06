"""Pydantic models for the ``/query`` endpoint."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Tuple

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request payload for the ``/query`` endpoint."""

    query: str
    top_k: int = 5
    mode: Literal["semantic", "lexical", "hybrid"] = "hybrid"
    provider: Literal["none", "transformers", "ollama"] = "none"
    graph: bool = False


class RetrieverScores(BaseModel):
    """Per-retriever scores for a retrieved text chunk."""

    semantic: float | None = None
    lexical: float | None = None


class RankedDocument(BaseModel):
    """Retrieved text with fused ranking, metadata and retriever scores."""

    text: str
    rank: int
    file_id: str
    page: int | None = None
    span: Tuple[int, int] | None = None
    scores: RetrieverScores = Field(default_factory=RetrieverScores)


class Citation(BaseModel):
    """Source location for an answer segment."""

    file_id: str
    page: int | None = None
    span: Tuple[int, int] | None = None
    text: str | None = None


class QueryResponse(BaseModel):
    """Response model for ``/query`` containing fused ranking information."""

    query: str
    answer: str = ""
    citations: List[Citation] = Field(default_factory=list)
    results: List[RankedDocument] = Field(default_factory=list)
    graph_context: Dict[str, Any] | None = None
