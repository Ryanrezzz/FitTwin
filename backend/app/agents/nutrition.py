"""Nutrition Agent — authoritative numbers from tools, meals from template/LLM."""
from __future__ import annotations

from app.agents import templates
from app.agents.prompts import NUTRITION_SYSTEM
from app.agents.schemas import Macros as _unused  # noqa: F401  (keep schemas import path warm)
from app.agents.schemas import MacrosOut, Meal, NutritionResult
from app.agents.state import trace
from app.agents.tools import nutrition_math as nm
from app.ai.llm import get_llm
from app.domain import ActivityLevel, Goal, Sex


def nutrition_agent(state: dict) -> dict:
    p = state["profile"]
    goal = Goal(p["goal"])
    targets = nm.full_targets(
        sex=Sex(p["sex"]),
        weight_kg=p["weight_kg"],
        height_cm=p["height_cm"],
        age=p["age"],
        activity_level=ActivityLevel(p["activity_level"]),
        goal=goal,
        rate_kg_per_week=p.get("rate_kg_per_week", 0.5),
    )

    # ── adaptation: a plateau upstream nudges the deficit (still deterministic) ──
    changes: list[str] = []
    progress = state.get("progress_result")
    if progress and progress.get("plateau"):
        new_cals = max(targets["calories"] - 100, int(targets["tdee"] * 0.75))
        if new_cals != targets["calories"]:
            targets["calories"] = new_cals
            m = nm.macros(new_cals, p["weight_kg"], goal)
            targets["macros"] = {"protein_g": m.protein_g, "carbs_g": m.carbs_g, "fat_g": m.fat_g}
            changes.append(
                f"Plateau detected → trimmed ~100 kcal to {new_cals} kcal; protein kept high."
            )

    meals = templates.build_meal_plan(
        targets["calories"], targets["macros"]["protein_g"],
        p.get("dietary_prefs", []), p.get("allergies", []),
    )
    fallback = NutritionResult(
        calories=targets["calories"],
        macros=MacrosOut(**targets["macros"]),
        meal_plan=[Meal(**m) for m in meals],
        changes=changes,
        rationale=(
            f"BMR {targets['bmr']} kcal × activity = TDEE {targets['tdee']} kcal "
            f"→ target {targets['calories']} kcal for goal '{p['goal']}'."
        ),
    )

    user = (
        f"User profile: {p}. Authoritative targets (DO NOT change numbers): {targets}. "
        f"Dietary preferences: {p.get('dietary_prefs', []) or 'none'}; "
        f"allergies: {p.get('allergies', []) or 'none'}."
    )
    result = get_llm().structured(
        system=NUTRITION_SYSTEM, user=user, schema=NutritionResult, fallback=fallback
    )
    # numbers are tool-owned; never trust the model's arithmetic
    result.calories = targets["calories"]
    result.macros = MacrosOut(**targets["macros"])
    if not result.changes:
        result.changes = changes

    return {
        "nutrition_result": result.model_dump(),
        "steps": [trace("nutrition", f"{result.calories} kcal / {result.macros.protein_g}g protein")],
    }
