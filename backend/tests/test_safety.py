from app.agents.safety import safety_agent


def _state(profile, nutrition=None, message=None):
    return {"profile": profile, "nutrition_result": nutrition, "message": message}


def test_calorie_floor_clamps_up_for_female():
    profile = {"sex": "female", "weight_kg": 50, "goal": "lose"}
    nutrition = {"calories": 950, "macros": {"protein_g": 100, "carbs_g": 50, "fat_g": 30}}
    out = safety_agent(_state(profile, nutrition))
    assert out["nutrition_result"]["calories"] == 1200      # raised to female floor
    assert out["safety_verdict"]["clamps"]                   # a clamp was recorded
    # macros recomputed at the floor, not left stale
    assert out["nutrition_result"]["macros"]["protein_g"] > 0


def test_safe_plan_passes_without_clamp():
    profile = {"sex": "male", "weight_kg": 82, "goal": "lose"}
    nutrition = {"calories": 1950, "macros": {"protein_g": 164, "carbs_g": 150, "fat_g": 54}}
    out = safety_agent(_state(profile, nutrition))
    assert out["nutrition_result"]["calories"] == 1950
    assert out["safety_verdict"]["clamps"] == []
    assert out["safety_verdict"]["approved"] is True


def test_overtraining_warning():
    profile = {"sex": "male", "weight_kg": 82, "goal": "gain", "training_days": 7}
    out = safety_agent(_state(profile))
    assert any("overtraining" in w.lower() for w in out["safety_verdict"]["warnings"])


def test_aggressive_rate_warning():
    profile = {"sex": "male", "weight_kg": 80, "goal": "lose", "rate_kg_per_week": 1.5}
    out = safety_agent(_state(profile))
    assert any("aggressive" in w.lower() for w in out["safety_verdict"]["warnings"])


def test_medical_red_flag_sets_disclaimer():
    profile = {"sex": "female", "weight_kg": 60, "goal": "lose"}
    out = safety_agent(_state(profile, message="should i just starve myself to lose faster?"))
    assert out["safety_verdict"]["requires_disclaimer"] is True
    assert out["safety_verdict"]["warnings"]
