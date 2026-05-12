import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

import observability
from core.auth import AuthUser, get_current_user
from core.config import get_settings
from db.supabase import SupabaseRepository


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


class QueriesOverTimePoint(BaseModel):
    date: str
    count: int


class DashboardMetricsResponse(BaseModel):
    total_queries: int
    average_response_time_ms: int
    average_overall_score: float
    queries_over_time: list[QueriesOverTimePoint]


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def dashboard_metrics(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    session_id: UUID = Query(...),
    days: int = Query(get_settings().dashboard_days_default, ge=1, le=get_settings().dashboard_days_max),
) -> DashboardMetricsResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        payload = repository.list_dashboard_metrics(session_id=str(session_id), user_id=auth_user.user_id, days=days)
        observer.record_trace_event(
            event_name="dashboard_metrics_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/dashboard/metrics",
            component="dashboard_router",
            metadata={"session_id": str(session_id), "days": days, "metrics": payload},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="dashboard_metrics_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/dashboard/metrics",
            component="dashboard_router",
            level="WARNING",
            status="failed",
            metadata={"session_id": str(session_id), "days": days},
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("dashboard_metrics_request_failed", extra={"request_id": request_id, "session_id": str(session_id), "days": days})
        observer.record_trace_event(
            event_name="dashboard_metrics_request_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/dashboard/metrics",
            component="dashboard_router",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(session_id), "days": days},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Dashboard metrics temporarily unavailable") from error
    return DashboardMetricsResponse(**payload)
