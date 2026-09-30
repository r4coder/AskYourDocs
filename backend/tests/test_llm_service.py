"""
Tests for the Gemini LLM service: key resolution and grounded/ungrounded
behavior. The actual HTTP call is mocked (via monkeypatched httpx.post), so
these run offline.
"""
from __future__ import annotations

import pytest

from app.models.chunk import DocumentChunk, RetrievedChunk
from app.services.llm_service import (
    NO_ANSWER_MESSAGE,
    LLMAuthError,
    LLMConfigError,
    LLMServiceError,
    _resolve_api_key,
    generate_answer,
)


def make_chunk() -> RetrievedChunk:
    chunk = DocumentChunk(
        chunk_id="c1", document_id="d1", document_name="doc.txt",
        text="PostgreSQL is the primary database.", page_number=1, chunk_index=0,
    )
    return RetrievedChunk(chunk=chunk, similarity_score=0.9)


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


def _ok_payload(text="The system uses PostgreSQL."):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


class TestResolveApiKey:
    def test_override_wins(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "server-key")
        assert _resolve_api_key("user-key") == "user-key"

    def test_falls_back_to_server_key(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "server-key")
        assert _resolve_api_key(None) == "server-key"

    def test_raises_when_neither_is_set(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "")
        with pytest.raises(LLMConfigError):
            _resolve_api_key(None)

    def test_blank_override_falls_back(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "server-key")
        assert _resolve_api_key("   ") == "server-key"


class TestGenerateAnswer:
    def test_no_chunks_returns_no_answer_message_without_a_call(self):
        assert generate_answer("q", [], api_key_override="k") == NO_ANSWER_MESSAGE

    def test_successful_call_returns_text(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_service.httpx.post", lambda *a, **k: _FakeResponse(_ok_payload())
        )
        answer = generate_answer("What database?", [make_chunk()], api_key_override="k")
        assert answer == "The system uses PostgreSQL."

    def test_request_uses_x_goog_api_key_header_and_model_url(self, monkeypatch):
        seen = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            seen["url"] = url
            seen["headers"] = headers
            seen["json"] = json
            return _FakeResponse(_ok_payload())

        monkeypatch.setattr("app.services.llm_service.httpx.post", fake_post)
        monkeypatch.setattr("app.services.llm_service.settings.llm_model", "gemini-3.8-flash")
        generate_answer("What database?", [make_chunk()], api_key_override="my-key")

        assert seen["headers"]["x-goog-api-key"] == "my-key"
        assert seen["url"].endswith("models/gemini-3.8-flash:generateContent")
        assert "PostgreSQL is the primary database." in seen["json"]["contents"][0]["parts"][0]["text"]

    def test_missing_key_raises_config_error(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "")
        with pytest.raises(LLMConfigError):
            generate_answer("q", [make_chunk()])

    def test_rejected_key_raises_auth_error(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_service.httpx.post",
            lambda *a, **k: _FakeResponse({"error": {"message": "bad key"}}, 401),
        )
        with pytest.raises(LLMAuthError):
            generate_answer("q", [make_chunk()], api_key_override="wrong")

    def test_safety_block_raises_clear_error(self, monkeypatch):
        payload = {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
        monkeypatch.setattr(
            "app.services.llm_service.httpx.post", lambda *a, **k: _FakeResponse(payload)
        )
        with pytest.raises(LLMServiceError, match="SAFETY"):
            generate_answer("q", [make_chunk()], api_key_override="k")
