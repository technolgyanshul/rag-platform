from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

import observability
from core.auth import AuthUser, get_current_user


router = APIRouter(prefix="/observability", tags=["observability"])
logger = logging.getLogger(__name__)


class UiEventRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    page: str = Field(default="", max_length=300)
    component: str = Field(default="", max_length=120)
    action: str = Field(default="", max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    client_timestamp: str = Field(default="", max_length=80)
    browser: dict[str, Any] = Field(default_factory=dict)


@router.post("/ui-events", status_code=status.HTTP_202_ACCEPTED)
async def record_ui_event(
    payload: UiEventRequest,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    ) -> dict[str, bool]:
    request_id = getattr(request.state, "request_id", request.headers.get("x-request-id", ""))
    try:
        observability.get_observability().record_ui_event(
            user_id=auth_user.user_id,
            request_id=request_id,
            event_name=payload.event_name,
            page=payload.page,
            component=payload.component,
            action=payload.action,
            payload=payload.payload,
            client_timestamp=payload.client_timestamp,
            browser=payload.browser,
        )
    except Exception as error:
        logger.exception("ui_event_observability_write_failed", extra={"request_id": request_id, "user_id": auth_user.user_id})
        raise HTTPException(status_code=503, detail="Observability temporarily unavailable") from error
    return {"accepted": True}
