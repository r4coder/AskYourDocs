"""
Shared pytest fixtures.

`FakeEmbeddingService` is a lightweight stand-in for the real Gemini
embedding backend so API-level tests run offline and fast (no network). It
records the API key it was called with, so tests can verify that per-request
keys are passed through.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np
import pytest

SESSION_ID = "test-session-0000000000000001"
OTHER_SESSION_ID = "test-session-0000000000000002"


class FakeEmbeddingService:
    """Deterministic bag-of-words hashing embeddings (lexical overlap => similarity)."""

    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        self.model_name = "fake-hash-embedding"
        self.last_api_key: str | None = None

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype="float32")
        for word in re.findall(r"\w+", text.lower()):
            idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dimension
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed_texts(self, texts: list[str], api_key: str | None = None) -> np.ndarray:
        self.last_api_key = api_key
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")
        return np.stack([self._embed_one(t) for t in texts]).astype("float32")

    def embed_query(self, query: str, api_key: str | None = None) -> np.ndarray:
        return self.embed_texts([query], api_key=api_key)


@pytest.fixture
def fake_embeddings() -> FakeEmbeddingService:
    return FakeEmbeddingService()


@pytest.fixture
def session_manager(fake_embeddings):
    """Install a SessionManager backed by the fake embedding service."""
    from app.services.session_manager import SessionManager

    manager = SessionManager(embedding_service=fake_embeddings)
    SessionManager._instance = manager
    yield manager
    SessionManager._instance = None
