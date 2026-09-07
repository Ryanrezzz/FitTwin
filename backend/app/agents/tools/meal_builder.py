"""Assemble a day's meals from the food catalog — deterministic, no LLM.

THE CONTRACT: a meal's kcal/protein are SUMMED from the portions on the plate.
We pick a dish, scale its staples/protein to fit the slot's budget, round the
portions to amounts a human can actually serve, then report the macros of THAT
rounded plate. The displayed number always describes the displayed food, even
when it lands a little off the budget — an honest 690 beats a fictional 700.

Selection order (all deterministic):
  1. HARD filter — diet lattice + allergens. Never negotiable.
  2. Score    — how close the scaled dish gets to the slot's kcal AND protein.
  3. Age bias — 50+ favours `light` dishes; under-30 tolerates `hearty`.
  4. Rotate   — pick from the top candidates by day_offset, so days differ.
"""
from __future__ import annotations

from app.agents.data.foods_in import (
    DIET_ALIASES,
    DIET_ORDER,
    DISHES,
    FOODS,
    Dish,
    dishes_for_slot,
)

# Indian eating rhythm: breakfast, a main lunch, an evening chai-time snack,
# then a lighter dinner. Fractions are of the day's total target.
MEAL_PLAN_SLOTS: tuple[tuple[str, str, float], ...] = (
    ("breakfast", "Breakfast", 0.27),
    ("lunch", "Lunch", 0.35),
    ("snack", "Evening Snack", 0.10),
    ("dinner", "Dinner", 0.28),
)

_PIECE_MIN = 1.0
_SCALE_MIN, _SCALE_MAX = 0.5, 2.0

# Absolute portion ceilings — scaling alone produced "rohu fish 360g", which is
# arithmetically on-target and nobody's dinner. A plan has to be servable.
_CAP_BY_UNIT = {"g": 300.0, "ml": 400.0, "piece": 6.0}
_CAP_BY_FOOD = {
    "chicken": 220, "chicken_thigh": 200, "fish_rohu": 220, "fish_basa": 220,
    "prawns": 200, "keema": 180, "paneer": 200, "tofu": 250, "whey": 60,
    "egg": 4, "egg_white": 8, "oil": 20, "ghee": 15, "peanuts": 60,
    "almonds": 40, "cashews": 40, "walnuts": 30, "sesame": 40, "chia": 25,
}


def diet_level(dietary_prefs: list[str]) -> str:
    """Map profile prefs onto the lattice. Unknown/empty -> `veg` (restrictive).

    Falling back to `veg` rather than `nonveg` matters: a typo must never
    escalate someone's diet into being served meat.
    """
    levels = [DIET_ALIASES[p.lower().strip()] for p in dietary_prefs
              if p.lower().strip() in DIET_ALIASES]
    if not levels:
        return "veg"
    return min(levels, key=lambda d: DIET_ORDER[d])


def _round_amount(food_id: str, amount: float) -> float:
    """Round to a servable portion and clamp to a realistic ceiling."""
    unit = FOODS[food_id].unit
    cap = min(_CAP_BY_FOOD.get(food_id, float("inf")), _CAP_BY_UNIT.get(unit, float("inf")))
    amount = min(amount, cap)
    if unit == "piece":
        return max(_PIECE_MIN, round(amount))
    if unit == "ml":
        return max(10.0, round(amount / 10) * 10)
    return max(5.0, round(amount / 5) * 5)


def fit_dish(dish: Dish, kcal_target: float) -> tuple[dict[str, float], dict[str, float]]:
    """Scale a dish's `scalable` components toward a calorie budget.

    Solves  fixed + scalable*x = target  for x, clamps it, then rounds each
    portion to a servable amount and returns the macros of the ROUNDED plate.
    """
    if not dish.scalable:
        return {}, dish.macros()

    fixed = sum(FOODS[f].scaled(a)[0] for f, a in dish.components if f not in dish.scalable)
    flex = sum(FOODS[f].scaled(a)[0] for f, a in dish.components if f in dish.scalable)
    if flex <= 0:
        return {}, dish.macros()

    x = (kcal_target - fixed) / flex
    x = max(_SCALE_MIN, min(_SCALE_MAX, x))

    # Round each scalable portion, then back out the effective factor it implies,
    # so the reported macros match the amounts we actually print.
    scale: dict[str, float] = {}
    for fid, amt in dish.components:
        if fid in dish.scalable:
            scale[fid] = _round_amount(fid, amt * x) / amt
    return scale, dish.macros(scale)


def _score(dish: Dish, kcal_t: float, prot_t: float, age: int) -> float:
    """Lower is better. Protein is weighted above calories: staple-scaling can
    always fix calories, but only dish CHOICE can fix protein."""
    _, m = fit_dish(dish, kcal_t)
    kcal_err = abs(m["kcal"] - kcal_t) / max(kcal_t, 1)
    prot_err = abs(m["protein_g"] - prot_t) / max(prot_t, 1)
    penalty = 0.0
    if age >= 50:
        if "light" in dish.tags:
            penalty -= 0.12
        if "hearty" in dish.tags:
            penalty += 0.12
    elif age < 30 and "hearty" in dish.tags:
        penalty -= 0.05
    return kcal_err + 1.4 * prot_err + penalty


def candidates(slot: str, level: str, allergens: set[str]) -> list[Dish]:
    """Hard filter only: diet lattice + allergens."""
    cap = DIET_ORDER[level]
    return [
        d for d in dishes_for_slot(slot)
        if DIET_ORDER[d.diet] <= cap and not (d.allergens & allergens)
    ]


def _label(food_id: str, amount: float) -> str:
    food = FOODS[food_id]
    if food.unit == "piece":
        return f"{amount:g} x {food.name}"
    return f"{food.name} {amount:g}{food.unit}"


def _amount_in(item: str, food_name: str) -> float:
    """Recover the numeric portion already printed in an item label."""
    digits = "".join(ch for ch in item.replace(food_name, " ") if ch.isdigit() or ch == ".")
    try:
        return float(digits)
    except ValueError:
        return 0.0


def _portion_text(dish: Dish, scale: dict[str, float]) -> list[str]:
    return [_label(fid, amt * scale.get(fid, 1.0)) for fid, amt in dish.components]


# Protein boosters, best-first per diet level. Hitting 2 g/kg on Indian
# vegetarian food genuinely needs a deliberate top-up — this is what a coach
# would actually say ("add a scoop of whey"), done in data instead of prose.
_BOOSTERS: dict[str, tuple[str, ...]] = {
    "vegan": ("soy_chunks", "tofu", "peanuts"),
    "veg": ("whey", "paneer", "curd", "soy_chunks", "tofu"),
    "egg": ("whey", "egg", "paneer", "curd", "soy_chunks"),
    "nonveg": ("whey", "chicken", "egg", "paneer", "curd"),
}


def _protein_topup(
    level: str, allergens: set[str], gap_g: float
) -> tuple[str, float, dict[str, float]] | None:
    """Smallest sensible portion of an allowed protein food that closes `gap_g`."""
    for fid in _BOOSTERS[level]:
        food = FOODS[fid]
        if set(food.allergens) & allergens or DIET_ORDER[food.diet] > DIET_ORDER[level]:
            continue
        if food.p <= 0:
            continue
        amount = _round_amount(fid, gap_g / (food.p / food.ref))
        k, p, c, f = food.scaled(amount)
        return fid, amount, {"kcal": k, "protein_g": p, "carbs_g": c, "fat_g": f}
    return None


def build_day(
    calories: int,
    protein_g: int,
    dietary_prefs: list[str],
    allergies: list[str],
    age: int = 30,
    day_offset: int = 0,
    top_k: int = 5,
    choices: dict[str, str] | None = None,
    rotations: dict[str, int] | None = None,
) -> list[dict]:
    """One day of meals whose numbers are computed from the food on the plate.

    `choices` optionally forces a dish id per slot (this is how the LLM gets to
    pick WHICH dish while the catalog still decides HOW MUCH). An id that is
    unknown, or not allowed for this diet/allergy set, is ignored rather than
    trusted — the deterministic ranking then fills that slot.

    `rotations` walks a slot further down its ranked list — the "I don't want
    this today" button. Rotation 0 is the default pick, so an un-rotated day is
    byte-identical to before. It steps through the WHOLE allowed list (~30 dishes
    per slot), not just the top few, and wraps, so a user can never rotate into
    an empty slot or into something their diet forbids.
    """
    level = diet_level(dietary_prefs)
    allerg = {a.lower().strip() for a in allergies if a.strip()}

    meals: list[dict] = []
    used: set[str] = set()
    for i, (slot, label, frac) in enumerate(MEAL_PLAN_SLOTS):
        kcal_t, prot_t = calories * frac, protein_g * frac
        pool = [d for d in candidates(slot, level, allerg) if d.id not in used]
        if not pool:
            meals.append({"name": label, "items": ["(no dish matches these restrictions)"],
                          "kcal": 0, "protein_g": 0})
            continue
        picked = (choices or {}).get(slot)
        allowed = {d.id: d for d in candidates(slot, level, allerg)}
        if picked in allowed:
            dish = allowed[picked]
        else:
            ranked = sorted(pool, key=lambda d: _score(d, kcal_t, prot_t, age))
            width = max(1, min(top_k, len(ranked)))
            base = (i + day_offset) % width
            dish = ranked[(base + (rotations or {}).get(slot, 0)) % len(ranked)]
        used.add(dish.id)

        scale, m = fit_dish(dish, kcal_t)
        meals.append({
            "name": label,
            "slot": slot,
            "dish": dish.name,
            "dish_id": dish.id,
            "items": _portion_text(dish, scale),
            "kcal": round(m["kcal"]),
            "protein_g": round(m["protein_g"]),
            "carbs_g": round(m["carbs_g"]),
            "fat_g": round(m["fat_g"]),
        })

    _apply_protein_topup(meals, protein_g, calories, level, allerg)
    return meals


def _apply_protein_topup(
    meals: list[dict], protein_g: int, calories: int, level: str, allergens: set[str]
) -> None:
    """Close a protein shortfall with a real portion, then pay for its calories.

    Two honest steps: add the booster to the evening snack, then shrink the
    dinner staple by the calories it cost, so the day still lands on target
    instead of quietly drifting over it.
    """
    gap = protein_g - sum(m["protein_g"] for m in meals)
    if gap < 8:
        return
    top = _protein_topup(level, allergens, gap)
    if top is None:
        return
    fid, amount, add = top
    food = FOODS[fid]

    # Put the booster where it distorts the day least. Dumping it all on the
    # snack turned a ~220 kcal "Evening Snack" into 455 kcal, which reads as a
    # mistake even though the arithmetic was right. Prefer the slot furthest
    # under its own budget.
    budgets = {slot: calories * frac for slot, _, frac in MEAL_PLAN_SLOTS}
    hosts = [m for m in meals if m.get("slot") in ("snack", "breakfast")]
    snack = min(
        hosts,
        key=lambda m: m["kcal"] / max(budgets.get(m.get("slot"), 1), 1),
        default=None,
    )
    if snack is None:
        return
    # If the snack already contains this food, grow that portion instead of
    # listing it twice ("whey protein 30g ... whey protein 35g").
    idx = next((i for i, s in enumerate(snack["items"]) if food.name in s), None)
    if idx is None:
        snack["items"].append(_label(fid, amount))
    else:
        prev = _amount_in(snack["items"][idx], food.name)
        snack["items"][idx] = _label(fid, _round_amount(fid, prev + amount))
    for key, src in (("kcal", "kcal"), ("protein_g", "protein_g"),
                     ("carbs_g", "carbs_g"), ("fat_g", "fat_g")):
        snack[key] = round(snack.get(key, 0) + add[src])

    # Pay for the added calories across BOTH main meals rather than gutting one:
    # a 370 kcal dinner is not a dinner. Only claw back an actual overshoot.
    over = sum(m["kcal"] for m in meals) - calories
    if over <= 0:
        return
    mains = [m for m in meals if m.get("slot") in ("lunch", "dinner") and "dish_id" in m]
    if not mains:
        return
    share = over / len(mains)
    for meal in mains:
        dish = DISHES[meal["dish_id"]]
        scale, m2 = fit_dish(dish, max(meal["kcal"] - share, meal["kcal"] * 0.75))
        meal["items"] = _portion_text(dish, scale)
        meal.update(kcal=round(m2["kcal"]), protein_g=round(m2["protein_g"]),
                    carbs_g=round(m2["carbs_g"]), fat_g=round(m2["fat_g"]))


def day_totals(meals: list[dict]) -> dict[str, int]:
    return {
        "kcal": sum(m["kcal"] for m in meals),
        "protein_g": sum(m["protein_g"] for m in meals),
    }


def allowed_menu(dietary_prefs: list[str], allergies: list[str]) -> dict[str, list[dict]]:
    """The dish ids a user is permitted, per slot — the menu handed to the LLM.

    Pre-filtered, so the model physically cannot name a dish that breaks the
    user's diet or allergies: the constraint lives in the data, not the prompt.
    """
    level = diet_level(dietary_prefs)
    allerg = {a.lower().strip() for a in allergies if a.strip()}
    return {
        slot: [{"id": d.id, "name": d.name, "tags": list(d.tags)}
               for d in candidates(slot, level, allerg)]
        for slot, _, _ in MEAL_PLAN_SLOTS
    }


def rotation_options(
    slot: str, dietary_prefs: list[str], allergies: list[str]
) -> int:
    """How many dishes a user can rotate through in this slot (for the UI)."""
    return len(candidates(slot, diet_level(dietary_prefs),
                          {a.lower().strip() for a in allergies if a.strip()}))
