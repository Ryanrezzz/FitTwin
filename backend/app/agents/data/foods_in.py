"""India-first food catalog — the macro source of truth for meal planning.

WHY THIS EXISTS
---------------
Meal calories used to be `daily_target * meal_fraction`: a *budget* printed next
to an unrelated dish name. Nothing ever measured the food. This catalog inverts
that — dishes are RECIPES over ingredients with real per-unit macros, so a meal's
kcal is SUMMED FROM WHAT'S ON THE PLATE, and portions are scaled to hit the
target. The number and the food finally describe the same thing.

VALUES: per-100 g (or per natural unit) reference values in the range published
by IFCT 2017 / USDA FDC for cooked-as-usual Indian preparations. They are
reference estimates, not lab assays — good to roughly +/-10%, which is well
inside the error of Mifflin-St Jeor itself. Treat them as planning figures.

DIET IS A LATTICE, not four separate menus:

    vegan  <  veg  <  egg  <  nonveg

Every food carries ONE diet tag; a user sees everything at or below their level.
Write `dal_tadka` once as vegan and it serves all four diets — which is what
makes a large catalog cheap, and why an eggetarian can no longer be handed
chicken (the old three-bank design had no slot for `egg` at all).
"""
# ruff: noqa: E501 — the food and dish tables are column-aligned on purpose:
# one row per item reads as data. Wrapping them would hurt reviewability.
from __future__ import annotations

from dataclasses import dataclass

# ── diet lattice ──────────────────────────────────────────────────────────────
DIET_ORDER: dict[str, int] = {"vegan": 0, "veg": 1, "egg": 2, "nonveg": 3}

# UI / profile values -> lattice level. Anything unknown falls back to the most
# RESTRICTIVE sensible level (veg) rather than silently serving meat.
DIET_ALIASES: dict[str, str] = {
    "vegan": "vegan",
    "veg": "veg", "vegetarian": "veg", "pure_veg": "veg",
    "egg": "egg", "eggetarian": "egg", "ovo": "egg", "ovo_vegetarian": "egg",
    "nonveg": "nonveg", "non-veg": "nonveg", "non_vegetarian": "nonveg",
    "omnivore": "nonveg", "nonvegetarian": "nonveg",
}

ALLERGENS = ("dairy", "gluten", "nuts", "soy", "egg", "seafood", "sesame")


@dataclass(frozen=True)
class Food:
    """Macros per `ref` of `unit` (e.g. 100 g, 1 piece, 100 ml)."""

    id: str
    name: str
    unit: str          # g | ml | piece
    ref: float
    kcal: float
    p: float
    c: float
    f: float
    diet: str
    allergens: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def scaled(self, amount: float) -> tuple[float, float, float, float]:
        k = amount / self.ref
        return self.kcal * k, self.p * k, self.c * k, self.f * k


def _F(i, n, unit, ref, kcal, p, c, f, diet, alg=(), al=()):
    return Food(i, n, unit, ref, kcal, p, c, f, diet, alg, al)


# ── ingredients ───────────────────────────────────────────────────────────────
# id, name, unit, ref, kcal, protein, carbs, fat, diet, allergens, aliases
_ALL: list[Food] = [
    # grains & carbs (dry/raw unless noted)
    _F("rice_raw", "rice (dry)", "g", 100, 345, 6.8, 78.0, 0.5, "vegan", (), ("rice", "chawal")),
    _F("rice_cooked", "steamed rice", "g", 100, 130, 2.7, 28.0, 0.3, "vegan", (), ("cooked rice",)),
    _F("atta", "whole-wheat flour", "g", 100, 340, 12.0, 72.0, 1.8, "vegan", ("gluten",), ("atta", "wheat flour")),
    _F("roti", "roti", "piece", 1, 110, 3.3, 21.0, 1.7, "vegan", ("gluten",), ("chapati", "phulka", "roti")),
    _F("paratha", "paratha", "piece", 1, 180, 4.2, 25.0, 7.0, "veg", ("gluten", "dairy"), ("paratha",)),
    _F("poha_dry", "poha (dry)", "g", 100, 350, 6.6, 77.0, 1.2, "vegan", (), ("poha", "flattened rice")),
    _F("oats_dry", "oats (dry)", "g", 100, 389, 16.9, 66.0, 6.9, "vegan", ("gluten",), ("oats", "oatmeal")),
    _F("suji", "suji / rava", "g", 100, 360, 12.7, 73.0, 1.1, "vegan", ("gluten",), ("rava", "semolina", "suji")),
    _F("idli", "idli", "piece", 1, 58, 2.0, 12.0, 0.3, "vegan", (), ("idli",)),
    _F("dosa", "dosa", "piece", 1, 133, 2.7, 22.0, 3.7, "vegan", (), ("dosa",)),
    _F("bread", "bread slice", "piece", 1, 66, 2.3, 12.0, 0.8, "vegan", ("gluten",), ("bread", "toast")),
    _F("potato", "potato", "g", 100, 77, 2.0, 17.0, 0.1, "vegan", (), ("aloo", "potato")),
    _F("sweet_potato", "sweet potato", "g", 100, 86, 1.6, 20.0, 0.1, "vegan", (), ("shakarkandi",)),
    _F("quinoa", "quinoa (dry)", "g", 100, 368, 14.0, 64.0, 6.0, "vegan", (), ("quinoa",)),
    _F("jowar", "jowar flour", "g", 100, 349, 10.4, 72.0, 3.2, "vegan", (), ("jowar", "sorghum")),
    _F("bajra", "bajra flour", "g", 100, 361, 11.6, 67.0, 5.0, "vegan", (), ("bajra", "pearl millet")),
    _F("ragi", "ragi flour", "g", 100, 328, 7.3, 72.0, 1.3, "vegan", (), ("ragi", "finger millet")),
    _F("vermicelli", "vermicelli (dry)", "g", 100, 350, 12.0, 71.0, 1.5, "vegan", ("gluten",), ("semiya", "vermicelli")),
    _F("sabudana", "sabudana", "g", 100, 351, 0.2, 87.0, 0.1, "vegan", (), ("sago", "sabudana")),
    _F("besan", "besan", "g", 100, 387, 22.0, 58.0, 6.7, "vegan", (), ("gram flour", "besan")),

    # pulses & legumes (dry)
    _F("toor_dal", "toor dal (dry)", "g", 100, 335, 22.0, 57.0, 1.7, "vegan", (), ("arhar", "toor", "tuvar")),
    _F("moong_dal", "moong dal (dry)", "g", 100, 347, 24.0, 59.0, 1.2, "vegan", (), ("moong", "mung")),
    _F("masoor_dal", "masoor dal (dry)", "g", 100, 352, 25.0, 60.0, 1.1, "vegan", (), ("masoor", "red lentil")),
    _F("chana_dal", "chana dal (dry)", "g", 100, 360, 20.0, 60.0, 5.3, "vegan", (), ("chana dal",)),
    _F("urad_dal", "urad dal (dry)", "g", 100, 341, 25.0, 59.0, 1.6, "vegan", (), ("urad", "black gram")),
    _F("rajma", "rajma (dry)", "g", 100, 333, 24.0, 60.0, 0.8, "vegan", (), ("kidney bean", "rajma")),
    _F("kabuli_chana", "chickpeas (dry)", "g", 100, 364, 19.0, 61.0, 6.0, "vegan", (), ("chana", "chickpea", "chole")),
    _F("kala_chana", "kala chana (dry)", "g", 100, 360, 20.0, 61.0, 5.0, "vegan", (), ("kala chana",)),
    _F("soy_chunks", "soy chunks (dry)", "g", 100, 345, 52.0, 33.0, 0.5, "vegan", ("soy",), ("soya", "soy chunk", "nutrela")),
    _F("sprouts", "moong sprouts", "g", 100, 30, 3.0, 6.0, 0.2, "vegan", (), ("sprouts",)),
    _F("peanuts", "peanuts", "g", 100, 567, 26.0, 16.0, 49.0, "vegan", ("nuts",), ("moongphali", "peanut", "groundnut")),

    # dairy, eggs, meat, protein
    _F("paneer", "paneer", "g", 100, 265, 18.0, 1.2, 21.0, "veg", ("dairy",), ("paneer", "cottage cheese")),
    _F("tofu", "tofu", "g", 100, 76, 8.0, 1.9, 4.8, "vegan", ("soy",), ("tofu",)),
    _F("curd", "curd (dahi)", "g", 100, 61, 3.1, 4.7, 3.3, "veg", ("dairy",), ("dahi", "curd", "yogurt")),
    _F("hung_curd", "hung curd", "g", 100, 97, 9.0, 3.6, 5.0, "veg", ("dairy",), ("hung curd", "greek yogurt")),
    _F("milk", "toned milk", "ml", 100, 58, 3.1, 4.7, 3.0, "veg", ("dairy",), ("milk", "doodh")),
    _F("buttermilk", "buttermilk", "ml", 100, 25, 1.5, 2.5, 1.0, "veg", ("dairy",), ("chaas", "buttermilk")),
    _F("soy_milk", "soy milk", "ml", 100, 43, 3.3, 3.0, 1.8, "vegan", ("soy",), ("soy milk",)),
    _F("whey", "whey protein", "g", 30, 120, 24.0, 3.0, 1.5, "veg", ("dairy",), ("whey", "protein powder")),
    _F("egg", "egg", "piece", 1, 78, 6.3, 0.6, 5.3, "egg", ("egg",), ("egg", "anda", "boiled egg")),
    _F("egg_white", "egg white", "piece", 1, 17, 3.6, 0.2, 0.1, "egg", ("egg",), ("egg white",)),
    _F("chicken", "chicken breast", "g", 100, 165, 31.0, 0.0, 3.6, "nonveg", (), ("chicken", "murgh")),
    _F("chicken_thigh", "chicken thigh", "g", 100, 209, 26.0, 0.0, 11.0, "nonveg", (), ("chicken thigh",)),
    _F("fish_rohu", "rohu fish", "g", 100, 97, 17.0, 0.0, 3.0, "nonveg", ("seafood",), ("rohu", "fish")),
    _F("fish_basa", "basa fish", "g", 100, 90, 15.0, 0.0, 3.0, "nonveg", ("seafood",), ("basa",)),
    _F("prawns", "prawns", "g", 100, 99, 24.0, 0.2, 0.3, "nonveg", ("seafood",), ("prawn", "jhinga")),
    _F("keema", "mutton keema", "g", 100, 258, 26.0, 0.0, 17.0, "nonveg", (), ("keema", "mutton")),
    _F("almonds", "almonds", "g", 100, 579, 21.0, 22.0, 50.0, "vegan", ("nuts",), ("badam", "almond")),
    _F("cashews", "cashews", "g", 100, 553, 18.0, 30.0, 44.0, "vegan", ("nuts",), ("kaju", "cashew")),
    _F("walnuts", "walnuts", "g", 100, 654, 15.0, 14.0, 65.0, "vegan", ("nuts",), ("akhrot", "walnut")),
    _F("chia", "chia seeds", "g", 100, 486, 17.0, 42.0, 31.0, "vegan", (), ("chia",)),
    _F("flaxseed", "flaxseed", "g", 100, 534, 18.0, 29.0, 42.0, "vegan", (), ("alsi", "flax")),
    _F("sesame", "sesame seeds", "g", 100, 573, 18.0, 23.0, 50.0, "vegan", ("sesame",), ("til", "sesame")),

    # vegetables
    _F("palak", "spinach", "g", 100, 23, 2.9, 3.6, 0.4, "vegan", (), ("palak", "spinach")),
    _F("bhindi", "okra", "g", 100, 33, 1.9, 7.0, 0.2, "vegan", (), ("bhindi", "okra", "ladyfinger")),
    _F("gobi", "cauliflower", "g", 100, 25, 1.9, 5.0, 0.3, "vegan", (), ("gobi", "cauliflower")),
    _F("cabbage", "cabbage", "g", 100, 25, 1.3, 6.0, 0.1, "vegan", (), ("patta gobi", "cabbage")),
    _F("carrot", "carrot", "g", 100, 41, 0.9, 10.0, 0.2, "vegan", (), ("gajar", "carrot")),
    _F("beans_green", "green beans", "g", 100, 31, 1.8, 7.0, 0.1, "vegan", (), ("french beans", "beans")),
    _F("lauki", "bottle gourd", "g", 100, 14, 0.6, 3.4, 0.1, "vegan", (), ("lauki", "ghiya")),
    _F("baingan", "brinjal", "g", 100, 25, 1.0, 6.0, 0.2, "vegan", (), ("baingan", "brinjal", "eggplant")),
    _F("tomato", "tomato", "g", 100, 18, 0.9, 3.9, 0.2, "vegan", (), ("tamatar", "tomato")),
    _F("onion", "onion", "g", 100, 40, 1.1, 9.0, 0.1, "vegan", (), ("pyaz", "onion")),
    _F("cucumber", "cucumber", "g", 100, 15, 0.6, 3.6, 0.1, "vegan", (), ("kheera", "cucumber")),
    _F("capsicum", "capsicum", "g", 100, 20, 0.9, 4.6, 0.2, "vegan", (), ("shimla mirch", "capsicum")),
    _F("mixed_veg", "mixed vegetables", "g", 100, 40, 2.0, 8.0, 0.3, "vegan", (), ("mixed veg", "sabzi")),
    _F("mushroom", "mushroom", "g", 100, 22, 3.1, 3.3, 0.3, "vegan", (), ("mushroom",)),
    _F("peas", "green peas", "g", 100, 81, 5.4, 14.0, 0.4, "vegan", (), ("matar", "peas")),
    _F("salad", "mixed salad", "g", 100, 20, 1.0, 4.0, 0.2, "vegan", (), ("salad",)),
    _F("methi", "fenugreek leaves", "g", 100, 49, 4.4, 6.0, 0.9, "vegan", (), ("methi",)),

    # fats, condiments, extras
    _F("oil", "cooking oil", "g", 100, 884, 0.0, 0.0, 100.0, "vegan", (), ("oil", "tel")),
    _F("ghee", "ghee", "g", 100, 900, 0.0, 0.0, 100.0, "veg", ("dairy",), ("ghee",)),
    _F("coconut_chutney", "coconut chutney", "g", 100, 190, 3.0, 6.0, 17.0, "vegan", (), ("coconut chutney",)),
    _F("mint_chutney", "mint chutney", "g", 100, 60, 2.0, 8.0, 2.0, "vegan", (), ("mint chutney", "chutney")),
    _F("sambar", "sambar", "g", 100, 60, 3.0, 8.0, 2.0, "vegan", (), ("sambar",)),
    _F("papad", "papad", "piece", 1, 35, 3.0, 5.0, 0.5, "vegan", (), ("papad",)),
    _F("pickle", "pickle", "g", 100, 150, 1.0, 5.0, 14.0, "vegan", (), ("achar", "pickle")),
    _F("jaggery", "jaggery", "g", 100, 383, 0.4, 98.0, 0.1, "vegan", (), ("gud", "jaggery")),
    _F("honey", "honey", "g", 100, 304, 0.3, 82.0, 0.0, "veg", (), ("honey", "shahad")),

    # fruit
    _F("banana", "banana", "piece", 1, 105, 1.3, 27.0, 0.4, "vegan", (), ("banana", "kela")),
    _F("apple", "apple", "piece", 1, 95, 0.5, 25.0, 0.3, "vegan", (), ("apple", "seb")),
    _F("orange", "orange", "piece", 1, 62, 1.2, 15.0, 0.2, "vegan", (), ("orange", "santra")),
    _F("papaya", "papaya", "g", 100, 43, 0.5, 11.0, 0.3, "vegan", (), ("papita", "papaya")),
    _F("guava", "guava", "piece", 1, 68, 2.6, 14.0, 1.0, "vegan", (), ("amrood", "guava")),
    _F("mango", "mango", "g", 100, 60, 0.8, 15.0, 0.4, "vegan", (), ("aam", "mango")),
    _F("dates", "dates", "piece", 1, 20, 0.2, 5.0, 0.0, "vegan", (), ("khajur", "date")),

    # beverages
    _F("chai", "masala chai", "ml", 150, 60, 2.0, 7.0, 2.5, "veg", ("dairy",), ("chai", "tea")),
    _F("green_tea", "green tea", "ml", 150, 2, 0.0, 0.4, 0.0, "vegan", (), ("green tea",)),
    _F("black_coffee", "black coffee", "ml", 150, 3, 0.1, 0.5, 0.0, "vegan", (), ("black coffee",)),
    _F("lemon_water", "lemon water", "ml", 250, 10, 0.1, 2.5, 0.0, "vegan", (), ("nimbu pani", "lemon water")),
]

FOODS: dict[str, Food] = {f.id: f for f in _ALL}


# ── dishes ────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Dish:
    """A recipe over `FOODS`. Macros are SUMMED from components, never asserted.

    `scalable` names the components a planner may grow/shrink to hit a calorie
    budget (staples and the protein anchor) — chutney and tea stay put.
    `tags`: light = easy-digesting/low-fried (suits 50+); hearty = high volume;
    quick = minimal cooking.
    """

    id: str
    name: str
    slots: tuple[str, ...]
    components: tuple[tuple[str, float], ...]
    scalable: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def macros(self, scale: dict[str, float] | None = None) -> dict[str, float]:
        k = p = c = f = 0.0
        for fid, amt in self.components:
            dk, dp, dc, df = FOODS[fid].scaled(amt * (scale or {}).get(fid, 1.0))
            k += dk
            p += dp
            c += dc
            f += df
        return {"kcal": k, "protein_g": p, "carbs_g": c, "fat_g": f}

    @property
    def diet(self) -> str:
        return max((FOODS[f].diet for f, _ in self.components), key=lambda d: DIET_ORDER[d])

    @property
    def allergens(self) -> frozenset[str]:
        return frozenset(a for f, _ in self.components for a in FOODS[f].allergens)


def _D(i, n, slots, comps, scal=(), tags=()):
    return Dish(i, n, tuple(slots.split()), tuple(comps.items()), scal, tags)


_DISHES: list[Dish] = [
    # ── breakfast ──
    _D("poha_peanut", "Poha with peanuts", "breakfast", {"poha_dry": 60, "peanuts": 15, "onion": 30, "oil": 5}, ("poha_dry",), ("quick",)),
    _D("upma", "Vegetable upma", "breakfast", {"suji": 60, "mixed_veg": 50, "oil": 8}, ("suji",), ("quick",)),
    _D("idli_sambar", "Idli with sambar", "breakfast", {"idli": 3, "sambar": 150, "coconut_chutney": 30}, ("idli",), ("light",)),
    _D("masala_dosa", "Masala dosa", "breakfast", {"dosa": 2, "potato": 100, "coconut_chutney": 30}, ("dosa",), ()),
    _D("besan_chilla", "Besan chilla", "breakfast", {"besan": 60, "onion": 30, "tomato": 30, "oil": 6}, ("besan",), ("quick",)),
    _D("moong_chilla", "Moong dal chilla", "breakfast", {"moong_dal": 60, "onion": 30, "oil": 6}, ("moong_dal",), ("light",)),
    _D("oats_milk", "Oats with milk and banana", "breakfast", {"oats_dry": 50, "milk": 200, "banana": 1}, ("oats_dry", "milk"), ("quick", "light")),
    _D("oats_masala", "Masala oats", "breakfast", {"oats_dry": 50, "mixed_veg": 60, "oil": 5}, ("oats_dry",), ("quick",)),
    _D("paneer_paratha", "Paneer paratha with curd", "breakfast", {"paratha": 2, "paneer": 60, "curd": 100}, ("paratha", "paneer"), ("hearty",)),
    _D("aloo_paratha", "Aloo paratha with curd", "breakfast", {"paratha": 2, "potato": 80, "curd": 100}, ("paratha",), ("hearty",)),
    _D("egg_bhurji_toast", "Egg bhurji with toast", "breakfast", {"egg": 3, "bread": 2, "onion": 30, "oil": 5}, ("egg", "bread"), ()),
    _D("eggs_oats", "Boiled eggs with oats", "breakfast", {"egg": 3, "oats_dry": 40, "milk": 150}, ("egg", "oats_dry"), ()),
    _D("egg_paratha", "Egg paratha with curd", "breakfast", {"paratha": 2, "egg": 2, "curd": 80}, ("paratha", "egg"), ("hearty",)),
    _D("omelette_toast", "Vegetable omelette with toast", "breakfast", {"egg": 3, "bread": 2, "capsicum": 30, "oil": 5}, ("egg", "bread"), ()),
    _D("sprouts_bowl_bf", "Sprouts bowl", "breakfast", {"sprouts": 150, "onion": 30, "tomato": 30, "lemon_water": 250}, ("sprouts",), ("light", "quick")),
    _D("ragi_porridge", "Ragi porridge", "breakfast", {"ragi": 50, "milk": 200, "jaggery": 10}, ("ragi", "milk"), ("light",)),
    _D("vermicelli_upma", "Vermicelli upma", "breakfast", {"vermicelli": 60, "mixed_veg": 50, "oil": 6}, ("vermicelli",), ("quick",)),
    _D("sabudana_khichdi", "Sabudana khichdi", "breakfast", {"sabudana": 60, "peanuts": 20, "potato": 50, "oil": 8}, ("sabudana",), ()),
    _D("tofu_scramble", "Tofu scramble with toast", "breakfast", {"tofu": 150, "bread": 2, "capsicum": 30, "oil": 5}, ("tofu", "bread"), ()),
    _D("chia_curd_bowl", "Curd bowl with chia and banana", "breakfast", {"curd": 200, "chia": 15, "banana": 1, "honey": 10}, ("curd",), ("light", "quick")),
    _D("pb_toast", "Peanut butter toast with banana", "breakfast", {"bread": 3, "peanuts": 25, "banana": 1}, ("bread", "peanuts"), ("quick",)),
    _D("dosa_sambar", "Dosa with sambar", "breakfast", {"dosa": 2, "sambar": 150}, ("dosa",), ("light",)),
    _D("methi_thepla", "Methi thepla with curd", "breakfast", {"paratha": 2, "methi": 50, "curd": 100}, ("paratha",), ()),
    _D("milk_banana_almond", "Milk with banana and almonds", "breakfast", {"milk": 250, "banana": 1, "almonds": 15}, ("milk",), ("quick", "light")),
    _D("quinoa_bowl_bf", "Quinoa breakfast bowl", "breakfast", {"quinoa": 60, "milk": 150, "apple": 1}, ("quinoa",), ("light",)),
    _D("chana_chaat_bf", "Chana chaat", "breakfast", {"kabuli_chana": 70, "onion": 30, "tomato": 30}, ("kabuli_chana",), ("light",)),
    _D("paneer_bhurji_bf", "Paneer bhurji with roti", "breakfast", {"paneer": 100, "roti": 2, "onion": 30, "oil": 5}, ("paneer", "roti"), ()),
    _D("bajra_roti_curd", "Bajra roti with curd", "breakfast", {"bajra": 60, "curd": 150, "pickle": 15}, ("bajra",), ("light",)),

    # ── lunch (main meal) ──
    _D("dal_rice_thali", "Dal-rice thali with sabzi and curd", "lunch", {"toor_dal": 60, "rice_raw": 70, "mixed_veg": 100, "curd": 100, "oil": 8}, ("toor_dal", "rice_raw"), ()),
    _D("rajma_chawal", "Rajma chawal with curd", "lunch", {"rajma": 70, "rice_raw": 70, "curd": 100, "onion": 30, "oil": 8}, ("rajma", "rice_raw"), ("hearty",)),
    _D("chole_rice", "Chole with rice", "lunch", {"kabuli_chana": 70, "rice_raw": 70, "salad": 80, "oil": 8}, ("kabuli_chana", "rice_raw"), ()),
    _D("dal_roti_bhindi", "Dal, roti and bhindi sabzi", "lunch", {"toor_dal": 60, "roti": 3, "bhindi": 120, "curd": 100, "oil": 8}, ("toor_dal", "roti"), ()),
    _D("paneer_butter_roti", "Paneer butter masala with roti", "lunch", {"paneer": 120, "roti": 3, "rice_raw": 40, "salad": 80, "oil": 8}, ("paneer", "roti"), ("hearty",)),
    _D("soy_curry_rice", "Soya chunk curry with rice", "lunch", {"soy_chunks": 50, "rice_raw": 70, "salad": 80, "oil": 8}, ("soy_chunks", "rice_raw"), ()),
    _D("chicken_curry_rice", "Chicken curry with rice", "lunch", {"chicken": 150, "rice_raw": 70, "curd": 100, "oil": 8}, ("chicken", "rice_raw"), ()),
    _D("chicken_roti", "Chicken curry with roti", "lunch", {"chicken": 150, "roti": 3, "salad": 80, "oil": 8}, ("chicken", "roti"), ()),
    _D("fish_curry_rice", "Fish curry with rice", "lunch", {"fish_rohu": 150, "rice_raw": 70, "salad": 80, "oil": 8}, ("fish_rohu", "rice_raw"), ("light",)),
    _D("egg_curry_rice", "Egg curry with rice", "lunch", {"egg": 3, "rice_raw": 70, "salad": 80, "oil": 8}, ("egg", "rice_raw"), ()),
    _D("keema_roti", "Mutton keema with roti", "lunch", {"keema": 120, "roti": 3, "onion": 40, "oil": 5}, ("keema", "roti"), ("hearty",)),
    _D("kadhi_chawal", "Kadhi chawal", "lunch", {"besan": 40, "curd": 200, "rice_raw": 70, "oil": 8}, ("rice_raw",), ()),
    _D("khichdi_curd", "Khichdi with curd", "lunch", {"moong_dal": 50, "rice_raw": 60, "curd": 100, "ghee": 8}, ("moong_dal", "rice_raw"), ("light",)),
    _D("sambar_rice", "Sambar rice with papad", "lunch", {"sambar": 200, "rice_raw": 70, "papad": 2}, ("rice_raw",), ("light",)),
    _D("chana_dal_roti", "Chana dal with roti and gobi", "lunch", {"chana_dal": 60, "roti": 3, "gobi": 120, "oil": 8}, ("chana_dal", "roti"), ()),
    _D("masoor_dal_rice", "Masoor dal with rice", "lunch", {"masoor_dal": 60, "rice_raw": 70, "salad": 80, "oil": 8}, ("masoor_dal", "rice_raw"), ("light",)),
    _D("palak_paneer_roti", "Palak paneer with roti", "lunch", {"paneer": 100, "palak": 150, "roti": 3, "oil": 8}, ("paneer", "roti"), ()),
    _D("aloo_gobi_dal", "Aloo gobi with dal and roti", "lunch", {"potato": 100, "gobi": 100, "toor_dal": 50, "roti": 3, "oil": 8}, ("toor_dal", "roti"), ()),
    _D("baingan_bharta_roti", "Baingan bharta with roti", "lunch", {"baingan": 200, "roti": 3, "curd": 100, "oil": 8}, ("roti",), ("light",)),
    _D("mushroom_masala_roti", "Mushroom masala with roti", "lunch", {"mushroom": 150, "roti": 3, "salad": 80, "oil": 8}, ("mushroom", "roti"), ("light",)),
    _D("prawn_curry_rice", "Prawn curry with rice", "lunch", {"prawns": 150, "rice_raw": 70, "salad": 80, "oil": 8}, ("prawns", "rice_raw"), ("light",)),
    _D("tofu_curry_rice", "Tofu curry with rice", "lunch", {"tofu": 200, "rice_raw": 70, "salad": 80, "oil": 8}, ("tofu", "rice_raw"), ("light",)),
    _D("chicken_biryani", "Chicken biryani with raita", "lunch", {"chicken": 150, "rice_raw": 90, "curd": 80, "oil": 10}, ("chicken", "rice_raw"), ("hearty",)),
    _D("veg_pulao_raita", "Veg pulao with raita", "lunch", {"rice_raw": 80, "mixed_veg": 120, "curd": 100, "oil": 8}, ("rice_raw",), ()),
    _D("rajma_roti", "Rajma with roti", "lunch", {"rajma": 70, "roti": 3, "salad": 80, "oil": 8}, ("rajma", "roti"), ()),
    _D("kala_chana_rice", "Kala chana with rice", "lunch", {"kala_chana": 70, "rice_raw": 70, "salad": 80, "oil": 8}, ("kala_chana", "rice_raw"), ()),
    _D("methi_dal_roti", "Methi dal with roti", "lunch", {"methi": 100, "toor_dal": 60, "roti": 3, "oil": 8}, ("toor_dal", "roti"), ("light",)),
    _D("lauki_dal_rice", "Lauki dal with rice", "lunch", {"lauki": 150, "toor_dal": 60, "rice_raw": 60, "oil": 6}, ("toor_dal", "rice_raw"), ("light",)),
    _D("quinoa_rajma_bowl", "Quinoa rajma bowl", "lunch", {"quinoa": 70, "rajma": 60, "salad": 80, "oil": 6}, ("quinoa", "rajma"), ("light",)),
    _D("chicken_salad_lunch", "Grilled chicken with salad and sweet potato", "lunch", {"chicken": 160, "salad": 150, "sweet_potato": 120, "oil": 6}, ("chicken", "sweet_potato"), ("light",)),

    # ── evening snack ──
    _D("sprouts_chaat", "Sprouts chaat", "snack", {"sprouts": 150, "onion": 30, "tomato": 30, "lemon_water": 250}, ("sprouts",), ("light", "quick")),
    _D("chana_chai", "Roasted chana with chai", "snack", {"kabuli_chana": 50, "chai": 150}, ("kabuli_chana",), ("quick",)),
    _D("paneer_tikka_snack", "Paneer tikka with green tea", "snack", {"paneer": 100, "capsicum": 40, "green_tea": 150}, ("paneer",), ()),
    _D("curd_fruit_bowl", "Curd bowl with fruit and almonds", "snack", {"curd": 200, "apple": 1, "almonds": 10}, ("curd",), ("light", "quick")),
    _D("egg_chai_peanut", "Boiled eggs with chai", "snack", {"egg": 2, "chai": 150, "peanuts": 15}, ("egg",), ("quick",)),
    _D("peanut_chaat", "Peanut chaat", "snack", {"peanuts": 40, "onion": 30, "tomato": 30}, ("peanuts",), ("quick",)),
    _D("dhokla_tea", "Dhokla with green tea", "snack", {"besan": 60, "green_tea": 150}, ("besan",), ("light",)),
    _D("fruit_nuts", "Fruit and nuts", "snack", {"banana": 1, "almonds": 15, "walnuts": 10}, ("almonds",), ("quick", "light")),
    _D("buttermilk_papad", "Buttermilk with papad", "snack", {"buttermilk": 250, "papad": 2}, ("buttermilk",), ("light", "quick")),
    _D("whey_milk_shake", "Whey shake with milk", "snack", {"whey": 30, "milk": 200}, ("whey", "milk"), ("quick",)),
    _D("whey_banana", "Whey shake with banana", "snack", {"whey": 30, "banana": 1}, ("whey",), ("quick",)),
    _D("chana_chaat_snack", "Chana chaat with cucumber", "snack", {"kabuli_chana": 60, "onion": 30, "cucumber": 50}, ("kabuli_chana",), ("light",)),
    _D("bhel", "Bhel", "snack", {"poha_dry": 40, "onion": 30, "tomato": 30, "peanuts": 15}, ("poha_dry",), ("quick",)),
    _D("papaya_chia", "Papaya bowl with chia", "snack", {"papaya": 200, "chia": 10}, ("papaya",), ("light", "quick")),
    _D("guava_chai", "Guava with chai", "snack", {"guava": 2, "chai": 150}, ("guava",), ("light", "quick")),
    _D("tofu_tikka_snack", "Tofu tikka with green tea", "snack", {"tofu": 150, "capsicum": 40, "green_tea": 150}, ("tofu",), ("light",)),
    _D("milk_dates", "Milk with dates", "snack", {"milk": 250, "dates": 4}, ("milk",), ("quick", "light")),
    _D("curd_sprouts", "Curd with sprouts", "snack", {"curd": 150, "sprouts": 100}, ("curd", "sprouts"), ("light",)),
    _D("chicken_sandwich", "Chicken sandwich", "snack", {"chicken": 80, "bread": 2, "cucumber": 40}, ("chicken", "bread"), ("quick",)),
    _D("egg_chaat", "Egg chaat with buttermilk", "snack", {"egg": 2, "onion": 30, "buttermilk": 250}, ("egg",), ("quick",)),
    _D("mango_curd", "Mango with curd", "snack", {"mango": 150, "curd": 150}, ("curd",), ("light", "quick")),
    _D("til_chikki", "Sesame chikki", "snack", {"sesame": 30, "jaggery": 20}, ("sesame",), ("quick",)),
    _D("green_tea_almonds", "Green tea with almonds", "snack", {"green_tea": 150, "almonds": 20}, ("almonds",), ("light", "quick")),

    # ── dinner (lighter than lunch) ──
    _D("dal_roti_palak", "Dal with roti and palak", "dinner", {"toor_dal": 60, "roti": 2, "palak": 150, "oil": 6}, ("toor_dal", "roti"), ("light",)),
    _D("paneer_bhurji_dinner", "Paneer bhurji with roti", "dinner", {"paneer": 120, "roti": 2, "salad": 80, "oil": 6}, ("paneer", "roti"), ()),
    _D("grilled_chicken_roti", "Grilled chicken with roti", "dinner", {"chicken": 150, "roti": 2, "mixed_veg": 100, "oil": 6}, ("chicken", "roti"), ("light",)),
    _D("fish_curry_dinner", "Fish curry with rice", "dinner", {"fish_basa": 150, "rice_raw": 50, "salad": 80, "oil": 6}, ("fish_basa", "rice_raw"), ("light",)),
    _D("egg_curry_roti", "Egg curry with roti", "dinner", {"egg": 3, "roti": 2, "palak": 120, "oil": 6}, ("egg", "roti"), ()),
    _D("khichdi_light", "Light khichdi with curd", "dinner", {"moong_dal": 50, "rice_raw": 50, "curd": 100, "ghee": 6}, ("moong_dal", "rice_raw"), ("light",)),
    _D("mixed_sabzi_roti", "Mixed sabzi with roti and curd", "dinner", {"mixed_veg": 200, "roti": 2, "curd": 100, "oil": 6}, ("roti",), ("light",)),
    _D("tofu_palak_roti", "Palak tofu with roti", "dinner", {"tofu": 200, "palak": 150, "roti": 2, "oil": 6}, ("tofu", "roti"), ("light",)),
    _D("soy_curry_roti", "Soya chunk curry with roti", "dinner", {"soy_chunks": 45, "roti": 2, "salad": 80, "oil": 6}, ("soy_chunks", "roti"), ()),
    _D("chana_roti_dinner", "Chana masala with roti", "dinner", {"kabuli_chana": 70, "roti": 2, "salad": 80, "oil": 6}, ("kabuli_chana", "roti"), ()),
    _D("rajma_roti_dinner", "Rajma with roti", "dinner", {"rajma": 60, "roti": 2, "salad": 80, "oil": 6}, ("rajma", "roti"), ()),
    _D("lauki_dal_roti", "Lauki dal with roti", "dinner", {"lauki": 200, "toor_dal": 50, "roti": 2, "oil": 5}, ("toor_dal", "roti"), ("light",)),
    _D("chicken_stew_roti", "Chicken stew with roti", "dinner", {"chicken_thigh": 130, "roti": 2, "carrot": 80, "oil": 6}, ("chicken_thigh", "roti"), ("light",)),
    _D("prawn_stirfry", "Prawn stir-fry with rice", "dinner", {"prawns": 150, "rice_raw": 50, "capsicum": 60, "oil": 6}, ("prawns", "rice_raw"), ("light",)),
    _D("paneer_tikka_dinner", "Paneer tikka with roti", "dinner", {"paneer": 130, "roti": 2, "salad": 100, "oil": 5}, ("paneer", "roti"), ()),
    _D("mushroom_dinner", "Mushroom masala with roti", "dinner", {"mushroom": 200, "roti": 2, "salad": 80, "oil": 6}, ("mushroom", "roti"), ("light",)),
    _D("baingan_dinner", "Baingan bharta with roti", "dinner", {"baingan": 200, "roti": 2, "curd": 100, "oil": 6}, ("roti",), ("light",)),
    _D("gobi_matar_roti", "Gobi matar with roti", "dinner", {"gobi": 150, "peas": 60, "roti": 2, "oil": 6}, ("roti",), ("light",)),
    _D("moong_khichdi_lauki", "Moong khichdi with lauki", "dinner", {"moong_dal": 60, "rice_raw": 50, "lauki": 100, "ghee": 6}, ("moong_dal", "rice_raw"), ("light",)),
    _D("egg_white_bhurji", "Egg-white bhurji with roti", "dinner", {"egg_white": 6, "roti": 2, "capsicum": 50, "oil": 5}, ("egg_white", "roti"), ("light",)),
    _D("curd_rice_light", "Curd rice with cucumber", "dinner", {"curd": 250, "rice_raw": 50, "cucumber": 60}, ("curd", "rice_raw"), ("light",)),
    _D("methi_dal_dinner", "Methi dal with roti", "dinner", {"methi": 120, "toor_dal": 55, "roti": 2, "oil": 6}, ("toor_dal", "roti"), ("light",)),
    _D("fish_grill_salad", "Grilled fish with salad", "dinner", {"fish_rohu": 180, "salad": 150, "sweet_potato": 100, "oil": 5}, ("fish_rohu", "sweet_potato"), ("light",)),
    _D("chicken_salad_bowl", "Chicken salad bowl", "dinner", {"chicken": 160, "salad": 150, "sweet_potato": 80, "oil": 5}, ("chicken", "sweet_potato"), ("light",)),
    _D("tofu_stirfry", "Tofu stir-fry with rice", "dinner", {"tofu": 200, "mixed_veg": 150, "rice_raw": 45, "oil": 6}, ("tofu", "rice_raw"), ("light",)),
    _D("dal_rice_dinner", "Masoor dal with rice", "dinner", {"masoor_dal": 55, "rice_raw": 55, "salad": 80, "oil": 6}, ("masoor_dal", "rice_raw"), ("light",)),
    _D("paneer_palak_dinner", "Palak paneer with roti", "dinner", {"paneer": 120, "palak": 150, "roti": 2, "oil": 6}, ("paneer", "roti"), ()),
    _D("veg_paneer_soup", "Vegetable soup with paneer and roti", "dinner", {"mixed_veg": 200, "roti": 2, "paneer": 60, "oil": 5}, ("paneer", "roti"), ("light",)),
    _D("sambar_rice_dinner", "Sambar rice", "dinner", {"sambar": 200, "rice_raw": 55, "papad": 1}, ("rice_raw",), ("light",)),
    _D("quinoa_veg_bowl", "Quinoa vegetable bowl with curd", "dinner", {"quinoa": 60, "mixed_veg": 150, "curd": 100, "oil": 5}, ("quinoa",), ("light",)),
]

DISHES: dict[str, Dish] = {d.id: d for d in _DISHES}
SLOTS = ("breakfast", "lunch", "snack", "dinner")


def dishes_for_slot(slot: str) -> list[Dish]:
    return [d for d in _DISHES if slot in d.slots]
