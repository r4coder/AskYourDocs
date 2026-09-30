"""
Chunking service.

Splits cleaned page text into overlapping chunks using LangChain's
`RecursiveCharacterTextSplitter`, which tries to split on paragraph/sentence
boundaries first and only falls back to hard character cuts when necessary.
Each resulting chunk keeps track of which document and page it came from.
"""
from __future__ import annotations

import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models.chunk import DocumentChunk
from app.utils.text_cleaning import clean_text
from app.utils.text_extraction import ExtractedPage


def build_splitter(chunk_size: int | None = None, chunk_overlap: int | None = None):
    """Create a configured text splitter instance."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_document(
    document_id: str,
    document_name: str,
    pages: list[ExtractedPage],
) -> list[DocumentChunk]:
    """
    Clean and split extracted pages into `DocumentChunk` objects.

    Each page is chunked independently so that page-number metadata stays
    accurate (a chunk never spans two pages).
    """
    splitter = build_splitter()
    chunks: list[DocumentChunk] = []
    global_index = 0

    for page in pages:
        cleaned = clean_text(page.text)
        if not cleaned:
            continue

        page_chunks = splitter.split_text(cleaned)
        for text in page_chunks:
            if not text.strip():
                continue
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                document_name=document_name,
                text=text.strip(),
                page_number=page.page_number,
                chunk_index=global_index,
            )
            chunks.append(chunk)
            global_index += 1

    return chunks
