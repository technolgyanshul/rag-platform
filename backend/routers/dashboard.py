from fastapi import APIRouter
from pydantic import BaseModel

from db.supabase import SupabaseRepository


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class QueriesOverTimePoint(BaseModel):
    date: str
    count: int


class DashboardMetricsResponse(BaseModel):
    total_queries: int
    average_response_time_ms: int
    average_overall_score: float
    queries_over_time: list[QueriesOverTimePoint]


@router.get("/metrics", response_model=DashboardMetricsResponse)
def dashboard_metrics(session_id: str, days: int = 7) -> DashboardMetricsResponse:
    repository = SupabaseRepository()
    payload = repository.list_dashboard_metrics(session_id=session_id, days=days)
    return DashboardMetricsResponse(**payload)
