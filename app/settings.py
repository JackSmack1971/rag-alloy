"""Application settings loaded from environment variables or `.env`.

This module defines a ``Settings`` class using Pydantic's ``BaseSettings``
that reads configuration from environment variables or a ``.env`` file.
It enforces that the running Python version matches the required version
(3.11) and exposes defaults for core service configuration.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    python_version: str = Field(default="3.11", alias="PYTHON_VERSION")
    app_port: int = Field(default=8080, alias="APP_PORT")
    app_auth_mode: str = Field(default="token", alias="APP_AUTH_MODE")
    app_token: str = Field(default="change_me", alias="APP_TOKEN")
    max_upload_bytes: int = Field(
        default=52_428_800, alias="MAX_UPLOAD_BYTES"
    )
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="CHUNK_OVERLAP")
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    retrieval_default_mode: str = Field(
        default="hybrid", alias="RETRIEVAL_DEFAULT_MODE"
    )
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")
    fusion_method: str = Field(default="rrf", alias="FUSION_METHOD")
    graph_enabled: bool = Field(default=False, alias="GRAPH_ENABLED")
    gen_provider: str = Field(default="none", alias="GEN_PROVIDER")
    transformers_model: str | None = Field(
        default=None, alias="TRANSFORMERS_MODEL"
    )
    ollama_model: str | None = Field(default=None, alias="OLLAMA_MODEL")

    @model_validator(mode="after")
    def enforce_python_version(self) -> "Settings":
        """Ensure the runtime Python version matches ``python_version``."""

        runtime = f"{sys.version_info.major}.{sys.version_info.minor}"
        if runtime != self.python_version:
            raise RuntimeError(
                f"Python {self.python_version} required, but running {runtime}"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
