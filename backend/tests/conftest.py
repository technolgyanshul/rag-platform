import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.auth import AuthUser, get_current_user
from db.supabase import reset_fallback_store
from main import app


@pytest.fixture(autouse=True)
def _auth_override_and_env() -> Generator[None, None, None]:
    os.environ["ALLOW_INMEMORY_REPOSITORY"] = "true"
    reset_fallback_store()

    def _test_user() -> AuthUser:
        return AuthUser(user_id="00000000-0000-0000-0000-000000000001", email="test@example.com")

    app.dependency_overrides[get_current_user] = _test_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
