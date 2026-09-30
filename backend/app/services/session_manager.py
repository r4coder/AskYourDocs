"""
Session manager: one isolated `DocumentService` per visitor.

The browser generates a random session id and sends it as `X-Session-ID`.
Each id maps to its own in-memory FAISS index, so visitors cannot see or
search each other's documents. Sessions expire after a period of inactivity,
and the total number of sessions is capped (least-recently-used are evicted),
which bounds memory use on a public server.
"""
from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from typing import Callable

from app.config import settings
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService, GeminiEmbeddingService

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


class InvalidSessionIdError(ValueError):
    """The supplied session id is malformed."""


class SessionManager:
    _instance: "SessionManager | None" = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        embedding_service: GeminiEmbeddingService | None = None,
        ttl_seconds: float | None = None,
        max_sessions: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._embedding_service = embedding_service or EmbeddingService.get_instance()
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.session_ttl_minutes * 60
        self.max_sessions = max_sessions if max_sessions is not None else settings.max_sessions
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: OrderedDict[str, tuple[DocumentService, float]] = OrderedDict()

    @classmethod
    def get_instance(cls) -> "SessionManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def peek_active_sessions(cls) -> int:
        """Active session count without creating the manager (or loading any model)."""
        return cls._instance.active_sessions() if cls._instance else 0

    def get(self, session_id: str) -> DocumentService:
        """Return this visitor's DocumentService, creating it on first use."""
        if not SESSION_ID_PATTERN.match(session_id or ""):
            raise InvalidSessionIdError(
                "Invalid X-Session-ID header (expected 16-64 letters, digits, '-' or '_')."
            )
        with self._lock:
            now = self._clock()
            self._evict_expired(now)
            entry = self._sessions.get(session_id)
            if entry is None:
                while len(self._sessions) >= self.max_sessions:
                    self._sessions.popitem(last=False)  # least recently used
                service = DocumentService(embedding_service=self._embedding_service, persist=False)
            else:
                service = entry[0]
            self._sessions[session_id] = (service, now)
            self._sessions.move_to_end(session_id)
            return service

    def active_sessions(self) -> int:
        with self._lock:
            self._evict_expired(self._clock())
            return len(self._sessions)

    def _evict_expired(self, now: float) -> None:
        expired = [sid for sid, (_, last) in self._sessions.items() if now - last > self.ttl_seconds]
        for sid in expired:
            del self._sessions[sid]
