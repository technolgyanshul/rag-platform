from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import AuthUser, get_current_user
from core.model_registry import ModelValidationError, default_model_selection, validate_model_selection
from db.supabase import SupabaseRepository


router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str | None = Field(default=None, max_length=200)


class TeamPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    domain: str | None = Field(default=None, max_length=200)


class TeamResponse(BaseModel):
    id: str
    user_id: str
    name: str
    domain: str | None = None
    created_at: str


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(min_length=1)
    model_provider: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    response_style: str | None = Field(default=None, max_length=120)
    execution_order: int = Field(default=0, ge=0, le=20)


class AgentPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=80)
    system_prompt: str | None = Field(default=None, min_length=1)
    model_provider: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    response_style: str | None = Field(default=None, max_length=120)
    execution_order: int | None = Field(default=None, ge=0, le=20)


class AgentResponse(BaseModel):
    id: str
    team_id: str
    name: str
    role: str
    system_prompt: str
    model_provider: str
    model_name: str
    response_style: str | None = None
    execution_order: int
    created_at: str


def _normalize_team_payload(row: dict[str, Any]) -> TeamResponse:
    return TeamResponse(
        id=str(row.get("id", "")),
        user_id=str(row.get("user_id", "")),
        name=str(row.get("name", "")),
        domain=row.get("domain"),
        created_at=str(row.get("created_at", "")),
    )


def _normalize_agent_payload(row: dict[str, Any]) -> AgentResponse:
    return AgentResponse(
        id=str(row.get("id", "")),
        team_id=str(row.get("team_id", "")),
        name=str(row.get("name", "")),
        role=str(row.get("role", "")),
        system_prompt=str(row.get("system_prompt", "")),
        model_provider=str(row.get("model_provider", "")),
        model_name=str(row.get("model_name", "")),
        response_style=row.get("response_style"),
        execution_order=int(row.get("execution_order", 0)),
        created_at=str(row.get("created_at", "")),
    )


def _ensure_owned_team(repository: SupabaseRepository, user_id: str, team_id: str) -> dict[str, Any]:
    try:
        row = repository.get_team(user_id=user_id, team_id=team_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return row


@router.get("", response_model=list[TeamResponse], responses={503: {"description": "Team service temporarily unavailable"}})
async def list_teams(auth_user: AuthUser = Depends(get_current_user)) -> list[TeamResponse]:
    try:
        rows = SupabaseRepository().list_teams(user_id=auth_user.user_id)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Team service temporarily unavailable") from error
    return [_normalize_team_payload(row) for row in rows]


@router.post("", response_model=TeamResponse, responses={400: {"description": "Validation failed"}, 503: {"description": "Team service temporarily unavailable"}})
async def create_team(payload: TeamCreateRequest, auth_user: AuthUser = Depends(get_current_user)) -> TeamResponse:
    try:
        row = SupabaseRepository().create_team(user_id=auth_user.user_id, name=payload.name, domain=payload.domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Team service temporarily unavailable") from error
    return _normalize_team_payload(row)


@router.get("/{team_id}", response_model=TeamResponse, responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Team service temporarily unavailable"}})
async def get_team(team_id: str, auth_user: AuthUser = Depends(get_current_user)) -> TeamResponse:
    repository = SupabaseRepository()
    try:
        row = _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Team service temporarily unavailable") from error
    return _normalize_team_payload(row)


@router.patch("/{team_id}", response_model=TeamResponse, responses={400: {"description": "Validation failed"}, 403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Team service temporarily unavailable"}})
async def patch_team(team_id: str, payload: TeamPatchRequest, auth_user: AuthUser = Depends(get_current_user)) -> TeamResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field is required")

    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    try:
        row = repository.update_team(user_id=auth_user.user_id, team_id=team_id, **updates)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Team service temporarily unavailable") from error
    return _normalize_team_payload(row)


@router.delete("/{team_id}", responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Team service temporarily unavailable"}})
async def delete_team(team_id: str, auth_user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    try:
        repository.delete_team(user_id=auth_user.user_id, team_id=team_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Team service temporarily unavailable") from error
    return {"ok": True}


@router.get("/{team_id}/agents", response_model=list[AgentResponse], responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Agent service temporarily unavailable"}})
async def list_agents(team_id: str, auth_user: AuthUser = Depends(get_current_user)) -> list[AgentResponse]:
    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    try:
        rows = repository.list_agents(user_id=auth_user.user_id, team_id=team_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable") from error
    return [_normalize_agent_payload(row) for row in rows]


@router.post("/{team_id}/agents", response_model=AgentResponse, responses={400: {"description": "Validation failed"}, 403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Agent service temporarily unavailable"}})
async def create_agent(team_id: str, payload: AgentCreateRequest, auth_user: AuthUser = Depends(get_current_user)) -> AgentResponse:
    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)

    default = default_model_selection()
    provider = payload.model_provider or default.provider
    model_name = payload.model_name or default.model_name

    try:
        selection = validate_model_selection(provider=provider, model_name=model_name)
    except ModelValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        row = repository.create_agent(
            user_id=auth_user.user_id,
            team_id=team_id,
            name=payload.name,
            role=payload.role,
            system_prompt=payload.system_prompt,
            model_provider=selection.provider,
            model_name=selection.model_name,
            response_style=payload.response_style or "balanced",
            execution_order=payload.execution_order,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable") from error
    return _normalize_agent_payload(row)


@router.patch("/{team_id}/agents/{agent_id}", response_model=AgentResponse, responses={400: {"description": "Validation failed"}, 403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Agent service temporarily unavailable"}})
async def patch_agent(team_id: str, agent_id: str, payload: AgentPatchRequest, auth_user: AuthUser = Depends(get_current_user)) -> AgentResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field is required")

    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    current = repository.get_agent(user_id=auth_user.user_id, team_id=team_id, agent_id=agent_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "model_provider" in updates or "model_name" in updates:
        provider = str(updates.get("model_provider", current.get("model_provider", "")))
        model_name = str(updates.get("model_name", current.get("model_name", "")))
        try:
            selection = validate_model_selection(provider=provider, model_name=model_name)
        except ModelValidationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        updates["model_provider"] = selection.provider
        updates["model_name"] = selection.model_name

    try:
        row = repository.update_agent(user_id=auth_user.user_id, team_id=team_id, agent_id=agent_id, **updates)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable") from error
    return _normalize_agent_payload(row)


@router.delete("/{team_id}/agents/{agent_id}", responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}, 503: {"description": "Agent service temporarily unavailable"}})
async def delete_agent(team_id: str, agent_id: str, auth_user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    repository = SupabaseRepository()
    _ensure_owned_team(repository=repository, user_id=auth_user.user_id, team_id=team_id)
    current = repository.get_agent(user_id=auth_user.user_id, team_id=team_id, agent_id=agent_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        repository.delete_agent(user_id=auth_user.user_id, team_id=team_id, agent_id=agent_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable") from error
    return {"ok": True}
