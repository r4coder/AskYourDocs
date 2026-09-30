"""API routes for document upload and listing (scoped to the caller's session)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_document_service
from app.config import settings
from app.schemas.document import DocumentInfo, DocumentListResponse, DocumentUploadResponse
from app.services.document_service import DocumentService, DocumentValidationError
from app.services.embedding_service import (
    EmbeddingAuthError,
    EmbeddingError,
    EmbeddingKeyMissingError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _to_document_info(record) -> DocumentInfo:
    return DocumentInfo(
        document_id=record.document_id,
        filename=record.filename,
        file_type=record.file_type,
        num_chunks=record.num_chunks,
        num_pages=record.num_pages,
        uploaded_at=record.uploaded_at,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or TXT document to be indexed for Q&A",
)
async def upload_document(
    file: UploadFile,
    service: DocumentService = Depends(get_document_service),
    x_gemini_api_key: str | None = Header(
        default=None,
        alias="X-Gemini-API-Key",
        description="Optional per-request Gemini key used to embed the document. Never stored.",
    ),
) -> DocumentUploadResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file name provided.")

    # Read at most limit+1 bytes so an oversized upload can't exhaust memory.
    raw_bytes = await file.read(settings.max_file_size_bytes + 1)

    try:
        # Ingestion does blocking work (parsing, embedding HTTP calls) — keep it off the event loop.
        record = await run_in_threadpool(
            service.ingest_document, file.filename, raw_bytes, x_gemini_api_key
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingKeyMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmbeddingAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected failure safety net
        logger.exception("Unexpected error while processing upload")
        raise HTTPException(status_code=500, detail="Failed to process the document.") from exc

    return DocumentUploadResponse(document=_to_document_info(record))


@router.get("", response_model=DocumentListResponse, summary="List the caller's uploaded documents")
async def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    documents = [_to_document_info(r) for r in service.list_documents()]
    return DocumentListResponse(documents=documents, total=len(documents))
