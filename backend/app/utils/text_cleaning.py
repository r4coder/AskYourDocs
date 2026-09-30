"""
Simple text cleaning utilities applied before chunking.

Kept intentionally minimal (no heavy NLP) to stay beginner-friendly and
transparent about what transformations are applied to the raw text.
"""
from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Normalize whitespace and strip common PDF extraction artifacts."""
    if not text:
        return ""

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove hyphenation artifacts from PDF line wraps, e.g. "docu-\nment".
    text = re.sub(r"-\n(?=[a-z])", "", text)

    # Collapse 3+ newlines into a paragraph break.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse runs of spaces/tabs.
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Strip trailing whitespace on each line.
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
