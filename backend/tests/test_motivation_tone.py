"""The coach responds to the person, not to the dashboard.

Regression target — a real reported failure. Someone wrote:

    "i am feeling demotivated cant study cant workout it feel i cant loose my weight"

and got back:

    "Your streak is at 0 days — complete one small workout..."

Two defects: the agent never received their message (it built its own prompt
from the streak count), and it prescribed the exact thing they'd said they
couldn't do while opening on a number that reads as an accusation.
"""
from app.agents.motivation import _tone, motivation_agent
from app.agents.orchestrator import classify_intent

HARD_DAY = "i am feeling demotivated cant study cant workout it feel i cant loose my weight"


def _reply(message, logs=None):
    return motivation_agent({"message": message, "history": {"logs": logs or []}})[
        "motivation_result"
    ]


# ── routing ──────────────────────────────────────────────────────────────────
def test_low_mood_reaches_the_motivation_agent_not_the_faq():
    """"I feel hopeless" used to fall through to the factual Q&A agent, which
    replied by quoting the user's calorie target."""
    for msg in (
        HARD_DAY,
        "i feel hopeless nothing is working",
        "im burnt out",
        "i feel like a failure",
    ):
        assert classify_intent(msg, "chat") == "motivation", msg


def test_topic_questions_are_not_swallowed_by_the_mood_rules():
    assert classify_intent("give me a meal plan", "chat") == "nutrition_request"
    assert classify_intent("my knee hurts", "chat") == "injury"
    assert classify_intent("how much protein should I eat?", "chat") == "general"


# ── tone detection ───────────────────────────────────────────────────────────
def test_tone_is_classified_from_what_they_wrote():
    assert _tone(HARD_DAY) == "struggling"
    assert _tone("i feel hopeless") == "distress"
    assert _tone("lets go, feeling strong") == "upbeat"


# ── the reply itself (deterministic provider) ────────────────────────────────
def test_reply_does_not_open_with_a_zero_streak():
    """Telling someone who feels like a failure that their streak is 0 is the
    least useful sentence available."""
    msg = _reply(HARD_DAY)["message"].lower()
    assert "0-day" not in msg and "0 day" not in msg
    assert "streak" not in msg


def test_reply_does_not_prescribe_the_thing_they_said_they_cannot_do():
    msg = _reply(HARD_DAY)["message"].lower()
    assert "workout" not in msg
    assert "work out" not in msg


def test_struggling_reply_gives_permission_rather_than_pressure():
    msg = _reply(HARD_DAY)["message"].lower()
    assert any(p in msg for p in ("don't owe", "doesn't undo", "enough for today"))


def test_distress_reply_points_toward_a_person():
    msg = _reply("i feel hopeless, there's no point")["message"].lower()
    assert "distress" == _reply("i feel hopeless, there's no point")["tone"]
    assert any(p in msg for p in ("talk to someone", "trust", "doctor"))
    # never a diagnosis, and never turned into a training lesson
    assert "workout" not in msg


def test_upbeat_path_still_reports_the_streak():
    logs = [{"workout_done": True, "calories": 2000} for _ in range(3)]
    result = _reply("feeling strong today", logs)
    assert result["tone"] == "upbeat"
    assert "3-day streak" in result["message"]


def test_the_message_actually_reaches_the_agent():
    """The original bug in one assertion: tone can only vary if the text is read."""
    assert _reply("i give up").get("tone") != _reply("feeling strong").get("tone")
