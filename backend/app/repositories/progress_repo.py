"""Bodyweight repository — upsert a day's weigh-in; read the recent series."""
from __future__ import annotations

from datetime import date as DateType
from typing import Protocol

from beanie import PydanticObjectId

from app.models.progress import ProgressEntry


class ProgressRepo(Protocol):
    async def upsert(
        self, user_id: str, day: DateType, weight_kg: float, note: str = ""
    ) -> ProgressEntry: ...
    async def recent(self, user_id: str, limit: int = 60) -> list[ProgressEntry]: ...
    async def latest(self, user_id: str) -> ProgressEntry | None: ...


class BeanieProgressRepo:
    async def upsert(
        self, user_id: str, day: DateType, weight_kg: float, note: str = ""
    ) -> ProgressEntry:
        oid = PydanticObjectId(user_id)
        existing = await ProgressEntry.find_one(
            ProgressEntry.user_id == oid, ProgressEntry.date == day
        )
        if existing is None:
            return await ProgressEntry(
                user_id=oid, date=day, weight_kg=weight_kg, note=note
            ).insert()
        existing.weight_kg = weight_kg
        existing.note = note
        await existing.save()
        return existing

    async def recent(self, user_id: str, limit: int = 60) -> list[ProgressEntry]:
        return (
            await ProgressEntry.find(ProgressEntry.user_id == PydanticObjectId(user_id))
            .sort(-ProgressEntry.date)
            .limit(limit)
            .to_list()
        )

    async def latest(self, user_id: str) -> ProgressEntry | None:
        return (
            await ProgressEntry.find(ProgressEntry.user_id == PydanticObjectId(user_id))
            .sort(-ProgressEntry.date)
            .first_or_none()
        )
