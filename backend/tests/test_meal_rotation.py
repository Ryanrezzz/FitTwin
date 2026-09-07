"""Meal rotation — "I don't want this today" for a single slot.

The guarantees that matter: it changes only the slot asked for, it survives a
reload, it can never rotate into a forbidden dish, and it never dead-ends.
"""
from app.agents.tools.meal_builder import build_day, rotation_options

MEAT = ("chicken", "fish", "prawn", "keema", "mutton", "rohu", "basa")


def _meal(client, headers, slot_label):
    summary = client.get("/api/v1/dashboard/summary", headers=headers).json()
    return next(m for m in summary["today_meals"] if m["name"] == slot_label)


def test_rotate_changes_the_requested_meal(client, auth_headers, onboarded):
    before = _meal(client, auth_headers, "Dinner")
    r = client.post("/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["rotation"] == 1
    assert body["meal"]["items"] != before["items"]


def _by_name(client, headers):
    return {m["name"]: m for m in
            client.get("/api/v1/dashboard/summary", headers=headers).json()["today_meals"]}


def test_rotate_swaps_only_the_requested_dish(client, auth_headers, onboarded):
    """Per-meal, not per-week — the user's actual request.

    Other slots keep the SAME DISH. Their portions may flex by a few grams,
    because the day is still balanced to one calorie/protein target: if dinner
    changes, something has to absorb the difference. Only dinner is re-chosen.
    """
    before, _ = _by_name(client, auth_headers), None
    client.post("/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers)
    after = _by_name(client, auth_headers)

    for name in ("Breakfast", "Lunch", "Evening Snack"):
        assert before[name]["dish"] == after[name]["dish"], f"{name} was re-chosen"
    assert before["Dinner"]["dish"] != after["Dinner"]["dish"]


def test_rebalancing_other_meals_stays_small(client, auth_headers, onboarded):
    """The flex above must be a nudge, not a rewrite."""
    before = _by_name(client, auth_headers)
    client.post("/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers)
    after = _by_name(client, auth_headers)
    for name in ("Breakfast", "Lunch", "Evening Snack"):
        drift = abs(after[name]["kcal"] - before[name]["kcal"])
        assert drift <= 120, f"{name} moved {drift} kcal on an unrelated rotation"


def test_rotation_survives_a_reload(client, auth_headers, onboarded):
    rotated = client.post(
        "/api/v1/meals/rotate", json={"slot": "lunch"}, headers=auth_headers
    ).json()["meal"]
    assert _meal(client, auth_headers, "Lunch")["items"] == rotated["items"]


def test_rotating_repeatedly_keeps_offering_new_dishes(client, auth_headers, onboarded):
    seen = set()
    for _ in range(6):
        body = client.post(
            "/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers
        ).json()
        seen.add(body["meal"]["dish_id"])
    assert len(seen) >= 5, f"rotation kept repeating: {seen}"


def test_rotation_reports_how_many_options_exist(client, auth_headers, onboarded):
    body = client.post(
        "/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers
    ).json()
    assert body["options"] > 1


def test_reset_restores_the_original_picks(client, auth_headers, onboarded):
    original = _meal(client, auth_headers, "Dinner")
    for _ in range(3):
        client.post("/api/v1/meals/rotate", json={"slot": "dinner"}, headers=auth_headers)
    assert _meal(client, auth_headers, "Dinner")["items"] != original["items"]

    client.post("/api/v1/meals/rotate/reset", headers=auth_headers)
    assert _meal(client, auth_headers, "Dinner")["items"] == original["items"]


def test_unknown_slot_is_rejected(client, auth_headers, onboarded):
    r = client.post("/api/v1/meals/rotate", json={"slot": "brunch"}, headers=auth_headers)
    assert r.status_code == 422


def test_rotation_requires_auth(client):
    assert client.post("/api/v1/meals/rotate", json={"slot": "dinner"}).status_code == 401


def test_rotation_can_never_escape_the_diet():
    """Rotate a vegetarian through every dinner option — no meat may appear."""
    for slot in ("breakfast", "lunch", "snack", "dinner"):
        for prefs in (["vegan"], ["veg"], ["egg"]):
            for rot in range(rotation_options(slot, prefs, []) + 3):
                day = build_day(2000, 150, prefs, [], rotations={slot: rot})
                items = " ".join(i for m in day for i in m["items"]).lower()
                assert not any(w in items for w in MEAT), f"{prefs} {slot} rot={rot}"


def test_rotation_can_never_escape_allergies():
    for rot in range(rotation_options("dinner", ["nonveg"], ["dairy"]) + 3):
        day = build_day(2000, 150, ["nonveg"], ["dairy"], rotations={"dinner": rot})
        dinner = next(m for m in day if m["name"] == "Dinner")
        text = " ".join(dinner["items"]).lower()
        for dairy in ("paneer", "curd", "milk", "ghee", "buttermilk"):
            assert dairy not in text, f"rot={rot} served {dairy}"


def test_rotation_wraps_instead_of_dead_ending():
    """Rotating past the end must wrap, never produce an empty slot."""
    n = rotation_options("dinner", ["veg"], [])
    for rot in (0, n, n * 2 + 1):
        day = build_day(2000, 150, ["veg"], [], rotations={"dinner": rot})
        dinner = next(m for m in day if m["name"] == "Dinner")
        assert dinner["items"] and dinner["kcal"] > 0


def test_rotation_keeps_calories_in_range():
    """A rotated meal is still portion-scaled to its slot budget."""
    for rot in range(10):
        day = build_day(2000, 150, ["veg"], [], rotations={"dinner": rot})
        dinner = next(m for m in day if m["name"] == "Dinner")
        assert 300 <= dinner["kcal"] <= 800, f"rot={rot} -> {dinner['kcal']}"
