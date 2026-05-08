# syntax=docker/dockerfile:1

# ── stage 1: dependency installation ──────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# ── stage 2: production image ──────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

# copy installed packages from deps stage (avoids re-downloading)
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# only copy application source, not tests/docs
COPY main.py .
COPY agents/ ./agents/
COPY llms/ ./llms/
COPY core/ ./core/
COPY db/ ./db/
COPY orchestration/ ./orchestration/
COPY prompts/ ./prompts/
COPY rag/ ./rag/
COPY routers/ ./routers/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
