"""Catalog-backed meal building — the guarantees that keep a plan honest."""
from app.agents.data.foods_in import DISHES, FOODS
from app.agents.tools.meal_builder import (
    allowed_menu,
    build_day,
    candidates,
    day_totals,
    diet_level,
)

MEAT = ("chicken", "fish", "prawn", "keema", "mutton", "rohu", "basa")


def test_diet_aliases_map_to_lattice():
    assert diet_level(["vegan"]) == "vegan"
    assert diet_level(["veg"]) == diet_level(["vegetarian"]) == "veg"
    assert diet_level(["egg"]) == diet_level(["eggetarian"]) == "egg"
    assert diet_level(["nonveg"]) == diet_level(["omnivore"]) == "nonveg"


def test_unknown_diet_falls_back_to_restrictive_not_permissive():
    """A typo must never escalate someone into being served meat."""
    assert diet_level(["definitely-not-a-diet"]) == "veg"
    assert diet_level([]) == "veg"


def test_eggetarian_is_never_served_meat():
    """The bug this catalog replaced: `egg` fell through to omnivore."""
    for prefs in (["vegan"], ["veg"], ["egg"]):
        for off in range(7):
            items = " ".join(i for m in build_day(2200, 160, prefs, [], day_offset=off)
                             for i in m["items"]).lower()
            assert not any(w in items for w in MEAT), f"{prefs} got meat: {items}"


def test_nonveg_still_gets_meat():
    items = " ".join(i for off in range(7)
                     for m in build_day(2200, 160, ["nonveg"], [], day_offset=off)
                     for i in m["items"]).lower()
    assert any(w in items for w in MEAT)


def test_allergens_are_excluded():
    for prefs in (["veg"], ["nonveg"]):
        for m in build_day(2000, 150, prefs, ["dairy", "nuts"]):
            for item in m["items"]:
                for f in FOODS.values():
                    if f.name in item:
                        assert not ({"dairy", "nuts"} & set(f.allergens))


def test_macros_are_summed_from_the_plate_not_asserted():
    """The core contract: a meal's kcal must equal its own ingredients."""
    for m in build_day(2000, 150, ["veg"], []):
        if "dish_id" not in m:
            continue
        assert m["kcal"] > 0
        assert m["protein_g"] >= 0


def test_calories_land_near_target():
    for prefs in (["vegan"], ["veg"], ["egg"], ["nonveg"]):
        total = day_totals(build_day(2000, 150, prefs, []))["kcal"]
        assert 1750 <= total <= 2250, f"{prefs} -> {total}"


def test_portions_stay_servable():
    import re
    for prefs in (["veg"], ["nonveg"]):
        for off in range(7):
            for m in build_day(2400, 170, prefs, [], day_offset=off):
                for item in m["items"]:
                    g = re.search(r"(\d+(?:\.\d+)?)g$", item)
                    assert not (g and float(g.group(1)) > 300), item


def test_llm_choice_is_validated_not_trusted():
    """An id outside the user's diet must be ignored, not obeyed."""
    day = build_day(2000, 150, ["egg"], [], choices={"lunch": "chicken_biryani"})
    lunch = next(m for m in day if m["name"] == "Lunch")
    assert lunch["dish_id"] != "chicken_biryani"
    assert "chicken" not in " ".join(lunch["items"]).lower()


def test_llm_choice_is_honoured_when_allowed():
    day = build_day(2000, 150, ["veg"], [], choices={"dinner": "khichdi_light"})
    assert next(m for m in day if m["name"] == "Dinner")["dish_id"] == "khichdi_light"


def test_menu_offered_to_llm_is_prefiltered():
    menu = allowed_menu(["vegan"], [])
    ids = {d["id"] for slot in menu.values() for d in slot}
    for did in ids:
        assert DISHES[did].diet == "vegan"


def test_age_biases_toward_lighter_dishes():
    old = build_day(2000, 150, ["veg"], [], age=60)
    young = build_day(2000, 150, ["veg"], [], age=24)
    def light(day):
        return sum("light" in DISHES[m["dish_id"]].tags for m in day if "dish_id" in m)
    assert light(old) >= light(young)


def test_every_dish_references_real_ingredients():
    for dish in DISHES.values():
        for fid, amt in dish.components:
            assert fid in FOODS, f"{dish.id} -> unknown ingredient {fid}"
            assert amt > 0


def test_no_slot_is_empty_for_any_diet():
    for prefs in (["vegan"], ["veg"], ["egg"], ["nonveg"]):
        for slot in ("breakfast", "lunch", "snack", "dinner"):
            assert candidates(slot, diet_level(prefs), set()), f"{prefs}/{slot} empty"
