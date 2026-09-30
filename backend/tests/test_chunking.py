"""Tests for the chunking service."""
from __future__ import annotations

from app.services.chunking_service import chunk_document
from app.utils.text_extraction import ExtractedPage


class TestChunkDocument:
    def test_chunks_have_correct_metadata(self):
        pages = [ExtractedPage(page_number=1, text="Sentence one. Sentence two. Sentence three.")]
        chunks = chunk_document("doc-1", "example.txt", pages)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == "doc-1"
            assert chunk.document_name == "example.txt"
            assert chunk.page_number == 1
            assert chunk.chunk_id  # non-empty unique id
            assert chunk.text.strip() != ""

    def test_chunk_indices_are_sequential(self):
        pages = [ExtractedPage(page_number=1, text="A. " * 500)]
        chunks = chunk_document("doc-1", "big.txt", pages)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_page_produces_no_chunks(self):
        pages = [ExtractedPage(page_number=1, text="   ")]
        chunks = chunk_document("doc-1", "empty.txt", pages)
        assert chunks == []

    def test_multiple_pages_preserve_page_numbers(self):
        pages = [
            ExtractedPage(page_number=1, text="Content of page one, quite short."),
            ExtractedPage(page_number=2, text="Content of page two, also short."),
        ]
        chunks = chunk_document("doc-1", "multi.pdf", pages)
        page_numbers = {c.page_number for c in chunks}
        assert page_numbers == {1, 2}

    def test_long_text_produces_multiple_chunks(self):
        long_text = "This is a sentence that repeats. " * 200
        pages = [ExtractedPage(page_number=None, text=long_text)]
        chunks = chunk_document("doc-1", "long.txt", pages)
        assert len(chunks) > 1
