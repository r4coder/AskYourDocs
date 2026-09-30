"""
End-to-end test over real HTTP against a local mock Gemini server.

Unlike the other API tests, nothing inside the app is faked here: the real
GeminiEmbeddingService and real llm_service make real HTTP requests to a
small server started on localhost, in the actual Gemini request/response
shape. This proves the whole bring-your-own-key flow works end to end, and
that only retrieved context (not the whole document) reaches the model.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.embedding_service import GeminiEmbeddingService
from app.services.session_manager import SessionManager
from tests.conftest import SESSION_ID

DIM = 768


def _hash_embedding(text: str) -> list[float]:
    vec = [0.0] * DIM
    for word in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, status: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        auth = self.headers.get("x-goog-api-key", "")
        self.server.calls.append({"path": self.path, "auth": auth, "body": body})

        if auth == "bad-key":
            return self._send(401, {"error": {"message": "API key not valid"}})

        if self.path.endswith(":batchEmbedContents"):
            values = [
                {"values": _hash_embedding(r["content"]["parts"][0]["text"])} for r in body["requests"]
            ]
            return self._send(200, {"embeddings": values})
        if self.path.endswith(":generateContent"):
            return self._send(
                200, {"candidates": [{"content": {"parts": [{"text": "The system uses PostgreSQL."}]}}]}
            )
        self._send(404, {"error": "unknown path"})


@pytest.fixture
def mock_gemini(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.calls = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/v1beta"

    # The server has NO key of its own: visitors must bring theirs.
    e, l = "app.services.embedding_service.settings", "app.services.llm_service.settings"
    monkeypatch.setattr(f"{e}.gemini_api_key", "")
    monkeypatch.setattr(f"{e}.gemini_base_url", base)
    monkeypatch.setattr(f"{l}.gemini_api_key", "")
    monkeypatch.setattr(f"{l}.gemini_base_url", base)
    monkeypatch.setattr(f"{l}.llm_model", "gemini-3.8-flash")

    SessionManager._instance = SessionManager(embedding_service=GeminiEmbeddingService())
    yield server
    SessionManager._instance = None
    server.shutdown()
    server.server_close()


client = TestClient(app, headers={"X-Session-ID": SESSION_ID})
DOC = b"PostgreSQL is the primary database. The frontend uses React."
QUESTION = "Which database is the primary database?"


def _calls(server, suffix):
    return [c for c in server.calls if c["path"].endswith(suffix)]


def test_full_flow_uses_visitor_key_for_both_steps(mock_gemini):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("architecture.txt", io.BytesIO(DOC), "text/plain")},
        headers={"X-Gemini-API-Key": "visitor-key"},
    )
    assert response.status_code == 201
    assert _calls(mock_gemini, ":batchEmbedContents")[0]["auth"] == "visitor-key"

    response = client.post(
        "/api/chat", json={"question": QUESTION}, headers={"X-Gemini-API-Key": "visitor-key"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["answer"] == "The system uses PostgreSQL."
    assert data["grounded"] is True
    assert data["sources"][0]["document_name"] == "architecture.txt"

    assert all(c["auth"] == "visitor-key" for c in mock_gemini.calls)
    gen_call = _calls(mock_gemini, ":generateContent")[0]
    prompt = gen_call["body"]["contents"][0]["parts"][0]["text"]
    assert "PostgreSQL is the primary database" in prompt
    assert QUESTION in prompt
    assert "React" in prompt  # both chunks of this short doc are retrieved


def test_rejected_key_gives_friendly_401(mock_gemini):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("a.txt", io.BytesIO(DOC), "text/plain")},
        headers={"X-Gemini-API-Key": "bad-key"},
    )
    assert response.status_code == 401
    assert "rejected the API key" in response.json()["detail"]


def test_no_key_anywhere_gives_clear_400(mock_gemini):
    response = client.post(
        "/api/documents/upload", files={"file": ("a.txt", io.BytesIO(DOC), "text/plain")}
    )
    assert response.status_code == 400
    assert "Gemini API key" in response.json()["detail"]
