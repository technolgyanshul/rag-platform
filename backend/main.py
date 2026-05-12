import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

import observability
from core.cors import get_cors_origins
from core.config import get_settings
from routers.dashboard import router as dashboard_router
from routers.health import router as health_router
from routers.ingest import router as ingest_router
from routers.observability import router as observability_router
from routers.query import router as query_router
from routers.sessions import router as sessions_router


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    observability.get_observability().initialize()
    yield


app = FastAPI(title="Multi-Agent RAG Backend", version="0.1.0", lifespan=lifespan)

cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(sessions_router)
app.include_router(dashboard_router)
app.include_router(observability_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    observer = observability.get_observability()
    route = request.url.path
    metadata = {
        "method": request.method,
        "path": route,
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "client": request.client.host if request.client else "",
    }
    observer.record_trace_event(
        event_name="http_request_started",
        request_id=request_id,
        route=route,
        component="fastapi",
        metadata=metadata,
    )
    try:
        response = await call_next(request)
    except Exception as error:
        observer.record_trace_event(
            event_name="http_request_failed",
            request_id=request_id,
            route=route,
            component="fastapi",
            level="ERROR",
            status="exception",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            metadata=metadata,
            error=error,
        )
        raise
    response.headers["x-request-id"] = request_id
    observer.record_trace_event(
        event_name="http_request_finished",
        request_id=request_id,
        route=route,
        component="fastapi",
        status=str(response.status_code),
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        metadata=metadata,
    )
    return response
