import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

import observability
from core.cors import get_cors_origins
from core.config import get_settings
from routers.dashboard import router as dashboard_router
from routers.health import router as health_router
from routers.ingest import router as ingest_router
from routers.observability import router as observability_router
from routers.query import router as query_router
from routers.sessions import router as sessions_router
from routers.teams import router as teams_router


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


configure_logging()


class RequestIdObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._header(scope, "x-request-id") or str(uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        started_at = time.perf_counter()
        observer = observability.get_observability()
        route = str(scope.get("path", ""))
        metadata = {
            "method": str(scope.get("method", "")),
            "path": route,
            "query_params": {},
            "headers": self._headers_dict(scope),
            "client": scope["client"][0] if scope.get("client") else "",
        }
        observer.record_trace_event(
            event_name="http_request_started",
            request_id=request_id,
            route=route,
            component="fastapi",
            metadata=metadata,
        )

        status_code = "500"

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 500))
                headers = MutableHeaders(raw=message["headers"])
                headers.append("x-request-id", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
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

        observer.record_trace_event(
            event_name="http_request_finished",
            request_id=request_id,
            route=route,
            component="fastapi",
            status=status_code,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            metadata=metadata,
        )

    @staticmethod
    def _header(scope: Scope, name: str) -> str | None:
        target = name.lower().encode()
        for key, value in scope.get("headers", []):
            if key.lower() == target:
                return value.decode("latin-1")
        return None

    @staticmethod
    def _headers_dict(scope: Scope) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            headers[key.decode("latin-1")] = value.decode("latin-1")
        return headers


@asynccontextmanager
async def lifespan(app: FastAPI):
    observability.get_observability().initialize()
    yield


app = FastAPI(title="Multi-Agent RAG Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestIdObservabilityMiddleware)

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
app.include_router(teams_router)
