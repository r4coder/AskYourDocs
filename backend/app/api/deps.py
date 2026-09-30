"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.services.document_service import DocumentService
from app.services.session_manager import InvalidSessionIdError, SessionManager


def get_document_service(
    x_session_id: str | None = Header(
        default=None,
        alias="X-Session-ID",
        description="Random per-browser id. Each id gets its own private document store.",
    ),
) -> DocumentService:
    """Resolve the calling visitor's private DocumentService from the session header."""
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-ID header.")
    try:
        return SessionManager.get_instance().get(x_session_id)
    except InvalidSessionIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
