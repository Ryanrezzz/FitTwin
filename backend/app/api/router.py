"""Aggregates the route modules into a single versioned router (`/api/v1`)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import coach, health

api_v1 = APIRouter()
api_v1.include_router(health.router)
api_v1.include_router(coach.router)
