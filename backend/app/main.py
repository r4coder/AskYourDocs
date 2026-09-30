"""
AI Document Q&A — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

If a built frontend exists (`frontend/dist`), it is served from the same
process, so the whole app deploys as a single service.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents, health
from app.config import settings
from app.services.session_manager import SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the embedding backend at startup so misconfiguration (e.g. the local
    # provider without PyTorch installed) fails immediately, not on first request.
    SessionManager.get_instance()
    yield


app = FastAPI(
    title="AI Document Q&A",
    description=(
        "A Retrieval-Augmented Generation (RAG) API that lets users upload "
        "PDF/TXT documents and ask grounded, cited questions about them."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(health.router)

_dist = Path(settings.frontend_dist_dir)
if (_dist / "index.html").exists():
    # Registered last so /api/* and /docs keep priority over the static catch-all.
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
else:

    @app.get("/", tags=["root"], summary="API root")
    async def root():
        return {
            "message": "AI Document Q&A API is running.",
            "docs": "/docs",
            "health": "/api/health",
        }
