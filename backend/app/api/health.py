"""API route for the health check endpoint (cheap: never loads a model)."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas.health import HealthResponse
from app.services.embedding_service import embedding_key_required
from app.services.session_manager import SessionManager

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Health check and setup requirements")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        api_key_required=embedding_key_required(),
        active_sessions=SessionManager.peek_active_sessions(),
    )
