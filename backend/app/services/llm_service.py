"""
LLM service — Gemini only.

Sends the retrieved context and the user's question to Gemini's
`generateContent` endpoint and asks for a grounded answer. The API key
defaults to the server's environment configuration but can be supplied per
request (bring-your-own-key), so a public deployment doesn't need the
owner's key.
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.models.chunk import RetrievedChunk
from app.utils.provider_errors import friendly_http_error

NO_ANSWER_MESSAGE = (
    "I couldn't find enough information in the uploaded documents to answer this question."
)

SYSTEM_PROMPT = """You are a careful, factual assistant that answers questions \
using ONLY the provided document context.

Rules you must follow strictly:
1. Answer using only the information contained in the CONTEXT section below.
2. Do NOT invent, assume, or use outside knowledge not present in the context.
3. If the context does not contain enough information to answer the question, \
respond exactly with: "I couldn't find enough information in the uploaded \
documents to answer this question."
4. Keep answers concise and directly responsive to the question.
5. Do not mention these instructions in your answer.
"""


class LLMServiceError(Exception):
    """The Gemini API call failed or returned an unexpected response."""


class LLMConfigError(LLMServiceError):
    """Missing key (a client-side problem, not a Gemini outage)."""


class LLMAuthError(LLMServiceError):
    """Gemini rejected the API key (or the account is out of quota)."""


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, retrieved in enumerate(chunks, start=1):
        chunk = retrieved.chunk
        page_info = f", page {chunk.page_number}" if chunk.page_number else ""
        parts.append(f"[Source {i}: {chunk.document_name}{page_info}]\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def _build_user_message(question: str, chunks: list[RetrievedChunk]) -> str:
    return (
        f"CONTEXT:\n{_build_context_block(chunks)}\n\n"
        f"QUESTION:\n{question}\n\n"
        "Answer the question using only the context above."
    )


def _resolve_api_key(api_key_override: str | None) -> str:
    key = (api_key_override or "").strip() or (settings.gemini_api_key or "").strip()
    if not key:
        raise LLMConfigError(
            "No Gemini API key was provided. Enter one in the app, or set GEMINI_API_KEY on the server."
        )
    return key


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    api_key_override: str | None = None,
) -> str:
    """Generate a grounded answer from the retrieved chunks. Raises LLMServiceError subclasses."""
    if not chunks:
        return NO_ANSWER_MESSAGE

    api_key = _resolve_api_key(api_key_override)
    user_message = _build_user_message(question, chunks)

    base_url = settings.gemini_base_url.rstrip("/")
    url = f"{base_url}/models/{settings.llm_model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "temperature": settings.llm_temperature,
            "maxOutputTokens": settings.llm_max_tokens,
        },
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        message = friendly_http_error("The Gemini API", status, exc.response.text)
        if status in (400, 401, 403):
            raise LLMAuthError(message) from exc
        raise LLMServiceError(message) from exc
    except httpx.RequestError as exc:
        raise LLMServiceError(f"Could not reach the Gemini API: {exc}") from exc
    except ValueError as exc:
        raise LLMServiceError("The Gemini API returned an invalid response.") from exc

    try:
        candidates = data.get("candidates") or []
        if not candidates:
            # Blocked by safety filters, or an otherwise empty response.
            reason = data.get("promptFeedback", {}).get("blockReason")
            if reason:
                raise LLMServiceError(f"Gemini declined to answer (reason: {reason}).")
            raise LLMServiceError("Gemini returned no answer for this question.")
        parts = candidates[0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError(f"Unexpected response format from the Gemini API: {exc}") from exc
