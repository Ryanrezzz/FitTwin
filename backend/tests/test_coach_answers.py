"""The AI Coach answers the question it was asked.

Regression target: every unrecognised message used to fall through to `general`,
route to the Progress agent, and come back as a Weekly Report — so "how much
protein should I eat?", "my knee hurts" and "hi" all returned the same block of
trend statistics.
"""
from app.agents.orchestrator import classify_intent
from app.agents.runner import run_coach

PROFILE = {
    "name": "Ravi", "age": 34, "sex": "male", "height_cm": 175, "weight_kg": 84,
    "goal": "lose", "activity_level": "moderate", "dietary_prefs": ["veg"],
    "allergies": [], "experience": "intermediate", "equipment": ["dumbbells"],
    "training_days": 4, "rate_kg_per_week": 0.5,
}
PLAN = {"calorie_target": 2192, "macros": {"protein_g": 168, "carbs_g": 243, "fat_g": 61}}


def _reply(message):
    out = run_coach(profile=PROFILE, message=message, active_plan=PLAN, trigger="chat")
    return out["final"]


def test_factual_questions_are_not_answered_with_a_weekly_report():
    for q in ("how much protein should I eat?", "what is my calorie target?"):
        final = _reply(q)
        assert "Weekly Report" not in final["message"], q
        assert "progress" not in final["agents_used"], q


def test_factual_question_returns_the_real_number_offline():
    """The deterministic fallback must still answer, with no LLM configured."""
    final = _reply("how much protein should I eat?")
    assert "168" in final["message"]


def test_injury_is_never_answered_with_a_streak_nudge():
    final = _reply("my knee hurts when I squat")
    assert final["intent"] == "injury"
    msg = final["message"].lower()
    assert "weekly report" not in msg
    assert "streak" not in msg
    assert "not a substitute for professional medical advice" in msg


def test_greeting_is_short_and_not_a_status_dump():
    final = _reply("hi")
    assert final["intent"] == "greeting"
    assert "Weekly Report" not in final["message"]


def test_greeting_words_do_not_match_inside_other_words():
    """'hi' is inside 'which'; 'hey' is inside 'they'."""
    assert classify_intent("which day is leg day?", "chat") != "greeting"
    assert classify_intent("they told me to rest", "chat") != "greeting"


def test_asking_what_to_eat_returns_actual_food():
    """Printing macros alone was the least useful reply the coach produced."""
    final = _reply("what should I eat tonight?")
    assert final["intent"] == "nutrition_request"
    msg = final["message"]
    assert "Breakfast" in msg and "Dinner" in msg
    # a real portion, not just a macro line
    assert "g" in msg and any(ch.isdigit() for ch in msg)


def test_plan_requests_still_build_a_plan():
    """The look-up rule must not swallow genuine plan requests."""
    assert classify_intent("give me a meal plan", "chat") == "nutrition_request"
    assert classify_intent("make me a vegetarian meal plan", "chat") == "nutrition_request"


def test_safety_warning_is_not_stapled_to_every_reply():
    """Repeating the same clamp after "hi" trains users to ignore warnings."""
    aggressive = {**PROFILE, "rate_kg_per_week": 1.0}
    out = run_coach(profile=aggressive, message="hi", active_plan=PLAN, trigger="chat")
    assert "aggressive" not in out["final"]["message"].lower()


def test_progress_concern_still_reaches_the_progress_agent():
    final = _reply("I haven't lost weight this week")
    assert "progress" in final["agents_used"]
