"""Meal-rotation repository — read today's rotation offsets; bump one slot."""
from __future__ import annotations

from datetime import date as DateType
from typing import Protocol

from beanie import PydanticObjectId

from app.models.meal_rotation import MealRotation


class RotationRepo(Protocol):
    async def get(self, user_id: str, day: DateType) -> dict[str, int]: ...
    async def bump(self, user_id: str, day: DateType, slot: str, by: int = 1) -> dict[str, int]: ...
    async def reset(self, user_id: str, day: DateType) -> dict[str, int]: ...


class BeanieRotationRepo:
    async def _doc(self, user_id: str, day: DateType) -> MealRotation | None:
        return await MealRotation.find_one(
            MealRotation.user_id == PydanticObjectId(user_id), MealRotation.date == day
        )

    async def get(self, user_id: str, day: DateType) -> dict[str, int]:
        doc = await self._doc(user_id, day)
        return dict(doc.rotations) if doc else {}

    async def bump(self, user_id: str, day: DateType, slot: str, by: int = 1) -> dict[str, int]:
        doc = await self._doc(user_id, day)
        if doc is None:
            doc = MealRotation(user_id=PydanticObjectId(user_id), date=day, rotations={slot: by})
            await doc.insert()
            return dict(doc.rotations)
        doc.rotations = {**doc.rotations, slot: doc.rotations.get(slot, 0) + by}
        await doc.save()
        return dict(doc.rotations)

    async def reset(self, user_id: str, day: DateType) -> dict[str, int]:
        doc = await self._doc(user_id, day)
        if doc is not None:
            doc.rotations = {}
            await doc.save()
        return {}
