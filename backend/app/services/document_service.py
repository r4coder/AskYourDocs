"""
Document service.

Holds one visitor's documents and runs the ingestion pipeline:

    upload bytes -> extract text -> chunk -> embed (Gemini) -> store in FAISS

In the web app each visitor session gets its own `DocumentService`
(`persist=False`: memory only, nothing written to disk), so visitors can
never see each other's documents.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import DOCUMENTS_DIR, settings
from app.models.chunk import DocumentRecord
from app.services.chunking_service import chunk_document
from app.services.embedding_service import EmbeddingService, GeminiEmbeddingService
from app.services.vector_store import VectorStore
from app.utils.text_extraction import TextExtractionError, extract_text


class DocumentValidationError(Exception):
    """Raised when an uploaded file fails validation checks."""


class DocumentService:
    def __init__(self, embedding_service: GeminiEmbeddingService | None = None, persist: bool = True):
        """`embedding_service` can be injected (tests, or a shared instance across sessions)."""
        self.persist = persist
        self._registry_lock = threading.Lock()
        self.documents: dict[str, DocumentRecord] = {}
        self.embedding_service = embedding_service or EmbeddingService.get_instance()
        self.vector_store = VectorStore(dimension=self.embedding_service.dimension, persist=persist)
        if persist:
            self._rebuild_registry_from_store()

    def _rebuild_registry_from_store(self) -> None:
        """Rebuild the document registry from persisted chunk metadata after a restart."""
        by_document: dict[str, list] = {}
        for chunk in self.vector_store.chunks:
            by_document.setdefault(chunk.document_id, []).append(chunk)

        for document_id, chunks in by_document.items():
            page_numbers = {c.page_number for c in chunks if c.page_number is not None}
            self.documents[document_id] = DocumentRecord(
                document_id=document_id,
                filename=chunks[0].document_name,
                file_type=Path(chunks[0].document_name).suffix.lower(),
                num_chunks=len(chunks),
                num_pages=max(page_numbers) if page_numbers else None,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                chunk_ids=[c.chunk_id for c in chunks],
            )

    # -- Validation ------------------------------------------------------------------

    def validate_upload(self, filename: str, raw_bytes: bytes) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in settings.allowed_extensions:
            raise DocumentValidationError(
                f"Unsupported file type '{suffix}'. Allowed types: "
                f"{', '.join(settings.allowed_extensions)}."
            )
        if len(raw_bytes) == 0:
            raise DocumentValidationError("The uploaded file is empty.")
        if len(raw_bytes) > settings.max_file_size_bytes:
            raise DocumentValidationError(
                f"File exceeds the maximum allowed size of {settings.max_file_size_mb} MB."
            )
        if len(self.documents) >= settings.max_documents_per_session:
            raise DocumentValidationError(
                f"You can upload at most {settings.max_documents_per_session} documents per session."
            )

    # -- Ingestion ---------------------------------------------------------------------

    def ingest_document(
        self,
        filename: str,
        raw_bytes: bytes,
        api_key: str | None = None,
    ) -> DocumentRecord:
        """Run the full ingestion pipeline for one uploaded file."""
        filename = Path(filename).name
        self.validate_upload(filename, raw_bytes)

        try:
            pages = extract_text(filename, raw_bytes)
        except TextExtractionError as exc:
            raise DocumentValidationError(str(exc)) from exc

        document_id = str(uuid.uuid4())
        chunks = chunk_document(document_id, filename, pages)
        if not chunks:
            raise DocumentValidationError(
                "No usable text could be extracted from this document after cleaning."
            )

        # May raise EmbeddingError subclasses (missing/rejected key, API failure).
        embeddings = self.embedding_service.embed_texts([c.text for c in chunks], api_key=api_key)
        self.vector_store.add(embeddings, chunks)

        if self.persist:
            (DOCUMENTS_DIR / f"{document_id}_{filename}").write_bytes(raw_bytes)

        page_numbers = {c.page_number for c in chunks if c.page_number is not None}
        record = DocumentRecord(
            document_id=document_id,
            filename=filename,
            file_type=Path(filename).suffix.lower(),
            num_chunks=len(chunks),
            num_pages=max(page_numbers) if page_numbers else None,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            chunk_ids=[c.chunk_id for c in chunks],
        )
        with self._registry_lock:
            self.documents[document_id] = record
        return record

    # -- Read access ----------------------------------------------------------------------

    def list_documents(self) -> list[DocumentRecord]:
        with self._registry_lock:
            return sorted(self.documents.values(), key=lambda d: d.uploaded_at, reverse=True)

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def total_chunks(self) -> int:
        return self.vector_store.total_chunks
