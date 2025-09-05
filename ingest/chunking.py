"""Utilities for splitting text into overlapping chunks."""

from __future__ import annotations

import os
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Return a ``RecursiveCharacterTextSplitter`` configured from the environment.

    The ``CHUNK_SIZE`` and ``CHUNK_OVERLAP`` variables control the maximum number
    of characters per chunk and the number of characters overlapping between
    consecutive chunks. Defaults are 800 and 120 respectively.
    """

    chunk_size = int(os.environ.get("CHUNK_SIZE", DEFAULT_CHUNK_SIZE))
    chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP))
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )


def chunk_text(text: str) -> List[str]:
    """Split ``text`` into chunks according to the configured splitter."""

    splitter = get_text_splitter()
    return splitter.split_text(text)
