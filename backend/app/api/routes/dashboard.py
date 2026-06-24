"""Dashboard routes — read-only aggregations for the product surface.

Everything here is *derived on read* from the user's profile + active plan by the
deterministic dashboard tool; there is no dashboard collection (see
docs/03-data-model.md and docs/05-frontend.md §5a).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends

from app.agents.registry import AGENTS
from app.agents.tools import dashboard_math
from app.config import settings
from app.deps import (
    ensure_persistence,
    get_active_plan,
    get_current_profile,
    get_current_user,
    get_log_repo,
)
from app.models.user import User
from app.repositories.log_repo import LogRepo
from app.schemas.dashboard import AgentInfo, DashboardSummaryOut

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(ensure_persistence)]
)


def _has_activity(log: Any) -> bool:
    return bool(log.workout_done or log.steps or log.water_ml or log.calories)


async def _today_from_logs(user_id: str, logs: LogRepo) -> dict[str, Any]:
    """Assemble today's values + streak + this-week workouts from the log history."""
    today = date.today()
    recent = await logs.recent(user_id, limit=30)
    by_date = {log.date: log for log in recent}
    active_dates = {log.date for log in recent if _has_activity(log)}
    workout_dates = {log.date for log in recent if log.workout_done}
    current = by_date.get(today)
    return {
        "calories": current.calories if current else 0,
        "protein_g": current.protein_g if current else 0,
        "steps": current.steps if current else 0,
        "water_ml": current.water_ml if current else 0,
        "streak_days": dashboard_math.streak_days(active_dates, today),
        "workouts_done_week": dashboard_math.workouts_done_in_week(workout_dates, today),
    }


def _engine() -> str:
    """Normalize the configured provider into a display label ("fake" == rule-based)."""
    provider = settings.llm_provider.lower()
    if provider in ("fake", "rule"):
        return "rule"
    if provider == "ollama":
        return "local"
    return provider


@router.get("/summary", response_model=DashboardSummaryOut)
async def summary(
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
    logs: LogRepo = Depends(get_log_repo),
) -> DashboardSummaryOut:
    """Overview cards (current/target weight, calories & protein remaining, water,
    steps, workout %, streak, est. weeks-to-goal) + the hybrid agent map."""
    today = await _today_from_logs(str(user.id), logs)
    metrics = dashboard_math.dashboard_summary(profile, active_plan, today)
    return DashboardSummaryOut(
        **metrics,
        engine=_engine(),
        agents=[AgentInfo(**a) for a in AGENTS],
    )
