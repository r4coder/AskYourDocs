"""
Central application configuration — Gemini-only build.

Google's Gemini API is used for BOTH steps of the RAG pipeline: turning text
into vectors (embeddings) and writing the final answer (generation). Both use
the SAME API key, so this app only ever needs one key, from one place:
https://aistudio.google.com/apikey

All values are sourced from environment variables (see `.env.example`).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
DOCUMENTS_DIR = DATA_DIR / "documents"
INDEX_DIR = DATA_DIR / "index"

try:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
except OSError:  # read-only filesystems (some hosts) — the web app doesn't need these
    pass


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Typed accessor for environment-driven configuration."""

    # --- Gemini API ------------------------------------------------------------
    # Leave blank to make visitors enter their own key on the app's first page
    # (bring-your-own-key — the right choice for a public deployment). Set it
    # here only for a single-user/local setup, or if you intend to pay for
    # everyone's usage on a public deployment.
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    )
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.8-flash")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    llm_max_tokens: int = _get_int("LLM_MAX_TOKENS", 1000)
    llm_temperature: float = _get_float("LLM_TEMPERATURE", 0.0)

    # --- Chunking settings -----------------------------------------------------
    chunk_size: int = _get_int("CHUNK_SIZE", 800)
    chunk_overlap: int = _get_int("CHUNK_OVERLAP", 150)

    # --- Retrieval settings ------------------------------------------------------
    top_k: int = _get_int("TOP_K", 4)
    min_similarity: float = _get_float("MIN_SIMILARITY", 0.2)

    # --- Upload validation --------------------------------------------------------
    max_file_size_mb: int = _get_int("MAX_FILE_SIZE_MB", 20)
    allowed_extensions: tuple[str, ...] = (".pdf", ".txt")

    # --- Public-deployment limits (per visitor session) -----------------------------
    session_ttl_minutes: int = _get_int("SESSION_TTL_MINUTES", 120)
    max_sessions: int = _get_int("MAX_SESSIONS", 100)
    max_documents_per_session: int = _get_int("MAX_DOCUMENTS_PER_SESSION", 10)

    # --- CORS / static frontend --------------------------------------------------------
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    frontend_dist_dir: str = os.getenv("FRONTEND_DIST_DIR", str(PROJECT_ROOT / "frontend" / "dist"))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
