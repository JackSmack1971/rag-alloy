from pathlib import Path
import sys
import os
import importlib

# Ensure repo root in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
    import app.main as main
    return importlib.reload(main)


def test_healthz_and_metrics():
    main = _reload_app()
    client = TestClient(main.app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text
