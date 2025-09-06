from pathlib import Path
import sys
import os
import importlib
import types
import collections

# Ensure repo root in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
    Version = collections.namedtuple("Version", "major minor micro releaselevel serial")
    sys.version_info = Version(3, 11, 0, "final", 0)  # type: ignore[attr-defined]
    import app.main as main
    return importlib.reload(main)


def test_ac_ops_01_healthz_and_metrics():
    """AC-OPS-01: /healthz returns OK and /metrics exposes counters."""

    main = _reload_app()
    client = TestClient(main.app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text
