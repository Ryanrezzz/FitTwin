"""Safety Agent — the GATE. Deterministic guardrails clamp unsafe plans before
they are ever composed/persisted. The LLM is not trusted to decide safety.
"""
from __future__ import annotations

from app.agents.schemas import SafetyVerdict
from app.agents.state import trace
from app.agents.tools import nutrition_math as nm
from app.domain import Goal

MIN_CALORIES = {"male": 1500, "female": 1200}  # hard absolute floors
MAX_TRAINING_DAYS = 6
RED_FLAGS = [
    "starve", "not eating", "stop eating", "throw up", "purge", "vomit",
    "laxative", "binge", "faint", "chest pain", "suicidal", "hurt myself",
]


def safety_agent(state: dict) -> dict:
    p = state["profile"]
    sex = p.get("sex", "female")
    weight = p.get("weight_kg", 0)

    clamps: list[str] = []
    warnings: list[str] = []
    requires_disclaimer = False

    out: dict = {}

    # 1) calorie floor — clamp UP and recompute macros at the floor
    nutrition = state.get("nutrition_result")
    if nutrition:
        nutrition = dict(nutrition)  # copy; don't mutate upstream state
        floor = MIN_CALORIES.get(sex, 1200)
        if nutrition["calories"] < floor:
            clamps.append(
                f"Calorie target raised from {nutrition['calories']} to the safe floor "
                f"of {floor} kcal/day."
            )
            nutrition["calories"] = floor
            m = nm.macros(floor, weight, Goal(p["goal"]))
            nutrition["macros"] = {"protein_g": m.protein_g, "carbs_g": m.carbs_g, "fat_g": m.fat_g}
        out["nutrition_result"] = nutrition

    # 2) unrealistic rate of loss (> ~1% bodyweight / week)
    rate = p.get("rate_kg_per_week", 0.5)
    max_rate = round(0.01 * weight, 2) if weight else 1.0
    if rate > max_rate:
        warnings.append(
            f"Targeting {rate} kg/week is aggressive; above ~{max_rate} kg/week risks muscle "
            f"loss and rebound. Consider a slower, more sustainable rate."
        )

    # 3) overtraining
    if int(p.get("training_days", 3)) > MAX_TRAINING_DAYS:
        warnings.append("Training 7 days/week risks overtraining — schedule at least one rest day.")

    # 4) medical red flags in the user's message → escalate
    msg = (state.get("message") or "").lower()
    if any(flag in msg for flag in RED_FLAGS):
        requires_disclaimer = True
        warnings.append(
            "This may need professional support. Please speak with a doctor or registered dietitian."
        )

    verdict = SafetyVerdict(
        approved=True,  # we always clamp TO a safe plan rather than blocking
        clamps=clamps,
        warnings=warnings,
        requires_disclaimer=requires_disclaimer,
    )
    out["safety_verdict"] = verdict.model_dump()
    out["steps"] = [trace("safety", f"clamps={len(clamps)} warnings={len(warnings)}")]
    return out
