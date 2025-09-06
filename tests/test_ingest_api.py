from __future__ import annotations

from pathlib import Path
import importlib
import sys
import types
import uuid

import pytest
from fastapi.testclient import TestClient

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))


class DummyStore:
    def __init__(self, *_, **__):
        self.texts: list[str] = []
        self.metadatas: list[dict] = []
        self.calls = 0

    def add_texts(self, texts, metadatas=None):
        self.calls += 1
        self.texts = list(texts)
        self.metadatas = list(metadatas) if metadatas else []
        return [f"id{i}" for i, _ in enumerate(self.texts)]


class DummyElement:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture()
def app_monkeypatched(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 11, 0, "final", 0))
    dummy_module = types.ModuleType("index.embedding_store")
    dummy_module.EmbeddingStore = DummyStore
    dummy_module.TextDoc = object
    sys.modules["index.embedding_store"] = dummy_module
    sys.modules.pop("app.main", None)
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "parse_document", lambda path: [DummyElement("hello world")])
    monkeypatch.setattr(main, "chunk_text", lambda text: ["hello", "world"])
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    main.HASH_MAP_PATH = tmp_path / "hashes.json"
    main.JOBS_PATH = tmp_path / "jobs.json"
    main.HASH_TO_JOB.clear()
    main.JOBS.clear()
    if main.HASH_MAP_PATH.exists():
        main.HASH_MAP_PATH.unlink()
    if main.JOBS_PATH.exists():
        main.JOBS_PATH.unlink()
    return main


def test_ingest_pipeline(app_monkeypatched):
    client = TestClient(app_monkeypatched.app)
    files = {"file": ("test.pdf", b"dummy", "application/pdf")}
    resp = client.post("/ingest", files=files)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    uuid.UUID(job_id)
    assert (app_monkeypatched.UPLOAD_DIR / f"{job_id}.pdf").exists()
    assert app_monkeypatched.store.texts == ["hello", "world"]
    assert app_monkeypatched.store.metadatas == [
        {"file_id": job_id},
        {"file_id": job_id},
    ]
    status = client.get(f"/ingest/{job_id}").json()
    assert status["status"] == "done"
    assert status["artifacts"] == [
        {"file_id": job_id, "pages": 1, "chunks": 2}
    ]
    assert status["duration_ms"] >= 0


def test_ingest_skips_duplicate(app_monkeypatched):
    client = TestClient(app_monkeypatched.app)
    files = {"file": ("test.pdf", b"dummy", "application/pdf")}
    job1 = client.post("/ingest", files=files).json()["job_id"]
    job2 = client.post("/ingest", files=files).json()["job_id"]
    assert job1 == job2
    assert app_monkeypatched.store.calls == 1
