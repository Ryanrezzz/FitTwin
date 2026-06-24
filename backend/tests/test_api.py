"""Coach API tests — exercise the authenticated HTTP boundary over the real
(fake-LLM) graph. Fixtures (`client`, `auth_headers`, `onboarded`) live in
conftest and inject in-memory repos, so these run fully offline + deterministic.
"""
from __future__ import annotations


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


def test_generate_plan_persists_v1(client, onboarded):
    r = client.post("/api/v1/plans/generate", headers=onboarded)
    assert r.status_code == 200
    body = r.json()
    final = body["final"]
    assert final["intent"] == "generate_plan"
    assert final["agents_used"] == ["nutrition", "workout", "safety"]
    assert final["nutrition"]["calories"] > 0
    # the complete plan was persisted as version 1
    assert body["plan_id"] and body["plan_version"] == 1

    active = client.get("/api/v1/plans/active", headers=onboarded)
    assert active.status_code == 200
    assert active.json()["version"] == 1 and active.json()["active"] is True
    assert active.json()["calorie_target"] == final["nutrition"]["calories"]


def test_second_generate_bumps_version_and_flips_active(client, onboarded):
    first = client.post("/api/v1/plans/generate", headers=onboarded).json()
    second = client.post("/api/v1/plans/generate", headers=onboarded).json()
    assert second["plan_version"] == 2

    active = client.get("/api/v1/plans/active", headers=onboarded).json()
    assert active["version"] == 2

    # the old version is retained but no longer active
    old = client.get(f"/api/v1/plans/{first['plan_id']}", headers=onboarded).json()
    assert old["version"] == 1 and old["active"] is False


def test_get_active_before_generate_is_404(client, onboarded):
    assert client.get("/api/v1/plans/active", headers=onboarded).status_code == 404


def test_get_unknown_plan_is_404(client, onboarded):
    assert client.get("/api/v1/plans/deadbeef", headers=onboarded).status_code == 404


def test_chat_plateau_adapts_against_stored_plan(client, onboarded):
    # establish an active plan, then log adherent days at its targets
    gen = client.post("/api/v1/plans/generate", headers=onboarded).json()["final"]["nutrition"]
    ct, pp = gen["calories"], gen["macros"]["protein_g"]
    history = {
        "weight_series": [{"weight_kg": 82.0} for _ in range(14)],
        "logs": [{"calories": ct, "protein_g": pp, "workout_done": True} for _ in range(14)],
    }
    r = client.post(
        "/api/v1/chat",
        headers=onboarded,
        json={"message": "I haven't lost weight this week", "history": history},
    )
    assert r.status_code == 200
    body = r.json()
    final = body["final"]
    assert final["intent"] == "progress_concern"
    assert final["progress"]["plateau"] is True
    assert {"progress", "nutrition", "workout", "safety"} <= set(final["agents_used"])
    # the adapted plan was persisted as a new version
    assert body["plan_version"] == 2


def test_dashboard_summary_requires_auth(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_dashboard_summary_derives_cards_before_a_plan(client, onboarded):
    r = client.get("/api/v1/dashboard/summary", headers=onboarded)
    assert r.status_code == 200
    s = r.json()
    # targets are derived from the profile even with no plan generated yet
    assert s["calorie_target"] > 0 and s["protein_target_g"] > 0
    assert s["current_weight_kg"] == 82.0
    assert s["target_weight_kg"] < 82.0          # "lose" → healthy-BMI target below current
    assert s["step_goal"] == 9000                # moderate activity
    assert s["workout_target_days"] == 4
    # the hybrid coaching-engine map is surfaced for the UI
    modes = {a["key"]: a["mode"] for a in s["agents"]}
    assert modes["progress"] == "rule" and modes["safety"] == "rule"
    assert modes["nutrition"] == "llm" and modes["workout"] == "hybrid"
    assert s["engine"] == "rule"                 # LLM_PROVIDER=fake → rule-based


def test_dashboard_summary_uses_active_plan_targets(client, onboarded):
    plan = client.post("/api/v1/plans/generate", headers=onboarded).json()["final"]["nutrition"]
    s = client.get("/api/v1/dashboard/summary", headers=onboarded).json()
    assert s["calorie_target"] == plan["calories"]
    assert s["protein_target_g"] == plan["macros"]["protein_g"]
    # no logging yet → remaining equals target
    assert s["calories_remaining"] == s["calorie_target"]


def test_logs_today_starts_empty_then_upserts(client, onboarded):
    r = client.get("/api/v1/logs/today", headers=onboarded)
    assert r.status_code == 200
    assert r.json()["water_ml"] == 0 and r.json()["steps"] == 0

    # partial update: only water — steps stay untouched
    r = client.put("/api/v1/logs/today", headers=onboarded, json={"water_ml": 500})
    assert r.status_code == 200 and r.json()["water_ml"] == 500
    r = client.put("/api/v1/logs/today", headers=onboarded, json={"steps": 4000})
    body = r.json()
    assert body["water_ml"] == 500 and body["steps"] == 4000


def test_dashboard_reflects_todays_log(client, onboarded):
    client.post("/api/v1/plans/generate", headers=onboarded)
    client.put(
        "/api/v1/logs/today",
        headers=onboarded,
        json={"water_ml": 1500, "steps": 6000, "workout_done": True},
    )
    s = client.get("/api/v1/dashboard/summary", headers=onboarded).json()
    assert s["water_ml"] == 1500
    assert s["steps"] == 6000
    assert s["streak_days"] == 1          # one active day (today)
    assert s["workouts_done"] == 1        # one workout this week
    assert s["workout_completion_pct"] == 25   # 1 of 4 planned days


def test_dashboard_uses_explicit_target_weight(client, auth_headers):
    profile = {
        "name": "Ryan", "age": 24, "sex": "male", "height_cm": 178, "weight_kg": 82,
        "goal": "lose", "target_weight_kg": 74, "activity_level": "moderate",
        "experience": "beginner", "gym_type": "full_gym", "training_days": 4,
    }
    assert client.put("/api/v1/profile", json=profile, headers=auth_headers).status_code == 200
    s = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    assert s["target_weight_kg"] == 74.0


def test_chat_rejects_unknown_field(client, onboarded):
    r = client.post(
        "/api/v1/chat",
        headers=onboarded,
        json={"message": "hi", "favorite_color": "volt-green"},   # extra="forbid"
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
