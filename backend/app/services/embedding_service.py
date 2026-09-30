"""
Embedding service — Gemini only.

Calls Gemini's `batchEmbedContents` endpoint, which embeds many texts in
one HTTP request. The API key can come from the server's environment OR be
supplied per request (bring-your-own-key), which is how a public deployment
works without the owner paying for everyone's usage.
"""
from __future__ import annotations

import threading

import httpx
import numpy as np

from app.config import settings
from app.utils.provider_errors import friendly_http_error

# Gemini's batchEmbedContents accepts up to 100 requests per call.
BATCH_SIZE = 100

# gemini-embedding-001 supports 3072, 1536, or 768 output dimensions via
# Matryoshka Representation Learning (MRL) truncation. 768 keeps the FAISS
# index small with minimal quality loss and matches what the older,
# now-retired text-embedding-004 model produced by default.
DEFAULT_OUTPUT_DIMENSION = 768

# Fallback sizes if an unrecognized model name is configured (used only to
# validate responses; the actual dimension always comes from the real reply).
_KNOWN_DIMENSIONS = {
    "gemini-embedding-001": DEFAULT_OUTPUT_DIMENSION,
    # text-embedding-004 was retired by Google on 2026-01-14; kept here only
    # so old configs fail with a clear model-not-found error from Gemini
    # rather than a confusing local one.
    "text-embedding-004": 768,
}


class EmbeddingError(RuntimeError):
    """The embedding backend failed."""


class EmbeddingKeyMissingError(EmbeddingError):
    """No Gemini API key was available for this request."""


class EmbeddingAuthError(EmbeddingError):
    """Gemini rejected the API key (or the account is out of quota)."""


class GeminiEmbeddingService:
    """Calls the Gemini embeddings API. The key is resolved per call."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        output_dimension: int | None = None,
    ):
        self.model_name = model_name or settings.embedding_model
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.dimension = (
            output_dimension
            or _KNOWN_DIMENSIONS.get(self.model_name)
            or DEFAULT_OUTPUT_DIMENSION
        )

    @staticmethod
    def server_key() -> str:
        """The key configured on the server, if any (used when a request supplies none)."""
        return (settings.gemini_api_key or "").strip()

    def _resolve_key(self, api_key: str | None) -> str:
        key = (api_key or "").strip() or self.server_key()
        if not key:
            raise EmbeddingKeyMissingError(
                "A Gemini API key is required to embed documents. Enter it in the app "
                "(or set GEMINI_API_KEY on the server)."
            )
        return key

    def embed_texts(self, texts: list[str], api_key: str | None = None) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        key = self._resolve_key(api_key)
        batches = [
            self._embed_batch(texts[start : start + BATCH_SIZE], key)
            for start in range(0, len(texts), BATCH_SIZE)
        ]
        matrix = np.vstack(batches).astype("float32")

        if matrix.shape[1] != self.dimension:
            raise EmbeddingError(
                f"Model '{self.model_name}' returned {matrix.shape[1]}-dimensional vectors "
                f"but {self.dimension} were expected."
            )

        # Normalize so FAISS inner product behaves like cosine similarity.
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (matrix / norms).astype("float32")

    def embed_query(self, query: str, api_key: str | None = None) -> np.ndarray:
        return self.embed_texts([query], api_key=api_key)

    def _embed_batch(self, batch: list[str], key: str) -> np.ndarray:
        url = f"{self.base_url}/models/{self.model_name}:batchEmbedContents"
        model_path = f"models/{self.model_name}"
        payload = {
            "requests": [
                {
                    "model": model_path,
                    "content": {"parts": [{"text": text}]},
                    # Without this, gemini-embedding-001 returns 3072-dim vectors
                    # by default; we ask for the smaller size explicitly so it
                    # matches self.dimension and keeps the FAISS index compact.
                    "outputDimensionality": self.dimension,
                }
                for text in batch
            ]
        }
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            message = friendly_http_error("The Gemini embeddings API", status, exc.response.text)
            if status in (400, 401, 403):
                raise EmbeddingAuthError(message) from exc
            raise EmbeddingError(message) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(f"Could not reach the Gemini API: {exc}") from exc
        except ValueError as exc:
            raise EmbeddingError("The Gemini API returned an invalid response.") from exc

        try:
            return np.array([e["values"] for e in data["embeddings"]], dtype="float32")
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Unexpected response format from the Gemini API.") from exc


class EmbeddingService:
    """Process-wide singleton holding the Gemini embedding backend."""

    _instance: GeminiEmbeddingService | None = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> GeminiEmbeddingService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = GeminiEmbeddingService()
        return cls._instance


def embedding_key_required() -> bool:
    """True when visitors must supply their own Gemini key (server has none)."""
    return not GeminiEmbeddingService.server_key()
