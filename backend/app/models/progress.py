"""ProgressEntry — a dated bodyweight measurement.

WHY THIS EXISTS: the dashboard used to read `profile.weight_kg`, the number typed
once at onboarding. It never changed, so "current weight" was frozen, the
weeks-to-goal estimate never moved, and plateau detection had no real series to
analyse — it was reasoning about a constant. This collection is the actual
time series the coach needs.

One entry per user per day (re-weighing the same day overwrites), indexed
descending by date because every read is "the most recent N".
"""
from __future__ import annotations

from datetime import date as DateType
from typing import Any

from beanie import Document, PydanticObjectId
from pymongo import IndexModel


class ProgressEntry(Document):
    user_id: PydanticObjectId
    date: DateType
    weight_kg: float
    note: str = ""

    class Settings:
        name = "progress_entries"
        indexes = [
            IndexModel(
                [("user_id", 1), ("date", -1)], unique=True, name="uq_progress_user_date"
            ),
        ]

    def to_api(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "weight_kg": round(self.weight_kg, 2),
            "note": self.note,
        }
