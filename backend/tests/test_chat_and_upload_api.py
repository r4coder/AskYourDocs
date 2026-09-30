"""
API integration tests for upload and chat.

The embedding backend is faked and the LLM call is mocked, so these run
offline. They focus on the API contract: validation, per-session isolation,
per-request key handling, and citation shape.
"""
from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app
from app.models.chunk import RetrievedChunk
from app.services.embedding_service import GeminiEmbeddingService
from app.services.session_manager import SessionManager
from tests.conftest import OTHER_SESSION_ID, SESSION_ID

client = TestClient(app, headers={"X-Session-ID": SESSION_ID})
other_client = TestClient(app, headers={"X-Session-ID": OTHER_SESSION_ID})


def upload(c, name="database.txt", content=b"The company uses PostgreSQL for storing application data.", **kw):
    return c.post(
        "/api/documents/upload",
        files={"file": (name, io.BytesIO(content), "text/plain")},
        **kw,
    )


class TestSessions:
    def test_missing_session_header_is_rejected(self, session_manager):
        response = TestClient(app).get("/api/documents")
        assert response.status_code == 400
        assert "X-Session-ID" in response.json()["detail"]

    def test_malformed_session_id_is_rejected(self, session_manager):
        response = TestClient(app, headers={"X-Session-ID": "short"}).get("/api/documents")
        assert response.status_code == 400

    def test_sessions_are_isolated(self, session_manager):
        assert upload(client).status_code == 201
        assert client.get("/api/documents").json()["total"] == 1
        assert other_client.get("/api/documents").json()["total"] == 0
        response = other_client.post("/api/chat", json={"question": "What database is used?"})
        assert response.status_code == 422


class TestUploadEndpoint:
    def test_upload_txt_succeeds(self, session_manager):
        response = upload(client)
        assert response.status_code == 201
        doc = response.json()["document"]
        assert doc["filename"] == "database.txt"
        assert doc["num_chunks"] >= 1

    def test_upload_empty_file_returns_422(self, session_manager):
        assert upload(client, content=b"").status_code == 422

    def test_upload_unsupported_type_returns_422(self, session_manager):
        assert upload(client, name="notes.docx", content=b"bytes").status_code == 422

    def test_oversized_file_returns_422(self, session_manager, monkeypatch):
        monkeypatch.setattr("app.services.document_service.settings.max_file_size_mb", 0)
        monkeypatch.setattr("app.api.documents.settings.max_file_size_mb", 0)
        assert upload(client).status_code == 422

    def test_document_limit_per_session(self, session_manager, monkeypatch):
        monkeypatch.setattr("app.services.document_service.settings.max_documents_per_session", 1)
        assert upload(client, name="a.txt").status_code == 201
        second = upload(client, name="b.txt")
        assert second.status_code == 422
        assert "at most" in second.json()["detail"]

    def test_list_documents_after_upload(self, session_manager):
        upload(client, name="arch.txt")
        data = client.get("/api/documents").json()
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "arch.txt"

    def test_gemini_key_header_is_forwarded(self, session_manager, fake_embeddings):
        upload(client, headers={"X-Gemini-API-Key": "user-gemini-key"})
        assert fake_embeddings.last_api_key == "user-gemini-key"

    def test_missing_key_returns_clear_400(self, monkeypatch):
        monkeypatch.setattr("app.services.embedding_service.settings.gemini_api_key", "")
        SessionManager._instance = SessionManager(embedding_service=GeminiEmbeddingService())
        try:
            response = upload(client)
        finally:
            SessionManager._instance = None
        assert response.status_code == 400
        assert "Gemini API key" in response.json()["detail"]


def _stored_chunk(session_manager):
    return session_manager.get(SESSION_ID).vector_store.chunks[0]


class TestChatEndpoint:
    def test_chat_without_documents_returns_422(self, session_manager):
        response = client.post("/api/chat", json={"question": "What database is used?"})
        assert response.status_code == 422

    def test_blank_question_returns_422(self, session_manager):
        upload(client)
        assert client.post("/api/chat", json={"question": "   "}).status_code == 422

    def test_grounded_answer_with_sources(self, session_manager, monkeypatch):
        upload(client)
        chunk = _stored_chunk(session_manager)
        monkeypatch.setattr(
            "app.api.chat.retrieve_relevant_chunks",
            lambda *a, **k: [RetrievedChunk(chunk=chunk, similarity_score=0.9)],
        )
        monkeypatch.setattr(
            "app.api.chat.generate_answer",
            lambda question, chunks, **kw: "The company uses PostgreSQL for storing application data.",
        )
        response = client.post("/api/chat", json={"question": "What database is used?"})
        assert response.status_code == 200
        data = response.json()
        assert "PostgreSQL" in data["answer"]
        assert data["grounded"] is True
        assert data["sources"][0]["document_name"] == "database.txt"

    def test_no_relevant_chunks_is_not_grounded(self, session_manager, monkeypatch):
        upload(client, name="cooking.txt", content=b"A recipe for baking sourdough bread.")
        monkeypatch.setattr("app.api.chat.retrieve_relevant_chunks", lambda *a, **k: [])
        data = client.post("/api/chat", json={"question": "Capital of France?"}).json()
        assert data["grounded"] is False
        assert data["sources"] == []
        assert "couldn't find enough information" in data["answer"]

    def test_key_header_is_forwarded_to_embedding_and_llm(self, session_manager, monkeypatch):
        upload(client)
        chunk = _stored_chunk(session_manager)
        seen = {}

        def fake_retrieve(service, question, top_k=None, api_key=None):
            seen["embedding_key"] = api_key
            return [RetrievedChunk(chunk=chunk, similarity_score=0.9)]

        def fake_generate(question, chunks, **kw):
            seen["llm_key"] = kw.get("api_key_override")
            return "An answer."

        monkeypatch.setattr("app.api.chat.retrieve_relevant_chunks", fake_retrieve)
        monkeypatch.setattr("app.api.chat.generate_answer", fake_generate)

        client.post(
            "/api/chat",
            json={"question": "What database is used?"},
            headers={"X-Gemini-API-Key": "user-gemini-key"},
        )
        assert seen["embedding_key"] == "user-gemini-key"
        assert seen["llm_key"] == "user-gemini-key"

    def test_missing_key_returns_400(self, session_manager, monkeypatch):
        upload(client)
        chunk = _stored_chunk(session_manager)
        monkeypatch.setattr(
            "app.api.chat.retrieve_relevant_chunks",
            lambda *a, **k: [RetrievedChunk(chunk=chunk, similarity_score=0.9)],
        )
        monkeypatch.setattr("app.services.llm_service.settings.gemini_api_key", "")
        response = client.post("/api/chat", json={"question": "What database is used?"})
        assert response.status_code == 400
        assert "Gemini API key" in response.json()["detail"]
