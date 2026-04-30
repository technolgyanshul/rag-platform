import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

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
def dashboard_metrics(
    request: Request,
    session_id: str = Query(..., min_length=1, max_length=128),
    days: int = Query(get_settings().dashboard_days_default, ge=1, le=get_settings().dashboard_days_max),
) -> DashboardMetricsResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    repository = SupabaseRepository()
    try:
        payload = repository.list_dashboard_metrics(session_id=session_id, days=days)
    except Exception as error:
        logger.exception("dashboard_metrics_request_failed", extra={"request_id": request_id, "session_id": session_id, "days": days})
        raise HTTPException(status_code=503, detail="Dashboard metrics temporarily unavailable") from error
    return DashboardMetricsResponse(**payload)
