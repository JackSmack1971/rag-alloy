from pathlib import Path
import sys
import os
import importlib

# Ensure repo root in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from qdrant_client.http import models as rest


def _reload_app():
    os.environ["QDRANT_LOCATION"] = ":memory:"
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
