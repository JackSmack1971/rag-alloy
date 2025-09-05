"""Entity extraction utilities using spaCy NER.

This module provides a lightweight wrapper around spaCy to extract
entities from text. It tries to load the small English model
``en_core_web_sm`` and falls back to a blank English pipeline with a
very small rule-based entity ruler so that tests can run without the
pretrained weights.
"""

from __future__ import annotations

from typing import Iterable, List

import spacy
from spacy.language import Language
from spacy.pipeline import EntityRuler

_nlp: Language | None = None


def _load_model() -> Language:
    """Load a spaCy model, falling back to a blank pipeline.

    The blank pipeline includes a tiny ``EntityRuler`` that labels
    capitalised tokens as generic ``MISC`` entities. This keeps the
    implementation dependency-light while still exercising spaCy's NER
    machinery in tests.
    """

    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        _nlp = spacy.load("en_core_web_sm")
    except Exception:
        _nlp = spacy.blank("en")
        ruler = EntityRuler(_nlp)
        ruler.add_patterns([
            {"label": "MISC", "pattern": [{"IS_TITLE": True}]},
        ])
        _nlp.add_pipe(ruler)
    return _nlp


def extract_entities(text: str, labels: Iterable[str] | None = None) -> List[str]:
    """Return unique entities found in ``text``.

    Parameters
    ----------
    text:
        The text to analyse.
    labels:
        Optional iterable of entity labels to filter by. When omitted all
        detected entities are returned.
    """

    nlp = _load_model()
    doc = nlp(text)
    entities: List[str] = []
    for ent in doc.ents:
        if labels and ent.label_ not in labels:
            continue
        if ent.text not in entities:
            entities.append(ent.text)
    return entities
