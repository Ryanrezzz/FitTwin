"""Daily-log repository — get/upsert a day; fetch recent days for streak math."""
from __future__ import annotations

from datetime import date as DateType
from typing import Any, Protocol

from beanie import PydanticObjectId

from app.models.log import DailyLog


class LogRepo(Protocol):
    async def get_day(self, user_id: str, day: DateType) -> DailyLog | None: ...
    async def upsert_day(self, user_id: str, day: DateType, data: dict[str, Any]) -> DailyLog: ...
    async def recent(self, user_id: str, limit: int = 30) -> list[DailyLog]: ...


class BeanieLogRepo:
    async def get_day(self, user_id: str, day: DateType) -> DailyLog | None:
        return await DailyLog.find_one(
            DailyLog.user_id == PydanticObjectId(user_id), DailyLog.date == day
        )

    async def upsert_day(self, user_id: str, day: DateType, data: dict[str, Any]) -> DailyLog:
        oid = PydanticObjectId(user_id)
        existing = await DailyLog.find_one(DailyLog.user_id == oid, DailyLog.date == day)
        if existing is None:
            return await DailyLog(user_id=oid, date=day, **data).insert()
        for key, value in data.items():
            setattr(existing, key, value)
        await existing.save()
        return existing

    async def recent(self, user_id: str, limit: int = 30) -> list[DailyLog]:
        return (
            await DailyLog.find(DailyLog.user_id == PydanticObjectId(user_id))
            .sort(-DailyLog.date)
            .limit(limit)
            .to_list()
        )
