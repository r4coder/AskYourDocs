"""
Internal (non-API) data models used to move data through the RAG pipeline.

These are plain dataclasses rather than Pydantic models because they are
never serialized directly over the API boundary — they are the internal
"currency" passed between the extraction, chunking, embedding, and
retrieval services.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    """A single chunk of text extracted from a document, with metadata."""

    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_number: int | None = None
    chunk_index: int = 0

    def to_metadata_dict(self) -> dict:
        """Serializable metadata used when persisting the FAISS index."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "text": self.text,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
        }

    @classmethod
    def from_metadata_dict(cls, data: dict) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            document_name=data["document_name"],
            text=data["text"],
            page_number=data.get("page_number"),
            chunk_index=data.get("chunk_index", 0),
        )


@dataclass
class RetrievedChunk:
    """A chunk returned from similarity search, paired with its score."""

    chunk: DocumentChunk
    similarity_score: float


@dataclass
class DocumentRecord:
    """Metadata about an uploaded document, tracked in memory."""

    document_id: str
    filename: str
    file_type: str
    num_chunks: int
    num_pages: int | None
    uploaded_at: str
    chunk_ids: list[str] = field(default_factory=list)
