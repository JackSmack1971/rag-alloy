from pathlib import Path
import sys

# Ensure the repository root is on the Python path for module resolution during tests.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from index.embedding_store import EmbeddingStore


def test_add_texts_deduplicates_and_stores_metadata():
    store = EmbeddingStore(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        location=":memory:",
    )
    text = "hello world"
    meta = {"source": "unit"}

    ids1 = store.add_texts([text], [meta])
    assert ids1

    ids2 = store.add_texts([text], [meta])
    assert ids2 == []

    retrieved = store.client.retrieve(
        collection_name=store.collection_name, ids=ids1
    )
    payload = retrieved[0].payload
    assert payload["text"] == text
    assert payload["tags"]["source"] == "unit"
