# 08 · Domain Model — Equipment, Indian Nutrition & Personalization

> Staff-engineer note: the architecture docs ([`02`](02-multi-agent-system.md), [`03`](03-data-model.md),
> [`05`](05-frontend.md)) describe *how* agents and data flow. This doc owns the **domain catalogs** they reference
> — the equipment taxonomy, the Indian food database, the personalization signals, and the meal-plan archetypes.
> Keeping the big enumerations here keeps the architecture docs about architecture and gives the catalogs a single
> source of truth. FitTwin's first audience is **Indian gym-goers, especially students/hostelers**, so the
> nutrition domain is built around that — not a generic Western food list bolted on later.

---

## 1. Equipment taxonomy

The old spec asked one thing: "barbell or dumbbell?" That can't drive a credible Workout Agent. We model
equipment as **(a) a training context** + **(b) a set of available items**. The Workout Agent generates plans
that *only* use what's available (see [`02 §3.3`](02-multi-agent-system.md#33-workout-agent-hybrid)).

### 1.1 Training context (`gym_type`, single-select)

| Value | Meaning | Default item set unlocked |
|---|---|---|
| `full_commercial_gym` | Everything below is assumed available | all machines + free weights + cardio |
| `basic_gym` | Free weights + a few machines | barbell, dumbbells, bench, pull-up bar, cable (maybe) |
| `home_gym` | Curated home setup | whatever the user explicitly checks in §1.2 |
| `bodyweight_only` | No equipment | none (bodyweight + optional bands) |

`gym_type` seeds sensible defaults so onboarding isn't 13 toggles for a commercial-gym user; the user can still
override individual items in §1.2.

### 1.2 Available equipment (`equipment[]`, multi-select)

```
dumbbells              adjustable_dumbbells   resistance_bands       kettlebells
pull_up_bar            bench                  cable_machine          smith_machine
leg_press_machine      chest_press_machine    treadmill              exercise_bike
barbell                no_equipment           (== bodyweight)
```

**Canonical enum** lives in code as `app/domain.py::Equipment`; the frontend renders it as a grouped multi-select
(see [`05 §7`](05-frontend.md#7-onboarding--personalization-step)). `no_equipment` is mutually exclusive with the
rest (selecting it clears the others).

### 1.3 Equipment → exercise capability map

This map is **deterministic data**, not LLM judgment — it's what makes "I have no dumbbells" produce a real
substitution rather than a hallucination. Each movement pattern lists fallbacks in priority order; the Workout
Agent walks the list and picks the first pattern the user *can* perform.

| Movement pattern | Preferred → fallback chain (first available wins) |
|---|---|
| Horizontal push | barbell bench → DB bench → chest-press machine → push-up (bands) |
| Vertical push | barbell OHP → DB OHP → pike push-up |
| Horizontal pull | barbell row → DB row → cable row → band row → inverted row (bar) |
| Vertical pull | pull-up (bar) → lat pulldown (cable) → band pulldown |
| Squat pattern | barbell squat → goblet squat (DB/KB) → leg press → bodyweight squat → split squat |
| Hinge | barbell deadlift → DB RDL → KB swing → band good-morning → bodyweight hip thrust |
| Cardio (Zone-2) | treadmill → exercise bike → brisk walk (steps target) |

> Why a table and not a prompt: a wrong macro number is a liability; a wrong *exercise substitution* is a
> credibility killer. Both belong in deterministic data the agent **selects from**, with the LLM only naming and
> ordering within the allowed set.

---

## 2. Indian nutrition domain

The Nutrition Agent's calorie/macro **targets** are computed by deterministic tools
([`02 §3.2`](02-multi-agent-system.md#32-nutrition-agent-llm)). This section is the **food universe** the agent
assembles meals from. It is **India-first**: staples, units, and meal shapes match how the target user actually
eats and shops.

### 2.1 Food database shape

Each food is a row in a seeded catalog (`app/agents/data/foods_in.py`, served read-only). Per 100 g (or per
natural unit, e.g. "1 roti", "1 egg") we store the macro quad + tags used for filtering.

```python
# representative row
{
  "id": "paneer",
  "name": "Paneer",
  "unit": "100g",
  "kcal": 296, "protein_g": 18.0, "carbs_g": 3.4, "fat_g": 25.0,
  "diet": "veg",                      # veg | nonveg | egg
  "tags": ["high_protein", "dairy"],
  "cost_tier": "mid",                 # budget | mid | premium
  "prep": ["no_cook", "stovetop"],    # cooking effort
  "hostel_friendly": True,            # makeable with a kettle/induction/minimal kit
}
```

### 2.2 Vegetarian staples (seed set)

`oats · paneer · dal (toor/moong) · rajma · chana (chickpea) · soy chunks · roti (whole wheat) · rice ·
curd (dahi) · milk · seasonal fruits · poha · upma · idli · dosa · besan chilla · peanuts · sprouts · tofu`

### 2.3 Non-vegetarian staples (seed set)

`chicken breast · whole eggs / egg whites · fish (rohu/basa) · chicken curry · egg curry · keema` — layered on
top of the shared base of `rice · roti · milk · paneer · dal · curd`.

### 2.4 Diet preference & allergy filtering

- `dietary_prefs` (multi): `veg`, `nonveg`, `egg`, `jain` (no onion/garlic/root), `vegan` (no dairy/egg),
  `no_beef`, `no_pork` (defaults on for the India-first audience), `high_protein`.
- `allergies` (multi, free-text + common presets): `lactose`, `gluten`, `nuts`, `soy`, `egg`, `seafood`.
- Filtering is a **hard pre-filter** on the catalog *before* the LLM ever sees it: a vegan user's candidate list
  never contains paneer, so the model cannot suggest it. Allergens are removed the same way. This is safety +
  correctness done in data, not prompt-begging.

---

## 3. Meal-plan archetypes

The system generates plans tuned to the user's life, not one generic plan. The archetype selects **which subset of
the catalog and which assembly rules** the Nutrition Agent uses; macro/calorie targets are identical across
archetypes (they come from the tools) — the archetype changes *food selection*, not the math.

| Archetype | Selection rule | Typical day |
|---|---|---|
| **Budget** | bias `cost_tier ∈ {budget, mid}`; protein from dal/chana/soy/eggs/milk, not paneer/chicken daily | poha → dal-rice + curd → chana chaat → roti-sabzi + egg |
| **High-protein** | maximize `protein_g` per kcal/₹; sort candidates by protein density | oats+milk+whey → paneer/chicken + rice → curd + sprouts → eggs/fish + roti |
| **Hostel-friendly** | only `hostel_friendly == True` (kettle/induction/no-cook); mess-meal aware | oats (kettle) → mess thali (logged) → milk + peanuts + fruit → besan chilla (induction) |
| **Vegetarian** | `diet == veg`; protein from paneer/dal/soy/curd/milk | besan chilla → rajma-rice → paneer bhurji + roti → curd + fruit |
| **Non-vegetarian** | allow `diet ∈ {veg, egg, nonveg}`; anchor protein on chicken/eggs/fish | eggs+oats → chicken + rice → curd + fruit → fish/chicken + roti |

Archetypes compose: "budget + hostel + vegetarian" is the common student case and is the **default** when the
profile signals a student/hosteler with a low budget tier.

---

## 4. Personalization signals

Nutrition recommendations adapt to the user's real constraints. These live on the Profile
(see [`03 §Profile`](03-data-model.md#profile-document-expanded)) and feed the Nutrition Agent.

| Signal | Field | Effect on recommendations |
|---|---|---|
| Student budget | `budget_tier ∈ {student, moderate, flexible}` | gates `cost_tier`; picks the **Budget** archetype |
| Hostel lifestyle | `lifestyle ∈ {hostel, home, pg, working}` | gates `hostel_friendly`; integrates a "mess meal" the user logs |
| Gym goal | `goal` + `goal.target_weight` | sets deficit/surplus & protein floor (via tools) |
| Food preferences | `dietary_prefs[]`, `disliked_foods[]` | hard pre-filter of the candidate catalog |
| Allergies | `allergies[]` | hard pre-filter (safety) |
| Meal frequency | `meals_per_day ∈ {3,4,5,6}` | how the day's macros are split into meals |
| Cooking time | `cooking_time ∈ {none, low, medium, high}` | gates `prep`; `none` ⇒ no-cook/mess-only options |

**Design rule:** every personalization signal is applied as a **deterministic filter or split** on the catalog
and the tool-computed targets. The LLM personalizes *language and variety* inside the already-constrained set — it
never overrides budget, allergy, or macro constraints. This is the same "agents own judgment, tools/data own
constraints" principle as the rest of the system.

---

## 5. Where this is enforced (traceability)

| Concern | Enforced in |
|---|---|
| Equipment availability | `domain.Equipment` enum + capability map (§1.3) → Workout Agent selection |
| Macro/calorie correctness | deterministic tools (`nutrition_math`) — unchanged by archetype |
| Diet/allergy exclusion | catalog **pre-filter** before the LLM (§2.4) |
| Budget / hostel / cooking | catalog tag filters (§4) driven by Profile fields |
| Archetype selection | rule from Profile (§3); overridable by an explicit chat request ("make it high-protein") |

This keeps the demo-able promise honest: *no plan suggests food you can't afford, can't make, are allergic to, or
that breaks your diet — by construction, not by hoping the prompt held.*
