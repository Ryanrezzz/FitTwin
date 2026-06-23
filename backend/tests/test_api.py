"""API-layer tests — exercise the HTTP boundary over the real (fake-LLM) graph.

Using the context-managed TestClient runs the app lifespan, so `app.state.graph`
is the actually-compiled LangGraph; these are true integration tests of the
router -> service -> agent path, deterministic because LLM_PROVIDER defaults to
"fake".
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

PROFILE = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178, "weight_kg": 82,
    "goal": "lose", "activity_level": "moderate", "experience": "beginner",
    "dietary_prefs": [], "allergies": [], "equipment": ["dumbbells"],
    "training_days": 4, "rate_kg_per_week": 0.5,
}
PLAN = {"calorie_target": 2000, "macros": {"protein_g": 164, "carbs_g": 150, "fat_g": 54}}


@pytest.fixture()
def client():
    with TestClient(app) as c:   # context-managed -> runs lifespan (compiles graph)
        yield c


def test_health_is_dependency_free(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers.get("X-Request-ID")


def test_ready_reports_compiled_graph(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["graph"] is True


def test_generate_plan_runs_nutrition_workout_safety(client):
    r = client.post("/api/v1/plans/generate", json={"profile": PROFILE})
    assert r.status_code == 200
    final = r.json()["final"]
    assert final["intent"] == "generate_plan"
    assert final["agents_used"] == ["nutrition", "workout", "safety"]
    assert final["nutrition"]["calories"] > 0
    assert final["workout"]["split"]


def test_chat_plateau_triggers_progress_then_adapt(client):
    history = {
        "weight_series": [{"weight_kg": 82.0} for _ in range(14)],
        "logs": [{"calories": 2000, "protein_g": 164, "workout_done": True} for _ in range(14)],
    }
    r = client.post(
        "/api/v1/chat",
        json={
            "profile": PROFILE,
            "message": "I haven't lost weight this week",
            "history": history,
            "active_plan": PLAN,
        },
    )
    assert r.status_code == 200
    final = r.json()["final"]
    assert final["intent"] == "progress_concern"
    assert final["progress"]["plateau"] is True
    # plateau -> the plan is adapted, so nutrition + workout ran after progress
    assert {"progress", "nutrition", "workout", "safety"} <= set(final["agents_used"])


def test_invalid_profile_returns_error_envelope(client):
    bad = {**PROFILE, "goal": "bulk", "age": 5}   # bad enum + out-of-range
    r = client.post("/api/v1/plans/generate", json={"profile": bad})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["request_id"]


def test_unknown_field_is_rejected(client):
    bad = {**PROFILE, "favorite_color": "volt-green"}   # extra="forbid"
    r = client.post("/api/v1/plans/generate", json={"profile": bad})
    assert r.status_code == 422
