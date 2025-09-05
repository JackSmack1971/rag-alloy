from pathlib import Path
import sys

# Ensure repository root is on the Python path for imports during tests.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from ingest.chunking import chunk_text, get_text_splitter


def test_get_text_splitter_env(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "10")
    monkeypatch.setenv("CHUNK_OVERLAP", "2")
    splitter = get_text_splitter()
    assert splitter._chunk_size == 10
    assert splitter._chunk_overlap == 2


def test_chunk_text(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "10")
    monkeypatch.setenv("CHUNK_OVERLAP", "2")
    text = "abcdefghijk"
    chunks = chunk_text(text)
    assert chunks == ["abcdefghij", "ijk"]
