"""Coach Q&A — answers the question the user actually asked.

Before this node existed, anything the keyword router didn't recognise fell to
`general`, which routed to `progress` and returned a Weekly Report. So "how much
protein should I eat?", "my knee hurts" and "hi" all produced the same block of
trend statistics — the app knew the answer (180 g) and never said it.

The LLM writes the prose; the NUMBERS are injected from the deterministic tools
and the user's stored plan, so the model reports figures rather than inventing
them. With no LLM configured the fallback still answers from those same numbers.
"""
from __future__ import annotations

from app.agents.prompts import COACH_SYSTEM
from app.agents.schemas import AnswerResult
from app.agents.state import trace
from app.ai.llm import get_llm


def _facts(state: dict) -> tuple[str, dict]:
    """The user's real numbers, as both prompt context and fallback material."""
    p = state.get("profile") or {}
    plan = state.get("active_plan") or {}
    macros = plan.get("macros") or {}
    facts = {
        "name": p.get("name"),
        "age": p.get("age"),
        "goal": p.get("goal"),
        "diet": p.get("dietary_prefs"),
        "allergies": p.get("allergies"),
        "training_days": p.get("training_days"),
        "experience": p.get("experience"),
        "calorie_target": plan.get("calorie_target"),
        "protein_g": macros.get("protein_g"),
        "carbs_g": macros.get("carbs_g"),
        "fat_g": macros.get("fat_g"),
    }
    lines = [f"{k}: {v}" for k, v in facts.items() if v not in (None, [], "")]
    return "\n".join(lines), facts


def _fallback_text(message: str, facts: dict) -> str:
    """Deterministic answer for the most common factual asks, so the offline
    provider still says something useful instead of a generic greeting."""
    q = (message or "").lower()
    cal, pro = facts.get("calorie_target"), facts.get("protein_g")
    if any(w in q for w in ("protein",)) and pro:
        return (
            f"Your daily protein target is **{pro} g**. Spread it across your meals — "
            f"roughly a quarter at breakfast and the rest over lunch, a snack and dinner."
        )
    if any(w in q for w in ("calorie", "kcal", "how much should i eat")) and cal:
        return f"Your daily target is **{cal} kcal**" + (f" with {pro} g protein." if pro else ".")
    if cal and pro:
        return (
            f"You're on **{cal} kcal / {pro} g protein** a day for your "
            f"'{facts.get('goal')}' goal. Ask me about your meals, training or progress."
        )
    return (
        "I can help with your meals, training, progress and safety. "
        "Generate a plan first and I'll have your targets to work from."
    )


def answer_agent(state: dict) -> dict:
    message = state.get("message") or ""
    context, facts = _facts(state)

    fallback = AnswerResult(answer=_fallback_text(message, facts))
    user = (
        f"User's question: {message}\n\n"
        f"Their stored numbers (authoritative — quote these, never invent):\n{context}\n\n"
        "Answer only what they asked, in 2-4 sentences."
    )
    result = get_llm().structured(
        system=COACH_SYSTEM, user=user, schema=AnswerResult, fallback=fallback
    )
    if not (result.answer or "").strip():
        result = fallback

    return {
        "answer_result": result.model_dump(),
        "steps": [trace("answer", (result.answer or "")[:60])],
    }
