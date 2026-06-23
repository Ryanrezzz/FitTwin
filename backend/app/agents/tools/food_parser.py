"""Deterministic food parser — "250g chicken and rice" -> macro estimate.

V1 uses a small built-in food table (macros per reference serving). It's a
heuristic, not a nutrition database, but it's deterministic and testable. V2
swaps in a real food API / vision model behind this same interface.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# macros per reference amount (cooked where relevant)
_FOOD_DB: dict[str, dict] = {
    # name:    unit  ref   kcal  protein carbs  fat   aliases
    "chicken": {"unit": "g", "ref": 100, "kcal": 165, "p": 31.0, "c": 0.0, "f": 3.6,
                "aliases": ["chicken breast", "chicken"]},
    "rice":    {"unit": "g", "ref": 100, "kcal": 130, "p": 2.7, "c": 28.0, "f": 0.3,
                "aliases": ["white rice", "rice"]},
    "egg":     {"unit": "each", "ref": 1, "kcal": 78, "p": 6.3, "c": 0.6, "f": 5.3,
                "aliases": ["eggs", "egg"]},
    "oats":    {"unit": "g", "ref": 100, "kcal": 389, "p": 16.9, "c": 66.0, "f": 6.9,
                "aliases": ["oatmeal", "oats"]},
    "banana":  {"unit": "each", "ref": 1, "kcal": 105, "p": 1.3, "c": 27.0, "f": 0.4,
                "aliases": ["bananas", "banana"]},
    "milk":    {"unit": "ml", "ref": 100, "kcal": 64, "p": 3.4, "c": 4.8, "f": 3.6,
                "aliases": ["milk"]},
    "paneer":  {"unit": "g", "ref": 100, "kcal": 265, "p": 18.0, "c": 1.2, "f": 21.0,
                "aliases": ["paneer", "cottage cheese"]},
    "lentils": {"unit": "g", "ref": 100, "kcal": 116, "p": 9.0, "c": 20.0, "f": 0.4,
                "aliases": ["dal", "lentils", "daal"]},
    "tofu":    {"unit": "g", "ref": 100, "kcal": 76, "p": 8.0, "c": 1.9, "f": 4.8,
                "aliases": ["tofu"]},
    "whey":    {"unit": "g", "ref": 30, "kcal": 120, "p": 24.0, "c": 3.0, "f": 1.5,
                "aliases": ["whey", "protein shake", "protein powder"]},
}

# default serving when the user gives no quantity
_DEFAULT_AMOUNT: dict[str, float] = {
    "chicken": 150, "rice": 150, "egg": 2, "oats": 50, "banana": 1,
    "milk": 250, "paneer": 100, "lentils": 150, "tofu": 150, "whey": 30,
}

_QTY_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>g|grams?|gm|kg|ml|l|each|pcs?|pieces?)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FoodItem:
    name: str
    amount: float
    unit: str
    kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float


def _canonical(token: str) -> str | None:
    token = token.lower().strip()
    for canon, data in _FOOD_DB.items():
        if token == canon or token in data["aliases"]:
            return canon
        # substring match on aliases (e.g. "grilled chicken")
        if any(alias in token for alias in data["aliases"]):
            return canon
    return None


def _amount_for(canon: str, chunk: str) -> tuple[float, str]:
    data = _FOOD_DB[canon]
    m = _QTY_RE.search(chunk)
    if not m:
        return float(_DEFAULT_AMOUNT[canon]), data["unit"]
    num = float(m.group("num"))
    unit = (m.group("unit") or "").lower()
    if unit == "kg":
        num *= 1000
    elif unit in ("l",):
        num *= 1000
    return num, data["unit"]


def _macros_for(canon: str, amount: float) -> FoodItem:
    d = _FOOD_DB[canon]
    factor = amount / d["ref"]
    return FoodItem(
        name=canon,
        amount=amount,
        unit=d["unit"],
        kcal=round(d["kcal"] * factor),
        protein_g=round(d["p"] * factor, 1),
        carbs_g=round(d["c"] * factor, 1),
        fat_g=round(d["f"] * factor, 1),
    )


def parse_food(text: str) -> list[FoodItem]:
    """Best-effort parse of free text into recognized food items with macros."""
    items: list[FoodItem] = []
    # split on conjunctions / commas, keep quantity attached to each food chunk
    chunks = re.split(r",|\band\b|\bwith\b|\+", text, flags=re.IGNORECASE)
    seen: set[str] = set()
    for chunk in chunks:
        canon = _canonical(chunk)
        if canon and canon not in seen:
            amount, _ = _amount_for(canon, chunk)
            items.append(_macros_for(canon, amount))
            seen.add(canon)
    return items


def summarize(items: list[FoodItem]) -> dict:
    """Total a parsed meal."""
    return {
        "calories": sum(i.kcal for i in items),
        "protein_g": round(sum(i.protein_g for i in items), 1),
        "carbs_g": round(sum(i.carbs_g for i in items), 1),
        "fat_g": round(sum(i.fat_g for i in items), 1),
        "items": [i.name for i in items],
    }
