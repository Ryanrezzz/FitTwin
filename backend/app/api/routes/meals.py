"""Meal rotation — swap a single slot's dish without touching the rest of the day.

The user's real complaint is per-meal ("not fish tonight"), not per-week, so
rotation is scoped to one slot on one day. The rotation index is persisted and
re-applied to the freshly filtered candidate list on every read, so a rotated
meal still honours diet and allergies by construction.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends

from app.agents import templates
from app.agents.tools import dashboard_math, meal_builder
from app.deps import (
    ensure_persistence,
    get_active_plan,
    get_current_profile,
    get_current_user,
    get_rotation_repo,
)
from app.models.user import User
from app.repositories.rotation_repo import RotationRepo
from app.schemas.meals import MealOut, RotateMealIn, RotateMealOut

router = APIRouter(prefix="/meals", tags=["meals"], dependencies=[Depends(ensure_persistence)])


def _targets(profile: dict[str, Any], active_plan: dict[str, Any] | None) -> tuple[int, int]:
    """Today's calorie/protein targets — the plan's if there is one, else derived."""
    if active_plan:
        return (
            int(active_plan["calorie_target"]),
            int(active_plan["macros"]["protein_g"]),
        )
    metrics = dashboard_math.dashboard_summary(profile, None, {})
    return int(metrics["calorie_target"]), int(metrics["protein_target_g"])


@router.post("/rotate", response_model=RotateMealOut)
async def rotate_meal(
    body: RotateMealIn,
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
    rotations: RotationRepo = Depends(get_rotation_repo),
) -> RotateMealOut:
    """Show a different dish for one slot today. Wraps around when options run out."""
    today = date.today()
    updated = await rotations.bump(str(user.id), today, body.slot)
    calories, protein = _targets(profile, active_plan)

    meals = templates.build_meal_plan(
        calories, protein,
        profile.get("dietary_prefs", []), profile.get("allergies", []),
        day_offset=today.weekday(), age=profile.get("age", 30), rotations=updated,
    )
    meal = next(m for m in meals if m.get("slot") == body.slot)
    return RotateMealOut(
        meal=MealOut(**{k: v for k, v in meal.items() if k in MealOut.model_fields}),
        rotation=updated.get(body.slot, 0),
        options=meal_builder.rotation_options(
            body.slot, profile.get("dietary_prefs", []), profile.get("allergies", [])
        ),
    )


@router.post("/rotate/reset", response_model=list[MealOut])
async def reset_rotations(
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
    rotations: RotationRepo = Depends(get_rotation_repo),
) -> list[MealOut]:
    """Back to the coach's original picks for today."""
    today = date.today()
    await rotations.reset(str(user.id), today)
    calories, protein = _targets(profile, active_plan)
    meals = templates.build_meal_plan(
        calories, protein,
        profile.get("dietary_prefs", []), profile.get("allergies", []),
        day_offset=today.weekday(), age=profile.get("age", 30),
    )
    return [MealOut(**{k: v for k, v in m.items() if k in MealOut.model_fields}) for m in meals]
