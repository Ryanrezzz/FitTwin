"""Nutrition Agent — authoritative numbers from tools, meals from template/LLM."""
from __future__ import annotations

from app.agents import templates
from app.agents.prompts import NUTRITION_SYSTEM
from app.agents.schemas import MacrosOut, Meal, MealSelection, NutritionResult
from app.agents.state import trace
from app.agents.tools import meal_builder
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
        p.get("dietary_prefs", []), p.get("allergies", []), age=p.get("age", 30),
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

    # ── LLM picks WHICH dish; the catalog decides HOW MUCH ───────────────────
    # The model is handed a pre-filtered menu, so it cannot name a dish that
    # breaks this user's diet or allergies, and it is never asked for a number.
    menu = meal_builder.allowed_menu(p.get("dietary_prefs", []), p.get("allergies", []))
    menu_text = "\n".join(
        f"{slot}: " + ", ".join(d["id"] for d in dishes) for slot, dishes in menu.items()
    )
    user = (
        f"Profile: age {p.get('age')}, goal {p.get('goal')}, "
        f"diet {p.get('dietary_prefs') or 'unspecified'}, "
        f"allergies {p.get('allergies') or 'none'}.\n"
        f"Daily targets (fixed, not yours to change): {targets['calories']} kcal, "
        f"{targets['macros']['protein_g']}g protein.\n"
        f"Choose exactly ONE dish id per slot from this menu. Reply with ids only.\n"
        f"{menu_text}"
    )
    picks = get_llm().structured(
        system=NUTRITION_SYSTEM, user=user, schema=MealSelection,
        fallback=MealSelection(),
    )
    chosen = {s: getattr(picks, s, "") for s in ("breakfast", "lunch", "snack", "dinner")}
    if any(chosen.values()):
        meals = templates.build_meal_plan(
            targets["calories"], targets["macros"]["protein_g"],
            p.get("dietary_prefs", []), p.get("allergies", []), age=p.get("age", 30),
            choices=chosen,
        )

    result = NutritionResult(
        calories=targets["calories"],
        macros=MacrosOut(**targets["macros"]),
        meal_plan=[
            Meal(**{k: m[k] for k in ("name", "items", "kcal", "protein_g")}) for m in meals
        ],
        changes=changes,
        rationale=picks.rationale or fallback.rationale,
    )

    return {
        "nutrition_result": result.model_dump(),
        "steps": [
            trace("nutrition", f"{result.calories} kcal / {result.macros.protein_g}g protein")
        ],
    }
