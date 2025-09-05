from pathlib import Path
import sys

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from graph.entities import extract_entities


def test_extract_entities_returns_capitalised_tokens():
    text = "Alice met Bob in Paris"
    ents = extract_entities(text)
    assert "Alice" in ents and "Bob" in ents and "Paris" in ents
