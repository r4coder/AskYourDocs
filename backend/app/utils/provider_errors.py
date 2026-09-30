"""Turn raw provider HTTP errors into short, user-friendly messages."""
from __future__ import annotations


def friendly_http_error(service_label: str, status_code: int, body: str) -> str:
    if status_code in (401, 403):
        return (
            f"{service_label} rejected the API key. Check that the key is correct "
            "and that the account has credit."
        )
    if status_code == 429:
        return (
            f"{service_label} rate-limited this request, or the account is out of credit. "
            "Check billing and try again shortly."
        )
    snippet = " ".join((body or "").split())[:300]
    return f"{service_label} returned an error ({status_code}): {snippet}"
