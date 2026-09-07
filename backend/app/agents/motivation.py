"""Motivation Agent — responds to what the person said, not just their streak.

WHY THIS WAS REWRITTEN
----------------------
It used to build one sentence from the streak count and send *that* to the model
as the user turn. The person's own words were never passed in, so the agent could
not respond to them — it could only ever produce streak variations. Someone
writing "I feel demotivated, can't study, can't work out, feel I can't lose
weight" got back "Your streak is at 0 days — complete one small workout", which
prescribes the exact thing they just said they couldn't do and opens by
reminding them they have nothing to show.

Two rules now hold:
  1. The message is the input. Numbers are context, not the subject.
  2. When someone is struggling, acknowledgement comes before advice, and the
     streak is never the opening line.
"""
from __future__ import annotations

from app.agents.prompts import MOTIVATION_SYSTEM
from app.agents.schemas import MotivationResult
from app.agents.state import trace
from app.ai.llm import get_llm

# Someone describing a bad patch. Deterministic so the offline provider reacts
# the same way the LLM is told to.
_STRUGGLING = (
    "demotivat", "unmotivat", "no motivation", "can't", "cant ", "cannot",
    "give up", "giving up", "quit", "failing", "failure", "stuck", "hate my",
    "exhaust", "burnt out", "burned out", "overwhelm", "stress", "anxious",
    "sad", "low", "tired of", "fed up", "lazy", "guilty", "ashamed",
)
# Heavier language. Still no diagnosis — just a warmer reply and a gentle
# pointer to a person, because a fitness app is the wrong place to stop at
# "do one workout".
_DISTRESS = (
    "hopeless", "no point", "pointless", "worthless", "hate myself",
    "can't go on", "cant go on", "give up on life", "depressed", "depression",
)


def _tone(message: str) -> str:
    text = (message or "").lower()
    if any(k in text for k in _DISTRESS):
        return "distress"
    if any(k in text for k in _STRUGGLING):
        return "struggling"
    return "upbeat"


def _streak_days(logs: list[dict]) -> int:
    """Trailing consecutive days that were logged or had a workout."""
    streak = 0
    for log in reversed(logs):
        if log.get("workout_done") or log.get("calories", 0) > 0:
            streak += 1
        else:
            break
    return streak


def _fallback(tone: str, streak: int, adherence_pct: float) -> str:
    """Deterministic reply. Must still be humane with no LLM configured."""
    if tone == "distress":
        return (
            "That sounds genuinely heavy, and it's not something you have to push "
            "through on your own. Nothing about your plan is urgent — it will keep. "
            "If this has been sitting with you for a while, please talk to someone you "
            "trust or a doctor; that matters far more than any training plan. I'm here when "
            "you want to pick things back up."
        )
    if tone == "struggling":
        return (
            "Feeling like this doesn't undo your progress, and flat weeks are part of "
            "it rather than a sign you've failed. You don't owe your plan anything "
            "today. If you want one small thing that isn't training: drink a glass of "
            "water and log it. That's enough for today."
        )
    if streak:
        base = f"You're on a {streak}-day streak"
        if adherence_pct:
            base += f" at {adherence_pct}% adherence"
        return base + " — consistency is what moves the needle. Keep stacking wins."
    return "Log one thing today — water, a meal, or a walk — and your Twin starts tracking."


def motivation_agent(state: dict) -> dict:
    message = state.get("message") or ""
    history = state.get("history") or {}
    logs = history.get("logs", [])
    streak = _streak_days(logs)
    adherence_pct = (state.get("progress_result") or {}).get("adherence_pct", 0)
    tone = _tone(message)

    fallback = _fallback(tone, streak, adherence_pct)

    # The message leads; the numbers are context the model may use, or ignore.
    user = (
        f'They wrote: "{message}"\n\n' if message else ""
    ) + (
        f"Context (use only if it helps them — never open with it): "
        f"streak {streak} days"
        + (f", adherence {adherence_pct}%" if adherence_pct else "")
        + f".\nRead of their tone: {tone}."
    )

    text = get_llm().text(system=MOTIVATION_SYSTEM, user=user, fallback=fallback)
    result = MotivationResult(
        message=(text or "").strip() or fallback,
        streak_days=streak,
        nudge="" if tone != "upbeat" else (
            "Log today to extend your streak." if streak else "Log your first day."
        ),
        tone=tone,
    )

    return {
        "motivation_result": result.model_dump(),
        "steps": [trace("motivation", f"tone={tone} streak={streak}d")],
    }
