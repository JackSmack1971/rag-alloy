from __future__ import annotations

"""Pydantic models representing ingestion job metadata."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Metadata about an ingested file artifact."""

    file_id: str
    pages: int
    chunks: int


class JobStatus(BaseModel):
    """Status metadata for an ingestion job."""

    status: Literal["pending", "processing", "done", "error"]
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
