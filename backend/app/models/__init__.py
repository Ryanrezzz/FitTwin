"""Beanie document models. `ALL_MODELS` is passed to init_beanie in db.py."""
from __future__ import annotations

from app.models.profile import Profile
from app.models.user import Role, User

ALL_MODELS = [User, Profile]

__all__ = ["ALL_MODELS", "Profile", "Role", "User"]
