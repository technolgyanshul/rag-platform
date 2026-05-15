from __future__ import annotations
"""CORS origin parsing with safe defaults for credentialed requests."""

import os


def get_cors_origins() -> list[str]:
    """Return normalized allowed origins from `CORS_ALLOWED_ORIGINS`."""
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:3000"]
    if "*" in origins:
        raise ValueError("CORS_ALLOWED_ORIGINS cannot include '*' when credentials are enabled")
    return origins
