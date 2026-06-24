"""Daily-log routes — the dashboard's manual quick-log (water / steps / workout).

There's no way to *auto*-measure water or steps without a wearable (that's a V2
integration), so the user logs them here; streak & workout-completion are derived
from these entries (see /dashboard/summary).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.deps import ensure_persistence, get_current_user, get_log_repo
from app.models.user import User
from app.repositories.log_repo import LogRepo
from app.schemas.logs import DailyLogIn, DailyLogOut

router = APIRouter(prefix="/logs", tags=["logs"], dependencies=[Depends(ensure_persistence)])


def _empty(day: date) -> DailyLogOut:
    return DailyLogOut(date=day.isoformat())


@router.get("/today", response_model=DailyLogOut)
async def get_today(
    user: User = Depends(get_current_user),
    logs: LogRepo = Depends(get_log_repo),
) -> DailyLogOut:
    day = date.today()
    log = await logs.get_day(str(user.id), day)
    return DailyLogOut(**log.to_api()) if log else _empty(day)


@router.put("/today", response_model=DailyLogOut)
async def put_today(
    body: DailyLogIn,
    user: User = Depends(get_current_user),
    logs: LogRepo = Depends(get_log_repo),
) -> DailyLogOut:
    """Upsert today's log. Only the provided fields are written (partial update)."""
    data = body.model_dump(exclude_none=True)
    log = await logs.upsert_day(str(user.id), date.today(), data)
    return DailyLogOut(**log.to_api())
