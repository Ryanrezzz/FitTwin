"""DailyLog — one document per user per day.

Feeds the dashboard's live cards (water, steps, workout completion, streak). High
write volume + queried by date range → its own collection with a unique
`{user_id, date}` index (see docs/03-data-model.md).
"""
from __future__ import annotations

from datetime import date as DateType
from typing import Any

from beanie import Document, PydanticObjectId
from pymongo import IndexModel


class DailyLog(Document):
    user_id: PydanticObjectId
    date: DateType
    water_ml: int = 0
    steps: int = 0
    calories: int = 0
    protein_g: float = 0
    workout_done: bool = False

    class Settings:
        name = "daily_logs"
        indexes = [
            IndexModel([("user_id", 1), ("date", -1)], unique=True, name="uq_log_user_date"),
        ]

    def to_api(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "water_ml": self.water_ml,
            "steps": self.steps,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "workout_done": self.workout_done,
        }
