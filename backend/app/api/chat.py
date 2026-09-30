"""API route for asking questions about the caller's uploaded documents."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import get_document_service
from app.schemas.chat import ChatRequest, ChatResponse, SourceReference
from app.services.document_service import DocumentService
from app.services.embedding_service import (
    EmbeddingAuthError,
    EmbeddingError,
    EmbeddingKeyMissingError,
)
from app.services.llm_service import (
    NO_ANSWER_MESSAGE,
    LLMAuthError,
    LLMConfigError,
    LLMServiceError,
    generate_answer,
)
from app.services.retrieval_service import retrieve_relevant_chunks

router = APIRouter(prefix="/api/chat", tags=["chat"])


# A plain `def` (not `async def`): FastAPI runs it in a worker thread, so the
# blocking embedding/LLM HTTP calls don't freeze the server for other visitors.
@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about the uploaded documents",
)
def ask_question(
    request: ChatRequest,
    service: DocumentService = Depends(get_document_service),
    x_gemini_api_key: str | None = Header(
        default=None,
        alias="X-Gemini-API-Key",
        description="Optional per-request Gemini key used for search and answering. Never stored.",
    ),
) -> ChatResponse:
    if service.total_documents == 0:
        raise HTTPException(
            status_code=422,
            detail="No documents have been uploaded yet. Upload a document before asking questions.",
        )

    try:
        retrieved = retrieve_relevant_chunks(
            service, request.question, top_k=request.top_k, api_key=x_gemini_api_key
        )
    except EmbeddingKeyMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmbeddingAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not retrieved:
        return ChatResponse(answer=NO_ANSWER_MESSAGE, sources=[], grounded=False)

    try:
        answer = generate_answer(request.question, retrieved, api_key_override=x_gemini_api_key)
    except LLMConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    is_grounded = answer.strip() != NO_ANSWER_MESSAGE
    sources = (
        [
            SourceReference(
                document_name=r.chunk.document_name,
                page_number=r.chunk.page_number,
                chunk_id=r.chunk.chunk_id,
                snippet=(r.chunk.text[:220] + "...") if len(r.chunk.text) > 220 else r.chunk.text,
                similarity_score=round(r.similarity_score, 4),
            )
            for r in retrieved
        ]
        if is_grounded
        else []
    )
    return ChatResponse(answer=answer, sources=sources, grounded=is_grounded)
