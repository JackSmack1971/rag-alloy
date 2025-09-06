from pathlib import Path
import sys
import os
import importlib
import types
import collections

# Ensure repo root in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from qdrant_client.http import models as rest


def _reload_app(auth_mode: str = "none", token: str = "change_me"):
    os.environ["APP_AUTH_MODE"] = auth_mode
    os.environ["APP_TOKEN"] = token
    os.environ["QDRANT_LOCATION"] = ":memory:"
    Version = collections.namedtuple("Version", "major minor micro releaselevel serial")
    sys.version_info = Version(3, 11, 0, "final", 0)  # type: ignore[attr-defined]
    from app.settings import get_settings
    get_settings.cache_clear()
    import app.main as main
    return importlib.reload(main)


def test_collection_stats_and_delete():
    main = _reload_app()
    client = TestClient(main.app)

    main.qdrant.recreate_collection(
        "test", rest.VectorParams(size=2, distance=rest.Distance.COSINE)
    )
    main.qdrant.upsert(
        "test",
        points=[
            rest.PointStruct(id=1, vector=[0.1, 0.2], payload={"text": "hello"})
        ],
    )

    stats = client.get("/collections/test/stats")
    assert stats.status_code == 200
    assert stats.json()["points_count"] == 1

    delete = client.delete("/collections/test")
    assert delete.status_code == 200
    names = {c.name for c in main.qdrant.get_collections().collections}
    assert "test" not in names


def test_delete_collection_requires_auth():
    main = _reload_app(auth_mode="token", token="secret")
    client = TestClient(main.app)
    main.qdrant.recreate_collection(
        "test", rest.VectorParams(size=2, distance=rest.Distance.COSINE)
    )
    resp = client.delete("/collections/test")
    assert resp.status_code == 401
    resp = client.delete(
        "/collections/test", headers={"Authorization": "Bearer secret"}
    )
    assert resp.status_code == 200
