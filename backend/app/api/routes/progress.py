"""Bodyweight tracking routes — the time series behind the trend and plateau logic.

Before this existed, "current weight" was `profile.weight_kg` (typed once at
onboarding), so the dashboard's weight card and weeks-to-goal estimate could
never move and the Progress agent had no real series to read.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.deps import ensure_persistence, get_current_user, get_progress_repo
from app.models.user import User
from app.repositories.progress_repo import ProgressRepo
from app.schemas.progress import WeightIn, WeightOut, WeightSeriesOut

router = APIRouter(
    prefix="/progress", tags=["progress"], dependencies=[Depends(ensure_persistence)]
)


@router.put("/weight", response_model=WeightOut)
async def log_weight(
    body: WeightIn,
    user: User = Depends(get_current_user),
    progress: ProgressRepo = Depends(get_progress_repo),
) -> WeightOut:
    """Record (or correct) a weigh-in. Re-weighing the same day overwrites it."""
    entry = await progress.upsert(
        str(user.id), body.date or date.today(), body.weight_kg, body.note
    )
    return WeightOut(**entry.to_api())


@router.get("/weight", response_model=WeightSeriesOut)
async def weight_series(
    days: int = Query(60, ge=1, le=365),
    user: User = Depends(get_current_user),
    progress: ProgressRepo = Depends(get_progress_repo),
) -> WeightSeriesOut:
    """Recent weigh-ins, newest first, plus the net change over the window."""
    entries = await progress.recent(str(user.id), limit=days)
    out = [WeightOut(**e.to_api()) for e in entries]
    if not out:
        return WeightSeriesOut()
    # `entries` is newest-first, so the net change is newest minus oldest.
    change = round(entries[0].weight_kg - entries[-1].weight_kg, 2) if len(entries) > 1 else None
    return WeightSeriesOut(
        entries=out,
        latest_kg=round(entries[0].weight_kg, 2),
        change_kg=change,
        days_tracked=len(out),
    )
