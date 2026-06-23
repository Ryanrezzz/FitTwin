"""Runnable demo of the FitTwin multi-agent graph (offline, no API key needed).

    cd backend && .venv/bin/python demo.py

Set LLM_PROVIDER=gemini|openai|ollama (+ key) in the env to see the LLM enrich
the deterministic output. With LLM_PROVIDER=fake (default) it runs fully offline.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.agents.runner import run_coach

PROFILE = {
    "name": "Alex", "age": 28, "sex": "male", "height_cm": 178, "weight_kg": 82,
    "goal": "lose", "activity_level": "moderate", "dietary_prefs": [], "allergies": [],
    "experience": "beginner", "equipment": ["dumbbells"], "training_days": 4,
    "rate_kg_per_week": 0.5,
}
PLAN = {"calorie_target": 2000, "macros": {"protein_g": 164, "carbs_g": 150, "fat_g": 54}}


def _flat_history(n=14):
    d0 = date(2026, 1, 1)
    return {
        "weight_series": [(d0 + timedelta(days=i), 82.0) for i in range(n)],
        "logs": [{"calories": 2000, "protein_g": 164, "workout_done": True} for _ in range(n)],
    }


def show(title: str, result: dict) -> None:
    final = result["final"]
    print("\n" + "═" * 78)
    print(f"  {title}")
    print("═" * 78)
    print(f"intent      : {final['intent']}")
    print(f"agents used : {' → '.join(final['agents_used'])}")
    print("trace       : " + " | ".join(s["summary"] for s in result["steps"]))
    print("-" * 78)
    print(final["message"])


if __name__ == "__main__":
    show("1) Onboarding — generate the first plan", run_coach(profile=PROFILE, trigger="generate_plan"))

    show(
        "2) Chat — 'I haven't lost weight this week' (plateau → adapt)",
        run_coach(
            profile=PROFILE, message="I haven't lost weight this week",
            history=_flat_history(), active_plan=PLAN, trigger="chat",
        ),
    )

    show(
        "3) Chat — 'create a vegetarian meal plan'",
        run_coach(
            profile={**PROFILE, "dietary_prefs": ["vegetarian"]},
            message="create a vegetarian meal plan",
        ),
    )

    show(
        "4) Chat — 'I have no dumbbells'",
        run_coach(profile={**PROFILE, "equipment": []}, message="I have no dumbbells"),
    )

    show(
        "5) Weekly review — on track (→ motivation, no needless re-plan)",
        run_coach(
            profile=PROFILE, history={
                "weight_series": [(date(2026, 1, 1) + timedelta(days=i), 82 - 0.06 * i) for i in range(14)],
                "logs": [{"calories": 2000, "protein_g": 164, "workout_done": True} for _ in range(14)],
            }, active_plan=PLAN, trigger="weekly_review",
        ),
    )
    print()
