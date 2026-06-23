"""Aggregates the route modules into a single versioned router (`/api/v1`)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, coach, health, profile

api_v1 = APIRouter()
api_v1.include_router(health.router)
api_v1.include_router(auth.router)
api_v1.include_router(profile.router)
api_v1.include_router(coach.router)
