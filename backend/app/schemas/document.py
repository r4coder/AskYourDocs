"""Pydantic request/response models for document endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Metadata describing a single uploaded document."""

    document_id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Original file name as uploaded")
    file_type: str = Field(..., description="File extension, e.g. '.pdf' or '.txt'")
    num_chunks: int = Field(..., description="Number of chunks the document was split into")
    num_pages: int | None = Field(None, description="Number of pages, if applicable (PDF only)")
    uploaded_at: datetime = Field(..., description="UTC timestamp of upload")


class DocumentUploadResponse(BaseModel):
    """Response returned after a successful document upload."""

    document: DocumentInfo
    message: str = "Document uploaded and indexed successfully."


class DocumentListResponse(BaseModel):
    """Response returned when listing all uploaded documents."""

    documents: list[DocumentInfo]
    total: int
