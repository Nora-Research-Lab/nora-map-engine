"""Fetch datasets registered by public URL (including raw Hugging Face file URLs)."""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.utils.errors import DatasetTooLargeError, RemoteFetchError

ALLOWED_SCHEMES = ("https://", "http://")


def fetch_url(url: str) -> bytes:
    if not url.startswith(ALLOWED_SCHEMES):
        raise RemoteFetchError("Only http(s) URLs are supported.")

    settings = get_settings()
    limit_bytes = settings.max_upload_mb * 1024 * 1024

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as resp:
            resp.raise_for_status()
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > limit_bytes:
                raise DatasetTooLargeError(settings.max_upload_mb)

            chunks = bytearray()
            for chunk in resp.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > limit_bytes:
                    raise DatasetTooLargeError(settings.max_upload_mb)
            return bytes(chunks)
    except httpx.HTTPError as exc:
        raise RemoteFetchError() from exc
