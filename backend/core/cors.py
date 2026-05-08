from __future__ import annotations

import os


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:3000"]
    if "*" in origins:
        raise ValueError("CORS_ALLOWED_ORIGINS cannot include '*' when credentials are enabled")
    return origins
