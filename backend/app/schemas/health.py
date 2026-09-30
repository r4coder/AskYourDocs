"""Pydantic response model for the health check endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_model: str
    embedding_model: str
    api_key_required: bool = Field(
        ..., description="True if visitors must supply their own Gemini API key"
    )
    active_sessions: int
