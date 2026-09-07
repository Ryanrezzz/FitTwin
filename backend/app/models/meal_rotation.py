"""MealRotation — how far a user has rotated each of today's meal slots.

"I don't want fish tonight" has to survive a page reload, so the choice is
stored rather than held in the browser. One small document per user per day:
`{"dinner": 2}` means dinner is showing the 3rd-ranked allowed dish.

Storing an INDEX rather than a dish id keeps the plan self-healing: if the
catalog changes, or the user's diet or allergies change, the index is re-applied
to the newly-filtered candidate list and can never resurrect a dish they are no
longer allowed to eat.
"""
from __future__ import annotations

from datetime import date as DateType

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class MealRotation(Document):
    user_id: PydanticObjectId
    date: DateType
    rotations: dict[str, int] = Field(default_factory=dict)

    class Settings:
        name = "meal_rotations"
        indexes = [
            IndexModel(
                [("user_id", 1), ("date", -1)], unique=True, name="uq_rotation_user_date"
            ),
        ]
