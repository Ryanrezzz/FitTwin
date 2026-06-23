import pytest

from app.agents.tools import nutrition_math as nm
from app.domain import ActivityLevel, Goal, Sex


def test_bmr_mifflin_male_known_value():
    # 80kg, 180cm, 30y male -> 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert nm.bmr_mifflin(Sex.male, 80, 180, 30) == pytest.approx(1780.0)


def test_bmr_mifflin_female_known_value():
    # 65kg, 165cm, 28y female -> 650 + 1031.25 - 140 - 161 = 1380.25
    assert nm.bmr_mifflin(Sex.female, 65, 165, 28) == pytest.approx(1380.25)


def test_bmr_rejects_nonpositive():
    with pytest.raises(ValueError):
        nm.bmr_mifflin(Sex.male, 0, 180, 30)


def test_tdee_applies_multiplier():
    assert nm.tdee(1780, ActivityLevel.moderate) == pytest.approx(1780 * 1.55)


def test_calorie_target_lose_creates_deficit():
    t = 2500
    out = nm.calorie_target(t, Goal.lose, rate_kg_per_week=0.5)
    assert out < t
    # 0.5 kg/wk ~= 550 kcal/day deficit -> ~1950, above the 25% floor (1875)
    assert out == pytest.approx(1950, abs=2)


def test_calorie_target_respects_max_deficit_clamp():
    t = 2000
    # an aggressive 2 kg/wk would be ~2200 kcal deficit -> impossible; clamp to 25%
    out = nm.calorie_target(t, Goal.lose, rate_kg_per_week=2.0)
    assert out == pytest.approx(t * 0.75, abs=1)


def test_calorie_target_maintain_equals_tdee():
    assert nm.calorie_target(2200, Goal.maintain) == 2200


def test_macros_sum_close_to_calories():
    m = nm.macros(2000, 80, Goal.lose)
    assert m.protein_g == 160          # 2.0 g/kg * 80
    assert abs(m.as_kcal() - 2000) <= 12  # rounding tolerance


def test_full_targets_shape():
    out = nm.full_targets(Sex.male, 80, 180, 30, ActivityLevel.moderate, Goal.lose)
    assert set(out) == {"bmr", "tdee", "calories", "macros"}
    assert set(out["macros"]) == {"protein_g", "carbs_g", "fat_g"}
