"""Integration tests for the Beanie repositories against a real MongoDB.

Skipped automatically when Mongo isn't reachable, so the default `pytest` run
stays fully offline. To run them: start Mongo (e.g. `brew services start
mongodb-community`) and `pytest tests/test_integration_db.py`. They use a
throwaway database that is dropped on teardown — no fixtures touch app data.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config import settings
from app.models import ALL_MODELS
from app.models.user import Role
from app.repositories.plan_repo import BeaniePlanRepo
from app.repositories.profile_repo import BeanieProfileRepo
from app.repositories.user_repo import BeanieUserRepo

NUTRITION = {"calories": 2200, "macros": {"protein_g": 160, "carbs_g": 200, "fat_g": 60}}
WORKOUT = {"split": "Upper / Lower", "sessions": [], "progression_notes": []}

PROFILE_DATA = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178.0, "weight_kg": 82.0,
    "goal": "lose", "activity_level": "moderate", "experience": "beginner",
    "dietary_prefs": [], "allergies": [], "equipment": ["dumbbells"],
    "training_days": 4, "rate_kg_per_week": 0.5,
}


@pytest_asyncio.fixture()
async def mongo_db():
    """A throwaway, Beanie-initialized database; skips if Mongo is unreachable."""
    client = AsyncMongoClient(settings.mongo_uri, serverSelectionTimeoutMS=800)
    try:
        await client.admin.command("ping")
    except Exception:  # noqa: BLE001
        await client.close()
        pytest.skip("MongoDB not reachable; skipping DB integration tests")
    db_name = f"fittwin_test_{uuid.uuid4().hex[:8]}"
    await init_beanie(database=client[db_name], document_models=ALL_MODELS)
    yield
    await client.drop_database(db_name)
    await client.close()


async def test_user_repo_round_trip(mongo_db):
    repo = BeanieUserRepo()
    created = await repo.create(email="ada@example.com", password_hash="hash", role=Role.user)
    assert created.id is not None

    by_email = await repo.get_by_email("ada@example.com")
    assert by_email is not None and by_email.email == "ada@example.com"

    by_id = await repo.get_by_id(str(created.id))
    assert by_id is not None and by_id.id == created.id

    assert await repo.get_by_email("missing@example.com") is None
    assert await repo.get_by_id("not-a-valid-objectid") is None


async def test_profile_repo_upsert_is_idempotent(mongo_db):
    user = await BeanieUserRepo().create(email="grace@example.com", password_hash="h")
    repo = BeanieProfileRepo()
    uid = str(user.id)

    first = await repo.upsert(uid, PROFILE_DATA)
    assert first.to_agent_profile()["training_days"] == 4

    # second upsert updates the same document, not a new one
    updated = await repo.upsert(uid, {**PROFILE_DATA, "training_days": 5})
    assert updated.id == first.id
    assert updated.to_agent_profile()["training_days"] == 5

    fetched = await repo.get_by_user(uid)
    assert fetched is not None and fetched.to_agent_profile()["training_days"] == 5


async def test_plan_repo_versioning_and_scoping(mongo_db):
    user = await BeanieUserRepo().create(email="lin@example.com", password_hash="h")
    repo = BeaniePlanRepo()
    uid = str(user.id)

    v1 = await repo.create_version(uid, nutrition=NUTRITION, workout=WORKOUT, intent="generate_plan")
    assert v1.version == 1 and v1.active is True and v1.calorie_target == 2200

    v2 = await repo.create_version(uid, nutrition={**NUTRITION, "calories": 2100}, workout=WORKOUT)
    assert v2.version == 2 and v2.active is True

    active = await repo.get_active(uid)
    assert active is not None and active.version == 2

    # v1 is retained but deactivated (audit trail)
    old = await repo.get_by_id(str(v1.id), uid)
    assert old is not None and old.active is False

    # object-level authz: another user cannot read this plan
    other = await BeanieUserRepo().create(email="other@example.com", password_hash="h")
    assert await repo.get_by_id(str(v2.id), str(other.id)) is None
