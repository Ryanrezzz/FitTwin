from app.agents.tools import food_parser as fp


def test_parses_quantity_and_food():
    items = fp.parse_food("250g chicken and rice")
    names = {i.name for i in items}
    assert "chicken" in names
    assert "rice" in names
    chicken = next(i for i in items if i.name == "chicken")
    assert chicken.amount == 250
    # 250g chicken -> ~2.5x of per-100g (31g protein) ~= 77.5g protein
    assert chicken.protein_g == 77.5


def test_default_serving_when_no_quantity():
    items = fp.parse_food("rice")
    rice = next(i for i in items if i.name == "rice")
    assert rice.amount == 150  # default serving


def test_each_unit_food():
    items = fp.parse_food("3 eggs")
    egg = next(i for i in items if i.name == "egg")
    assert egg.amount == 3
    assert egg.protein_g == round(6.3 * 3, 1)


def test_aliases_resolve():
    items = fp.parse_food("grilled chicken breast with dal")
    names = {i.name for i in items}
    assert "chicken" in names
    assert "lentils" in names      # "dal" alias


def test_summarize_totals():
    items = fp.parse_food("250g chicken and rice")
    total = fp.summarize(items)
    assert total["calories"] > 0
    assert total["protein_g"] >= 77.5
    assert set(total) == {"calories", "protein_g", "carbs_g", "fat_g", "items"}


def test_unknown_food_ignored():
    assert fp.parse_food("a glass of unicorn juice") == []
