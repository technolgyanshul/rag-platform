"""Session endpoints for creation, listing, detail, and export."""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

import observability
from core.auth import AuthUser, get_current_user
from db.supabase import SupabaseRepository


router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    """Payload for creating a session."""
    title: str | None = Field(default=None, max_length=200)
    team_id: UUID | None = None


class SessionResponse(BaseModel):
    """Minimal session creation response payload."""
    id: str
    team_id: str
    title: str | None = None
    created_at: str


class SessionListItem(BaseModel):
    """Session list row returned by `/sessions`."""
    id: str
    team_id: str
    team_name: str | None = None
    title: str | None = None
    created_at: str
    query_count: int
    last_query_at: str | None = None


class SessionMessageItem(BaseModel):
    """Serialized chat message attached to a session."""
    id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class SessionScorecardItem(BaseModel):
    """Scorecard metadata associated with one query in a session."""
    id: str
    session_id: str
    query_id: str | None = None
    overall_quality: int | None = None
    citation_accuracy: int | None = None
    insight_depth: int | None = None
    model_contribution_breakdown: dict[str, Any]
    notes: str | None = None
    created_at: str


class SessionAgentTraceItem(BaseModel):
    """Serialized per-agent execution trace for one query."""
    id: str
    session_id: str
    query_id: str | None = None
    agent_id: str | None = None
    agent_name: str
    agent_role: str
    model_provider: str
    model_name: str
    input: dict[str, Any]
    output: str
    citations: list[dict[str, Any]]
    latency_ms: int | None = None
    status: str
    error: str | None = None
    created_at: str


class SessionQueryItem(BaseModel):
    """Full persisted query record embedded in session detail/export."""
    id: str
    session_id: str
    query_text: str
    final_answer: str | None = None
    overall_score: float | None = None
    citation_accuracy: float | None = None
    insight_depth: float | None = None
    response_time_ms: int | None = None
    created_at: str
    sources: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    retrieval_metadata: dict[str, Any]
    model_version: str | None = None
    insufficient_context: bool
    scorecard: SessionScorecardItem | None = None
    agent_traces: list[SessionAgentTraceItem]


class SessionDetail(BaseModel):
    """Top-level session metadata for detail/export responses."""
    id: str
    team_id: str
    team_name: str | None = None
    title: str | None = None
    created_at: str


class SessionDetailResponse(BaseModel):
    """Session detail payload with messages and query timeline."""
    session: SessionDetail
    messages: list[SessionMessageItem]
    queries: list[SessionQueryItem]


class SessionExportResponse(BaseModel):
    """Portable JSON export payload shape for a session."""
    exported_at: str
    schema_version: str
    session: SessionDetail
    messages: list[SessionMessageItem]
    queries: list[SessionQueryItem]


@router.post(
    "",
    response_model=SessionResponse,
    responses={
        403: {"description": "Forbidden"},
        503: {"description": "Session service temporarily unavailable"},
    },
)
async def create_session(
    payload: CreateSessionRequest,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> SessionResponse:
    """Create a new session for the authenticated user."""
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        row = repository.create_session(
            user_id=auth_user.user_id,
            title=payload.title,
            team_id=str(payload.team_id) if payload.team_id else None,
        )
        observer.record_trace_event(
            event_name="session_created",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions",
            component="sessions_router",
            metadata={"session": row, "team_id": str(payload.team_id) if payload.team_id else None, "title": payload.title},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="session_create_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions",
            component="sessions_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception(
            "session_create_failed",
            extra={"request_id": request_id, "user_id": auth_user.user_id},
        )
        observer.record_trace_event(
            event_name="session_create_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions",
            component="sessions_router",
            level="ERROR",
            status="failed",
            metadata={"team_id": str(payload.team_id) if payload.team_id else None, "title": payload.title},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Session service temporarily unavailable") from error

    return SessionResponse(
        id=str(row.get("id", "")),
        team_id=str(row.get("team_id", "")),
        title=row.get("title"),
        created_at=str(row.get("created_at", "")),
    )


@router.get(
    "",
    response_model=list[SessionListItem],
    responses={
        503: {"description": "Session list temporarily unavailable"},
    },
)
async def list_sessions(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> list[SessionListItem]:
    """List sessions for the authenticated user."""
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        rows = repository.list_sessions(user_id=auth_user.user_id)
        observer.record_trace_event(
            event_name="session_list_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions",
            component="sessions_router",
            metadata={"row_count": len(rows)},
        )
        return [SessionListItem(**row) for row in rows]
    except Exception as error:
        logger.exception(
            "session_list_failed",
            extra={"request_id": request_id, "user_id": auth_user.user_id},
        )
        observer.record_trace_event(
            event_name="session_list_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions",
            component="sessions_router",
            level="ERROR",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=503, detail="Session list temporarily unavailable") from error


@router.get(
    "/{session_id}/export.json",
    response_model=SessionExportResponse,
    responses={
        403: {"description": "Forbidden"},
        503: {"description": "Session export temporarily unavailable"},
    },
)
async def export_session_json(
    session_id: UUID,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> JSONResponse:
    """Export one session as downloadable JSON."""
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        detail = repository.get_session_detail(user_id=auth_user.user_id, session_id=str(session_id))
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "session-export-v1",
            "session": detail["session"],
            "messages": detail["messages"],
            "queries": detail["queries"],
        }
        observer.record_trace_event(
            event_name="session_export_ready",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}/export.json",
            component="sessions_router",
            metadata={"session_id": str(session_id), "query_count": len(detail.get("queries", []))},
        )
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="session-{session_id}.json"'},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="session_export_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}/export.json",
            component="sessions_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception(
            "session_export_failed",
            extra={"request_id": request_id, "user_id": auth_user.user_id, "session_id": str(session_id)},
        )
        observer.record_trace_event(
            event_name="session_export_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}/export.json",
            component="sessions_router",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(session_id)},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Session export temporarily unavailable") from error


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    responses={
        403: {"description": "Forbidden"},
        503: {"description": "Session detail temporarily unavailable"},
    },
)
async def get_session_detail(
    session_id: UUID,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> SessionDetailResponse:
    """Return full detail for one session."""
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        detail = repository.get_session_detail(user_id=auth_user.user_id, session_id=str(session_id))
        observer.record_trace_event(
            event_name="session_detail_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}",
            component="sessions_router",
            metadata={"session_id": str(session_id), "query_count": len(detail.get("queries", []))},
        )
        return SessionDetailResponse(**detail)
    except PermissionError as error:
        observer.record_trace_event(
            event_name="session_detail_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}",
            component="sessions_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception(
            "session_detail_failed",
            extra={"request_id": request_id, "user_id": auth_user.user_id, "session_id": str(session_id)},
        )
        observer.record_trace_event(
            event_name="session_detail_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/sessions/{session_id}",
            component="sessions_router",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(session_id)},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Session detail temporarily unavailable") from error
