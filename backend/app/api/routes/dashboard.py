"""Dashboard routes — read-only aggregations for the product surface.

Everything here is *derived on read* from the user's profile + active plan by the
deterministic dashboard tool; there is no dashboard collection (see
docs/03-data-model.md and docs/05-frontend.md §5a).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.agents.registry import AGENTS
from app.agents.tools import dashboard_math
from app.config import settings
from app.deps import ensure_persistence, get_active_plan, get_current_profile
from app.schemas.dashboard import AgentInfo, DashboardSummaryOut

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(ensure_persistence)]
)


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
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
) -> DashboardSummaryOut:
    """Overview cards (current/target weight, calories & protein remaining, water,
    steps, workout %, streak, est. weeks-to-goal) + the hybrid agent map."""
    metrics = dashboard_math.dashboard_summary(profile, active_plan)
    return DashboardSummaryOut(
        **metrics,
        engine=_engine(),
        agents=[AgentInfo(**a) for a in AGENTS],
    )
