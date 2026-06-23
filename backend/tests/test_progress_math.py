from datetime import date, timedelta

from app.agents.tools import progress_math as pm
from app.domain import Goal


def _series(start_weight, daily_delta, n):
    d0 = date(2026, 1, 1)
    return [(d0 + timedelta(days=i), start_weight + daily_delta * i) for i in range(n)]


def test_weight_trend_detects_loss():
    series = _series(80.0, -0.05, 14)     # losing 0.05 kg/day = 0.35 kg/wk
    trend = pm.weight_trend(series)
    assert trend.slope_kg_per_week < 0
    assert trend.slope_kg_per_week == round(-0.05 * 7, 3)
    assert trend.n_points == 14


def test_ewma_smooths_noise():
    # noisy around 80 should smooth near 80
    vals = [80, 81, 79, 80.5, 79.5, 80]
    assert 79 <= pm.ewma(vals) <= 81


def test_plateau_true_when_adherent_but_flat():
    flat = _series(80.0, 0.0, 14)
    trend = pm.weight_trend(flat)
    assert pm.plateau_detected(trend, Goal.lose, adherence_pct=92) is True


def test_not_plateau_when_still_losing():
    losing = _series(80.0, -0.05, 14)
    trend = pm.weight_trend(losing)
    assert pm.plateau_detected(trend, Goal.lose, adherence_pct=92) is False


def test_low_adherence_is_not_a_plateau():
    flat = _series(80.0, 0.0, 14)
    trend = pm.weight_trend(flat)
    assert pm.plateau_detected(trend, Goal.lose, adherence_pct=40) is False


def test_insufficient_data_is_not_a_plateau():
    flat = _series(80.0, 0.0, 3)
    trend = pm.weight_trend(flat)
    assert pm.plateau_detected(trend, Goal.lose, adherence_pct=95) is False


def test_maintain_goal_never_plateaus():
    flat = _series(80.0, 0.0, 30)
    trend = pm.weight_trend(flat)
    assert pm.plateau_detected(trend, Goal.maintain, adherence_pct=95) is False


def test_adherence_percentage():
    plan = {"calorie_target": 2000, "macros": {"protein_g": 160}}
    logs = [
        {"calories": 2000, "protein_g": 160},   # adherent
        {"calories": 1950, "protein_g": 150},   # adherent (within 10% / 90%)
        {"calories": 2600, "protein_g": 100},   # not adherent (over cals, low protein)
        {"calories": 2050, "protein_g": 145},   # adherent
    ]
    assert pm.adherence(logs, plan) == 75.0


def test_adherence_no_logs_is_zero():
    assert pm.adherence([], {"calorie_target": 2000, "macros": {"protein_g": 160}}) == 0.0
