"""
Retrieval service: question -> embedding -> FAISS similarity search -> top-K chunks.

A minimum similarity threshold filters weak matches so the LLM isn't fed
irrelevant context when the documents genuinely don't contain an answer.
"""
from __future__ import annotations

from app.config import settings
from app.models.chunk import RetrievedChunk
from app.services.document_service import DocumentService


def retrieve_relevant_chunks(
    service: DocumentService,
    question: str,
    top_k: int | None = None,
    api_key: str | None = None,
) -> list[RetrievedChunk]:
    """Embed the question and return the most similar chunks from this session's documents."""
    k = top_k or settings.top_k
    query_embedding = service.embedding_service.embed_query(question, api_key=api_key)
    results = service.vector_store.search(query_embedding, top_k=k)
    return [r for r in results if r.similarity_score >= settings.min_similarity]
