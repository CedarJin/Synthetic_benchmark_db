"""FDA labeling regulations knowledge base.

Includes:
  - RACC (Reference Amounts Customarily Consumed) table — 21 CFR 101.12
  - Food category classification
  - Serving size determination from food category
  - %DV reference values (from FDA Nutrition Facts final rule)
  - Nutrient content claim thresholds
"""

# ruff: noqa: E501

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# ── Food categories (simplified FDA product categories) ───────────────────────


class FoodCategory(StrEnum):
    """Broad FDA food categories for serving size regulation."""

    # Baked goods
    BAKERY_PRODUCTS = "bakery_products"
    BREADS_ROLLS = "breads_rolls"
    CAKES_COOKIES = "cakes_cookies"
    CRACKERS = "crackers"
    PASTRIES = "pastries"

    # Dairy
    MILK = "milk"
    YOGURT = "yogurt"
    CHEESE = "cheese"
    BUTTER = "butter"
    CREAM = "cream"
    ICE_CREAM = "ice_cream"

    # Beverages
    BEVERAGES_CARBONATED = "beverages_carbonated"
    JUICE = "juice"
    COFFEE_TEA = "coffee_tea"
    DAIRY_DRINKS = "dairy_drinks"

    # Fruits & Vegetables
    FRESH_FRUIT = "fresh_fruit"
    CANNED_FRUIT = "canned_fruit"
    DRIED_FRUIT = "dried_fruit"
    FRESH_VEGETABLES = "fresh_vegetables"
    CANNED_VEGETABLES = "canned_vegetables"

    # Meat & Protein
    MEAT_POULTRY = "meat_poultry"
    FISH_SEAFOOD = "fish_seafood"
    EGGS = "eggs"
    NUTS_SEEDS = "nuts_seeds"
    TOFU_MEAT_ALTERNATIVES = "tofu_meat_alternatives"

    # Grains
    RICE_PASTA = "rice_pasta"
    BREAKFAST_CEREALS = "breakfast_cereals"
    OATMEAL = "oatmeal"

    # Fats & Oils
    OILS = "oils"
    SALAD_DRESSINGS = "salad_dressings"
    MAYONNAISE = "mayonnaise"
    SPREADS = "spreads"

    # Condiments & Sauces
    CONDIMENTS = "condiments"
    SAUCES = "sauces"
    GRAVIES = "gravies"
    JAMS_JELLIES = "jams_jellies"

    # Snacks
    CHIPS_CRISPS = "chips_crisps"
    POPCORN = "popcorn"
    CANDY = "candy"
    CHOCOLATE = "chocolate"
    GRANOLA_BARS = "granola_bars"

    # Soups
    SOUP_READY_TO_EAT = "soup_ready_to_eat"
    SOUP_CONDENSED = "soup_condensed"

    # Frozen
    FROZEN_MEALS = "frozen_meals"
    FROZEN_PIZZA = "frozen_pizza"
    FROZEN_DESSERTS = "frozen_desserts"

    # Baby
    BABY_FOOD = "baby_food"

    # Other
    BEVERAGE_MIXES = "beverage_mixes"
    UNCATEGORIZED = "uncategorized"


# ── RACC Entry ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RACCEntry:
    """A single entry in the RACC table.

    Attributes:
        category: FDA product category.
        racc_g: Reference amount in grams.
        racc_ml: Reference amount in mL (for liquids).
        label_statement: Typical serving size declaration format.
        household_measure: Typical household measure (cups, tbsp, etc.).
    """

    category: FoodCategory | str
    racc_g: float = 0.0
    racc_ml: float = 0.0
    label_statement: str = ""
    household_measure: str = ""


# ── RACC Table (21 CFR 101.12) ────────────────────────────────────────────────
# Reference values for the most common FDA product categories.

RACC_TABLE: dict[FoodCategory | str, RACCEntry] = {
    # ── Bakery ──
    FoodCategory.BREADS_ROLLS: RACCEntry(
        FoodCategory.BREADS_ROLLS, racc_g=50, label_statement="1 slice", household_measure="1 slice (__g)"
    ),
    FoodCategory.CAKES_COOKIES: RACCEntry(
        FoodCategory.CAKES_COOKIES, racc_g=80, label_statement="1 piece", household_measure="1 piece (__g)"
    ),
    FoodCategory.CRACKERS: RACCEntry(
        FoodCategory.CRACKERS, racc_g=30, label_statement="about __ crackers", household_measure="__ crackers (__g)"
    ),
    FoodCategory.BAKERY_PRODUCTS: RACCEntry(
        FoodCategory.BAKERY_PRODUCTS, racc_g=55, label_statement="1 serving", household_measure="1 serving (__g)"
    ),
    FoodCategory.PASTRIES: RACCEntry(
        FoodCategory.PASTRIES, racc_g=80, label_statement="1 pastry", household_measure="1 pastry (__g)"
    ),

    # ── Dairy ──
    FoodCategory.MILK: RACCEntry(
        FoodCategory.MILK, racc_ml=240, label_statement="1 cup", household_measure="1 cup (__ml)"
    ),
    FoodCategory.YOGURT: RACCEntry(
        FoodCategory.YOGURT, racc_g=170, label_statement="1 container", household_measure="1 container (__g)"
    ),
    FoodCategory.CHEESE: RACCEntry(
        FoodCategory.CHEESE, racc_g=30, label_statement="1 oz", household_measure="about 1 oz (__g)"
    ),
    FoodCategory.BUTTER: RACCEntry(
        FoodCategory.BUTTER, racc_g=14, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),
    FoodCategory.CREAM: RACCEntry(
        FoodCategory.CREAM, racc_ml=15, label_statement="1 tbsp", household_measure="1 tbsp (__ml)"
    ),
    FoodCategory.ICE_CREAM: RACCEntry(
        FoodCategory.ICE_CREAM, racc_g=85, label_statement="1 scoop", household_measure="about 1/2 cup (__g)"
    ),

    # ── Beverages ──
    FoodCategory.BEVERAGES_CARBONATED: RACCEntry(
        FoodCategory.BEVERAGES_CARBONATED, racc_ml=360, label_statement="1 bottle", household_measure="1 bottle (__ml)"
    ),
    FoodCategory.JUICE: RACCEntry(
        FoodCategory.JUICE, racc_ml=240, label_statement="1 cup", household_measure="1 cup (__ml)"
    ),
    FoodCategory.COFFEE_TEA: RACCEntry(
        FoodCategory.COFFEE_TEA, racc_ml=240, label_statement="1 cup", household_measure="1 cup (__ml)"
    ),
    FoodCategory.DAIRY_DRINKS: RACCEntry(
        FoodCategory.DAIRY_DRINKS, racc_ml=240, label_statement="1 cup", household_measure="1 cup (__ml)"
    ),

    # ── Fruits ──
    FoodCategory.FRESH_FRUIT: RACCEntry(
        FoodCategory.FRESH_FRUIT, racc_g=140, label_statement="1 medium", household_measure="1 medium (__g)"
    ),
    FoodCategory.CANNED_FRUIT: RACCEntry(
        FoodCategory.CANNED_FRUIT, racc_g=125, label_statement="1/2 cup", household_measure="about 1/2 cup (__g)"
    ),
    FoodCategory.DRIED_FRUIT: RACCEntry(
        FoodCategory.DRIED_FRUIT, racc_g=40, label_statement="1/4 cup", household_measure="about 1/4 cup (__g)"
    ),

    # ── Vegetables ──
    FoodCategory.FRESH_VEGETABLES: RACCEntry(
        FoodCategory.FRESH_VEGETABLES, racc_g=85, label_statement="1 cup", household_measure="1 cup (__g)"
    ),
    FoodCategory.CANNED_VEGETABLES: RACCEntry(
        FoodCategory.CANNED_VEGETABLES, racc_g=125, label_statement="1/2 cup", household_measure="about 1/2 cup (__g)"
    ),

    # ── Meat & Protein ──
    FoodCategory.MEAT_POULTRY: RACCEntry(
        FoodCategory.MEAT_POULTRY, racc_g=85, label_statement="3 oz", household_measure="about 3 oz (__g)"
    ),
    FoodCategory.FISH_SEAFOOD: RACCEntry(
        FoodCategory.FISH_SEAFOOD, racc_g=85, label_statement="3 oz", household_measure="about 3 oz (__g)"
    ),
    FoodCategory.EGGS: RACCEntry(
        FoodCategory.EGGS, racc_g=50, label_statement="1 large egg", household_measure="1 large egg (__g)"
    ),
    FoodCategory.NUTS_SEEDS: RACCEntry(
        FoodCategory.NUTS_SEEDS, racc_g=30, label_statement="1 oz", household_measure="about 1 oz (__g)"
    ),
    FoodCategory.TOFU_MEAT_ALTERNATIVES: RACCEntry(
        FoodCategory.TOFU_MEAT_ALTERNATIVES, racc_g=85, label_statement="3 oz", household_measure="about 3 oz (__g)"
    ),

    # ── Grains ──
    FoodCategory.RICE_PASTA: RACCEntry(
        FoodCategory.RICE_PASTA, racc_g=140, label_statement="1 cup cooked", household_measure="about 1 cup (__g)"
    ),
    FoodCategory.BREAKFAST_CEREALS: RACCEntry(
        FoodCategory.BREAKFAST_CEREALS, racc_g=40, label_statement="1 cup", household_measure="about 1 cup (__g)"
    ),
    FoodCategory.OATMEAL: RACCEntry(
        FoodCategory.OATMEAL, racc_g=240, label_statement="1 cup cooked", household_measure="about 1 cup (__g)"
    ),

    # ── Fats ──
    FoodCategory.OILS: RACCEntry(
        FoodCategory.OILS, racc_g=14, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),
    FoodCategory.SALAD_DRESSINGS: RACCEntry(
        FoodCategory.SALAD_DRESSINGS, racc_g=30, label_statement="2 tbsp", household_measure="2 tbsp (__g)"
    ),
    FoodCategory.MAYONNAISE: RACCEntry(
        FoodCategory.MAYONNAISE, racc_g=14, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),
    FoodCategory.SPREADS: RACCEntry(
        FoodCategory.SPREADS, racc_g=14, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),

    # ── Condiments ──
    FoodCategory.CONDIMENTS: RACCEntry(
        FoodCategory.CONDIMENTS, racc_g=14, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),
    FoodCategory.SAUCES: RACCEntry(
        FoodCategory.SAUCES, racc_g=30, label_statement="2 tbsp", household_measure="2 tbsp (__g)"
    ),
    FoodCategory.GRAVIES: RACCEntry(
        FoodCategory.GRAVIES, racc_g=30, label_statement="2 tbsp", household_measure="2 tbsp (__g)"
    ),
    FoodCategory.JAMS_JELLIES: RACCEntry(
        FoodCategory.JAMS_JELLIES, racc_g=20, label_statement="1 tbsp", household_measure="1 tbsp (__g)"
    ),

    # ── Snacks ──
    FoodCategory.CHIPS_CRISPS: RACCEntry(
        FoodCategory.CHIPS_CRISPS, racc_g=30, label_statement="about __ chips", household_measure="about __ chips (__g)"
    ),
    FoodCategory.POPCORN: RACCEntry(
        FoodCategory.POPCORN, racc_g=30, label_statement="1 cup", household_measure="about 1 cup (__g)"
    ),
    FoodCategory.CANDY: RACCEntry(
        FoodCategory.CANDY, racc_g=40, label_statement="about __ pieces", household_measure="about __ pieces (__g)"
    ),
    FoodCategory.CHOCOLATE: RACCEntry(
        FoodCategory.CHOCOLATE, racc_g=40, label_statement="1 bar", household_measure="1 bar (__g)"
    ),
    FoodCategory.GRANOLA_BARS: RACCEntry(
        FoodCategory.GRANOLA_BARS, racc_g=40, label_statement="1 bar", household_measure="1 bar (__g)"
    ),

    # ── Soups ──
    FoodCategory.SOUP_READY_TO_EAT: RACCEntry(
        FoodCategory.SOUP_READY_TO_EAT, racc_g=245, label_statement="1 cup", household_measure="about 1 cup (__g)"
    ),
    FoodCategory.SOUP_CONDENSED: RACCEntry(
        FoodCategory.SOUP_CONDENSED, racc_g=120, label_statement="1/2 cup condensed", household_measure="about 1/2 cup (__g)"
    ),

    # ── Frozen ──
    FoodCategory.FROZEN_MEALS: RACCEntry(
        FoodCategory.FROZEN_MEALS, racc_g=270, label_statement="1 meal", household_measure="1 meal (__g)"
    ),
    FoodCategory.FROZEN_PIZZA: RACCEntry(
        FoodCategory.FROZEN_PIZZA, racc_g=135, label_statement="1 slice", household_measure="1 slice (__g)"
    ),
    FoodCategory.FROZEN_DESSERTS: RACCEntry(
        FoodCategory.FROZEN_DESSERTS, racc_g=85, label_statement="1 serving", household_measure="about 1/2 cup (__g)"
    ),

    # ── Baby ──
    FoodCategory.BABY_FOOD: RACCEntry(
        FoodCategory.BABY_FOOD, racc_g=60, label_statement="1 jar", household_measure="1 jar (__g)"
    ),

    # ── Beverage mixes ──
    FoodCategory.BEVERAGE_MIXES: RACCEntry(
        FoodCategory.BEVERAGE_MIXES, racc_g=20, label_statement="1 packet", household_measure="1 packet (__g)"
    ),
}


# ── FNDDS food code → FDA food category heuristics ────────────────────────────

# FNDDS food code ranges mapped to FDA categories
_FOOD_CODE_PREFIX_MAP: dict[str, FoodCategory] = {
    "11": FoodCategory.MILK,
    "12": FoodCategory.MILK,
    "13": FoodCategory.MILK,
    "14": FoodCategory.CHEESE,
    "21": FoodCategory.MEAT_POULTRY,
    "22": FoodCategory.MEAT_POULTRY,
    "23": FoodCategory.MEAT_POULTRY,
    "24": FoodCategory.MEAT_POULTRY,
    "25": FoodCategory.FISH_SEAFOOD,
    "26": FoodCategory.FISH_SEAFOOD,
    "27": FoodCategory.EGGS,
    "31": FoodCategory.FRESH_FRUIT,
    "32": FoodCategory.CANNED_FRUIT,
    "33": FoodCategory.DRIED_FRUIT,
    "34": FoodCategory.FRESH_VEGETABLES,
    "35": FoodCategory.CANNED_VEGETABLES,
    "41": FoodCategory.BAKERY_PRODUCTS,
    "42": FoodCategory.BAKERY_PRODUCTS,
    "43": FoodCategory.BAKERY_PRODUCTS,
    "44": FoodCategory.BAKERY_PRODUCTS,
    "51": FoodCategory.RICE_PASTA,
    "52": FoodCategory.RICE_PASTA,
    "53": FoodCategory.BREAKFAST_CEREALS,
    "54": FoodCategory.BREAKFAST_CEREALS,
    "55": FoodCategory.BREAKFAST_CEREALS,
    "56": FoodCategory.BREAKFAST_CEREALS,
    "57": FoodCategory.BAKERY_PRODUCTS,
    "58": FoodCategory.SOUP_READY_TO_EAT,
    "61": FoodCategory.FRESH_VEGETABLES,
    "62": FoodCategory.FRESH_VEGETABLES,
    "63": FoodCategory.FRESH_VEGETABLES,
    "64": FoodCategory.FRESH_VEGETABLES,
    "71": FoodCategory.CHIPS_CRISPS,
    "72": FoodCategory.CHIPS_CRISPS,
    "73": FoodCategory.CANDY,
    "74": FoodCategory.UNCATEGORIZED,
    "75": FoodCategory.SALAD_DRESSINGS,
    "76": FoodCategory.CONDIMENTS,
    "77": FoodCategory.SPREADS,
    "81": FoodCategory.BEVERAGES_CARBONATED,
    "82": FoodCategory.JUICE,
    "83": FoodCategory.BEVERAGES_CARBONATED,
    "84": FoodCategory.COFFEE_TEA,
    "85": FoodCategory.BEVERAGES_CARBONATED,
    "91": FoodCategory.FISH_SEAFOOD,
    "92": FoodCategory.FISH_SEAFOOD,
    "93": FoodCategory.UNCATEGORIZED,
}

# Keyword-based fallback for food name classification
_FOOD_NAME_KEYWORDS: list[tuple[re.Pattern, FoodCategory]] = [
    (re.compile(r"\b(bread|roll|bagel|toast|bun)\b", re.I), FoodCategory.BREADS_ROLLS),
    (re.compile(r"\b(cake|cookie|brownie|donut|doughnut|muffin|cupcake)\b", re.I), FoodCategory.CAKES_COOKIES),
    (re.compile(r"\b(cracker|pretzel|rice cake)\b", re.I), FoodCategory.CRACKERS),
    (re.compile(r"\b(pie|croissant|danish|turnover)\b", re.I), FoodCategory.PASTRIES),
    (re.compile(r"\b(milk|buttermilk|evaporated|condensed)\b", re.I), FoodCategory.MILK),
    (re.compile(r"\b(yogurt|yoghurt)\b", re.I), FoodCategory.YOGURT),
    (re.compile(r"\b(cheese|cheddar|mozzarella|swiss|provolone)\b", re.I), FoodCategory.CHEESE),
    (re.compile(r"\b(butter|margarine)\b", re.I), FoodCategory.BUTTER),
    (re.compile(r"\b(ice cream|gelato|sorbet|frozen yogurt)\b", re.I), FoodCategory.ICE_CREAM),
    (re.compile(r"\b(juice|nectar|fruit drink)\b", re.I), FoodCategory.JUICE),
    (re.compile(r"\b(soda|cola|ginger ale|seltzer|tonic|pop)\b", re.I), FoodCategory.BEVERAGES_CARBONATED),
    (re.compile(r"\b(coffee|tea|latte|cappuccino|espresso)\b", re.I), FoodCategory.COFFEE_TEA),
    (re.compile(r"\b(fruit|apple|banana|orange|grape|berry|berries)\b", re.I), FoodCategory.FRESH_FRUIT),
    (re.compile(r"\b(chicken|beef|pork|turkey|ham|bacon|sausage|meat)\b", re.I), FoodCategory.MEAT_POULTRY),
    (re.compile(r"\b(salmon|tuna|cod|shrimp|crab|lobster|fish)\b", re.I), FoodCategory.FISH_SEAFOOD),
    (re.compile(r"\b(egg|omelet|omelette)\b", re.I), FoodCategory.EGGS),
    (re.compile(r"\b(almond|walnut|peanut|cashew|nut|seed)\b", re.I), FoodCategory.NUTS_SEEDS),
    (re.compile(r"\b(cereal|granola)\b", re.I), FoodCategory.BREAKFAST_CEREALS),
    (re.compile(r"\b(oatmeal|porridge|oat)\b", re.I), FoodCategory.OATMEAL),
    (re.compile(r"\b(rice|pasta|spaghetti|noodle|macaroni)\b", re.I), FoodCategory.RICE_PASTA),
    (re.compile(r"\b(chip|fry|fries|crisp|tortilla chip|potato chip)\b", re.I), FoodCategory.CHIPS_CRISPS),
    (re.compile(r"\b(candy|chocolate|bonbon|toffee|caramel)\b", re.I), FoodCategory.CANDY),
    (re.compile(r"\b(soup|broth|stock|bisque)\b", re.I), FoodCategory.SOUP_READY_TO_EAT),
    (re.compile(r"\b(dressing|vinagrette|dip)\b", re.I), FoodCategory.SALAD_DRESSINGS),
    (re.compile(r"\b(ketchup|mustard|mayonnaise|relish|salsa|soy sauce|hot sauce)\b", re.I), FoodCategory.CONDIMENTS),
    (re.compile(r"\b(jam|jelly|preserve|marmalade|honey|syrup)\b", re.I), FoodCategory.JAMS_JELLIES),
    (re.compile(r"\b(pizza)\b", re.I), FoodCategory.FROZEN_PIZZA),
    (re.compile(r"\b(baby|infant|toddler)\b", re.I), FoodCategory.BABY_FOOD),
    (re.compile(r"\b(protein|energy|granola) bar\b", re.I), FoodCategory.GRANOLA_BARS),
]


# ── % Daily Value Reference ───────────────────────────────────────────────────

# Reference Daily Intake (RDI) values for vitamins and minerals
# Updated per FDA Nutrition Facts final rule (2016).
DAILY_VALUE_REFERENCES: dict[str, float] = {
    "Total Fat": 78,  # g
    "Saturated Fat": 20,  # g
    "Cholesterol": 300,  # mg
    "Sodium": 2300,  # mg
    "Total Carbohydrate": 275,  # g
    "Dietary Fiber": 28,  # g
    "Protein": 50,  # g
    "Vitamin D": 20,  # µg
    "Calcium": 1300,  # mg
    "Iron": 18,  # mg
    "Potassium": 4700,  # mg
    "Vitamin A": 900,  # µg
    "Vitamin C": 90,  # mg
    "Vitamin E": 15,  # mg
    "Vitamin K": 120,  # µg
    "Thiamin (Vitamin B1)": 1.2,  # mg
    "Riboflavin (Vitamin B2)": 1.3,  # mg
    "Niacin (Vitamin B3)": 16,  # mg
    "Vitamin B6": 1.7,  # mg
    "Vitamin B12": 2.4,  # µg
    "Folate": 400,  # µg
    "Magnesium": 420,  # mg
    "Zinc": 11,  # mg
    "Chloride": 2300,  # mg
    "Manganese": 2.3,  # mg
    "Selenium": 55,  # µg
    "Iodine": 150,  # µg
    "Phosphorus": 1250,  # mg
    "Molybdenum": 45,  # µg
    "Biotin": 30,  # µg
    "Pantothenic Acid": 5,  # mg
    "Added Sugars": 50,  # g
}

# Map common USDA nutrient names to DV reference names
NUTRIENT_TO_DV_KEY: dict[str, str] = {
    "Total lipid (fat)": "Total Fat",
    "Fatty acids, total saturated": "Saturated Fat",
    "Fatty acids, total trans": "Trans Fat",
    "Cholesterol": "Cholesterol",
    "Sodium, Na": "Sodium",
    "Carbohydrate, by difference": "Total Carbohydrate",
    "Fiber, total dietary": "Dietary Fiber",
    "Total Sugars": "Total Sugars",
    "Sugars, added": "Added Sugars",
    "Protein": "Protein",
    "Vitamin D (D2 + D3)": "Vitamin D",
    "Calcium, Ca": "Calcium",
    "Iron, Fe": "Iron",
    "Potassium, K": "Potassium",
}


# ── Nutrient Content Claims (21 CFR 101.13, 101.54-101.69) ────────────────────


@dataclass(frozen=True)
class ClaimThreshold:
    """Threshold for a nutrient content claim.

    - 'free': amount below this threshold
    - 'low': amount below this threshold
    - 'reduced': at least 25% less than reference
    - 'light/lean': at least 50% less or specific criteria
    - 'good_source': 10-19% of DV per RACC
    - 'excellent_source': 20%+ of DV per RACC
    """

    claim: str
    threshold_per_serving: float | None = None
    threshold_per_100g: float | None = None
    threshold_per_100g_solid: float | None = None
    threshold_per_100g_liquid: float | None = None
    unit: str = "g"


NUTRIENT_CONTENT_CLAIMS: dict[str, list[ClaimThreshold]] = {
    "fat": [
        ClaimThreshold("fat_free", threshold_per_serving=0.5, unit="g"),
        ClaimThreshold("low_fat", threshold_per_100g_solid=3.0, threshold_per_100g_liquid=1.5, unit="g"),
        ClaimThreshold("reduced_fat", unit="%"),
    ],
    "saturated_fat": [
        ClaimThreshold("saturated_fat_free", threshold_per_serving=0.5, unit="g"),
        ClaimThreshold("low_saturated_fat", threshold_per_100g_solid=1.0, threshold_per_serving=1.0, unit="g"),
    ],
    "cholesterol": [
        ClaimThreshold("cholesterol_free", threshold_per_serving=2, unit="mg"),
        ClaimThreshold("low_cholesterol", threshold_per_100g_solid=20, threshold_per_100g_liquid=10, unit="mg"),
    ],
    "sodium": [
        ClaimThreshold("sodium_free", threshold_per_serving=5, unit="mg"),
        ClaimThreshold("very_low_sodium", threshold_per_100g=35, unit="mg"),
        ClaimThreshold("low_sodium", threshold_per_100g=140, unit="mg"),
    ],
    "sugar": [
        ClaimThreshold("sugar_free", threshold_per_serving=0.5, unit="g"),
        ClaimThreshold("no_added_sugar", unit=""),  # no sugar-based ingredients
    ],
    "energy": [
        ClaimThreshold("calorie_free", threshold_per_serving=5, unit="kcal"),
        ClaimThreshold("low_calorie", threshold_per_100g=40, unit="kcal"),
    ],
    "fiber": [],  # Source claims handled by check_source_claims() via %DV
}

# ── Public API ────────────────────────────────────────────────────────────────


def get_racc(category: FoodCategory | str) -> RACCEntry | None:
    """Look up the RACC entry for a food category.

    Args:
        category: A FoodCategory enum value or string.

    Returns:
        RACCEntry if found, None otherwise.
    """
    if isinstance(category, str):
        try:
            category = FoodCategory(category)
        except ValueError:
            return None
    return RACC_TABLE.get(category)


def classify_food_code(food_code: str) -> FoodCategory:
    """Classify an FNDDS 8-digit food code into an FDA food category.

    Args:
        food_code: 8-digit FNDDS food code string.

    Returns:
        Best-guess FoodCategory, or UNCATEGORIZED.
    """
    if len(food_code) >= 2:
        prefix = food_code[:2]
        if prefix in _FOOD_CODE_PREFIX_MAP:
            return _FOOD_CODE_PREFIX_MAP[prefix]
    return FoodCategory.UNCATEGORIZED


def classify_food_name(food_name: str) -> FoodCategory | None:
    """Classify a food by its name using keyword matching.

    Args:
        food_name: Food description string.

    Returns:
        Best-guess FoodCategory, or None if no match.
    """
    for pattern, category in _FOOD_NAME_KEYWORDS:
        if pattern.search(food_name):
            return category
    return None


def determine_serving_size(
    food_code: str = "",
    food_name: str = "",
    fndds_serving_size_g: float | None = None,
) -> float:
    """Determine appropriate serving size for a food.

    Priority:
      1. FNDDS serving size (if available and reasonable).
      2. RACC lookup by food code.
      3. RACC lookup by food name keywords.
      4. Default 100g.

    Args:
        food_code: FNDDS food code (8-digit).
        food_name: Food description.
        fndds_serving_size_g: Serving size from FNDDS data.

    Returns:
        Serving size in grams.
    """
    # Priority 1: FNDDS serving size
    if fndds_serving_size_g is not None and 5 <= fndds_serving_size_g <= 500:
        return fndds_serving_size_g

    # Priority 2: RACC by food code
    if food_code:
        code_category = classify_food_code(food_code)
        racc = get_racc(code_category)
        if racc:
            if racc.racc_g > 0:
                return racc.racc_g
            if racc.racc_ml > 0:
                return racc.racc_ml

    # Priority 3: RACC by food name
    if food_name:
        name_category = classify_food_name(food_name)
        if name_category:
            racc = get_racc(name_category)
            if racc:
                if racc.racc_g > 0:
                    return racc.racc_g
                if racc.racc_ml > 0:
                    return racc.racc_ml

    return 100.0


def compute_daily_value_percent(
    nutrient_name: str,
    amount_per_serving: float,
) -> float | None:
    """Compute % Daily Value for a nutrient per serving.

    Args:
        nutrient_name: USDA standard nutrient name (e.g. 'Sodium, Na').
        amount_per_serving: Amount per serving in appropriate unit.

    Returns:
        %DV as a float, or None if the DV reference is unknown.
    """
    dv_key = NUTRIENT_TO_DV_KEY.get(nutrient_name, nutrient_name)
    dv = DAILY_VALUE_REFERENCES.get(dv_key)
    if dv is None or dv <= 0:
        return None
    return (amount_per_serving / dv) * 100.0


def check_nutrient_content_claim(
    claim_group: str,
    amount_per_serving: float,
    amount_per_100g: float,
    is_liquid: bool = False,
) -> list[str]:
    """Check which nutrient content claims apply.

    Args:
        claim_group: The nutrient group key (e.g. 'fat', 'sodium', 'sugar').
        amount_per_serving: Nutrient amount per serving.
        amount_per_100g: Nutrient amount per 100g.
        is_liquid: Whether the food is a liquid (affects certain thresholds).

    Returns:
        List of applicable claim labels.
    """
    results: list[str] = []
    thresholds = NUTRIENT_CONTENT_CLAIMS.get(claim_group, [])
    for th in thresholds:
        # Check per-serving threshold
        if th.threshold_per_serving is not None:
            if amount_per_serving < th.threshold_per_serving:
                results.append(th.claim)

        # Check per-100g threshold
        if th.threshold_per_100g is not None:
            if amount_per_100g < th.threshold_per_100g:
                results.append(th.claim)

        # Check solid/liquid-specific threshold
        if is_liquid and th.threshold_per_100g_liquid is not None:
            if amount_per_100g < th.threshold_per_100g_liquid:
                results.append(th.claim)
        if not is_liquid and th.threshold_per_100g_solid is not None:
            if amount_per_100g < th.threshold_per_100g_solid:
                results.append(th.claim)

    return results
