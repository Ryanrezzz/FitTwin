"""Coach API tests — exercise the authenticated HTTP boundary over the real
(fake-LLM) graph. Fixtures (`client`, `auth_headers`, `onboarded`) live in
conftest and inject in-memory repos, so these run fully offline + deterministic.
"""
from __future__ import annotations

PLAN = {"calorie_target": 2000, "macros": {"protein_g": 164, "carbs_g": 150, "fat_g": 54}}


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


def test_coach_requires_auth(client):
    r = client.post("/api/v1/plans/generate")
    assert r.status_code == 401


def test_generate_plan_without_profile_is_400(client, auth_headers):
    r = client.post("/api/v1/plans/generate", headers=auth_headers)
    assert r.status_code == 400
    assert "onboarding" in r.json()["error"]["message"].lower()


def test_generate_plan_runs_nutrition_workout_safety(client, onboarded):
    r = client.post("/api/v1/plans/generate", headers=onboarded)
    assert r.status_code == 200
    final = r.json()["final"]
    assert final["intent"] == "generate_plan"
    assert final["agents_used"] == ["nutrition", "workout", "safety"]
    assert final["nutrition"]["calories"] > 0
    assert final["workout"]["split"]


def test_chat_plateau_triggers_progress_then_adapt(client, onboarded):
    history = {
        "weight_series": [{"weight_kg": 82.0} for _ in range(14)],
        "logs": [{"calories": 2000, "protein_g": 164, "workout_done": True} for _ in range(14)],
    }
    r = client.post(
        "/api/v1/chat",
        headers=onboarded,
        json={
            "message": "I haven't lost weight this week",
            "history": history,
            "active_plan": PLAN,
        },
    )
    assert r.status_code == 200
    final = r.json()["final"]
    assert final["intent"] == "progress_concern"
    assert final["progress"]["plateau"] is True
    assert {"progress", "nutrition", "workout", "safety"} <= set(final["agents_used"])


def test_chat_rejects_unknown_field(client, onboarded):
    r = client.post(
        "/api/v1/chat",
        headers=onboarded,
        json={"message": "hi", "favorite_color": "volt-green"},   # extra="forbid"
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
