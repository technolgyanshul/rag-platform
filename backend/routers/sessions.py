import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import observability
from core.auth import AuthUser, get_current_user
from db.supabase import SupabaseRepository


router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    team_id: UUID | None = None


class SessionResponse(BaseModel):
    id: str
    team_id: str
    title: str | None = None
    created_at: str


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
