from pathlib import Path
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))


class DummyStore:
    def __init__(self, *_, **__):
        self.texts: list[str] = []
        self.metadatas: list[dict] = []

    def add_texts(self, texts, metadatas=None):
        self.texts = list(texts)
        self.metadatas = list(metadatas) if metadatas else []
        return [f"id{i}" for i, _ in enumerate(self.texts)]


class DummyElement:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture()
def app_monkeypatched(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 11, 0, "final", 0))
    monkeypatch.setattr("index.embedding_store.EmbeddingStore", DummyStore)
    import app.main as main

    monkeypatch.setattr(
        main, "parse_document", lambda path: [DummyElement("hello world")]
    )
    monkeypatch.setattr(main, "chunk_text", lambda text: ["hello", "world"])
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
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
