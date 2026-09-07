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
    # Pain/injury outranks everything else: a knee complaint must never be
    # answered with a streak nudge.
    ("injury", [
        "hurt", "hurts", "pain", "painful", "injur", "sore", "strain", "sprain",
        "ache", "aching", "tweak", "pulled a", "swollen", "cramp",
    ]),
    ("safety_question", [
        "is it safe", "is it ok", "dangerous", "starve", "too few calories",
        "1000 cal", "skip meals",
    ]),
    # Emotional state routes here, ahead of the topic rules: someone writing
    # "I feel hopeless" was falling through to the factual Q&A agent, which
    # answered by quoting their calorie target. Feelings are not a look-up.
    ("motivation", [
        "motivat", "pep talk", "give up", "giving up", "encourage",
        "feel like quitting", "lazy",
        # low mood / struggling
        "hopeless", "no point", "pointless", "worthless", "hate myself",
        "depressed", "depression", "burnt out", "burned out", "exhausted",
        "overwhelmed", "i feel low", "feeling low", "feel sad", "feeling sad",
        "anxious", "stressed", "fed up", "nothing is working",
        "nothing works", "can't do this", "cant do this", "i give up",
        "want to quit", "feel like a failure", "failing at",
    ]),
    ("nutrition_request", [
        "meal plan", "diet plan", "vegetarian", "vegan", "recipe",
        "what should i eat", "what to eat", "macros", "calorie", "kcal",
        "protein", "carbs", "fat intake", "food", "meal", "breakfast", "lunch",
        "dinner", "snack", "how much should i eat",
    ]),
    ("workout_request", [
        "workout", "exercise", "routine", "training plan", "program", "split", "lift",
        "squat", "deadlift", "bench", "reps", "sets", "cardio", "rest day",
    ]),
    ("greeting", ["hi", "hello", "hey", "yo", "namaste", "good morning", "good evening"]),
]

# Factual look-ups ("how much protein?", "what's my calorie target?") are
# questions, not plan requests. Without this they hit `nutrition_request` and the
# user got a whole day of meals when they wanted one number.
_LOOKUP_PHRASES = (
    "how much", "how many", "what is my", "what's my", "whats my",
    "what are my", "how long", "when should", "why ",
)

# A greeting keyword must match the WHOLE message — "hi" is inside "which",
# and "hey" inside "they".
_WHOLE_MESSAGE_INTENTS = {"greeting"}


def classify_intent(message: str | None, trigger: str) -> str:
    if trigger == "generate_plan":
        return "generate_plan"
    if trigger == "weekly_review":
        return "weekly_review"
    text = (message or "").lower().strip()
    stripped = text.strip("!?.,'\" ")
    # A look-up phrasing wins over topic keywords, unless the user is actually
    # asking for a plan to be built.
    if any(p in text for p in _LOOKUP_PHRASES) and not any(
        k in text for k in ("plan", "generate", "build me", "give me a")
    ):
        return "general"
    for intent, keywords in _INTENT_RULES:
        if intent in _WHOLE_MESSAGE_INTENTS:
            if stripped in keywords:
                return intent
        elif any(k in text for k in keywords):
            return intent
    return "general"


# ── nodes ──────────────────────────────────────────────────────────────────
def orchestrator_route(state: dict) -> dict:
    intent = classify_intent(state.get("message"), state.get("trigger", "chat"))
    return {"intent": intent, "route": [], "steps": [trace("route", f"intent={intent}")]}


def route_selector(state: dict):
    """Conditional edge after `route` — returns next node name(s)."""
    intent = state.get("intent")
    # `general` used to land on `progress`, so every unrecognised question came
    # back as a Weekly Report. It now goes to the Q&A node, which answers it.
    if intent in ("general", "greeting"):
        return "answer"
    if intent == "injury":
        return "answer"
    if intent in ("progress_concern", "weekly_review"):
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
    return "answer"


def after_progress(state: dict):
    """Conditional edge after `progress` — adapt the plan only if plateaued."""
    pr = state.get("progress_result") or {}
    if pr.get("plateau"):
        return ["nutrition", "workout"]
    return "motivation"


# Intents whose replies are about the plan itself, so safety clamps/warnings are
# on-topic rather than noise.
_SAFETY_RELEVANT_INTENTS = {
    "generate_plan", "weekly_review", "progress_concern", "nutrition_request",
    "workout_request", "equipment_change", "safety_question", "log_food",
}


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

    answer = state.get("answer_result")

    parts: list[str] = []
    # A direct question gets its answer first and alone — appending the plan or a
    # trend report underneath is what made every reply feel like a status dump.
    if answer and answer.get("answer"):
        parts.append(answer["answer"])
    if progress:
        parts.append(progress.get("report_md", ""))
    if nutrition:
        parts.append(
            f"**{nutrition['calories']} kcal · "
            f"{nutrition['macros']['protein_g']}g protein / "
            f"{nutrition['macros']['carbs_g']}g carbs / {nutrition['macros']['fat_g']}g fat**"
        )
        # Someone asking what to eat wants FOOD. Printing only macros was the
        # single most useless response the coach produced.
        for meal in nutrition.get("meal_plan", []):
            items = ", ".join(meal.get("items", []))
            dish = meal.get("dish")
            head = f"**{meal['name']}**" + (f" — {dish}" if dish else "")
            macros = f"_{meal['kcal']} kcal · {meal['protein_g']}g protein_"
            parts.append(f"{head}  \n{items}  \n{macros}")
        parts += [f"- {c}" for c in nutrition.get("changes", [])]
    if workout:
        parts.append(f"**Training:** {workout['split']}.")
        parts += [f"- {n}" for n in workout.get("progression_notes", [])]
    if motivation:
        parts.append(motivation["message"])
    # Safety notes belong on plan-shaped replies and on health questions — not
    # stapled to every message. Repeating "your rate is aggressive" after "hi"
    # trains the user to ignore the one warning that matters.
    if intent in _SAFETY_RELEVANT_INTENTS:
        parts += [f"⚠️ {c}" for c in safety.get("clamps", [])]
        parts += [f"⚠️ {w}" for w in safety.get("warnings", [])]
    if intent == "injury" or safety.get("requires_disclaimer"):
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
