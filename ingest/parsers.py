from __future__ import annotations

"""Document parsing utilities using Unstructured."""

from importlib import import_module
from pathlib import Path
from typing import Callable, List, Optional

from unstructured.documents.elements import Element, FigureCaption, Image, Table, Text

# Mapping of file suffixes to the fully qualified partition function names.
_PARTITIONER_NAMES = {
    ".pdf": "unstructured.partition.pdf.partition_pdf",
    ".docx": "unstructured.partition.docx.partition_docx",
    ".pptx": "unstructured.partition.pptx.partition_pptx",
    ".xlsx": "unstructured.partition.xlsx.partition_xlsx",
    ".png": "unstructured.partition.image.partition_image",
    ".jpg": "unstructured.partition.image.partition_image",
    ".jpeg": "unstructured.partition.image.partition_image",
    ".gif": "unstructured.partition.image.partition_image",
    ".bmp": "unstructured.partition.image.partition_image",
    ".tiff": "unstructured.partition.image.partition_image",
    ".tif": "unstructured.partition.image.partition_image",
}


def _get_partitioner(suffix: str) -> Optional[Callable[..., list[Element]]]:
    """Dynamically import the Unstructured partition function for a suffix."""
    name = _PARTITIONER_NAMES.get(suffix)
    if not name:
        return None
    module_name, func_name = name.rsplit(".", 1)
    try:
        module = import_module(module_name)
    except Exception:
        return None
    return getattr(module, func_name, None)


class _SimpleElement:
    def __init__(self, text: str) -> None:
        self.text = text
        self.metadata: dict = {}


def parse_document(path: Path) -> List[Element]:
    """Parse a document into Unstructured elements.

    Parameters
    ----------
    path:
        Path to the document to parse.

    Returns
    -------
    list[Element]
        A list of text, table, and caption elements extracted from the document.

    Raises
    ------
    ValueError
        If the file extension is unsupported.
    """

    suffix = path.suffix.lower()
    if suffix not in _PARTITIONER_NAMES:
        raise ValueError(f"Unsupported file type: {suffix}")
    partitioner = _get_partitioner(suffix)
    if partitioner is None:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [_SimpleElement(text)]

    try:
        elements = partitioner(filename=str(path))
    except Exception:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [_SimpleElement(text)]
    allowed = (Text, Table, FigureCaption)
    return [el for el in elements if isinstance(el, allowed) and not isinstance(el, Image)]
