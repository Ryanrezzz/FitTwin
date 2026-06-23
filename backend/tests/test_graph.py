"""End-to-end graph tests — the whole multi-agent collaboration, offline (FakeLLM)."""
from datetime import date, timedelta

from app.agents.runner import run_coach
from app.agents.schemas import CoachResponse

BASE_PROFILE = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178, "weight_kg": 82,
    "goal": "lose", "activity_level": "moderate", "dietary_prefs": [], "allergies": [],
    "experience": "beginner", "equipment": ["dumbbells"], "training_days": 4,
    "rate_kg_per_week": 0.5,
}

PLAN = {"calorie_target": 2000, "macros": {"protein_g": 164, "carbs_g": 150, "fat_g": 54}}


def _series(start, daily_delta, n):
    d0 = date(2026, 1, 1)
    return [(d0 + timedelta(days=i), start + daily_delta * i) for i in range(n)]


def _adherent_logs(n):
    return [{"calories": 2000, "protein_g": 164, "steps": 9000, "workout_done": True} for _ in range(n)]


def _final(result) -> CoachResponse:
    return CoachResponse(**result["final"])


def test_generate_plan_runs_nutrition_workout_safety():
    result = run_coach(profile=BASE_PROFILE, trigger="generate_plan")
    final = _final(result)
    assert final.intent == "generate_plan"
    assert set(final.agents_used) >= {"nutrition", "workout", "safety"}
    assert final.nutrition is not None and final.nutrition.calories > 0
    assert final.workout is not None and final.workout.sessions
    assert final.progress is None


def test_plateau_triggers_full_adaptation():
    history = {"weight_series": _series(82.0, 0.0, 14), "logs": _adherent_logs(14)}
    result = run_coach(
        profile=BASE_PROFILE,
        message="I haven't lost weight this week",
        history=history,
        active_plan=PLAN,
        trigger="chat",
    )
    final = _final(result)
    assert final.intent == "progress_concern"
    # Progress -> plateau -> Nutrition + Workout -> Safety (the spec's flow)
    assert set(final.agents_used) >= {"progress", "nutrition", "workout", "safety"}
    assert final.progress.plateau is True
    assert final.nutrition.changes, "nutrition should record a plateau adaptation"


def test_on_track_routes_to_motivation_not_adaptation():
    history = {"weight_series": _series(82.0, -0.06, 14), "logs": _adherent_logs(14)}
    result = run_coach(
        profile=BASE_PROFILE,
        message="how am I doing this week?",
        history=history,
        active_plan=PLAN,
        trigger="weekly_review",
    )
    final = _final(result)
    assert final.progress.plateau is False
    assert "motivation" in final.agents_used
    assert "nutrition" not in final.agents_used  # no needless re-plan when on track


def test_vegetarian_meal_plan_routes_to_nutrition():
    veg = {**BASE_PROFILE, "dietary_prefs": ["vegetarian"]}
    result = run_coach(profile=veg, message="create a vegetarian meal plan")
    final = _final(result)
    assert final.intent == "nutrition_request"
    assert "nutrition" in final.agents_used
    foods = " ".join(item for meal in final.nutrition.meal_plan for item in meal.items).lower()
    assert "chicken" not in foods  # vegetarian: no meat
    assert any(v in foods for v in ("paneer", "tofu", "lentils", "yogurt"))


def test_no_equipment_yields_bodyweight_workout():
    home = {**BASE_PROFILE, "equipment": []}
    result = run_coach(profile=home, message="I have no dumbbells, give me a workout")
    final = _final(result)
    assert final.intent == "equipment_change"
    assert "workout" in final.agents_used
    assert "home" in final.workout.split.lower()
    names = " ".join(e.name for s in final.workout.sessions for e in s.exercises).lower()
    assert any(bw in names for bw in ("push-up", "squat", "row", "bridge"))


def test_calories_never_below_safe_floor():
    tiny = {
        **BASE_PROFILE, "sex": "female", "age": 30, "height_cm": 155,
        "weight_kg": 48, "activity_level": "sedentary", "rate_kg_per_week": 1.0,
    }
    result = run_coach(profile=tiny, trigger="generate_plan")
    final = _final(result)
    assert final.nutrition.calories >= 1200  # female floor enforced by Safety gate


def test_steps_trace_is_recorded():
    result = run_coach(profile=BASE_PROFILE, trigger="generate_plan")
    nodes = [s["node"] for s in result["steps"]]
    assert "route" in nodes and "compose" in nodes
    assert "safety" in nodes
