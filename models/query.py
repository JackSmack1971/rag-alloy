"""Pydantic models for the ``/query`` endpoint."""

from __future__ import annotations

from typing import Literal, List

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request payload for the ``/query`` endpoint."""

    query: str
    top_k: int = 5
    mode: Literal["semantic", "lexical", "hybrid"] = "hybrid"
    provider: Literal["none", "transformers", "ollama"] = "none"


class RetrieverScores(BaseModel):
    """Per-retriever scores for a retrieved text chunk."""

    semantic: float | None = None
    lexical: float | None = None


class RankedDocument(BaseModel):
    """Retrieved text with fused ranking and retriever scores."""

    text: str
    rank: int
    scores: RetrieverScores = Field(default_factory=RetrieverScores)


class QueryResponse(BaseModel):
    """Response model for ``/query`` containing fused ranking information."""

    query: str
    answer: str = ""
    results: List[RankedDocument] = Field(default_factory=list)
