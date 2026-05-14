from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import AuthUser, get_current_user
from core.model_registry import ModelValidationError, default_model_selection, model_catalog, validate_model_selection
from db.supabase import SupabaseRepository, default_team_agents
from llms.lmstudio_client import LMStudioClient, LMStudioError


router = APIRouter(prefix="/teams", tags=["teams"])
_COLLABORATION_RULES = {"sequential", "debate", "hierarchical"}


class ModelsResponse(BaseModel):
    groq: list[str]
    sarvam: list[str]
    lmstudio: list[str]


class LMStudioProbeRequest(BaseModel):
    base_url: str = Field(min_length=1, max_length=500)
    passcode: str | None = Field(default=None, max_length=500)
    timeout_seconds: float = Field(default=10, ge=1, le=120)


class LMStudioHealthResponse(BaseModel):
    ok: bool
    models_count: int


class LMStudioModelsResponse(BaseModel):
    models: list[str]


class AgentDefaultsResponse(BaseModel):
    agents: list[AgentResponse]


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str | None = Field(default=None, max_length=200)
    collaboration_rule: str = Field(default="sequential", min_length=1, max_length=32)


class TeamPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    domain: str | None = Field(default=None, max_length=200)
    collaboration_rule: str | None = Field(default=None, min_length=1, max_length=32)


class TeamResponse(BaseModel):
    id: str
    user_id: str
    name: str
    domain: str | None = None
    collaboration_rule: str
    created_at: str


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(min_length=1)
    model_provider: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    provider_base_url: str | None = Field(default=None, max_length=500)
    provider_passcode: str | None = Field(default=None, max_length=500)
    response_style: str | None = Field(default=None, max_length=120)
    execution_order: int = Field(default=0, ge=0, le=20)


class AgentPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=80)
    system_prompt: str | None = Field(default=None, min_length=1)
    model_provider: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    provider_base_url: str | None = Field(default=None, max_length=500)
    provider_passcode: str | None = Field(default=None, max_length=500)
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
    provider_base_url: str | None = None
    provider_passcode_configured: bool = False
    response_style: str | None = None
    execution_order: int
    created_at: str


def _normalize_team_payload(row: dict[str, Any]) -> TeamResponse:
    return TeamResponse(
        id=str(row.get("id", "")),
        user_id=str(row.get("user_id", "")),
        name=str(row.get("name", "")),
        domain=row.get("domain"),
        collaboration_rule=str(row.get("collaboration_rule", "sequential")),
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
        provider_base_url=row.get("provider_base_url"),
        provider_passcode_configured=bool(row.get("provider_passcode")),
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


def _normalize_collaboration_rule(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _COLLABORATION_RULES:
        raise HTTPException(status_code=400, detail="Unsupported collaboration_rule")
    return normalized


@router.get("/models", response_model=ModelsResponse, responses={503: {"description": "Model catalog temporarily unavailable"}})
async def list_models(_auth_user: AuthUser = Depends(get_current_user)) -> ModelsResponse:
    try:
        catalog = model_catalog()
        return ModelsResponse(**catalog)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Model catalog temporarily unavailable") from error


def _lmstudio_http_error(error: LMStudioError) -> HTTPException:
    details = {"category": error.category, "message": error.message}
    if error.category in {"invalid_config", "malformed_response"}:
        return HTTPException(status_code=400, detail=details)
    if error.category == "auth_rejection":
        return HTTPException(status_code=401, detail=details)
    if error.category == "unreachable_server":
        return HTTPException(status_code=503, detail=details)
    if error.category == "timeout":
        return HTTPException(status_code=504, detail=details)
    if error.category == "model_missing":
        return HTTPException(status_code=404, detail=details)
    return HTTPException(status_code=502, detail=details)


@router.post("/lmstudio/health", response_model=LMStudioHealthResponse)
async def lmstudio_health_probe(payload: LMStudioProbeRequest, _auth_user: AuthUser = Depends(get_current_user)) -> LMStudioHealthResponse:
    try:
        result = LMStudioClient().health(
            base_url=payload.base_url,
            passcode=payload.passcode,
            timeout_seconds=payload.timeout_seconds,
        )
    except LMStudioError as error:
        raise _lmstudio_http_error(error) from error
    return LMStudioHealthResponse(**result)


@router.post("/lmstudio/models", response_model=LMStudioModelsResponse)
async def lmstudio_model_probe(payload: LMStudioProbeRequest, _auth_user: AuthUser = Depends(get_current_user)) -> LMStudioModelsResponse:
    try:
        models = LMStudioClient().list_models(
            base_url=payload.base_url,
            passcode=payload.passcode,
            timeout_seconds=payload.timeout_seconds,
        )
    except LMStudioError as error:
        raise _lmstudio_http_error(error) from error
    return LMStudioModelsResponse(models=models)


@router.get(
    "/defaults/agents",
    response_model=AgentDefaultsResponse,
    responses={503: {"description": "Agent defaults temporarily unavailable"}},
)
async def list_agent_defaults(_auth_user: AuthUser = Depends(get_current_user)) -> AgentDefaultsResponse:
    try:
        defaults = default_team_agents()
        rows: list[AgentResponse] = []
        for template in defaults:
            rows.append(
                AgentResponse(
                    id="",
                    team_id="",
                    name=str(template["name"]),
                    role=str(template["role"]),
                    system_prompt=str(template["system_prompt"]),
                    model_provider="",
                    model_name="",
                    provider_base_url=None,
                    provider_passcode_configured=False,
                    response_style=str(template["response_style"]),
                    execution_order=int(template["execution_order"]),
                    created_at="",
                )
            )
        return AgentDefaultsResponse(agents=rows)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Agent defaults temporarily unavailable") from error


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
        row = SupabaseRepository().create_team(
            user_id=auth_user.user_id,
            name=payload.name.strip(),
            domain=payload.domain.strip() if isinstance(payload.domain, str) else None,
            collaboration_rule=_normalize_collaboration_rule(payload.collaboration_rule),
        )
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
    if "collaboration_rule" in updates:
        updates["collaboration_rule"] = _normalize_collaboration_rule(str(updates["collaboration_rule"]))

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

    if selection.provider == "lmstudio" and not (payload.provider_base_url or "").strip():
        raise HTTPException(status_code=400, detail="LM Studio provider requires provider_base_url")

    try:
        row = repository.create_agent(
            user_id=auth_user.user_id,
            team_id=team_id,
            name=payload.name,
            role=payload.role,
            system_prompt=payload.system_prompt,
            model_provider=selection.provider,
            model_name=selection.model_name,
            provider_base_url=(payload.provider_base_url or "").strip() or None,
            provider_passcode=payload.provider_passcode,
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
    else:
        selection = validate_model_selection(
            provider=str(current.get("model_provider", "")),
            model_name=str(current.get("model_name", "")),
        )

    next_base_url = updates.get("provider_base_url", current.get("provider_base_url"))
    if selection.provider == "lmstudio" and not str(next_base_url or "").strip():
        raise HTTPException(status_code=400, detail="LM Studio provider requires provider_base_url")

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
