"""Orchestrator — intent classification, routing decisions, and final composition.

Routing is deterministic (rules over keywords) so it is fast and unit-testable.
An LLM classifier can be layered on later behind the same `classify_intent` seam.
"""
from __future__ import annotations

from app.agents.schemas import (
    CoachResponse,
    MotivationResult,
    NutritionResult,
    ProgressResult,
    SafetyVerdict,
    WorkoutResult,
)
from app.agents.state import trace

# (intent, keywords) in priority order — first match wins
_INTENT_RULES: list[tuple[str, list[str]]] = [
    ("log_food", ["i ate", "i had", "i consumed", "grams of", "just ate", "g of"]),
    ("equipment_change", [
        "no dumbbell", "don't have", "dont have", "no equipment", "no gym",
        "at home", "no barbell", "without weights", "lost access",
    ]),
    ("progress_concern", [
        "haven't lost", "havent lost", "not losing", "no progress", "plateau",
        "stuck", "gained", "lost only", "didn't lose", "didnt lose", "same weight",
    ]),
    ("safety_question", [
        "is it safe", "is it ok", "dangerous", "starve", "too few calories",
        "1000 cal", "skip meals",
    ]),
    ("motivation", [
        "motivat", "pep talk", "give up", "demotivated", "encourage",
        "feel like quitting", "lazy",
    ]),
    ("nutrition_request", [
        "meal plan", "diet plan", "vegetarian", "vegan", "recipe",
        "what should i eat", "macros", "calorie",
    ]),
    ("workout_request", [
        "workout", "exercise", "routine", "training plan", "program", "split", "lift",
    ]),
]


def classify_intent(message: str | None, trigger: str) -> str:
    if trigger == "generate_plan":
        return "generate_plan"
    if trigger == "weekly_review":
        return "weekly_review"
    text = (message or "").lower()
    for intent, keywords in _INTENT_RULES:
        if any(k in text for k in keywords):
            return intent
    return "general"


# ── nodes ──────────────────────────────────────────────────────────────────
def orchestrator_route(state: dict) -> dict:
    intent = classify_intent(state.get("message"), state.get("trigger", "chat"))
    return {"intent": intent, "route": [], "steps": [trace("route", f"intent={intent}")]}


def route_selector(state: dict):
    """Conditional edge after `route` — returns next node name(s)."""
    intent = state.get("intent")
    if intent in ("progress_concern", "weekly_review", "general"):
        return "progress"
    if intent == "generate_plan":
        return ["nutrition", "workout"]
    if intent in ("nutrition_request", "log_food"):
        return "nutrition"
    if intent in ("workout_request", "equipment_change"):
        return "workout"
    if intent == "motivation":
        return "motivation"
    if intent == "safety_question":
        return "safety"
    return "progress"


def after_progress(state: dict):
    """Conditional edge after `progress` — adapt the plan only if plateaued."""
    pr = state.get("progress_result") or {}
    if pr.get("plateau"):
        return ["nutrition", "workout"]
    return "motivation"


def compose_final(state: dict) -> dict:
    intent = state.get("intent", "general")
    nutrition = state.get("nutrition_result")
    workout = state.get("workout_result")
    progress = state.get("progress_result")
    motivation = state.get("motivation_result")
    safety = state.get("safety_verdict") or {}

    used = [
        s["node"]
        for s in state.get("steps", [])
        if s["node"] in {"progress", "nutrition", "workout", "motivation", "safety"}
    ]
    used = list(dict.fromkeys(used))  # unique, order-preserving

    parts: list[str] = []
    if progress:
        parts.append(progress.get("report_md", ""))
    if nutrition:
        parts.append(
            f"**Nutrition:** {nutrition['calories']} kcal · "
            f"{nutrition['macros']['protein_g']}g protein / "
            f"{nutrition['macros']['carbs_g']}g carbs / {nutrition['macros']['fat_g']}g fat."
        )
        parts += [f"- {c}" for c in nutrition.get("changes", [])]
    if workout:
        parts.append(f"**Training:** {workout['split']}.")
        parts += [f"- {n}" for n in workout.get("progression_notes", [])]
    if motivation:
        parts.append(motivation["message"])
    parts += [f"⚠️ {c}" for c in safety.get("clamps", [])]
    parts += [f"⚠️ {w}" for w in safety.get("warnings", [])]
    if safety.get("requires_disclaimer"):
        parts.append("_FitTwin is not a substitute for professional medical advice._")

    message = "\n\n".join(p for p in parts if p).strip() or "All set — keep it up!"

    final = CoachResponse(
        message=message,
        intent=intent,
        agents_used=used,
        nutrition=NutritionResult(**nutrition) if nutrition else None,
        workout=WorkoutResult(**workout) if workout else None,
        progress=ProgressResult(**progress) if progress else None,
        motivation=MotivationResult(**motivation) if motivation else None,
        safety=SafetyVerdict(**safety) if safety else None,
    )
    return {"final": final.model_dump(), "steps": [trace("compose", "final response built")]}
