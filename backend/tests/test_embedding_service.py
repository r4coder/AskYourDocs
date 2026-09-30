"""
Tests for the Gemini embedding backend. Fully offline: the HTTP call is
mocked, so no network access or API key is needed to run this file.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.embedding_service import (
    BATCH_SIZE,
    EmbeddingAuthError,
    EmbeddingError,
    EmbeddingKeyMissingError,
    GeminiEmbeddingService,
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._payload


def _payload(vectors: list[list[float]]) -> dict:
    return {"embeddings": [{"values": v} for v in vectors]}


@pytest.fixture
def no_server_key(monkeypatch):
    monkeypatch.setattr("app.services.embedding_service.settings.gemini_api_key", "")


@pytest.fixture
def service():
    return GeminiEmbeddingService(model_name="gemini-embedding-001")


class TestGeminiEmbeddingService:
    def test_constructing_without_a_key_is_fine(self, no_server_key):
        # The server must start even when visitors are expected to bring their own key.
        assert GeminiEmbeddingService(model_name="gemini-embedding-001").dimension == 768

    def test_embedding_without_a_key_raises_clear_error(self, service, no_server_key):
        with pytest.raises(EmbeddingKeyMissingError):
            service.embed_texts(["hello"])

    def test_output_dimensionality_is_requested_explicitly(self, service, monkeypatch):
        # gemini-embedding-001 defaults to 3072-dim output; without requesting
        # 768 explicitly, vectors would silently mismatch self.dimension.
        seen = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            seen["requests"] = json["requests"]
            return _FakeResponse(_payload([[1.0] + [0.0] * 767]))

        monkeypatch.setattr("app.services.embedding_service.httpx.post", fake_post)
        service.embed_texts(["hello"], api_key="k")
        assert seen["requests"][0]["outputDimensionality"] == 768

    def test_per_call_key_is_sent_as_header(self, service, no_server_key, monkeypatch):
        seen = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            seen["header"] = headers["x-goog-api-key"]
            seen["url"] = url
            return _FakeResponse(_payload([[1.0] + [0.0] * 767]))

        monkeypatch.setattr("app.services.embedding_service.httpx.post", fake_post)
        service.embed_texts(["hello"], api_key="user-key")
        assert seen["header"] == "user-key"
        assert seen["url"].endswith("models/gemini-embedding-001:batchEmbedContents")

    def test_vectors_are_normalized(self, service, no_server_key, monkeypatch):
        vectors = [[3.0, 4.0] + [0.0] * 766, [1.0, 0.0] + [0.0] * 766]
        monkeypatch.setattr(
            "app.services.embedding_service.httpx.post", lambda *a, **k: _FakeResponse(_payload(vectors))
        )
        out = service.embed_texts(["a", "b"], api_key="k")
        assert out.shape == (2, 768)
        assert abs(np.linalg.norm(out[0]) - 1.0) < 1e-5

    def test_empty_input_returns_empty_array(self, service):
        assert service.embed_texts([]).shape == (0, 768)

    def test_large_inputs_are_sent_in_batches(self, service, monkeypatch):
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            calls.append(len(json["requests"]))
            return _FakeResponse(_payload([[1.0] + [0.0] * 767] * len(json["requests"])))

        monkeypatch.setattr("app.services.embedding_service.httpx.post", fake_post)
        out = service.embed_texts(["t"] * (BATCH_SIZE * 2 + 5), api_key="k")
        assert calls == [BATCH_SIZE, BATCH_SIZE, 5]
        assert out.shape[0] == BATCH_SIZE * 2 + 5

    def test_rejected_key_raises_auth_error(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.embedding_service.httpx.post",
            lambda *a, **k: _FakeResponse({"error": "bad key"}, 401),
        )
        with pytest.raises(EmbeddingAuthError):
            service.embed_texts(["hello"], api_key="wrong")

    def test_wrong_dimension_is_reported(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.embedding_service.httpx.post",
            lambda *a, **k: _FakeResponse(_payload([[1.0, 0.0]])),
        )
        with pytest.raises(EmbeddingError):
            service.embed_texts(["hello"], api_key="k")
