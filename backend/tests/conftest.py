"""Shared test fixtures.

The agent core stays offline (`LLM_PROVIDER=fake`); persistence is faked with
in-memory repos injected via `app.dependency_overrides`, so the real security /
service / route code runs without a live MongoDB. `DB_ENABLED=false` keeps the
app lifespan from dialing a real Mongo on startup.
"""
import os

os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ["DB_ENABLED"] = "false"

from typing import Any  # noqa: E402

import pytest  # noqa: E402
from beanie import PydanticObjectId  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import deps  # noqa: E402
from app.main import app  # noqa: E402
from app.models.profile import Profile  # noqa: E402
from app.models.user import Role, User  # noqa: E402

# A complete onboarding profile (PUT /profile body shape — no wrapper).
PROFILE = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178, "weight_kg": 82,
    "goal": "lose", "activity_level": "moderate", "experience": "beginner",
    "dietary_prefs": [], "allergies": [], "equipment": ["dumbbells"],
    "training_days": 4, "rate_kg_per_week": 0.5,
}
CREDS = {"email": "alex@example.com", "password": "supersecret1"}


class InMemoryUserRepo:
    """Satisfies the UserRepo Protocol; stores Beanie User objects in dicts."""

    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, User] = {}

    async def get_by_id(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    async def create(self, *, email: str, password_hash: str, role: Role = Role.user) -> User:
        user = User(email=email, password_hash=password_hash, role=role)
        user.id = PydanticObjectId()
        self._by_id[str(user.id)] = user
        self._by_email[email] = user
        return user


class InMemoryProfileRepo:
    def __init__(self) -> None:
        self._by_user: dict[str, Profile] = {}

    async def get_by_user(self, user_id: str) -> Profile | None:
        return self._by_user.get(user_id)

    async def upsert(self, user_id: str, data: dict[str, Any]) -> Profile:
        existing = self._by_user.get(user_id)
        if existing is None:
            profile = Profile(user_id=PydanticObjectId(user_id), **data)
            profile.id = PydanticObjectId()
            self._by_user[user_id] = profile
            return profile
        for key, value in data.items():
            setattr(existing, key, value)
        return existing


@pytest.fixture()
def client():
    users, profiles = InMemoryUserRepo(), InMemoryProfileRepo()
    app.dependency_overrides[deps.get_user_repo] = lambda: users
    app.dependency_overrides[deps.get_profile_repo] = lambda: profiles
    with TestClient(app) as c:   # context-managed -> runs lifespan (compiles graph)
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Register + login a user; return an Authorization header (no profile yet)."""
    client.post("/api/v1/auth/register", json=CREDS)
    tokens = client.post("/api/v1/auth/login", json=CREDS).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture()
def onboarded(client, auth_headers):
    """auth_headers + a stored profile, so coach routes have something to read."""
    r = client.put("/api/v1/profile", json=PROFILE, headers=auth_headers)
    assert r.status_code == 200, r.text
    return auth_headers
