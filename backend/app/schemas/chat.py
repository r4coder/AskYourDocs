"""Pydantic request/response models for the chat (Q&A) endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """A user's question about the uploaded documents."""

    question: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    top_k: int | None = Field(
        None, ge=1, le=20, description="Override the number of chunks to retrieve"
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be empty or whitespace only.")
        return value.strip()


class SourceReference(BaseModel):
    """A single citation pointing back to the source document chunk."""

    document_name: str
    page_number: int | None = None
    chunk_id: str
    snippet: str = Field(..., description="Short excerpt of the chunk used as evidence")
    similarity_score: float = Field(..., description="Cosine similarity score (higher is closer)")


class ChatResponse(BaseModel):
    """The generated answer along with the sources that back it up."""

    answer: str
    sources: list[SourceReference]
    grounded: bool = Field(
        ..., description="False when no relevant context was found in the documents"
    )
