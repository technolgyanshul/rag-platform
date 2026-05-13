import time

from fastapi import APIRouter

import observability


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    started_at = time.perf_counter()
    observability.get_observability().record_infra_check(
        service="backend",
        status="ok",
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        metadata={"endpoint": "/health"},
    )
    return {"status": "ok"}
