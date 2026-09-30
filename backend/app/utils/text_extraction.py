"""
Text extraction utilities.

Supports plain `.txt` files and `.pdf` files. PDF extraction is done
page-by-page so that page numbers can be preserved as metadata, which is
required for accurate source citations later in the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class TextExtractionError(Exception):
    """Raised when a document's text cannot be extracted."""


@dataclass
class ExtractedPage:
    """One page (or the whole file, for .txt) of extracted raw text."""

    page_number: int | None
    text: str


def extract_txt(raw_bytes: bytes) -> list[ExtractedPage]:
    """Decode a plain text file. Returns a single 'page' with no page number."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise TextExtractionError("Could not decode text file as UTF-8 or Latin-1.") from exc

    if not text.strip():
        raise TextExtractionError("The text file is empty.")

    return [ExtractedPage(page_number=None, text=text)]


def extract_pdf(raw_bytes: bytes) -> list[ExtractedPage]:
    """Extract text from a PDF file, one entry per page (1-indexed)."""
    import io

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except PdfReadError as exc:
        raise TextExtractionError("The PDF file appears to be corrupted or unreadable.") from exc
    except Exception as exc:  # pragma: no cover - defensive catch-all
        raise TextExtractionError(f"Failed to open PDF file: {exc}") from exc

    if reader.is_encrypted:
        try:
            # Try an empty password in case it's a "restricted but not really
            # password protected" PDF; otherwise fail clearly.
            reader.decrypt("")
        except Exception as exc:
            raise TextExtractionError("The PDF is password-protected and cannot be read.") from exc

    if len(reader.pages) == 0:
        raise TextExtractionError("The PDF has no pages.")

    pages: list[ExtractedPage] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        pages.append(ExtractedPage(page_number=i, text=page_text))

    if not any(p.text.strip() for p in pages):
        raise TextExtractionError(
            "No extractable text was found in the PDF. "
            "It may be a scanned image without an OCR text layer."
        )

    return pages


def extract_text(filename: str, raw_bytes: bytes) -> list[ExtractedPage]:
    """Dispatch to the right extractor based on file extension."""
    if not raw_bytes:
        raise TextExtractionError("The uploaded file is empty.")

    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf(raw_bytes)
    if lower.endswith(".txt"):
        return extract_txt(raw_bytes)

    raise TextExtractionError(f"Unsupported file type for: {filename}")
