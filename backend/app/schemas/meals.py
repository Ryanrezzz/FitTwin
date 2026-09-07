"""Meal rotation DTOs — the "give me something else today" surface."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agents.tools.meal_builder import MEAL_PLAN_SLOTS

SLOT_VALUES = tuple(slot for slot, _, _ in MEAL_PLAN_SLOTS)


class RotateMealIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Constrained to real slots so a typo returns 422 rather than silently
    # rotating nothing.
    slot: str = Field(pattern=f"^({'|'.join(SLOT_VALUES)})$")


class MealOut(BaseModel):
    name: str
    slot: str
    dish: str = ""
    dish_id: str = ""
    items: list[str] = []
    kcal: int = 0
    protein_g: int = 0
    carbs_g: int = 0
    fat_g: int = 0


class RotateMealOut(BaseModel):
    """The replacement meal, plus where the user now sits in the rotation."""

    meal: MealOut
    rotation: int
    options: int
