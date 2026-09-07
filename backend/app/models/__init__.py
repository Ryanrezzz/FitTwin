"""Beanie document models. `ALL_MODELS` is passed to init_beanie in db.py."""
from __future__ import annotations

from app.models.log import DailyLog
from app.models.meal_rotation import MealRotation
from app.models.plan import Plan
from app.models.profile import Profile
from app.models.progress import ProgressEntry
from app.models.user import Role, User

ALL_MODELS = [User, Profile, Plan, DailyLog, ProgressEntry, MealRotation]

__all__ = [
    "ALL_MODELS", "DailyLog", "MealRotation", "Plan", "Profile",
    "ProgressEntry", "Role", "User",
]
