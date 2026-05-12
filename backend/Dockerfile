# syntax=docker/dockerfile:1

# ── stage 1: dependency installation ──────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# ── stage 2: test runner ───────────────────────────────────────────────────────
FROM deps AS test

WORKDIR /app

# pre-download both embedding models during build so tests run fully offline
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
SentenceTransformer('BAAI/bge-base-en-v1.5')"

COPY main.py .
COPY llms/ ./llms/
COPY core/ ./core/
COPY db/ ./db/
COPY rag/ ./rag/
COPY routers/ ./routers/
COPY tests/ ./tests/

ENV TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

CMD ["pytest", "-q", "--tb=short"]

# ── stage 3: production image ──────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

RUN groupadd --system app && \
    useradd --system --gid app --home-dir /home/app --create-home app && \
    mkdir -p /home/app/.cache && \
    chown -R app:app /app /home/app

ENV HOME=/home/app \
    XDG_CACHE_HOME=/home/app/.cache

# copy installed packages from deps stage (avoids re-downloading)
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# only copy application source, not tests/docs
COPY --chown=app:app main.py .
COPY --chown=app:app llms/ ./llms/
COPY --chown=app:app core/ ./core/
COPY --chown=app:app db/ ./db/
COPY --chown=app:app rag/ ./rag/
COPY --chown=app:app routers/ ./routers/

USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
