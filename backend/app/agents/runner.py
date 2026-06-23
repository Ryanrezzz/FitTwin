"""Entry point for invoking the multi-agent graph.

`run_coach(...)` builds the initial state, runs the compiled graph (singleton),
and returns the merged result containing `final` (CoachResponse) and `steps`
(the AgentRun trace).

Expected `profile` shape::

    {
        "name": "Alex", "age": 28, "sex": "male",            # "male" | "female"
        "height_cm": 178, "weight_kg": 82,
        "goal": "lose",                                       # lose | maintain | gain
        "activity_level": "moderate",                        # sedentary..very_active
        "dietary_prefs": ["vegetarian"], "allergies": [],
        "experience": "beginner",                            # beginner | intermediate | advanced
        "equipment": ["dumbbells"], "training_days": 4,
        "rate_kg_per_week": 0.5,
    }

Expected `history` shape::

    {
        "weight_series": [(date(2026,1,1), 82.0), ...],
        "logs": [{"date": ..., "calories": 2000, "protein_g": 160,
                  "steps": 8000, "workout_done": True}, ...],
    }
"""
from __future__ import annotations

from typing import Any

from app.agents.graph import build_graph

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_coach(
    *,
    profile: dict[str, Any],
    message: str | None = None,
    history: dict[str, Any] | None = None,
    active_plan: dict[str, Any] | None = None,
    trigger: str = "chat",
    user_id: str = "demo",
    recursion_limit: int = 25,
) -> dict[str, Any]:
    initial: dict[str, Any] = {
        "user_id": user_id,
        "trigger": trigger,
        "message": message,
        "profile": profile,
        "history": history or {},
        "active_plan": active_plan,
        "intent": None,
        "route": [],
        "progress_result": None,
        "nutrition_result": None,
        "workout_result": None,
        "motivation_result": None,
        "safety_verdict": None,
        "steps": [],
        "final": None,
    }
    return get_graph().invoke(initial, config={"recursion_limit": recursion_limit})
