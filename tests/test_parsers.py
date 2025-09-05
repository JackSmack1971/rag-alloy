from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the repository root is on the Python path for module resolution during tests.
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from unstructured.documents.elements import (
    Element,
    FigureCaption,
    Image,
    Table,
    Text,
    Title,
)

from ingest.parsers import parse_document


@pytest.mark.parametrize("suffix", [".pdf", ".docx", ".pptx", ".xlsx", ".png"])
def test_parse_document_filters_elements(suffix: str) -> None:
    """Verify that parse_document extracts only text, table and caption elements."""
    dummy_elements: list[Element] = [
        Text("text"),
        Table("table"),
        FigureCaption("caption"),
        Title("title"),
        Image("img"),
    ]

    with patch("ingest.parsers._get_partitioner", return_value=lambda *_, **__: dummy_elements) as mock_get:
        result = parse_document(Path(f"doc{suffix}"))

    mock_get.assert_called_once_with(suffix)
    assert all(isinstance(el, (Text, Table, FigureCaption)) for el in result)
    assert not any(isinstance(el, Image) for el in result)
    assert len(result) == 4


def test_parse_document_unsupported_extension() -> None:
    with pytest.raises(ValueError):
        parse_document(Path("unsupported.txt"))
