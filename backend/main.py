import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.health import router as health_router
from routers.ingest import router as ingest_router
from routers.query import router as query_router


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


configure_logging()


app = FastAPI(title="Multi-Agent RAG Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
