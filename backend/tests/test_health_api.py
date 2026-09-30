"""Tests for the /api/health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_expected_shape(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        for field in ("llm_model", "embedding_model", "api_key_required", "active_sessions"):
            assert field in data

    def test_health_does_not_need_a_session(self):
        assert client.get("/api/health").status_code == 200

    def test_key_required_reflects_server_key(self, monkeypatch):
        monkeypatch.setattr("app.services.embedding_service.settings.gemini_api_key", "")
        assert client.get("/api/health").json()["api_key_required"] is True
        monkeypatch.setattr("app.services.embedding_service.settings.gemini_api_key", "server-key")
        assert client.get("/api/health").json()["api_key_required"] is False

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
