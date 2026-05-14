import httpx
import pytest

from core.auth import AuthUser, get_current_user
from db.supabase import _FALLBACK
from main import app
import routers.teams as teams_router


pytestmark = pytest.mark.anyio


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test")


async def _create_team(name: str = "Research Demo Team", domain: str = "AI safety") -> dict:
    async with _client() as client:
        response = await client.post(
            "/teams",
            json={"name": name, "domain": domain, "collaboration_rule": "sequential"},
        )
    assert response.status_code == 200
    return response.json()


async def test_team_creation_and_openapi_paths() -> None:
    team = await _create_team()
    assert team["id"]
    assert team["name"] == "Research Demo Team"
    assert team["collaboration_rule"] == "sequential"

    async with _client() as client:
        teams_response = await client.get("/teams")
        schema_response = await client.get("/openapi.json")

    assert teams_response.status_code == 200
    assert len(teams_response.json()) == 1

    schema = schema_response.json()
    for path in (
        "/teams",
        "/teams/{team_id}",
        "/teams/{team_id}/agents",
        "/teams/{team_id}/agents/{agent_id}",
    ):
        assert path in schema["paths"]


async def test_multiple_agents_with_different_models_and_patch_flow() -> None:
    team = await _create_team()
    team_id = team["id"]

    async with _client() as client:
        create_a = await client.post(
            f"/teams/{team_id}/agents",
            json={
                "name": "Researcher Plus",
                "role": "researcher",
                "system_prompt": "Find primary evidence.",
                "model_provider": "groq",
                "model_name": "llama-3.1-8b-instant",
                "response_style": "evidence-first",
                "execution_order": 3,
            },
        )
        create_b = await client.post(
            f"/teams/{team_id}/agents",
            json={
                "name": "Local Critic",
                "role": "critic",
                "system_prompt": "Challenge unsupported claims.",
                "model_provider": "sarvam",
                "model_name": "sarvam-m",
                "response_style": "skeptical",
                "execution_order": 4,
            },
        )
        list_response = await client.get(f"/teams/{team_id}/agents")

    assert create_a.status_code == 200
    assert create_b.status_code == 200
    assert list_response.status_code == 200

    agents = list_response.json()
    assert len(agents) == 5
    assert any(a["name"] == "Researcher Plus" and a["model_provider"] == "groq" for a in agents)
    assert any(a["name"] == "Local Critic" and a["model_name"] == "sarvam-m" for a in agents)

    patch_target = create_b.json()["id"]
    async with _client() as client:
        patch_response = await client.patch(
            f"/teams/{team_id}/agents/{patch_target}",
            json={"model_provider": "sarvam", "model_name": "sarvam-m", "response_style": "balanced"},
        )
        patch_team_response = await client.patch(
            f"/teams/{team_id}",
            json={"name": "Updated Team", "domain": "Policy", "collaboration_rule": "debate"},
        )

    assert patch_response.status_code == 200
    patched_agent = patch_response.json()
    assert patched_agent["model_provider"] == "sarvam"
    assert patched_agent["model_name"] == "sarvam-m"

    assert patch_team_response.status_code == 200
    patched_team = patch_team_response.json()
    assert patched_team["name"] == "Updated Team"
    assert patched_team["domain"] == "Policy"
    assert patched_team["collaboration_rule"] == "debate"


async def test_invalid_provider_and_model_rejected() -> None:
    team = await _create_team()

    async with _client() as client:
        bad_provider = await client.post(
            f"/teams/{team['id']}/agents",
            json={
                "name": "Bad Provider",
                "role": "researcher",
                "system_prompt": "x",
                "model_provider": "unknown-provider",
                "model_name": "some-model",
            },
        )
        bad_model = await client.post(
            f"/teams/{team['id']}/agents",
            json={
                "name": "Bad Model",
                "role": "researcher",
                "system_prompt": "x",
                "model_provider": "groq",
                "model_name": "invalid-model",
            },
        )

    assert bad_provider.status_code == 400
    assert "Unsupported model provider" in bad_provider.json()["detail"]
    assert bad_model.status_code == 400
    assert "Unsupported model for groq" in bad_model.json()["detail"]


async def test_lmstudio_requires_base_url_and_allows_custom_model_name() -> None:
    team = await _create_team()
    async with _client() as client:
        missing_url = await client.post(
            f"/teams/{team['id']}/agents",
            json={
                "name": "Local Agent",
                "role": "researcher",
                "system_prompt": "Use local runtime",
                "model_provider": "lmstudio",
                "model_name": "phi-3-mini",
            },
        )
        valid = await client.post(
            f"/teams/{team['id']}/agents",
            json={
                "name": "Local Agent",
                "role": "researcher",
                "system_prompt": "Use local runtime",
                "model_provider": "lmstudio",
                "model_name": "phi-3-mini",
                "provider_base_url": "http://localhost:1234/v1",
                "provider_passcode": "secret-pass",
            },
        )
    assert missing_url.status_code == 400
    assert "requires provider_base_url" in missing_url.json()["detail"]
    assert valid.status_code == 200
    payload = valid.json()
    assert payload["model_provider"] == "lmstudio"
    assert payload["model_name"] == "phi-3-mini"
    assert payload["provider_base_url"] == "http://localhost:1234/v1"
    assert payload["provider_passcode_configured"] is True


async def test_cross_user_team_forbidden() -> None:
    team = await _create_team()

    async def _other_user() -> AuthUser:
        return AuthUser(user_id="99999999-9999-9999-9999-999999999999", email="other@example.com")

    app.dependency_overrides[get_current_user] = _other_user
    try:
        async with _client() as client:
            response = await client.get(f"/teams/{team['id']}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_delete_team_cascades_agents_in_fallback_store() -> None:
    team = await _create_team()
    team_id = team["id"]

    assert len([a for a in _FALLBACK.agents if a.get("team_id") == team_id]) == 3

    async with _client() as client:
        create_agent = await client.post(
            f"/teams/{team_id}/agents",
            json={
                "name": "Extra",
                "role": "researcher",
                "system_prompt": "Add one more.",
                "model_provider": "groq",
                "model_name": "llama-3.3-70b-versatile",
            },
        )

    assert create_agent.status_code == 200
    assert len([a for a in _FALLBACK.agents if a.get("team_id") == team_id]) == 4

    async with _client() as client:
        delete_response = await client.delete(f"/teams/{team_id}")
        list_agents_after = await client.get(f"/teams/{team_id}/agents")

    assert delete_response.status_code == 200
    assert len([a for a in _FALLBACK.agents if a.get("team_id") == team_id]) == 0
    assert list_agents_after.status_code == 404


async def test_lmstudio_probe_endpoints_return_health_and_models(monkeypatch) -> None:
    class FakeLMStudioClient:
        def health(self, base_url: str, passcode: str | None = None, timeout_seconds: float = 10.0) -> dict:
            assert base_url == "http://localhost:1234"
            assert passcode == "secret"
            assert timeout_seconds == 7
            return {"ok": True, "models_count": 2}

        def list_models(self, base_url: str, passcode: str | None = None, timeout_seconds: float = 10.0) -> list[str]:
            assert base_url == "http://localhost:1234"
            assert passcode == "secret"
            assert timeout_seconds == 7
            return ["phi-3-mini", "qwen3-8b"]

    monkeypatch.setattr(teams_router, "LMStudioClient", lambda: FakeLMStudioClient())

    async with _client() as client:
        health_response = await client.post(
            "/teams/lmstudio/health",
            json={"base_url": "http://localhost:1234", "passcode": "secret", "timeout_seconds": 7},
        )
        models_response = await client.post(
            "/teams/lmstudio/models",
            json={"base_url": "http://localhost:1234", "passcode": "secret", "timeout_seconds": 7},
        )

    assert health_response.status_code == 200
    assert health_response.json() == {"ok": True, "models_count": 2}
    assert models_response.status_code == 200
    assert models_response.json() == {"models": ["phi-3-mini", "qwen3-8b"]}
