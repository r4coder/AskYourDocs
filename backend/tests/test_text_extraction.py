"""Tests for text extraction from PDF and TXT files."""
from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from app.utils.text_extraction import (
    TextExtractionError,
    extract_pdf,
    extract_text,
    extract_txt,
)


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    """Build a minimal real PDF with the given page texts using pypdf."""
    writer = PdfWriter()
    for text in pages_text:
        # pypdf's writer can't easily draw arbitrary text without reportlab,
        # so we build blank pages here and rely on extract_pdf's page-count
        # and error-handling behavior; text-content tests use extract_txt
        # and integration tests instead cover realistic extracted text via
        # monkeypatched pages where needed.
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestExtractTxt:
    def test_extract_valid_txt(self):
        pages = extract_txt(b"Hello, this is a test document.")
        assert len(pages) == 1
        assert pages[0].page_number is None
        assert "Hello" in pages[0].text

    def test_extract_empty_txt_raises(self):
        with pytest.raises(TextExtractionError):
            extract_txt(b"   \n\n  ")

    def test_extract_latin1_txt(self):
        raw = "café".encode("latin-1")
        pages = extract_txt(raw)
        assert "caf" in pages[0].text


class TestExtractPdf:
    def test_blank_pdf_with_no_text_raises(self):
        pdf_bytes = make_pdf_bytes(["", ""])
        with pytest.raises(TextExtractionError):
            extract_pdf(pdf_bytes)

    def test_corrupted_pdf_raises(self):
        with pytest.raises(TextExtractionError):
            extract_pdf(b"this is not a real pdf file at all")

    def test_empty_bytes_raises_via_extract_text(self):
        with pytest.raises(TextExtractionError):
            extract_text("file.pdf", b"")


class TestExtractTextDispatch:
    def test_unsupported_extension_raises(self):
        with pytest.raises(TextExtractionError):
            extract_text("file.docx", b"some bytes")

    def test_dispatches_to_txt_extractor(self):
        pages = extract_text("notes.txt", b"Some plain text content.")
        assert pages[0].text == "Some plain text content."
