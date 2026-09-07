"""Shared test fixtures.

The agent core stays offline (`LLM_PROVIDER=fake`); persistence is faked with
in-memory repos injected via `app.dependency_overrides`, so the real security /
service / route code runs without a live MongoDB. `DB_ENABLED=false` keeps the
app lifespan from dialing a real Mongo on startup.
"""
import os

os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ["DB_ENABLED"] = "false"
# The suite logs in far more often than a human would; the limiter has its own
# dedicated test (test_ratelimit.py) that switches it back on.
os.environ["RATE_LIMIT_ENABLED"] = "false"

from datetime import UTC, datetime  # noqa: E402
from enum import Enum  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from beanie import PydanticObjectId  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import deps  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import Role  # noqa: E402

# A complete onboarding profile (PUT /profile body shape — no wrapper).
PROFILE = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178, "weight_kg": 82,
    "goal": "lose", "activity_level": "moderate", "experience": "beginner",
    "dietary_prefs": [], "allergies": [], "equipment": ["dumbbells"],
    "training_days": 4, "rate_kg_per_week": 0.5,
}
CREDS = {"email": "alex@example.com", "password": "supersecret1"}


# Beanie Documents can't be instantiated without init_beanie, so the fakes use
# lightweight stand-ins that duck-type only what the app code touches.
def _agent_shape(data: dict[str, Any]) -> dict[str, Any]:
    """ProfileIn.model_dump() (enum members) -> the agent-profile dict (str values)."""
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in data.items()}


class _FakeUser:
    def __init__(
        self,
        email: str,
        password_hash: str | None,
        role: Role,
        *,
        google_sub: str | None = None,
        email_verified: bool = False,
        display_name: str = "",
        avatar_url: str = "",
    ) -> None:
        self.id = PydanticObjectId()
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = True
        self.created_at = datetime.now(UTC)
        self.google_sub = google_sub
        self.email_verified = email_verified
        self.display_name = display_name
        self.avatar_url = avatar_url

    @property
    def providers(self) -> list[str]:
        out = []
        if self.password_hash:
            out.append("password")
        if self.google_sub:
            out.append("google")
        return out


class _FakeProfile:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_agent_profile(self) -> dict[str, Any]:
        return _agent_shape(self._data)

    def to_api(self) -> dict[str, Any]:
        return _agent_shape(self._data)


class InMemoryUserRepo:
    """Satisfies the UserRepo Protocol with in-memory dicts."""

    def __init__(self) -> None:
        self._by_id: dict[str, _FakeUser] = {}
        self._by_email: dict[str, _FakeUser] = {}

    async def get_by_id(self, user_id: str):
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str):
        return self._by_email.get(email)

    async def get_by_google_sub(self, google_sub: str):
        return next(
            (u for u in self._by_id.values() if u.google_sub == google_sub), None
        )

    async def create(
        self,
        *,
        email: str,
        password_hash: str | None = None,
        role: Role = Role.user,
        google_sub: str | None = None,
        email_verified: bool = False,
        display_name: str = "",
        avatar_url: str = "",
    ):
        user = _FakeUser(
            email, password_hash, role,
            google_sub=google_sub, email_verified=email_verified,
            display_name=display_name, avatar_url=avatar_url,
        )
        self._by_id[str(user.id)] = user
        self._by_email[email] = user
        return user

    async def save(self, user):
        self._by_id[str(user.id)] = user
        self._by_email[user.email] = user
        return user


class InMemoryProfileRepo:
    def __init__(self) -> None:
        self._by_user: dict[str, _FakeProfile] = {}

    async def get_by_user(self, user_id: str):
        return self._by_user.get(user_id)

    async def upsert(self, user_id: str, data: dict[str, Any]):
        profile = _FakeProfile(data)
        self._by_user[user_id] = profile
        return profile


class _FakePlan:
    def __init__(self, user_id, version, *, nutrition, workout, intent, degraded) -> None:
        self.id = PydanticObjectId()
        self.user_id = user_id
        self.version = version
        self.active = True
        self.intent = intent
        self.calorie_target = int(nutrition.get("calories", 0))
        self.macros = nutrition.get("macros", {})
        self.nutrition = nutrition
        self.workout = workout
        self.degraded = degraded
        self.created_at = datetime.now(UTC)


class InMemoryPlanRepo:
    def __init__(self) -> None:
        self._plans: list[_FakePlan] = []

    async def create_version(self, user_id, *, nutrition, workout, intent=None, degraded=False):
        mine = [p for p in self._plans if str(p.user_id) == user_id]
        for p in mine:
            p.active = False
        plan = _FakePlan(
            PydanticObjectId(user_id), max((p.version for p in mine), default=0) + 1,
            nutrition=nutrition, workout=workout, intent=intent, degraded=degraded,
        )
        self._plans.append(plan)
        return plan

    async def get_active(self, user_id):
        return next((p for p in self._plans if str(p.user_id) == user_id and p.active), None)

    async def get_by_id(self, plan_id, user_id):
        return next(
            (p for p in self._plans if str(p.id) == plan_id and str(p.user_id) == user_id), None
        )


class _FakeDailyLog:
    def __init__(self, day, data: dict[str, Any]) -> None:
        self.date = day
        self.water_ml = data.get("water_ml", 0)
        self.steps = data.get("steps", 0)
        self.calories = data.get("calories", 0)
        self.protein_g = data.get("protein_g", 0)
        self.workout_done = data.get("workout_done", False)

    def update(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def to_api(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(), "water_ml": self.water_ml, "steps": self.steps,
            "calories": self.calories, "protein_g": self.protein_g,
            "workout_done": self.workout_done,
        }


class InMemoryLogRepo:
    def __init__(self) -> None:
        self._by_user: dict[str, dict[Any, _FakeDailyLog]] = {}

    async def get_day(self, user_id: str, day):
        return self._by_user.get(user_id, {}).get(day)

    async def upsert_day(self, user_id: str, day, data: dict[str, Any]):
        days = self._by_user.setdefault(user_id, {})
        if day in days:
            days[day].update(data)
        else:
            days[day] = _FakeDailyLog(day, data)
        return days[day]

    async def recent(self, user_id: str, limit: int = 30):
        days = self._by_user.get(user_id, {})
        return sorted(days.values(), key=lambda log: log.date, reverse=True)[:limit]


class _FakeWeighIn:
    def __init__(self, day, weight_kg: float, note: str = "") -> None:
        self.date, self.weight_kg, self.note = day, weight_kg, note

    def to_api(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "weight_kg": round(self.weight_kg, 2),
            "note": self.note,
        }


class InMemoryProgressRepo:
    def __init__(self) -> None:
        self._by_user: dict[str, dict[Any, _FakeWeighIn]] = {}

    async def upsert(self, user_id: str, day, weight_kg: float, note: str = ""):
        days = self._by_user.setdefault(user_id, {})
        days[day] = _FakeWeighIn(day, weight_kg, note)
        return days[day]

    async def recent(self, user_id: str, limit: int = 60):
        days = self._by_user.get(user_id, {})
        return sorted(days.values(), key=lambda e: e.date, reverse=True)[:limit]

    async def latest(self, user_id: str):
        entries = await self.recent(user_id, limit=1)
        return entries[0] if entries else None


class InMemoryRotationRepo:
    def __init__(self) -> None:
        self._by_user: dict[str, dict[Any, dict[str, int]]] = {}

    async def get(self, user_id: str, day) -> dict[str, int]:
        return dict(self._by_user.get(user_id, {}).get(day, {}))

    async def bump(self, user_id: str, day, slot: str, by: int = 1) -> dict[str, int]:
        days = self._by_user.setdefault(user_id, {})
        current = days.setdefault(day, {})
        current[slot] = current.get(slot, 0) + by
        return dict(current)

    async def reset(self, user_id: str, day) -> dict[str, int]:
        self._by_user.setdefault(user_id, {})[day] = {}
        return {}


@pytest.fixture()
def client():
    users, profiles, plans = InMemoryUserRepo(), InMemoryProfileRepo(), InMemoryPlanRepo()
    logs, progress = InMemoryLogRepo(), InMemoryProgressRepo()
    rotations = InMemoryRotationRepo()
    app.dependency_overrides[deps.get_user_repo] = lambda: users
    app.dependency_overrides[deps.get_profile_repo] = lambda: profiles
    app.dependency_overrides[deps.get_plan_repo] = lambda: plans
    app.dependency_overrides[deps.get_log_repo] = lambda: logs
    app.dependency_overrides[deps.get_progress_repo] = lambda: progress
    app.dependency_overrides[deps.get_rotation_repo] = lambda: rotations
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
