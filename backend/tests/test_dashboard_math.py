from datetime import date, timedelta

from app.agents.tools import dashboard_math as dm
from app.domain import ActivityLevel, Goal


def _profile(**over):
    base = {
        "sex": "male",
        "age": 28,
        "height_cm": 178,
        "weight_kg": 82.0,
        "goal": "lose",
        "activity_level": "moderate",
        "training_days": 4,
        "rate_kg_per_week": 0.5,
    }
    base.update(over)
    return base


def test_healthy_target_weight_lose_is_below_current():
    # 178cm → BMI22 ≈ 69.7kg; an 82kg "lose" user targets the healthy weight.
    assert dm.healthy_target_weight(178, 82, Goal.lose) < 82


def test_healthy_target_weight_lose_never_above_current():
    # already lean (60kg) wanting to lose → target clamped to current, not BMI22.
    assert dm.healthy_target_weight(178, 60, Goal.lose) == 60.0


def test_healthy_target_weight_gain_never_below_current():
    assert dm.healthy_target_weight(178, 60, Goal.gain) >= 60.0


def test_healthy_target_weight_maintain_equals_current():
    assert dm.healthy_target_weight(178, 75, Goal.maintain) == 75.0


def test_water_goal_rounds_to_50ml():
    g = dm.water_goal_ml(82)            # 35*82 = 2870 → nearest 50 = 2850
    assert g % 50 == 0
    assert g == 2850


def test_step_goal_by_activity():
    assert dm.step_goal(ActivityLevel.sedentary) == 6000
    assert dm.step_goal(ActivityLevel.very_active) == 12000


def test_weeks_to_goal_basic_and_edge_cases():
    assert dm.weeks_to_goal(82, 70, 0.5) == 24      # 12kg / 0.5 = 24 wks
    assert dm.weeks_to_goal(70, 70, 0.5) is None     # already there
    assert dm.weeks_to_goal(82, 70, 0) is None       # no rate


def test_summary_uses_plan_targets_when_present():
    plan = {"calorie_target": 1900, "macros": {"protein_g": 164, "carbs_g": 180, "fat_g": 53}}
    s = dm.dashboard_summary(_profile(), plan)
    assert s["calorie_target"] == 1900
    assert s["protein_target_g"] == 164
    # with an empty day, remaining == target
    assert s["calories_remaining"] == 1900
    assert s["protein_remaining_g"] == 164


def test_summary_derives_targets_without_a_plan():
    s = dm.dashboard_summary(_profile(), None)
    assert s["calorie_target"] > 0
    assert s["protein_target_g"] > 0
    assert s["step_goal"] == 9000
    assert s["workout_target_days"] == 4


def test_summary_prefers_explicit_target_weight():
    s = dm.dashboard_summary(_profile(target_weight_kg=75.0), None)
    assert s["target_weight_kg"] == 75.0
    assert s["est_goal_weeks"] == 14          # |82-75| / 0.5 = 14 wks


def test_streak_counts_consecutive_days_including_today():
    today = date(2026, 6, 24)
    active = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert dm.streak_days(active, today) == 3


def test_streak_breaks_on_a_gap_but_tolerates_no_log_today():
    today = date(2026, 6, 24)
    # nothing today, but yesterday + the day before → a live 2-day streak
    active = {today - timedelta(days=1), today - timedelta(days=2)}
    assert dm.streak_days(active, today) == 2
    # a gap two days ago stops the count
    gapped = {today, today - timedelta(days=2)}
    assert dm.streak_days(gapped, today) == 1


def test_workouts_done_in_week_window():
    today = date(2026, 6, 24)
    dates = {today, today - timedelta(days=3), today - timedelta(days=8)}  # last one is >7d
    assert dm.workouts_done_in_week(dates, today) == 2


def test_summary_reflects_todays_log():
    plan = {"calorie_target": 2000, "macros": {"protein_g": 160, "carbs_g": 200, "fat_g": 55}}
    today = {"calories": 1400, "protein_g": 120, "steps": 5000, "water_ml": 1000,
             "workouts_done_week": 2, "streak_days": 3}
    s = dm.dashboard_summary(_profile(), plan, today)
    assert s["calories_remaining"] == 600
    assert s["protein_remaining_g"] == 40
    assert s["steps"] == 5000
    assert s["workout_completion_pct"] == 50    # 2 of 4 days
    assert s["streak_days"] == 3
